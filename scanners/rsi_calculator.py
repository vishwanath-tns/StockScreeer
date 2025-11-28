"""Compute RSI (Wilder) for symbols and upsert results to DB tables.

Provides run_rsi(engine, period=9, freqs=['daily','weekly','monthly'], workers=4, progress_cb=None, symbols=None, start=None, end=None)
which computes RSI per symbol in parallel and upserts into the tables:
 - nse_rsi_daily
 - nse_rsi_weekly
 - nse_rsi_monthly

The upsert uses a temporary table + INSERT ... ON DUPLICATE KEY UPDATE and deduplicates by (symbol, trade_date, period).
"""
from __future__ import annotations

import pandas as pd
import math
import multiprocessing
from typing import Callable, List, Optional
from sqlalchemy import text

try:
    # prefer existing engine builder if available
    from import_nifty_index import build_engine
except Exception:
    build_engine = None


DAILY_TABLE_SQL = '''
CREATE TABLE IF NOT EXISTS nse_rsi_daily (
    symbol VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    period INT NOT NULL,
    rsi DOUBLE NULL,
    PRIMARY KEY (symbol, trade_date, period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
'''

WEEKLY_TABLE_SQL = '''
CREATE TABLE IF NOT EXISTS nse_rsi_weekly (
    symbol VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    period INT NOT NULL,
    rsi DOUBLE NULL,
    PRIMARY KEY (symbol, trade_date, period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
'''

MONTHLY_TABLE_SQL = '''
CREATE TABLE IF NOT EXISTS nse_rsi_monthly (
    symbol VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    period INT NOT NULL,
    rsi DOUBLE NULL,
    PRIMARY KEY (symbol, trade_date, period)
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


def compute_rsi(series: pd.Series, period: int = 9) -> pd.Series:
    """Compute Wilder RSI using EWM smoothing (alpha=1/period).

    Returns a series aligned with the input index; NaN for initial values.
    """
    if series is None or series.empty:
        return pd.Series(dtype='float64')
    close = series.astype('float64')
    delta = close.diff()
    gain = delta.clip(lower=0.0).fillna(0.0)
    loss = -delta.clip(upper=0.0).fillna(0.0)

    # Wilder's smoothing: RMA which is EMA with alpha=1/period
    alpha = 1.0 / float(period)
    avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
    avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.replace([math.inf, -math.inf], pd.NA)
    return rsi


def fetch_all_closes(conn, start: Optional[str] = None, end: Optional[str] = None, symbols: Optional[List[str]] = None) -> pd.DataFrame:
    """Fetch trade_date,symbol,close_price from BHAV table for the optional range and symbols."""
    if symbols:
        q = text("SELECT trade_date, symbol, close_price FROM nse_equity_bhavcopy_full WHERE symbol IN :syms AND series = 'EQ' AND trade_date BETWEEN :a AND :b ORDER BY symbol, trade_date")
        rows = conn.execute(q, {"syms": tuple(symbols), "a": start, "b": end}).fetchall()
    else:
        if start and end:
            q = text("SELECT trade_date, symbol, close_price FROM nse_equity_bhavcopy_full WHERE series = 'EQ' AND trade_date BETWEEN :a AND :b ORDER BY symbol, trade_date")
            rows = conn.execute(q, {"a": start, "b": end}).fetchall()
        else:
            q = text("SELECT trade_date, symbol, close_price FROM nse_equity_bhavcopy_full WHERE series = 'EQ' ORDER BY symbol, trade_date")
            rows = conn.execute(q).fetchall()

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=["trade_date", "symbol", "close"])
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df = df[df['trade_date'].notna() & df['symbol'].notna()]
    # remove duplicate (trade_date,symbol) pairs keeping last
    df = df.sort_values(['symbol', 'trade_date']).drop_duplicates(subset=['symbol', 'trade_date'], keep='last')
    return df


def upsert_rsi(engine, df: pd.DataFrame, table: str):
    if df.empty:
        print('No RSI rows to upsert for', table)
        return
    with engine.begin() as conn:
        if table == 'nse_rsi_daily':
            conn.execute(text(DAILY_TABLE_SQL))
        elif table == 'nse_rsi_weekly':
            conn.execute(text(WEEKLY_TABLE_SQL))
        else:
            conn.execute(text(MONTHLY_TABLE_SQL))

        tmp = f"tmp_{table}"
        conn.execute(text(f"DROP TEMPORARY TABLE IF EXISTS {tmp}"))
        conn.execute(text(f"CREATE TEMPORARY TABLE {tmp} LIKE {table}"))

        # ensure dedupe
        if 'symbol' in df.columns and 'trade_date' in df.columns and 'period' in df.columns:
            df = df.sort_values(['symbol', 'trade_date', 'period']).drop_duplicates(subset=['symbol', 'trade_date', 'period'], keep='last')

        # write to temp table
        df.to_sql(name=tmp, con=conn, if_exists='append', index=False, method='multi', chunksize=1000)

        cols = list(df.columns)
        col_list = ", ".join([f"`{c}`" for c in cols])
        select_list = col_list
        update_cols = [c for c in cols if c not in ('symbol', 'trade_date', 'period')]
        update_list = ", ".join([f"`{c}`=VALUES(`{c}`)" for c in update_cols]) or 'period=period'
        insert_sql = f"INSERT INTO {table} ({col_list}) SELECT {select_list} FROM {tmp} ON DUPLICATE KEY UPDATE {update_list};"
        conn.execute(text(insert_sql))
        print(f"Upserted {len(df)} rows into {table}")


def _compute_symbol(sym, rows, freqs, period, cancel_token=None):
    """Top-level worker callable for parallel execution.
    rows: list of (trade_date, close)
    returns (symbol, out_rows)
    """
    out_rows = {f: [] for f in freqs}
    try:
        if cancel_token and cancel_token.get('cancel'):
            return sym, out_rows

        import pandas as _pd
        g = _pd.DataFrame(rows, columns=['trade_date', 'close'])
        g['trade_date'] = _pd.to_datetime(g['trade_date'])
        g = g.set_index('trade_date').sort_index()
        if g.empty:
            return sym, out_rows

        # daily
        if 'daily' in freqs:
            rsi_daily = compute_rsi(g['close'], period=period)
            for dt, val in rsi_daily.dropna().items():
                out_rows['daily'].append({'symbol': sym, 'trade_date': _pd.to_datetime(dt).date(), 'period': period, 'rsi': float(val)})

        # weekly
        if 'weekly' in freqs:
            weekly_close = g['close'].resample('W-FRI').last().dropna()
            if not weekly_close.empty:
                rsi_week = compute_rsi(weekly_close, period=period)
                for dt, val in rsi_week.dropna().items():
                    out_rows['weekly'].append({'symbol': sym, 'trade_date': _pd.to_datetime(dt).date(), 'period': period, 'rsi': float(val)})

        # monthly
        if 'monthly' in freqs:
            monthly_close = g['close'].resample('M').last().dropna()
            if not monthly_close.empty:
                rsi_mon = compute_rsi(monthly_close, period=period)
                for dt, val in rsi_mon.dropna().items():
                    out_rows['monthly'].append({'symbol': sym, 'trade_date': _pd.to_datetime(dt).date(), 'period': period, 'rsi': float(val)})

    except Exception:
        # swallow per-symbol exceptions; caller will log via progress_cb
        pass
    return sym, out_rows


def run_rsi(engine, period: int = 9, freqs: Optional[List[str]] = None, workers: int = 4, progress_cb: Optional[Callable] = None, symbols: Optional[List[str]] = None, start: Optional[str] = None, end: Optional[str] = None, limit: int = 0, cancel_token: Optional[dict] = None):
    """Compute RSI for all symbols and upsert per frequency.

    progress_cb(current:int, total:int, message:str) will be called with updates.
    """
    if freqs is None:
        freqs = ['daily', 'weekly', 'monthly']

    # fetch closes
    with engine.connect() as conn:
        df_all = fetch_all_closes(conn, start=start, end=end, symbols=symbols)

    if df_all.empty:
        if progress_cb:
            progress_cb(0, 0, 'No price rows found')
        return

    # optionally limit symbols for testing
    all_syms = sorted(df_all['symbol'].unique())
    if limit and limit > 0:
        all_syms = all_syms[:limit]

    total = len(all_syms)
    if progress_cb:
        progress_cb(0, total, f'Starting RSI compute for {total} symbols')

    results_by_freq = {f: [] for f in freqs}

    # prepare per-symbol rows to pass to worker processes
    symbol_rows = []
    for sym in all_syms:
        rows = df_all[df_all['symbol'] == sym][['trade_date', 'close']].itertuples(index=False, name=None)
        rows = list(rows)
        symbol_rows.append((sym, rows))

    from concurrent.futures import ProcessPoolExecutor, as_completed

    # prepare a cancel token (manager dict) if not provided
    mgr = None
    mgr_cancel = None
    if cancel_token is None:
        mgr = multiprocessing.Manager()
        mgr_cancel = mgr.dict()
        mgr_cancel['cancel'] = False
        cancel_token = mgr_cancel

    with ProcessPoolExecutor(max_workers=max(1, workers)) as ex:
        futures = {}
        for sym, rows in symbol_rows:
            futures[ex.submit(_compute_symbol, sym, rows, freqs, period, cancel_token)] = sym

        processed = 0
        for fut in as_completed(futures):
            sym = futures[fut]
            try:
                _, out_rows = fut.result()
                for f in freqs:
                    if out_rows.get(f):
                        results_by_freq[f].extend(out_rows[f])
            except Exception as e:
                if progress_cb:
                    progress_cb(processed, total, f'Error processing {sym}: {e}')
            processed += 1
            if progress_cb:
                progress_cb(processed, total, f'Processed {sym} ({processed}/{total})')

    # cleanup manager if we created it
    if mgr is not None:
        try:
            mgr.shutdown()
        except Exception:
            pass

    # convert results to DataFrames and upsert per freq
    for f in freqs:
        rows = results_by_freq.get(f, [])
        if not rows:
            if progress_cb:
                progress_cb(0, total, f'No rows for {f}')
            continue
        df_res = pd.DataFrame(rows)
        # ensure columns and dedupe
        df_res = df_res[['symbol', 'trade_date', 'period', 'rsi']]
        df_res = df_res.sort_values(['symbol', 'trade_date', 'period']).drop_duplicates(subset=['symbol', 'trade_date', 'period'], keep='last')
        tbl = 'nse_rsi_daily' if f == 'daily' else ('nse_rsi_weekly' if f == 'weekly' else 'nse_rsi_monthly')
        upsert_rsi(engine, df_res, tbl)
        if progress_cb:
            progress_cb(total, total, f'Upserted {len(df_res)} rows into {tbl}')


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--period', type=int, default=9)
    p.add_argument('--freqs', default='daily,weekly,monthly')
    p.add_argument('--workers', type=int, default=4)
    p.add_argument('--start')
    p.add_argument('--end')
    p.add_argument('--limit', type=int, default=0)
    args = p.parse_args()

    eng = _ensure_engine()

    def _print_progress(c, t, m):
        print(f"{c}/{t}: {m}")

    run_rsi(eng, period=args.period, freqs=[x.strip() for x in args.freqs.split(',') if x.strip()], workers=args.workers, progress_cb=_print_progress, start=args.start, end=args.end, limit=args.limit)
