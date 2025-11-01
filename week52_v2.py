"""Simpler, robust 52-week counts pipeline.

Functions:
- compute_and_upsert_counts(engine_or_conn, as_of=None, lookback_days=365)
- backfill_counts(engine_or_conn, lookback_days=365, progress_cb=None, parallel_workers=4)

This module reads BHAV table `nse_equity_bhavcopy_full` (series='EQ') and writes into
`daily_52w_counts` table (dt DATE PRIMARY KEY, count_high INT, count_low INT).

The implementation prefers pandas for clarity and opens fresh connections for per-date writes.
"""
from __future__ import annotations
import datetime
import pandas as pd
from sqlalchemy import text
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


def _ensure_table(conn):
    conn.execute(text(
        """
        CREATE TABLE IF NOT EXISTS daily_52w_counts (
            dt DATE PRIMARY KEY,
            count_high INT DEFAULT 0,
            count_low INT DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;
        """
    ))


def compute_counts_for_date(conn, as_of: datetime.date | None = None, lookback_days: int = 365) -> dict:
    """Compute 52-week counts for a single date using the provided connection.
    Returns dict with date, count_high, count_low
    """
    if as_of is None:
        r = conn.execute(text("SELECT MAX(trade_date) FROM nse_equity_bhavcopy_full WHERE series='EQ'")).scalar()
        if isinstance(r, datetime.datetime):
            as_of = r.date()
        else:
            as_of = r
    start = as_of - datetime.timedelta(days=lookback_days)

    # read symbol,min,max, and last close on as_of
    q = text(
        "SELECT symbol, trade_date, close_price FROM nse_equity_bhavcopy_full "
        "WHERE series='EQ' AND trade_date BETWEEN :a AND :b"
    )
    df = pd.read_sql(q, con=conn, params={"a": start, "b": as_of})
    if df.empty:
        return {"date": as_of, "count_high": 0, "count_low": 0}

    # ensure types
    df['close_price'] = pd.to_numeric(df['close_price'], errors='coerce')
    # group
    g = df.groupby('symbol')
    low52 = g['close_price'].min()
    high52 = g['close_price'].max()
    # last close on as_of per symbol
    last_df = df[df['trade_date'] == pd.to_datetime(as_of)]
    last_close = last_df.set_index('symbol')['close_price']

    # align indices
    sym_index = low52.index.union(high52.index).union(last_close.index)
    low52 = low52.reindex(sym_index)
    high52 = high52.reindex(sym_index)
    last_close = last_close.reindex(sym_index)

    # compute booleans: new high/low on as_of
    is_high = last_close >= high52
    is_low = last_close <= low52
    ch = int(is_high.sum())
    cl = int(is_low.sum())
    return {"date": as_of, "count_high": ch, "count_low": cl}


def compute_and_upsert_counts(engine_or_conn, as_of: datetime.date | None = None, lookback_days: int = 365):
    """Compute counts for as_of and upsert into daily_52w_counts. Accepts Engine or Connection.
    Returns the inserted dict.
    """
    # accept either engine or connection
    engine = getattr(engine_or_conn, 'engine', None) or engine_or_conn
    with engine.connect() as conn:
        # compute with a reader connection (same conn is fine since we don't use begin yet)
        result = compute_counts_for_date(conn, as_of=as_of, lookback_days=lookback_days)

    # ensure table exists and upsert using a fresh connection
    with engine.connect() as conn:
        _ensure_table(conn)
        params = {"d": result['date'], "ch": int(result['count_high']), "cl": int(result['count_low'])}
        upsert_q = text(
            "INSERT INTO daily_52w_counts (dt, count_high, count_low) VALUES (:d, :ch, :cl) "
            "ON DUPLICATE KEY UPDATE count_high = :ch, count_low = :cl"
        )
        try:
            # avoid nested transaction: if this Connection already has an active
            # transaction (possible if caller passed in a Connection), detect and
            # execute without calling begin(). Otherwise start a transaction and commit.
            in_tx = False
            try:
                in_tx = getattr(conn, 'in_transaction', lambda: False)()
            except Exception:
                in_tx = False

            if in_tx:
                conn.execute(upsert_q, params)
            else:
                with conn.begin():
                    conn.execute(upsert_q, params)
        except Exception:
            logger.exception("Upsert failed for %s", result['date'])
            raise
    return result


def backfill_counts(engine_or_conn, lookback_days: int = 365, progress_cb=None, parallel_workers: int = 4):
    """Backfill counts for all available BHAV dates. Uses ThreadPoolExecutor with per-date fresh connections.
    Returns summary dict.
    """
    engine = getattr(engine_or_conn, 'engine', None) or engine_or_conn
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT DISTINCT trade_date FROM nse_equity_bhavcopy_full WHERE series='EQ' ORDER BY trade_date ASC")).fetchall()
    dates = [r[0] for r in rows]
    total = len(dates)
    attempted = succeeded = failed = 0

    # ensure table exists
    with engine.connect() as conn:
        _ensure_table(conn)

    def _task(as_of):
        try:
            with engine.connect() as conn:
                res = compute_counts_for_date(conn, as_of=as_of, lookback_days=lookback_days)
            # upsert for this date
            with engine.connect() as conn:
                params = {"d": res['date'], "ch": int(res['count_high']), "cl": int(res['count_low'])}
                upsert_q = text(
                    "INSERT INTO daily_52w_counts (dt, count_high, count_low) VALUES (:d, :ch, :cl) "
                    "ON DUPLICATE KEY UPDATE count_high = :ch, count_low = :cl"
                )
                with conn.begin():
                    conn.execute(upsert_q, params)
            return (as_of, True, None)
        except Exception as e:
            logger.exception("Backfill task error for %s", as_of)
            return (as_of, False, e)

    if parallel_workers and parallel_workers > 1:
        with ThreadPoolExecutor(max_workers=parallel_workers) as ex:
            futures = {ex.submit(_task, d): d for d in dates}
            for fut in as_completed(futures):
                attempted += 1
                d = futures[fut]
                try:
                    as_of, ok, err = fut.result()
                    if ok:
                        succeeded += 1
                    else:
                        failed += 1
                except Exception as e:
                    failed += 1
                if progress_cb:
                    try:
                        progress_cb(attempted, total)
                    except Exception:
                        pass
    else:
        for d in dates:
            attempted += 1
            ok = False
            try:
                r = _task(d)
                ok = r[1]
                if ok:
                    succeeded += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
            if progress_cb:
                try:
                    progress_cb(attempted, total)
                except Exception:
                    pass

    return {"attempted": attempted, "succeeded": succeeded, "failed": failed}
