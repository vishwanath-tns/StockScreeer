"""liquidity_baseline_and_scan.py

Compute and store baseline average traded quantity and turnover per symbol, and
scan recent periods for symbols trading many times the baseline.

Features:
- Creates/updates table `symbol_liq_stats` with baseline averages.
- Scans a recent window and reports symbols where recent avg qty/turnover exceed
  baseline by configurable multipliers.

Usage examples:
  # compute baseline for Jan-Jun 2025
  python liquidity_baseline_and_scan.py --baseline-start 2025-01-01 --baseline-end 2025-06-30 --update-baseline

  # scan Aug 1 - Oct 10 against stored baseline and write CSV of spikes
  python liquidity_baseline_and_scan.py --recent-start 2025-08-01 --recent-end 2025-10-10 --qty-mult 3 --turnover-mult 4 --out spikes.csv

"""
from datetime import datetime, date
import argparse
import csv
import os
from typing import List, Dict, Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
import pandas as pd

load_dotenv()

HOST = os.getenv("MYSQL_HOST", "localhost")
PORT = int(os.getenv("MYSQL_PORT", "3306"))
DB = os.getenv("MYSQL_DB", "marketdata")
USER = os.getenv("MYSQL_USER", "root")
PWD = os.getenv("MYSQL_PASSWORD", "")


def engine():
    url = URL.create(
        drivername="mysql+pymysql",
        username=USER,
        password=PWD,
        host=HOST,
        port=PORT,
        database=DB,
        query={"charset": "utf8mb4"},
    )
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600)


def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def ensure_stats_table(conn):
    ddl = f"""
    CREATE TABLE IF NOT EXISTS symbol_liq_stats (
      symbol VARCHAR(64) NOT NULL,
      series VARCHAR(8) NOT NULL,
      avg_ttl_trd_qnty BIGINT NULL,
      avg_turnover_lacs DECIMAL(20,4) NULL,
      sample_start DATE NULL,
      sample_end DATE NULL,
      computed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (symbol, series)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    conn.execute(text(ddl))


def compute_and_upsert_baseline(conn, start: date, end: date):
    # ensure stats table exists
    ensure_stats_table(conn)

    # compute averages per symbol,series
    sql = text(f"""
        SELECT symbol, series,
          AVG(ttl_trd_qnty) AS avg_qty,
          AVG(turnover_lacs) AS avg_turnover,
          COUNT(*) AS days
        FROM nse_equity_bhavcopy_full
        WHERE trade_date BETWEEN :a AND :b
        GROUP BY symbol, series
    """)
    rows = conn.execute(sql, {"a": start, "b": end}).mappings().all()

    upsert = text(f"""
        INSERT INTO symbol_liq_stats(symbol, series, avg_ttl_trd_qnty, avg_turnover_lacs, sample_start, sample_end)
        VALUES(:symbol, :series, :avg_qty, :avg_turnover, :a, :b)
        ON DUPLICATE KEY UPDATE
          avg_ttl_trd_qnty = VALUES(avg_ttl_trd_qnty),
          avg_turnover_lacs = VALUES(avg_turnover_lacs),
          sample_start = VALUES(sample_start),
          sample_end = VALUES(sample_end),
          computed_at = CURRENT_TIMESTAMP
    """)

    cnt = 0
    for r in rows:
        conn.execute(upsert, {"symbol": r["symbol"], "series": r["series"], "avg_qty": int(r["avg_qty"] if r["avg_qty"] is not None else 0), "avg_turnover": float(r["avg_turnover"] if r["avg_turnover"] is not None else 0.0), "a": start, "b": end})
        cnt += 1
    return cnt


def scan_recent_vs_baseline(conn, recent_start: date, recent_end: date, qty_mult: float = 3.0, turnover_mult: float = 3.0, min_recent_days: int = 1, compare_latest: bool = False) -> List[Dict[str, Any]]:
    # compute recent averages OR latest single-day values depending on compare_latest
    if not compare_latest:
        recent_sql = text(f"""
            SELECT symbol, series,
              AVG(ttl_trd_qnty) AS recent_avg_qty,
              AVG(turnover_lacs) AS recent_avg_turnover,
              COUNT(*) AS recent_days
            FROM nse_equity_bhavcopy_full
            WHERE trade_date BETWEEN :a AND :b
            GROUP BY symbol, series
        """)
        recent_rows = conn.execute(recent_sql, {"a": recent_start, "b": recent_end}).mappings().all()
    else:
        # For each symbol+series find the latest trade_date inside the recent window and take that day's values
        latest_sql = text(f"""
            SELECT t.symbol, t.series, t.ttl_trd_qnty AS recent_avg_qty, t.turnover_lacs AS recent_avg_turnover, 1 AS recent_days
            FROM nse_equity_bhavcopy_full t
            JOIN (
                SELECT symbol, series, MAX(trade_date) AS md
                FROM nse_equity_bhavcopy_full
                WHERE trade_date BETWEEN :a AND :b
                GROUP BY symbol, series
            ) m ON t.symbol = m.symbol AND t.series = m.series AND t.trade_date = m.md
        """)
        recent_rows = conn.execute(latest_sql, {"a": recent_start, "b": recent_end}).mappings().all()

    # load baseline table into dict
    baseline_rows = conn.execute(text("SELECT symbol, series, avg_ttl_trd_qnty, avg_turnover_lacs FROM symbol_liq_stats")).mappings().all()
    baseline = {(r["symbol"], r["series"]): r for r in baseline_rows}

    results = []
    for r in recent_rows:
        key = (r["symbol"], r["series"])
        recent_avg_qty = float(r["recent_avg_qty"] if r["recent_avg_qty"] is not None else 0.0)
        recent_avg_turn = float(r["recent_avg_turnover"] if r["recent_avg_turnover"] is not None else 0.0)
        recent_days = int(r["recent_days"])
        if recent_days < min_recent_days:
            continue

        base = baseline.get(key)
        if not base:
            # no baseline available — skip or optionally include
            continue

        base_qty = float(base["avg_ttl_trd_qnty"] if base["avg_ttl_trd_qnty"] is not None else 0.0)
        base_turn = float(base["avg_turnover_lacs"] if base["avg_turnover_lacs"] is not None else 0.0)

        qty_ratio = (recent_avg_qty / base_qty) if base_qty > 0 else None
        turn_ratio = (recent_avg_turn / base_turn) if base_turn > 0 else None

        if (qty_ratio is not None and qty_ratio >= qty_mult) or (turn_ratio is not None and turn_ratio >= turnover_mult):
            results.append({
                "symbol": r["symbol"],
                "series": r["series"],
                "recent_avg_qty": recent_avg_qty,
                "recent_avg_turnover": recent_avg_turn,
                "recent_days": recent_days,
                "base_avg_qty": base_qty,
                "base_avg_turnover": base_turn,
                "qty_ratio": qty_ratio,
                "turn_ratio": turn_ratio,
            })

    # sort by max ratio desc
    results.sort(key=lambda x: max(x["qty_ratio"] if x["qty_ratio"] is not None else 0.0, x["turn_ratio"] if x["turn_ratio"] is not None else 0.0), reverse=True)
    return results


def save_csv(results: List[Dict[str, Any]], out_path: str):
    if not results:
        print("No spikes found — nothing to write.")
        return
    keys = ["symbol", "series", "recent_days", "recent_avg_qty", "base_avg_qty", "qty_ratio", "recent_avg_turnover", "base_avg_turnover", "turn_ratio"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r.get(k) for k in keys})
    print(f"Wrote {len(results)} rows to {out_path}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--baseline-start", type=str, default=None)
    p.add_argument("--baseline-end", type=str, default=None)
    p.add_argument("--recent-start", type=str, default="2025-08-01")
    p.add_argument("--recent-end", type=str, default="2025-10-10")
    p.add_argument("--qty-mult", type=float, default=3.0)
    p.add_argument("--turnover-mult", type=float, default=3.0)
    p.add_argument("--min-recent-days", type=int, default=1)
    p.add_argument("--update-baseline", action="store_true", help="Recompute and upsert baseline stats from baseline-start..baseline-end")
    p.add_argument("--compare-latest", action="store_true", help="Compare the latest single-day qty/turnover in recent window vs baseline instead of recent averages")
    p.add_argument("--out", type=str, default=None, help="CSV output for spikes")
    args = p.parse_args()

    recent_start = parse_date(args.recent_start)
    recent_end = parse_date(args.recent_end)

    eng = engine()
    with eng.begin() as conn:
        ensure_stats_table(conn)
        if args.update_baseline:
            if not args.baseline_start or not args.baseline_end:
                raise SystemExit("--baseline-start and --baseline-end are required when --update-baseline is used")
            bstart = parse_date(args.baseline_start)
            bend = parse_date(args.baseline_end)
            cnt = compute_and_upsert_baseline(conn, bstart, bend)
            print(f"Computed and upserted baseline for {cnt} symbols (range {bstart}..{bend})")

            results = scan_recent_vs_baseline(conn, recent_start, recent_end, qty_mult=args.qty_mult, turnover_mult=args.turnover_mult, min_recent_days=args.min_recent_days, compare_latest=args.compare_latest)

    print(f"Found {len(results)} symbols exceeding multipliers (qty_mult={args.qty_mult}, turnover_mult={args.turnover_mult})")
    for r in results[:200]:
        print(f"{r['symbol']} {r['series']} recent_days={r['recent_days']} recent_qty={r['recent_avg_qty']:.0f} base_qty={r['base_avg_qty']:.0f} qty_ratio={r['qty_ratio'] if r['qty_ratio'] is not None else 'NA'} recent_turn={r['recent_avg_turnover']:.2f} base_turn={r['base_avg_turnover']:.2f} turn_ratio={r['turn_ratio'] if r['turn_ratio'] is not None else 'NA'}")

    if args.out:
        save_csv(results, args.out)


if __name__ == "__main__":
    main()
