"""scan_delivery_count.py

Scan for stocks with delivery percentage above a threshold and count the days.

Functions:
- scan(start, end, series, threshold) -> list of dicts {symbol, series, days_over, total_days, pct}
- save_csv(results, path)
"""
from datetime import date
from typing import List, Dict
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
import os

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


def scan(start: date, end: date, series: str = None, threshold: float = 20.0) -> List[Dict]:
    q = f"""
    SELECT symbol, series,
      SUM(CASE WHEN deliv_per > :thr THEN 1 ELSE 0 END) AS days_over,
      COUNT(*) AS total_days
    FROM nse_equity_bhavcopy_full
    WHERE trade_date BETWEEN :a AND :b
    """
    params = {"a": start, "b": end, "thr": threshold}
    if series:
        q += " AND series = :series"
        params["series"] = series
    q += "\nGROUP BY symbol, series"
    q += "\nHAVING days_over > 0"
    q += "\nORDER BY days_over DESC, symbol ASC"

    eng = engine()
    with eng.connect() as conn:
        rows = conn.execute(text(q), params).mappings().all()

    results = []
    for r in rows:
        days_over = int(r["days_over"] or 0)
        total = int(r["total_days"] or 0)
        pct = (days_over / total * 100.0) if total > 0 else 0.0
        results.append({
            "symbol": r["symbol"],
            "series": r["series"],
            "days_over": days_over,
            "total_days": total,
            "pct": pct,
        })
    return results


def save_csv(results: List[Dict], path: str):
    import csv
    keys = ["symbol", "series", "days_over", "total_days", "pct"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in results:
            w.writerow({k: r.get(k) for k in keys})
