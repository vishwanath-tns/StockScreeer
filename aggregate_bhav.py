"""Aggregate daily BHAV to weekly and monthly OHLCV and upsert to DB tables.

Creates/updates tables:
- nse_bhav_weekly (symbol, trade_date, open, high, low, close, volume)
- nse_bhav_monthly (symbol, trade_date, open, high, low, close, volume)

Usage examples:
    python aggregate_bhav.py --freq both --start 2024-01-01 --end 2025-10-18

Notes:
- weekly bars use week ending on Friday (W-FRI) to match market convention.
- volume is summed across the period (ttl_trd_qnty column from daily table).

"""
from __future__ import annotations

import argparse
from datetime import datetime, date, timedelta
from typing import Optional, List

import pandas as pd
from sqlalchemy import text

# try to reuse existing engine builder
try:
    from import_nifty_index import build_engine
except Exception:
    build_engine = None


WEEKLY_TABLE_SQL = '''
CREATE TABLE IF NOT EXISTS nse_bhav_weekly (
    symbol VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    open DOUBLE NULL,
    high DOUBLE NULL,
    low DOUBLE NULL,
    close DOUBLE NULL,
    volume BIGINT NULL,
    PRIMARY KEY (symbol, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
'''

MONTHLY_TABLE_SQL = '''
CREATE TABLE IF NOT EXISTS nse_bhav_monthly (
    symbol VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    open DOUBLE NULL,
    high DOUBLE NULL,
    low DOUBLE NULL,
    close DOUBLE NULL,
    volume BIGINT NULL,
    PRIMARY KEY (symbol, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
'''


def _ensure_engine():
    if build_engine:
        return build_engine()
    try:
        from import_nifty_index import build_engine as b2
        return b2()
    except Exception:
        raise RuntimeError('No engine builder available; ensure import_nifty_index.build_engine is importable')


def fetch_daily_range(conn, start: str, end: str, symbols: Optional[List[str]] = None) -> pd.DataFrame:
    """Fetch daily OHLCV for the date range. Returns DataFrame with columns: trade_date, symbol, open, high, low, close, volume"""
    if symbols:
        q = text("SELECT trade_date, symbol, open_price, high_price, low_price, close_price, ttl_trd_qnty FROM nse_equity_bhavcopy_full WHERE symbol IN :syms AND trade_date BETWEEN :a AND :b ORDER BY trade_date, symbol")
        rows = conn.execute(q, {"syms": tuple(symbols), "a": start, "b": end}).fetchall()
    else:
        q = text("SELECT trade_date, symbol, open_price, high_price, low_price, close_price, ttl_trd_qnty FROM nse_equity_bhavcopy_full WHERE trade_date BETWEEN :a AND :b ORDER BY trade_date, symbol")
        rows = conn.execute(q, {"a": start, "b": end}).fetchall()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=["trade_date", "symbol", "open", "high", "low", "close", "volume"])
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    # ensure numeric types
    for c in ('open','high','low','close'):
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0).astype('int64')

    # drop rows without symbol or trade_date
    df = df[df['trade_date'].notna() & df['symbol'].notna()]

    # remove duplicate (trade_date,symbol) pairs keeping last
    df = df.sort_values(['trade_date','symbol']).drop_duplicates(subset=['trade_date','symbol'], keep='last')

    return df


def aggregate_symbol(df_sym: pd.DataFrame, freq: str) -> pd.DataFrame:
    """Aggregate a single symbol df (with datetime index) to freq ('W-FRI' or 'M').

    df_sym: DataFrame with index=trade_date (datetime) and columns open, high, low, close, volume
    """
    if df_sym.empty:
        return pd.DataFrame()

    if freq.upper().startswith('W'):
        res = df_sym.resample('W-FRI').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
    else:
        # monthly
        res = df_sym.resample('M').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })

    # drop periods with no data (e.g., all NaN open/close)
    res = res.dropna(subset=['open','close'])
    return res


def aggregate_all(df_daily: pd.DataFrame, freq: str) -> pd.DataFrame:
    """Aggregate all symbols in the daily df to the frequency and return rows:
    columns: symbol, trade_date (period end), open, high, low, close, volume
    """
    if df_daily.empty:
        return pd.DataFrame()

    out_rows = []
    grouped = df_daily.groupby('symbol')
    for sym, g in grouped:
        g2 = g.set_index('trade_date').sort_index()
        agg = aggregate_symbol(g2[['open','high','low','close','volume']], freq)
        if agg.empty:
            continue
        agg = agg.reset_index()
        agg['symbol'] = sym
        # trade_date as date (period end)
        agg['trade_date'] = pd.to_datetime(agg['trade_date']).dt.date
        out_rows.append(agg[['symbol','trade_date','open','high','low','close','volume']])

    if not out_rows:
        return pd.DataFrame()
    return pd.concat(out_rows, ignore_index=True)


def upsert_aggregates(engine, df: pd.DataFrame, table: str):
    if df.empty:
        print('No rows to upsert for', table)
        return
    with engine.begin() as conn:
        if table == 'nse_bhav_weekly':
            conn.execute(text(WEEKLY_TABLE_SQL))
        else:
            conn.execute(text(MONTHLY_TABLE_SQL))

        tmp = f"tmp_{table}"
        conn.execute(text(f"DROP TEMPORARY TABLE IF EXISTS {tmp}"))
        conn.execute(text(f"CREATE TEMPORARY TABLE {tmp} LIKE {table}"))
        # Deduplicate dataframe on (symbol, trade_date) keeping last to avoid duplicate inserts
        if 'symbol' in df.columns and 'trade_date' in df.columns:
            df = df.sort_values(['symbol', 'trade_date']).drop_duplicates(subset=['symbol', 'trade_date'], keep='last')
        # Use pandas to_sql with the connection
        df.to_sql(name=tmp, con=conn, if_exists='append', index=False, method='multi', chunksize=1000)
        cols = list(df.columns)
        col_list = ", ".join([f"`{c}`" for c in cols])
        select_list = col_list
        update_cols = [c for c in cols if c not in ('symbol','trade_date')]
        update_list = ", ".join([f"`{c}`=VALUES(`{c}`)" for c in update_cols]) or 'trade_date=trade_date'
        insert_sql = f"INSERT INTO {table} ({col_list}) SELECT {select_list} FROM {tmp} ON DUPLICATE KEY UPDATE {update_list};"
        conn.execute(text(insert_sql))
        print(f"Upserted {len(df)} rows into {table}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--freq', choices=['weekly','monthly','both'], default='both')
    p.add_argument('--start', help='YYYY-MM-DD', required=True)
    p.add_argument('--end', help='YYYY-MM-DD', required=True)
    p.add_argument('--limit', type=int, default=0, help='Limit symbols for testing')
    args = p.parse_args()

    start = args.start
    end = args.end

    eng = _ensure_engine()
    with eng.connect() as conn:
        df_daily = fetch_daily_range(conn, start, end, symbols=None)

    if df_daily.empty:
        print('No daily rows found in range')
        return

    if args.limit and args.limit > 0:
        syms = sorted(df_daily['symbol'].unique())[:args.limit]
        df_daily = df_daily[df_daily['symbol'].isin(syms)]

    if args.freq in ('weekly','both'):
        print('Aggregating weekly...')
        df_week = aggregate_all(df_daily, 'W')
        upsert_aggregates(eng, df_week, 'nse_bhav_weekly')

    if args.freq in ('monthly','both'):
        print('Aggregating monthly...')
        df_month = aggregate_all(df_daily, 'M')
        upsert_aggregates(eng, df_month, 'nse_bhav_monthly')


def run_aggregate(engine, start: str, end: str, freq: str = 'both', progress_cb=None, limit: int = 0):
    """Programmatic API to run aggregation with progress callbacks.

    progress_cb: optional callable(current:int, total:int, message:str) invoked during processing.
    """
    # fetch daily rows
    with engine.connect() as conn:
        df_daily = fetch_daily_range(conn, start, end, symbols=None)

    if df_daily.empty:
        if progress_cb:
            progress_cb(0, 0, 'No daily rows found in range')
        return

    if limit and limit > 0:
        syms = sorted(df_daily['symbol'].unique())[:limit]
        df_daily = df_daily[df_daily['symbol'].isin(syms)]

    symbols = sorted(df_daily['symbol'].unique())
    total = len(symbols)

    if freq in ('weekly', 'both'):
        if progress_cb:
            progress_cb(0, total, 'Starting weekly aggregation')
        out_rows = []
        for i, sym in enumerate(symbols, start=1):
            g = df_daily[df_daily['symbol'] == sym].set_index('trade_date').sort_index()
            agg = aggregate_symbol(g[['open','high','low','close','volume']], 'W')
            if not agg.empty:
                agg = agg.reset_index()
                agg['symbol'] = sym
                agg['trade_date'] = pd.to_datetime(agg['trade_date']).dt.date
                out_rows.append(agg[['symbol','trade_date','open','high','low','close','volume']])
            if progress_cb:
                progress_cb(i, total, f'Weekly: processed {sym} ({i}/{total})')
        if out_rows:
            df_week = pd.concat(out_rows, ignore_index=True)
        else:
            df_week = pd.DataFrame()
        # dedupe before upsert
        if not df_week.empty:
            df_week = df_week.sort_values(['symbol','trade_date']).drop_duplicates(subset=['symbol','trade_date'], keep='last')
        upsert_aggregates(engine, df_week, 'nse_bhav_weekly')
        if progress_cb:
            progress_cb(total, total, f'Weekly aggregation complete: {len(df_week)} rows')

    if freq in ('monthly', 'both'):
        if progress_cb:
            progress_cb(0, total, 'Starting monthly aggregation')
        out_rows = []
        for i, sym in enumerate(symbols, start=1):
            g = df_daily[df_daily['symbol'] == sym].set_index('trade_date').sort_index()
            agg = aggregate_symbol(g[['open','high','low','close','volume']], 'M')
            if not agg.empty:
                agg = agg.reset_index()
                agg['symbol'] = sym
                agg['trade_date'] = pd.to_datetime(agg['trade_date']).dt.date
                out_rows.append(agg[['symbol','trade_date','open','high','low','close','volume']])
            if progress_cb:
                progress_cb(i, total, f'Monthly: processed {sym} ({i}/{total})')
        if out_rows:
            df_month = pd.concat(out_rows, ignore_index=True)
        else:
            df_month = pd.DataFrame()
        if not df_month.empty:
            df_month = df_month.sort_values(['symbol','trade_date']).drop_duplicates(subset=['symbol','trade_date'], keep='last')
        upsert_aggregates(engine, df_month, 'nse_bhav_monthly')
        if progress_cb:
            progress_cb(total, total, f'Monthly aggregation complete: {len(df_month)} rows')


if __name__ == '__main__':
    main()
