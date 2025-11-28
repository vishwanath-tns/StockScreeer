"""sma50_scanner.py

Compute per-date counts of symbols above/below sma_50 and upsert into sma50_counts.

Functions:
- scan_and_upsert(engine, workers=8, progress_cb=None, start=None, end=None)
- fetch_counts(engine, start=None, end=None) -> pandas.DataFrame
- plot_counts(engine, start=None, end=None, index_name='NIFTY 50') -> matplotlib.figure.Figure

Notes:
- Assumes table `moving_averages` has column `sma_50` and `nse_equity_bhavcopy_full` has `close_price` and `series='EQ'` rows.
- Output table name: `sma50_counts` with columns (trade_date DATE PRIMARY KEY, above_count INT, below_count INT, total_count INT, created_at TIMESTAMP)

"""
from __future__ import annotations
import concurrent.futures
from typing import Callable, Iterable, List, Optional
from sqlalchemy import text
import pandas as pd
import datetime


def _ensure_engine():
    # reuse the project's engine helper
    import reporting_adv_decl as rad
    return rad.engine()


def ensure_table(conn):
    ddl = """
    CREATE TABLE IF NOT EXISTS sma50_counts (
      trade_date DATE NOT NULL,
      above_count INT NULL,
            pct_above DOUBLE NULL,
      below_count INT NULL,
            na_count INT NULL,
      total_count INT NULL,
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (trade_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    conn.execute(text(ddl))


def _compute_for_date(conn, d: datetime.date) -> dict:
    # compute counts for single date using SQL join between BHAV and moving_averages
    # Force a common collation for symbol comparison to avoid "Illegal mix of collations" errors
    # Use a generally-available utf8mb4 collation; adjust if your server uses a different default.
    sql = text(
        "SELECT :d as trade_date, "
        "SUM(CASE WHEN b.close_price > m.sma_50 THEN 1 ELSE 0 END) AS above_count, "
        "SUM(CASE WHEN b.close_price < m.sma_50 THEN 1 ELSE 0 END) AS below_count, "
        "SUM(CASE WHEN m.sma_50 IS NULL OR b.close_price IS NULL THEN 1 ELSE 0 END) AS na_count, "
        "COUNT(*) AS total_count "
        "FROM nse_equity_bhavcopy_full b JOIN moving_averages m "
        "ON b.symbol COLLATE utf8mb4_unicode_ci = m.symbol COLLATE utf8mb4_unicode_ci "
        "AND b.trade_date = m.trade_date "
        "WHERE b.series = 'EQ' AND b.trade_date = :d"
    )
    r = conn.execute(sql, {"d": d.strftime('%Y-%m-%d')}).fetchone()
    if r is None:
        return {"trade_date": d, "above_count": 0, "below_count": 0, "na_count": 0, "total_count": 0, "pct_above": 0.0}
    above = int(r[1] or 0)
    below = int(r[2] or 0)
    na = int(r[3] or 0)
    total = int(r[4] or 0)
    pct = (above / total * 100.0) if total else 0.0
    return {"trade_date": r[0], "above_count": above, "below_count": below, "na_count": na, "total_count": total, "pct_above": float(pct)}


def _upsert_row(conn, row: dict):
    ins = text(
        "INSERT INTO sma50_counts (trade_date, above_count, pct_above, below_count, na_count, total_count) VALUES (:d, :a, :p, :b, :n, :t) "
        "ON DUPLICATE KEY UPDATE above_count = VALUES(above_count), pct_above = VALUES(pct_above), below_count = VALUES(below_count), na_count = VALUES(na_count), total_count = VALUES(total_count)"
    )
    conn.execute(ins, {"d": row["trade_date"].strftime('%Y-%m-%d') if isinstance(row["trade_date"], (datetime.date, datetime.datetime)) else row["trade_date"],
                       "a": row.get("above_count", 0),
                       "p": float(row.get("pct_above", 0.0)),
                       "b": row.get("below_count", 0),
                       "n": row.get("na_count", 0),
                       "t": row.get("total_count", 0)})


def scan_and_upsert(engine=None, workers: int = 8, progress_cb: Optional[Callable[[int,int,str], None]] = None, start: Optional[str] = None, end: Optional[str] = None):
    """Scan all trade dates present in `nse_equity_bhavcopy_full`, compute counts, and upsert into `sma50_counts`.

    progress_cb(current, total, message) - optional callback for progress updates.
    """
    if engine is None:
        engine = _ensure_engine()

    with engine.begin() as conn:
        ensure_table(conn)
        # fetch distinct trade dates from bhav table
        q = text("SELECT DISTINCT trade_date FROM nse_equity_bhavcopy_full ORDER BY trade_date")
        rows = conn.execute(q).scalars().all()
        dates = [pd.to_datetime(r).date() for r in rows]

    # filter by start/end if provided
    if start:
        sdt = pd.to_datetime(start).date()
        dates = [d for d in dates if d >= sdt]
    if end:
        edt = pd.to_datetime(end).date()
        dates = [d for d in dates if d <= edt]

    total = len(dates)
    if progress_cb:
        progress_cb(0, total, f"Starting scan ({total} dates)")

    # process in parallel; each worker creates its own connection
    completed = 0
    errors: List[str] = []

    def _worker(d: datetime.date):
        try:
            with engine.begin() as conn:
                row = _compute_for_date(conn, d)
                _upsert_row(conn, row)
            return (d, None)
        except Exception as e:
            return (d, str(e))

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futures = {ex.submit(_worker, d): d for d in dates}
        for fut in concurrent.futures.as_completed(futures):
            d = futures[fut]
            err = None
            try:
                res = fut.result()
                err = res[1]
            except Exception as e:
                err = str(e)
            completed += 1
            if err:
                errors.append(f"{d}: {err}")
                if progress_cb:
                    progress_cb(completed, total, f"{d} FAILED: {err}")
            else:
                if progress_cb:
                    progress_cb(completed, total, f"{d} done")

    if progress_cb:
        progress_cb(total, total, f"Finished. {total} dates processed, {len(errors)} errors")
    return errors


def fetch_counts(engine=None, start: Optional[str] = None, end: Optional[str] = None) -> pd.DataFrame:
    if engine is None:
        engine = _ensure_engine()
    with engine.connect() as conn:
        q = "SELECT trade_date, above_count, pct_above, below_count, na_count, total_count FROM sma50_counts"
        params = {}
        if start and end:
            q += " WHERE trade_date BETWEEN :a AND :b"
            params = {"a": start, "b": end}
        elif start:
            q += " WHERE trade_date >= :a"
            params = {"a": start}
        elif end:
            q += " WHERE trade_date <= :b"
            params = {"b": end}
        q += " ORDER BY trade_date"
        df = pd.read_sql(text(q), con=conn, params=params, parse_dates=["trade_date"]) if params else pd.read_sql(text(q), con=conn, parse_dates=["trade_date"])
    return df


def plot_counts(engine=None, start: Optional[str] = None, end: Optional[str] = None, index_name: str = 'NIFTY 50'):
    """Return a matplotlib Figure plotting index price on top and counts below.

    This helper returns a Figure object which the GUI can embed.
    """
    import matplotlib.pyplot as plt
    engine = engine or _ensure_engine()
    df_counts = fetch_counts(engine, start=start, end=end)
    if df_counts.empty:
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, 'No SMA50 counts data', ha='center', va='center')
        return fig

    # fetch index daily prices
    with engine.connect() as conn:
        # indices_daily uses column name `close` (see import_nifty_index.py). Use that column.
        q = text("SELECT trade_date, close FROM indices_daily WHERE index_name = :idx AND trade_date BETWEEN :a AND :b ORDER BY trade_date")
        a = df_counts['trade_date'].min().strftime('%Y-%m-%d')
        b = df_counts['trade_date'].max().strftime('%Y-%m-%d')
        idx_df = pd.read_sql(q, con=conn, params={"idx": index_name, "a": a, "b": b}, parse_dates=["trade_date"]) if True else pd.DataFrame()

    # merge/index align
    idx_df = idx_df.set_index('trade_date')
    df_counts2 = df_counts.set_index('trade_date')
    # reindex counts to index dates (or vice versa). We'll plot counts on the counts dates and index on its dates; to align, we'll inner join on dates
    merged = idx_df.join(df_counts2, how='inner')
    # create figure with 2 rows (index, counts)
    fig, (ax_idx, ax_counts) = plt.subplots(2, 1, figsize=(10, 6), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
    # `idx_df` has column 'close' per import_nifty_index.py
    ax_idx.plot(merged.index, merged['close'], color='black')
    ax_idx.set_ylabel(index_name)
    ax_idx.grid(True, linestyle='--', alpha=0.4)

    ax_counts.plot(merged.index, merged['above_count'], label='above 50 SMA', color='green')
    ax_counts.plot(merged.index, merged['below_count'], label='below 50 SMA', color='red')
    ax_counts.set_ylabel('Counts')
    # secondary axis for pct_above
    ax_pct = ax_counts.twinx()
    if 'pct_above' in merged.columns:
        ax_pct.plot(merged.index, merged['pct_above'], label='pct above 50 SMA', color='blue', linestyle='--')
        ax_pct.set_ylabel('Pct Above (%)')
        ax_pct.set_ylim(0, 100)
    # legend combining both axes
    lines, labels = ax_counts.get_legend_handles_labels()
    if 'pct_above' in merged.columns:
        l2, lab2 = ax_pct.get_legend_handles_labels()
        lines += l2
        labels += lab2
    ax_counts.legend(lines, labels, loc='upper left')
    ax_counts.grid(True, linestyle='--', alpha=0.4)
    # annotate NaN/mismatch count for the period
    try:
        total_na = int(merged['na_count'].sum()) if 'na_count' in merged.columns else 0
        ann = f"NaN/mismatch total: {total_na}"
        ax_idx.text(0.99, 0.01, ann, transform=ax_idx.transAxes, ha='right', va='bottom', fontsize=9, bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
    except Exception:
        pass
    fig.autofmt_xdate()
    return fig
