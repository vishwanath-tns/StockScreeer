"""verify_bhav_imports.py

Check that BHAV copies for a date range were imported.

Behavior:
- Computes expected trading sessions as weekdays (Mon-Fri) in the given date
  range, then removes any dates present in the `trading_holidays` table.
- Considers a date 'imported' if either:
  - `imports_log` contains a row for that trade_date, or
  - `nse_equity_bhavcopy_full` contains any rows for that trade_date.
- Prints a summary and lists missing dates (non-holiday trading sessions without data).

Usage (PowerShell):
    python verify_bhav_imports.py 2025-08-01 2025-10-10

If no arguments are provided the script will default to 2025-08-01 .. 2025-10-10.
"""
from datetime import date, datetime, timedelta
import os
import sys
from typing import Set
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


def parse_ymd(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def business_weekdays(start: date, end: date) -> Set[date]:
    d = start
    out = set()
    while d <= end:
        if d.weekday() < 5:  # Mon-Fri
            out.add(d)
        d += timedelta(days=1)
    return out


def fetch_holidays(conn, start: date, end: date) -> Set[date]:
    # If table doesn't exist return empty set
    try:
        rows = conn.execute(
            text("SELECT holiday_date FROM trading_holidays WHERE holiday_date BETWEEN :a AND :b"),
            {"a": start, "b": end},
        ).scalars().all()
        return {r for r in rows if r is not None}
    except Exception:
        return set()


def fetch_imports_log_dates(conn, start: date, end: date) -> Set[date]:
    try:
        rows = conn.execute(
            text("SELECT trade_date FROM imports_log WHERE trade_date BETWEEN :a AND :b"),
            {"a": start, "b": end},
        ).scalars().all()
        return {r for r in rows if r is not None}
    except Exception:
        return set()


def fetch_bhav_dates(conn, start: date, end: date) -> Set[date]:
    try:
        rows = conn.execute(
            text("SELECT DISTINCT trade_date FROM nse_equity_bhavcopy_full WHERE trade_date BETWEEN :a AND :b"),
            {"a": start, "b": end},
        ).scalars().all()
        return {r for r in rows if r is not None}
    except Exception:
        return set()


def main(argv):
    if len(argv) >= 3:
        start = parse_ymd(argv[1])
        end = parse_ymd(argv[2])
    else:
        start = date(2025, 8, 1)
        end = date(2025, 10, 10)

    eng = engine()
    with eng.connect() as conn:
        expected = business_weekdays(start, end)
        holidays = fetch_holidays(conn, start, end)
        trading_sessions = sorted(expected - holidays)

        imports_dates = fetch_imports_log_dates(conn, start, end)
        bhav_dates = fetch_bhav_dates(conn, start, end)

    imported = imports_dates.union(bhav_dates)

    missing = [d for d in trading_sessions if d not in imported]
    extra = sorted([d for d in imported if d not in trading_sessions])

    print(f"Date range: {start} -> {end}")
    print(f"Total weekdays: {len(expected)}")
    print(f"Holidays (from trading_holidays): {len(holidays)}")
    print(f"Expected trading sessions (weekdays - holidays): {len(trading_sessions)}")
    print(f"Imported dates (imports_log ∪ bhav table): {len(imported)}")
    print()

    if missing:
        print("Missing trading sessions (not imported):")
        for d in missing:
            print("  ", d.isoformat())
    else:
        print("All expected trading sessions are present.")

    if extra:
        print()
        print("Dates that have data/imports but are not expected trading sessions (weekend/holiday):")
        for d in extra:
            print("  ", d.isoformat())


if __name__ == "__main__":
    main(sys.argv)
