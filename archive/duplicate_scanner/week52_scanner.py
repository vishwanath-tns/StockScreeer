"""week52_scanner.py

Scans for stocks relative to their 52-week low/high and manages daily counts.

Functions:
- scan_52week_thresholds(conn, as_of, pct_above_high=0.30, pct_above_low=0.30, limit=0)
    returns DataFrame with columns: symbol, date, close, low52, high52, pct_above_high, pct_above_low

- ensure_52week_counts_table(conn)
    creates table `daily_52w_counts` with columns date, count_high, count_low

- upsert_daily_52w_counts(conn, as_of)
    computes counts of symbols hitting 52-week high/low on as_of and upserts row

"""
from __future__ import annotations
import datetime
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from sqlalchemy import text
import logging
import traceback
import os
import sys

# module logger for diagnostics; do not configure root handlers here
logger = logging.getLogger(__name__)


# If the environment variable WEEK52_DEBUG=1 is set, configure console logging
def enable_console_debug():
    """Configure logging to print DEBUG logs to stdout for debugging runs."""
    root = logging.getLogger()
    # Avoid adding duplicate handlers
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        h = logging.StreamHandler(sys.stdout)
        h.setLevel(logging.DEBUG)
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        h.setFormatter(fmt)
        root.addHandler(h)
    root.setLevel(logging.DEBUG)
    logger.debug("Console debug logging enabled for week52_scanner")


if os.environ.get('WEEK52_DEBUG') == '1':
    enable_console_debug()


def scan_52week_thresholds(conn, as_of: datetime.date | None = None, pct_above_high: float = 0.30, pct_above_low: float = 0.30, limit: int = 0) -> pd.DataFrame:
    if as_of is None:
        # consider only EQ series rows when deriving the latest trade date
        q = text("SELECT MAX(trade_date) FROM nse_equity_bhavcopy_full WHERE series='EQ'")
        r = conn.execute(q).scalar()
        if isinstance(r, datetime.datetime):
            as_of = r.date()
        else:
            as_of = r
    # compute 52-week window
    start = as_of - datetime.timedelta(days=365)
    q = text(
        "SELECT symbol, MIN(close_price) as low52, MAX(close_price) as high52, "
        "(SELECT close_price FROM nse_equity_bhavcopy_full b2 WHERE b2.symbol = t.symbol AND b2.series='EQ' AND b2.trade_date <= :d ORDER BY b2.trade_date DESC LIMIT 1) AS close "
        "FROM nse_equity_bhavcopy_full t WHERE t.series='EQ' AND t.trade_date BETWEEN :a AND :b GROUP BY symbol"
    )
    df = pd.read_sql(q, con=conn, params={"a": start, "b": as_of, "d": as_of})
    if df.empty:
        return df
    df['pct_above_low'] = (df['close'] - df['low52']) / df['low52']
    df['pct_above_high'] = (df['close'] - df['high52']) / df['high52']
    df['date'] = pd.to_datetime(as_of)
    # filter
    res_high = df[df['pct_above_high'] >= pct_above_high]
    res_low = df[df['pct_above_low'] >= pct_above_low]
    res = pd.concat([res_high, res_low]).drop_duplicates('symbol').reset_index(drop=True)
    if limit and limit > 0:
        res = res.head(limit)
    return res


def ensure_52week_counts_table(conn):
    # create table if not exists
    try:
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
        logger.debug("ensure_52week_counts_table: ensured table daily_52w_counts exists")
        print("[week52] ensure_52week_counts_table: ensured table daily_52w_counts exists")
    except Exception as e:
        # log and re-raise with context
        print(f"[week52] ERROR ensuring daily_52w_counts table: {e}")
        print(traceback.format_exc())
        logger.error("Error ensuring daily_52w_counts table: %s", e)
        logger.error(traceback.format_exc())
        raise


def upsert_daily_52w_counts(conn, as_of: Optional[datetime.date] = None, lookback_days: int = 365) -> dict:
    if as_of is None:
        # consider only EQ series rows when deriving the latest trade date
        q = text("SELECT MAX(trade_date) FROM nse_equity_bhavcopy_full WHERE series='EQ'")
        r = conn.execute(q).scalar()
        if isinstance(r, datetime.datetime):
            as_of = r.date()
        else:
            as_of = r
    start = as_of - datetime.timedelta(days=lookback_days)
    # compute counts
    q_counts = text(
        "SELECT SUM(CASE WHEN close_price >= (SELECT MAX(close_price) FROM nse_equity_bhavcopy_full x WHERE x.symbol=t.symbol AND x.trade_date BETWEEN :a AND :b) THEN 1 ELSE 0 END) as count_high, "
        "SUM(CASE WHEN close_price >= 1.30*(SELECT MIN(close_price) FROM nse_equity_bhavcopy_full x WHERE x.symbol=t.symbol AND x.trade_date BETWEEN :a AND :b) THEN 1 ELSE 0 END) as count_low "
        "FROM (SELECT DISTINCT symbol FROM nse_equity_bhavcopy_full WHERE series='EQ') t"
    )
    # The above SQL is a bit heavy; compute in pandas for clarity
    q = text(
        "SELECT symbol, MIN(close_price) as low52, MAX(close_price) as high52, "
        "(SELECT close_price FROM nse_equity_bhavcopy_full b2 WHERE b2.symbol = t.symbol AND b2.series='EQ' AND b2.trade_date <= :d ORDER BY b2.trade_date DESC LIMIT 1) AS close "
        "FROM nse_equity_bhavcopy_full t WHERE t.series='EQ' AND t.trade_date BETWEEN :a AND :b GROUP BY symbol"
    )
    # Use a fresh connection for the read so we don't accidentally start a transaction
    engine = getattr(conn, 'engine', None) or conn
    with engine.connect() as reader_conn:
        df = pd.read_sql(q, con=reader_conn, params={"a": start, "b": as_of, "d": as_of})
    print(f"[week52] Read {len(df)} symbols for as_of={as_of} start={start}")
    logger.debug("Read DataFrame shape: %s", getattr(df, 'shape', None))
    if df.empty:
        ch = 0
        cl = 0
    else:
        ch = int((df['close'] >= df['high52']).sum())
        cl = int((df['close'] >= df['low52'] * 1.30).sum())
    print(f"[week52] Computed counts for {as_of}: count_high={ch}, count_low={cl}")
    # ensure table exists
    ensure_52week_counts_table(conn)
    # upsert
    upsert_q = text(
        "INSERT INTO daily_52w_counts (dt, count_high, count_low) VALUES (:d, :ch, :cl) "
        "ON DUPLICATE KEY UPDATE count_high = :ch, count_low = :cl"
    )
    # perform upsert inside a transaction to ensure commit
    params = {"d": as_of, "ch": ch, "cl": cl}
    logger.debug("upsert_daily_52w_counts: prepared upsert for date=%s params=%s", as_of, params)
    print(f"[week52] Prepared upsert for {as_of} -> {params}")
    try:
        # If the provided connection already has an active transaction (e.g. began by caller
        # or via an earlier statement's autobegin), avoid calling begin() again. Use
        # conn.in_transaction() to detect this and execute accordingly.
        in_tx = False
        try:
            in_tx = getattr(conn, 'in_transaction', lambda: False)()
        except Exception:
            # older SQLAlchemy or unexpected object; default to False
            in_tx = False

        if in_tx:
            logger.debug("upsert_daily_52w_counts: connection already in transaction, executing upsert without begin")
            print(f"[week52] Executing upsert within existing transaction for {as_of}")
            conn.execute(upsert_q, params)
            print(f"[week52] Executed upsert within existing transaction for {as_of} (high={ch} low={cl})")
            logger.info("upsert_daily_52w_counts: executed upsert within existing transaction for %s (high=%s low=%s)", as_of, ch, cl)
        else:
            print(f"[week52] Beginning transaction to upsert counts for {as_of}")
            with conn.begin():
                logger.debug("upsert_daily_52w_counts: executing upsert SQL: %s", str(upsert_q))
                conn.execute(upsert_q, params)
            print(f"[week52] Upsert committed for {as_of} (high={ch} low={cl})")
            logger.info("upsert_daily_52w_counts: upsert committed for %s (high=%s low=%s)", as_of, ch, cl)
    except Exception as e:
        # log full context for debugging: SQL, params and stack
        try:
            print(f"[week52] ERROR: Failed to upsert daily_52w_counts for date={as_of} params={params}")
            print(traceback.format_exc())
            logger.error("Failed to upsert daily_52w_counts for date=%s with params=%s", as_of, params)
            logger.error(traceback.format_exc())
        except Exception:
            # ensure we don't hide the original exception during logging
            pass
        # re-raise so callers can handle/log as needed
        raise
    return {"date": as_of, "count_high": ch, "count_low": cl}


def backfill_daily_52w_counts_range(conn, lookback_days: int = 365, progress_cb=None, parallel_workers: Optional[int] = None) -> dict:
    """Backfill daily_52w_counts for every trade_date present in BHAV.

    For each trade_date `d` the routine calls upsert_daily_52w_counts(conn, d, lookback_days=lookback_days).
    This means we always attempt a count for every date and let the per-symbol MIN/MAX compute over
    whatever history exists for that symbol (so newly-listed symbols will be handled with their
    available data).

    Returns a summary dict: {"attempted": n, "succeeded": s, "failed": f}
    """
    # Determine engine from provided argument. Accept either an Engine or a Connection.
    engine = None
    try:
        # Connection has .engine attribute
        engine = getattr(conn, 'engine', None) or conn
    except Exception:
        engine = conn

    # read all distinct dates (ascending) using a fresh connection so we don't hold
    # an open transaction on the caller-provided connection.
    with engine.connect() as reader_conn:
        rows = reader_conn.execute(text("SELECT DISTINCT trade_date FROM nse_equity_bhavcopy_full WHERE series='EQ' ORDER BY trade_date ASC")).fetchall()
    dates = [r[0] for r in rows]
    total = len(dates)
    if total == 0:
        logger.info("No trade dates found in BHAV table; nothing to backfill")
        return {"attempted": 0, "succeeded": 0, "failed": 0}

    attempted = succeeded = failed = 0

    # Ensure counts table exists once before starting many connections
    try:
        with engine.connect() as c:
            ensure_52week_counts_table(c)
    except Exception:
        logger.exception('Failed to ensure daily_52w_counts table exists')

    # Helper run for a single date that opens its own connection
    def _process_date(d):
        try:
            print(f"[week52] Worker starting upsert for {d}")
            logger.debug("Worker starting upsert for %s", d)
            with engine.connect() as up_conn:
                res = upsert_daily_52w_counts(up_conn, d, lookback_days=lookback_days)
                # verify row exists after upsert
                try:
                    r = up_conn.execute(text("SELECT count_high, count_low FROM daily_52w_counts WHERE dt = :d"), {"d": d}).fetchone()
                    print(f"[week52] Verify upsert for {d} -> {r}")
                    logger.debug("Verify upsert for %s -> %s", d, r)
                except Exception:
                    print(f"[week52] Verify read failed for {d}")
                    logger.exception("Verify read failed for %s", d)
            print(f"[week52] Worker finished upsert for {d}")
            return (d, True, None)
        except Exception as e:
            print(f"[week52] Worker error for {d}: {e}")
            logger.exception("Worker error for %s", d)
            return (d, False, e)

    # Default: single-threaded loop (preserves original behaviour)
    if total == 0:
        return {"attempted": 0, "succeeded": 0, "failed": 0}

    # Determine degree of parallelism. Caller may pass explicit parallel_workers. If
    # not provided, fall back to module attribute _parallel_workers (default 4).
    if parallel_workers is None:
        parallel_workers = getattr(backfill_daily_52w_counts_range, '_parallel_workers', 4)
    if parallel_workers and parallel_workers > 1:
        logger.info("Running backfill in parallel with %d workers", parallel_workers)
        futures = []
        with ThreadPoolExecutor(max_workers=parallel_workers) as ex:
            for d in dates:
                futures.append(ex.submit(_process_date, d))

            for fut in as_completed(futures):
                attempted += 1
                try:
                    d, ok, err = fut.result()
                    if ok:
                        succeeded += 1
                    else:
                        failed += 1
                        logger.error("Backfill failed for %s: %s", d, err)
                except Exception as e:
                    failed += 1
                    logger.exception("Unexpected error processing future: %s", e)

                if progress_cb:
                    try:
                        progress_cb(attempted, total)
                    except Exception:
                        pass
    else:
        # single-threaded
        for idx, d in enumerate(dates, start=1):
            attempted += 1
            try:
                logger.debug("Backfilling counts for %s (%d/%d) using lookback_days=%d", d, idx, total, lookback_days)
                with engine.connect() as up_conn:
                    _ = upsert_daily_52w_counts(up_conn, d, lookback_days=lookback_days)
                succeeded += 1
            except Exception:
                failed += 1
                logger.exception("Failed to upsert counts for %s", d)
            if progress_cb:
                try:
                    progress_cb(attempted, total)
                except Exception:
                    pass

    return {"attempted": attempted, "succeeded": succeeded, "failed": failed}
