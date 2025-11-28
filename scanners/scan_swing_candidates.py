"""scan_swing_candidates.py

Scanner to select swing-trading candidates (cash) using traded quantity and turnover
plus simple price/momentum and volatility filters.

Heuristics implemented (configurable):
- Liquidity: average daily `turnover_lacs` >= --min-turnover-lacs
- Volume: average daily `ttl_trd_qnty` >= --min-qty
- Momentum: last close > SMA(window=20)
- Volatility: daily return std between --min-volatility and --max-volatility

Usage examples:
  python scan_swing_candidates.py --start 2025-08-01 --end 2025-10-10 --series EQ --min-turnover-lacs 5 --min-qty 10000 --out swing_candidates.csv

Defaults are conservative/tunable; see recommendations in README or script help.
"""
from datetime import datetime, date
import argparse
import csv
import os
from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv

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


def compute_metrics(df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """Compute required metrics from symbol dataframe with trade_date, close_price, ttl_trd_qnty, turnover_lacs."""
    df = df.dropna(subset=["close_price"])  # need price
    if df.empty:
        return None
    df = df.sort_values("trade_date")

    # compute daily returns (close-to-close)
    df["ret"] = df["close_price"].pct_change()
    volatility = float(df["ret"].std(skipna=True) or 0.0)
    avg_turnover = float(df["turnover_lacs"].mean(skipna=True) or 0.0)
    median_turnover = float(df["turnover_lacs"].median(skipna=True) or 0.0)
    avg_qty = float(df["ttl_trd_qnty"].mean(skipna=True) or 0.0)

    last_close = float(df["close_price"].iloc[-1])
    # 20-day SMA (or available window)
    window = min(20, len(df))
    sma20 = float(df["close_price"].rolling(window=window).mean().iloc[-1])

    # short-term momentum: last close vs SMA20, and 5-day return
    ret_5d = float(df["close_price"].pct_change(periods=min(5, len(df)-1)).iloc[-1]) if len(df) > 1 else 0.0

    return {
        "n_days": len(df),
        "avg_turnover_lacs": avg_turnover,
        "median_turnover_lacs": median_turnover,
        "avg_ttl_trd_qnty": avg_qty,
        "volatility": volatility,
        "last_close": last_close,
        "sma20": sma20,
        "ret_5d": ret_5d,
    }


def scan(start: date, end: date, series: Optional[str] = 'EQ', min_turnover_lacs: float = 5.0, min_qty: int = 10000,
         min_vol: float = 0.005, max_vol: float = 0.06, require_momentum: bool = False) -> List[Dict[str, Any]]:
    q = """
    SELECT trade_date, symbol, series, close_price, ttl_trd_qnty, turnover_lacs
    FROM nse_equity_bhavcopy_full
    WHERE trade_date BETWEEN :a AND :b
    """
    params = {"a": start, "b": end}
    if series:
        q += " AND series = :series"
        params["series"] = series

    eng = engine()
    with eng.connect() as conn:
        df = pd.read_sql(text(q), con=conn, params=params, parse_dates=["trade_date"])

    if df.empty:
        print("No data found in the requested range.")
        return []

    results = []
    for (symbol, ser), g in df.groupby(["symbol", "series"]):
        metrics = compute_metrics(g[["trade_date", "close_price", "ttl_trd_qnty", "turnover_lacs"]])
        if not metrics:
            continue

        # apply liquidity filters
        if metrics["avg_turnover_lacs"] < min_turnover_lacs:
            continue
        if metrics["avg_ttl_trd_qnty"] < min_qty:
            continue

        # volatility filter
        if metrics["volatility"] < min_vol or metrics["volatility"] > max_vol:
            continue

        # momentum filter optionally
        momentum_ok = metrics["last_close"] > metrics["sma20"]
        if require_momentum and not momentum_ok:
            continue

        r = {
            "symbol": symbol,
            "series": ser,
            **metrics,
        }
        results.append(r)

    # sort by avg_turnover_lacs desc then volatility desc
    results.sort(key=lambda x: (x["avg_turnover_lacs"], x["volatility"]), reverse=True)
    return results


def save_csv(results: List[Dict[str, Any]], out_path: str):
    if not results:
        print("No results to write.")
        return
    keys = ["symbol", "series", "n_days", "avg_turnover_lacs", "median_turnover_lacs", "avg_ttl_trd_qnty", "volatility", "last_close", "sma20", "ret_5d"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r.get(k) for k in keys})
    print(f"Wrote {len(results)} rows to {out_path}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--start", type=str, default="2025-08-01")
    p.add_argument("--end", type=str, default="2025-10-10")
    p.add_argument("--series", type=str, default='EQ')
    p.add_argument("--min-turnover-lacs", type=float, default=5.0, help="Minimum average turnover_lacs (1 lac = 100k) — default 5.0")
    p.add_argument("--min-qty", type=int, default=10000, help="Minimum average traded quantity per day")
    p.add_argument("--min-vol", type=float, default=0.005, help="Minimum daily return std (e.g., 0.005=0.5%)")
    p.add_argument("--max-vol", type=float, default=0.06, help="Maximum daily return std")
    p.add_argument("--momentum", action="store_true", help="Require last close > SMA20")
    p.add_argument("--out", type=str, default=None, help="CSV output file")
    args = p.parse_args()

    start = parse_date(args.start)
    end = parse_date(args.end)

    results = scan(start=start, end=end, series=args.series, min_turnover_lacs=args.min_turnover_lacs,
                   min_qty=args.min_qty, min_vol=args.min_vol, max_vol=args.max_vol, require_momentum=args.momentum)

    print(f"Found {len(results)} swing candidates")
    for r in results[:200]:
        print(f"{r['symbol']} {r['series']} days={r['n_days']} avg_turnover={r['avg_turnover_lacs']:.2f}L avg_qty={r['avg_ttl_trd_qnty']:.0f} vol={r['volatility']:.4f} sma20={r['sma20']:.2f} close={r['last_close']:.2f} 5d_ret={r['ret_5d']:.2%}")

    if args.out:
        save_csv(results, args.out)


if __name__ == "__main__":
    main()
