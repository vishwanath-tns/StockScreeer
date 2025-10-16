"""scan_accumulation_by_delivery.py

Scan for accumulation signals using delivery percentage time series.

Features:
- Computes linear trend (slope) of `deliv_per` per symbol over a date range.
- Computes rolling averages, percent of days above a threshold, average/median deliv_per.
- Ranks symbols by a composite score and allows CSV export.
- Optional plotting of top-N candidates' delivery% series (saved as PNGs).

Usage examples:
  python scan_accumulation_by_delivery.py --start 2025-08-01 --end 2025-10-10 --series EQ --min-days 15 --min-slope 0.5 --out results.csv --plot-top 10

"""
from datetime import datetime, date
import argparse
import os
import math
import csv
from typing import Optional, Dict, Any, List

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


def symbol_trend_metrics(df: pd.DataFrame, roll_window: int = 7, high_thresh: float = 40.0) -> Optional[Dict[str, Any]]:
    """Compute metrics for a single symbol DataFrame with columns ['trade_date','deliv_per'].
    Returns None if insufficient data.
    """
    df = df.dropna(subset=["deliv_per"])
    n = len(df)
    if n < 6:
        return None

    # ensure sorted
    df = df.sort_values("trade_date")

    # convert dates to ordinal for regression
    x = np.array([d.toordinal() for d in pd.to_datetime(df["trade_date"]).dt.date], dtype=float)
    y = np.array(df["deliv_per"], dtype=float)

    # linear regression (least squares) - polyfit
    try:
        slope, intercept = np.polyfit(x, y, 1)
    except Exception:
        return None

    # slope per 30 days
    slope_30d = slope * 30.0

    # rolling average
    roll = df["deliv_per"].rolling(window=min(roll_window, max(1, n))).mean()
    roll_nonnull = roll.dropna()
    if len(roll_nonnull) >= 2:
        roll_start = float(roll_nonnull.iloc[0])
        roll_end = float(roll_nonnull.iloc[-1])
    else:
        roll_start = float(df["deliv_per"].iloc[0])
        roll_end = float(df["deliv_per"].iloc[-1])

    pct_days_high = float((df["deliv_per"] > high_thresh).sum()) / n
    avg = float(df["deliv_per"].mean())
    median = float(df["deliv_per"].median())

    # composite score (tunable): give weight to slope, rolling change, and fraction of high-delivery days
    score = slope_30d * 1.0 + (roll_end - roll_start) * 5.0 + pct_days_high * 10.0

    return {
        "n_days": n,
        "avg": avg,
        "median": median,
        "slope_per_30d": slope_30d,
        "roll_start": roll_start,
        "roll_end": roll_end,
        "pct_days_high": pct_days_high,
        "score": score,
    }


def scan(start: date, end: date, series: Optional[str] = None, min_days: int = 10, min_slope_30d: float = 0.5,
         high_thresh: float = 40.0, roll_window: int = 7) -> List[Dict[str, Any]]:
    eng = engine()
    q = "SELECT trade_date, symbol, series, deliv_per, deliv_qty FROM nse_equity_bhavcopy_full WHERE trade_date BETWEEN :a AND :b"
    params = {"a": start, "b": end}
    if series:
        q += " AND series = :series"
        params["series"] = series

    with eng.connect() as conn:
        df = pd.read_sql(text(q), con=conn, params=params, parse_dates=["trade_date"])

    if df.empty:
        print("No data found in the requested range.")
        return []

    results = []
    # group by symbol and series
    for (symbol, ser), g in df.groupby(["symbol", "series"]):
        metrics = symbol_trend_metrics(g[["trade_date", "deliv_per"]], roll_window=roll_window, high_thresh=high_thresh)
        if not metrics:
            continue
        if metrics["n_days"] >= min_days and metrics["slope_per_30d"] >= min_slope_30d:
            results.append({
                "symbol": symbol,
                "series": ser,
                **metrics,
            })

    # sort by score then slope
    results.sort(key=lambda r: (r["score"], r["slope_per_30d"]), reverse=True)
    return results


def save_csv(results: List[Dict[str, Any]], out_path: str):
    if not results:
        print("No results to write.")
        return
    keys = ["symbol", "series", "n_days", "avg", "median", "slope_per_30d", "roll_start", "roll_end", "pct_days_high", "score"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r.get(k) for k in keys})
    print(f"Wrote {len(results)} rows to {out_path}")


def plot_top(results: List[Dict[str, Any]], start: date, end: date, top_n: int = 5, out_dir: str = "acc_plots"):
    if not results:
        print("No results to plot.")
        return
    try:
        import matplotlib.pyplot as plt
    except Exception:
        print("matplotlib is not available; skipping plotting")
        return

    os.makedirs(out_dir, exist_ok=True)
    eng = engine()
    for r in results[:top_n]:
        symbol = r["symbol"]
        ser = r["series"]
        q = "SELECT trade_date, deliv_per FROM nse_equity_bhavcopy_full WHERE trade_date BETWEEN :a AND :b AND symbol = :sym AND series = :ser ORDER BY trade_date"
        with eng.connect() as conn:
            df = pd.read_sql(text(q), con=conn, params={"a": start, "b": end, "sym": symbol, "ser": ser}, parse_dates=["trade_date"])

        if df.empty:
            continue
        df = df.set_index("trade_date").sort_index()
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(df.index, df["deliv_per"], marker="o", linestyle="-", markersize=4)
        ax.set_title(f"{symbol} {ser} — delivery% {start} to {end}")
        ax.set_ylabel("delivery %")
        ax.grid(which="major", linestyle="-", linewidth=0.6, alpha=0.8)
        ax.grid(which="minor", linestyle=":", linewidth=0.4, alpha=0.6)
        fig.autofmt_xdate()
        fig.tight_layout()
        fname = os.path.join(out_dir, f"{symbol}_{ser}.png")
        fig.savefig(fname)
        plt.close(fig)
        print(f"Saved plot: {fname}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--start", type=str, default="2025-08-01")
    p.add_argument("--end", type=str, default="2025-10-10")
    p.add_argument("--series", type=str, default=None)
    p.add_argument("--min-days", type=int, default=10)
    p.add_argument("--min-slope", type=float, default=0.5, help="slope threshold in percentage points per 30 days")
    p.add_argument("--high-thresh", type=float, default=40.0, help="delivery% considered 'high' for pct_days_high metric")
    p.add_argument("--roll-window", type=int, default=7)
    p.add_argument("--out", type=str, default=None, help="CSV output path")
    p.add_argument("--plot-top", type=int, default=0, help="Save plots for top N symbols")
    args = p.parse_args()

    start = parse_date(args.start)
    end = parse_date(args.end)

    results = scan(start=start, end=end, series=args.series, min_days=args.min_days, min_slope_30d=args.min_slope, high_thresh=args.high_thresh, roll_window=args.roll_window)

    print(f"Found {len(results)} candidates")
    for r in results[:200]:
        print(f"{r['symbol']} {r['series']} days={r['n_days']} avg={r['avg']:.2f}% slope30d={r['slope_per_30d']:.2f}% score={r['score']:.2f}")

    if args.out:
        save_csv(results, args.out)

    if args.plot_top and results:
        plot_top(results, start, end, top_n=args.plot_top)


if __name__ == "__main__":
    main()
