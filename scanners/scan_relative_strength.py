"""Compute Relative Strength of stocks vs an index and upsert to DB.

Relative Strength (RS) implemented here compares cumulative returns over a lookback window.
RS = (stock_return / index_return) where returns are (close_t / close_t0) - 1.
We store RS along with the underlying returns.

Usage examples:
    python scan_relative_strength.py --index "NIFTY 50" --as-of 2025-10-17 --lookback 90

The script will:
- load closes for the index and all symbols from `nse_equity_bhavcopy_full` for the date range
- compute stock_return and index_return over the lookback period ending at as-of date
- compute rs_value = (1 + stock_return) / (1 + index_return) - 1
- upsert into table `relative_strength` with PRIMARY KEY (symbol, index_name, trade_date, lookback_days)

"""
from __future__ import annotations

import os
import argparse
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

import pandas as pd
from sqlalchemy import text

# reuse existing engine helper from compute_moving_averages or other modules
# import direct local helper if present
try:
    from import_nifty_index import build_engine
except Exception:
    # fallback: try sync_bhav_gui's engine builder if exists
    try:
        from sync_bhav_gui import engine as build_engine_fallback
    except Exception:
        build_engine = None


REL_TABLE_SQL = '''
CREATE TABLE IF NOT EXISTS relative_strength (
    symbol VARCHAR(20) NOT NULL,
    index_name VARCHAR(64) NOT NULL,
    trade_date DATE NOT NULL,
    lookback_days INT NOT NULL,
    rs_value DOUBLE NULL,
    stock_return DOUBLE NULL,
    index_return DOUBLE NULL,
    PRIMARY KEY (symbol, index_name, trade_date, lookback_days)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
'''


def _ensure_engine():
    if 'build_engine' in globals() and callable(globals()['build_engine']):
        return globals()['build_engine']()
    # try fallback
    try:
        from import_nifty_index import build_engine as b2
        return b2()
    except Exception:
        raise RuntimeError('No engine builder available; ensure import_nifty_index.build_engine is importable')


def fetch_index_series(conn, index_name: str, start: str, end: str) -> pd.Series:
    q = text("SELECT trade_date, close FROM indices_daily WHERE index_name=:idx AND trade_date BETWEEN :a AND :b ORDER BY trade_date")
    rows = conn.execute(q, {"idx": index_name, "a": start, "b": end}).fetchall()
    if not rows:
        return pd.Series(dtype=float)
    df = pd.DataFrame(rows, columns=["trade_date", "close"])  # trade_date is date already
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
    df = df.set_index("trade_date").sort_index()
    return df["close"]


def fetch_stock_closes(conn, symbol: str, start: str, end: str) -> pd.Series:
    q = text("SELECT trade_date, close_price FROM nse_equity_bhavcopy_full WHERE symbol=:s AND series = 'EQ' AND trade_date BETWEEN :a AND :b ORDER BY trade_date")
    rows = conn.execute(q, {"s": symbol, "a": start, "b": end}).fetchall()
    if not rows:
        return pd.Series(dtype=float)
    df = pd.DataFrame(rows, columns=["trade_date", "close_price"])  # trade_date is date already
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
    df = df.set_index("trade_date").sort_index()
    return df["close_price"]


def compute_rs_for_symbol(conn, symbol: str, index_name: str, as_of: datetime.date, lookback_days: int) -> Optional[dict]:
    # date range
    end = as_of
    start = as_of - timedelta(days=lookback_days * 2)  # fetch extra in case of non-trading days

    idx_series = fetch_index_series(conn, index_name, start.isoformat(), end.isoformat())
    stock_series = fetch_stock_closes(conn, symbol, start.isoformat(), end.isoformat())

    if idx_series.empty or stock_series.empty:
        return None

    # align on nearest available dates: pick the last available date <= as_of
    try:
        idx_last_date = max(d for d in idx_series.index if d <= as_of)
        stock_last_date = max(d for d in stock_series.index if d <= as_of)
    except ValueError:
        return None

    # find the date roughly lookback_days ago in the series (closest <= target)
    def find_t0(series_index, as_of_date, lookback):
        # target date
        target = as_of_date - timedelta(days=lookback)
        candidates = [d for d in series_index if d <= target]
        if not candidates:
            # fallback to earliest available
            return min(series_index)
        return max(candidates)

    idx_t0 = find_t0(idx_series.index, as_of, lookback_days)
    stock_t0 = find_t0(stock_series.index, as_of, lookback_days)

    idx_close_t0 = idx_series.loc[idx_t0]
    idx_close_last = idx_series.loc[idx_last_date]
    stock_close_t0 = stock_series.loc[stock_t0]
    stock_close_last = stock_series.loc[stock_last_date]

    # returns
    idx_ret = (float(idx_close_last) / float(idx_close_t0)) - 1.0
    stock_ret = (float(stock_close_last) / float(stock_close_t0)) - 1.0

    rs_value = (1.0 + stock_ret) / (1.0 + idx_ret) - 1.0

    return {
        "symbol": symbol,
        "index_name": index_name,
        "trade_date": as_of,
        "lookback_days": lookback_days,
        "rs_value": rs_value,
        "stock_return": stock_ret,
        "index_return": idx_ret,
    }


def all_symbols(conn):
    rows = conn.execute(text("SELECT DISTINCT symbol FROM nse_equity_bhavcopy_full ORDER BY symbol")).fetchall()
    return [r[0] for r in rows]


def compute_relative_strength_bulk(conn, index_name: str, as_of: datetime.date, lookback_days: int, symbols: list[str] | None = None) -> pd.DataFrame:
    """Bulk compute RS for many symbols using fewer queries.

    Strategy:
    - Fetch index closes for date range into a Series.
    - Fetch all stock closes for symbols (or all symbols) into a DataFrame with columns [trade_date, symbol, close_price].
    - Pivot to a wide DataFrame (index=trade_date, columns=symbol).
    - For each symbol, find t0 and tlast close values and compute returns.
    - Return DataFrame with rows for symbols and columns: symbol, index_name, trade_date, lookback_days, rs_value, stock_return, index_return
    """
    end = as_of
    start = as_of - timedelta(days=lookback_days * 2)

    # index series
    idx_ser = fetch_index_series(conn, index_name, start.isoformat(), end.isoformat())
    if idx_ser.empty:
        return pd.DataFrame()

    # fetch stock closes in one query
    if symbols:
        # parameterize symbol list
        q = text("SELECT trade_date, symbol, close_price FROM nse_equity_bhavcopy_full WHERE symbol IN :syms AND series = 'EQ' AND trade_date BETWEEN :a AND :b ORDER BY trade_date")
        rows = conn.execute(q, {"syms": tuple(symbols), "a": start.isoformat(), "b": end.isoformat()}).fetchall()
    else:
        q = text("SELECT trade_date, symbol, close_price FROM nse_equity_bhavcopy_full WHERE series = 'EQ' AND trade_date BETWEEN :a AND :b ORDER BY trade_date")
        rows = conn.execute(q, {"a": start.isoformat(), "b": end.isoformat()}).fetchall()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=["trade_date", "symbol", "close_price"])
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date

    # remove duplicate (trade_date, symbol) pairs, keep last seen (SQL ordered by trade_date)
    df = df.sort_values(["trade_date", "symbol"]).drop_duplicates(subset=["trade_date", "symbol"], keep="last")

    # pivot
    pivot = df.pivot(index="trade_date", columns="symbol", values="close_price").sort_index()

    # helper to find last available <= as_of and t0 <= target
    def last_le(series_index, dt):
        cand = [d for d in series_index if d <= dt]
        return max(cand) if cand else None

    def t0_for(series_index, dt, lookback):
        target = dt - timedelta(days=lookback)
        cand = [d for d in series_index if d <= target]
        return max(cand) if cand else min(series_index)

    results = []
    # ensure index series has unique dates (take last if duplicates)
    if idx_ser.index.duplicated().any():
        idx_df = idx_ser.reset_index().rename(columns={0: 'close'}) if False else pd.DataFrame({'trade_date': idx_ser.index, 'close': idx_ser.values})
        idx_df = idx_df.sort_values('trade_date').drop_duplicates(subset=['trade_date'], keep='last')
        idx_ser = pd.Series(data=idx_df['close'].values, index=idx_df['trade_date'].values)

    idx_dates = list(idx_ser.index)
    idx_last_date = last_le(idx_dates, as_of)
    if not idx_last_date:
        return pd.DataFrame()
    idx_t0 = t0_for(idx_dates, as_of, lookback_days)
    idx_close_t0 = float(idx_ser.loc[idx_t0])
    idx_close_last = float(idx_ser.loc[idx_last_date])
    idx_ret = (idx_close_last / idx_close_t0) - 1.0

    for sym in (symbols or pivot.columns.tolist()):
        if sym not in pivot.columns:
            continue
        col = pivot[sym].dropna()
        if col.empty:
            continue
        stock_last_date = last_le(list(col.index), as_of)
        if not stock_last_date:
            continue
        stock_t0 = t0_for(list(col.index), as_of, lookback_days)
        stock_close_t0 = float(col.loc[stock_t0])
        stock_close_last = float(col.loc[stock_last_date])
        stock_ret = (stock_close_last / stock_close_t0) - 1.0
        rs_value = (1.0 + stock_ret) / (1.0 + idx_ret) - 1.0
        results.append({
            "symbol": sym,
            "index_name": index_name,
            "trade_date": as_of,
            "lookback_days": lookback_days,
            "rs_value": rs_value,
            "stock_return": stock_ret,
            "index_return": idx_ret,
        })

    return pd.DataFrame(results)


def upsert_results(engine, df: pd.DataFrame, table: str = "relative_strength") -> None:
    if df.empty:
        print('No rows to upsert')
        return
    with engine.begin() as conn:
        conn.execute(text(REL_TABLE_SQL))
        tmp = "tmp_relative_strength"
        conn.execute(text(f"DROP TEMPORARY TABLE IF EXISTS {tmp}"))
        conn.execute(text(f"CREATE TEMPORARY TABLE {tmp} LIKE {table}"))
        df.to_sql(name=tmp, con=conn, if_exists='append', index=False, method='multi', chunksize=1000)
        cols = list(df.columns)
        col_list = ", ".join([f"`{c}`" for c in cols])
        select_list = col_list
        update_cols = [c for c in cols if c not in ('symbol', 'index_name', 'trade_date', 'lookback_days')]
        update_list = ", ".join([f"`{c}`=VALUES(`{c}`)" for c in update_cols]) or 'trade_date=trade_date'
        insert_sql = f"INSERT INTO {table} ({col_list}) SELECT {select_list} FROM {tmp} ON DUPLICATE KEY UPDATE {update_list};"
        conn.execute(text(insert_sql))
        print(f"Upserted {len(df)} rows into {table}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--index', default='NIFTY 50', help='Index name as stored in indices_daily.index_name')
    p.add_argument('--as-of', required=True, help='As-of date YYYY-MM-DD')
    p.add_argument('--lookback', type=int, default=90, help='Lookback days')
    p.add_argument('--limit', type=int, default=0, help='Limit number of symbols processed (for testing)')
    args = p.parse_args()

    as_of = datetime.strptime(args.as_of, '%Y-%m-%d').date()
    lookback = args.lookback

    eng = _ensure_engine()
    # attempt bulk compute
    with eng.connect() as conn:
        syms = None
        if args.limit:
            syms = all_symbols(conn)[: args.limit]
        df = compute_relative_strength_bulk(conn, args.index, as_of, lookback, symbols=syms)

    if df.empty:
        print('No RS rows computed')
        return

    # normalize trade_date to date string
    df['trade_date'] = pd.to_datetime(df['trade_date']).dt.date
    upsert_results(eng, df)


def compute_relative_strength_preview(index_name: str, as_of: str, lookback: int, top_n: int = 20):
    """Return top N symbols by RS (descending) as a DataFrame (without upserting).

    Useful for a GUI preview.
    """
    as_of_d = datetime.strptime(as_of, '%Y-%m-%d').date()
    eng = _ensure_engine()
    with eng.connect() as conn:
        df = compute_relative_strength_bulk(conn, index_name, as_of_d, lookback, symbols=None)

    if df.empty:
        return pd.DataFrame()
    df = df.sort_values(by='rs_value', ascending=False)
    if top_n:
        return df.head(top_n)
    return df


if __name__ == '__main__':
    main()
