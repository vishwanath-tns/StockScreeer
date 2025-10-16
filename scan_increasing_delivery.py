"""scan_increasing_delivery.py

Scanner: list stocks with increasing delivery percentage from August to October.

Default behaviour:
- Compares average `deliv_per` for Aug 2025 vs Oct 2025 per (symbol, series).
- Lists symbols where Oct average > Aug average, sorted by delta (desc).

Usage:
    python scan_increasing_delivery.py
    python scan_increasing_delivery.py --year 2025 --series EQ --out out.csv

"""
import os
import csv
import argparse
from datetime import date
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

load_dotenv()

HOST = os.getenv("MYSQL_HOST", "localhost")
PORT = int(os.getenv("MYSQL_PORT", "3306"))
DB   = os.getenv("MYSQL_DB", "marketdata")
USER = os.getenv("MYSQL_USER", "root")
PWD  = os.getenv("MYSQL_PASSWORD", "")


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


def scan(year=2025, series=None, out_csv=None):
    # Define date bounds for Aug and Oct of given year
    aug_start = date(year, 8, 1)
    aug_end = date(year, 8, 31)
    oct_start = date(year, 10, 1)
    oct_end = date(year, 10, 31)

    sql = f"""
    SELECT symbol, series,
      AVG(CASE WHEN trade_date BETWEEN :aug_start AND :aug_end THEN deliv_per END) AS aug_avg,
      AVG(CASE WHEN trade_date BETWEEN :oct_start AND :oct_end THEN deliv_per END) AS oct_avg,
      COUNT(CASE WHEN trade_date BETWEEN :aug_start AND :aug_end THEN 1 END) AS aug_count,
      COUNT(CASE WHEN trade_date BETWEEN :oct_start AND :oct_end THEN 1 END) AS oct_count
    FROM nse_equity_bhavcopy_full
    WHERE trade_date BETWEEN :aug_start AND :oct_end
    """

    params = {
        "aug_start": aug_start,
        "aug_end": aug_end,
        "oct_start": oct_start,
        "oct_end": oct_end,
    }

    if series:
        sql += "\n AND series = :series"
        params["series"] = series

    sql += "\nGROUP BY symbol, series"
    sql += "\nHAVING aug_avg IS NOT NULL AND oct_avg IS NOT NULL AND oct_avg > aug_avg"
    sql += "\nORDER BY (oct_avg - aug_avg) DESC"

    eng = engine()
    with eng.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    results = []
    for r in rows:
        symbol = r["symbol"]
        ser = r["series"]
        aug_avg = float(r["aug_avg"]) if r["aug_avg"] is not None else None
        oct_avg = float(r["oct_avg"]) if r["oct_avg"] is not None else None
        aug_count = int(r["aug_count"]) if r["aug_count"] is not None else 0
        oct_count = int(r["oct_count"]) if r["oct_count"] is not None else 0
        delta = oct_avg - aug_avg
        results.append({
            "symbol": symbol,
            "series": ser,
            "aug_avg": aug_avg,
            "oct_avg": oct_avg,
            "delta": delta,
            "aug_count": aug_count,
            "oct_count": oct_count,
        })

    # Print summary
    print(f"Found {len(results)} symbols with higher delivery% in Oct {year} vs Aug {year} (series={series})")
    print("symbol, series, aug_avg, oct_avg, delta, aug_count, oct_count")
    for r in results[:200]:
        print(f"{r['symbol']}, {r['series']}, {r['aug_avg']:.2f}, {r['oct_avg']:.2f}, {r['delta']:.2f}, {r['aug_count']}, {r['oct_count']}")

    if out_csv:
        keys = ["symbol", "series", "aug_avg", "oct_avg", "delta", "aug_count", "oct_count"]
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for r in results:
                writer.writerow(r)
        print(f"Wrote {len(results)} rows to {out_csv}")

    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--year", type=int, default=2025)
    p.add_argument("--series", type=str, default=None, help="Filter by series (e.g., EQ)")
    p.add_argument("--out", type=str, default=None, help="Write results to CSV file")
    args = p.parse_args()
    scan(year=args.year, series=args.series, out_csv=args.out)


if __name__ == "__main__":
    main()
