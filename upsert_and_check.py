#!/usr/bin/env python3
"""Run upsert_daily_52w_counts for one date and print read-back.

Usage:
  py upsert_and_check.py [YYYY-MM-DD]

Environment variables used (if not provided, defaults are used):
  MYSQL_HOST, MYSQL_PORT, MYSQL_DB, MYSQL_USER, MYSQL_PASSWORD

"""
import os
import sys
import datetime
from sqlalchemy import create_engine, text
import week52_scanner as w52


def engine_from_env():
    # Prefer existing project engine factory if available
    try:
        import reporting_adv_decl as rad
        eng = rad.engine()
        print(f"Using engine from reporting_adv_decl: {eng}")
        return eng
    except Exception:
        pass

    host = os.environ.get('MYSQL_HOST', 'localhost')
    port = os.environ.get('MYSQL_PORT', '3306')
    db = os.environ.get('MYSQL_DB', 'test')
    user = os.environ.get('MYSQL_USER', 'root')
    pw = os.environ.get('MYSQL_PASSWORD', '')
    url = f"mysql+pymysql://{user}:{pw}@{host}:{port}/{db}?charset=utf8mb4"
    print(f"Connecting to: {url}")
    return create_engine(url)


def main():
    if len(sys.argv) >= 2:
        as_of = datetime.datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    else:
        as_of = None

    engine = engine_from_env()
    with engine.connect() as conn:
        print(f"Calling upsert_daily_52w_counts(as_of={as_of})")
        res = w52.upsert_daily_52w_counts(conn, as_of=as_of)
        print("upsert result:", res)
        try:
            r = conn.execute(text("SELECT dt, count_high, count_low, updated_at FROM daily_52w_counts WHERE dt = :d"), {"d": res['date']}).fetchone()
            print("read back:", r)
        except Exception as e:
            print("read-back failed:", e)


if __name__ == '__main__':
    main()
