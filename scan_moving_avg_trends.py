"""scan_moving_avg_trends.py

Simple scanner that reads the `moving_averages` table and identifies symbols
that meet trend criteria such as:
 - close > sma_short > sma_long (momentum)
 - golden cross recently (short SMA crossed above long SMA)

Usage:
    python scan_moving_avg_trends.py --short 20 --long 50 --since 2025-09-01
"""
from __future__ import annotations
import argparse
from datetime import date
import pandas as pd
from sqlalchemy import text


def engine():
    import reporting_adv_decl as rad
    return rad.engine()


def scan(short: int = 20, long: int = 50, since: date | None = None):
    eng = engine()
    with eng.connect() as conn:
        params = {}
        q = f"SELECT trade_date, symbol, sma_{short} as sma_short, sma_{long} as sma_long FROM moving_averages"
        if since:
            q += " WHERE trade_date >= :since"
            params["since"] = since
        df = pd.read_sql(text(q), con=conn, params=params, parse_dates=["trade_date"])

    if df.empty:
        return []

    # For each symbol, look at the latest date and previous date to detect recent cross
    res = []
    for sym, g in df.groupby("symbol"):
        g2 = g.sort_values("trade_date")
        if len(g2) < 2:
            continue
        last = g2.iloc[-1]
        prev = g2.iloc[-2]
        # Must have non-null SMAs
        if pd.isna(last["sma_short"]) or pd.isna(last["sma_long"]):
            continue
        # Momentum condition: short above long now
        momentum = last["sma_short"] > last["sma_long"]
        # Golden cross: previously short <= long, now short > long
        golden = (prev["sma_short"] <= prev["sma_long"]) and (last["sma_short"] > last["sma_long"])
        if momentum or golden:
            res.append({
                "symbol": sym,
                "date": last["trade_date"].date(),
                "sma_short": float(last["sma_short"]),
                "sma_long": float(last["sma_long"]),
                "momentum": bool(momentum),
                "golden_cross": bool(golden),
            })
    return res


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--short", type=int, default=20)
    p.add_argument("--long", type=int, default=50)
    p.add_argument("--since", help="Start date (YYYY-MM-DD)")
    args = p.parse_args(argv)
    since = pd.to_datetime(args.since).date() if args.since else None
    res = scan(short=args.short, long=args.long, since=since)
    for r in res:
        print(r)


if __name__ == "__main__":
    main()
