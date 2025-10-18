"""compute_moving_averages.py

Compute simple moving averages (SMA) per-symbol from the BHAV table and
upsert results into `moving_averages` table for downstream scanning.

Usage:
    python compute_moving_averages.py [--symbols RELIANCE,TCS] [--windows 5,10,20]

By default windows = 5,10,20,50,100,200 and all symbols are processed.
"""
from __future__ import annotations
import argparse
import sys
from typing import List
import pandas as pd
from sqlalchemy import text

def engine_from_reporting():
    # import the project's engine helper to ensure consistent DB config
    import reporting_adv_decl as rad
    return rad.engine()


DEFAULT_WINDOWS = [5, 10, 20, 50, 100, 200]


def ensure_table(conn, windows: List[int]):
    cols = ",\n      ".join([f"sma_{w} DOUBLE NULL" for w in windows])
    ddl = f"""
    CREATE TABLE IF NOT EXISTS moving_averages (
      trade_date DATE NOT NULL,
      symbol VARCHAR(32) NOT NULL,
      {cols},
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (symbol, trade_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    conn.execute(text(ddl))


def compute_for_symbol(conn, symbol: str, windows: List[int], min_periods: int | None = None):
    # fetch OHLC for symbol
    q = text(
        "SELECT trade_date as dt, close_price as Close FROM nse_equity_bhavcopy_full "
        "WHERE symbol=:s ORDER BY trade_date"
    )
    df = pd.read_sql(q, con=conn, params={"s": symbol}, parse_dates=["dt"])  # may be empty
    if df.empty:
        return 0

    df = df.set_index("dt").sort_index()

    # compute SMAs
    for w in windows:
        mp = w if min_periods is None else min_periods
        df[f"sma_{w}"] = df["Close"].rolling(window=w, min_periods=mp).mean()

    # prepare rows to upsert
    out = df.reset_index()
    out["symbol"] = symbol
    cols = ["dt", "symbol"] + [f"sma_{w}" for w in windows]
    out = out.rename(columns={"dt": "trade_date"})
    out = out[["trade_date", "symbol"] + [f"sma_{w}" for w in windows]]

    # Ensure we don't have duplicate primary-key rows which would cause
    # INSERT INTO tmp_mv to fail (tmp_mv has same PRIMARY KEY as moving_averages).
    out = out.drop_duplicates(subset=["trade_date", "symbol"], keep="last")
    # use a temporary table and upsert using ON DUPLICATE KEY UPDATE
    conn.execute(text("DROP TEMPORARY TABLE IF EXISTS tmp_mv"))
    # If moving_averages doesn't exist, ensure_table should have created it earlier
    conn.execute(text("CREATE TEMPORARY TABLE tmp_mv LIKE moving_averages"))
    # bulk insert using pandas
    # Use the same Connection object so the temporary table is written to
    # the same transactional connection (avoids visibility issues when
    # pandas opens a separate engine connection).
    out.to_sql(name="tmp_mv", con=conn, if_exists="append", index=False, method="multi", chunksize=1000)

    # build upsert
    cols_list = ", ".join([f"sma_{w}" for w in windows])
    insert_cols = "trade_date, symbol, " + cols_list
    select_cols = "trade_date, symbol, " + cols_list
    updates = ", ".join([f"{c}=VALUES({c})" for c in cols_list.split(", ")])
    upsert_sql = f"""
        INSERT INTO moving_averages ({insert_cols})
        SELECT {select_cols} FROM tmp_mv
        ON DUPLICATE KEY UPDATE {updates}
    """
    conn.execute(text(upsert_sql))
    conn.execute(text("DROP TEMPORARY TABLE IF EXISTS tmp_mv"))
    return len(out)


def main(argv: List[str] | None = None):
    p = argparse.ArgumentParser()
    p.add_argument("--symbols", help="Comma-separated list of symbols to process")
    p.add_argument("--windows", help="Comma-separated SMA windows, e.g. 5,10,20", default=",".join(map(str, DEFAULT_WINDOWS)))
    p.add_argument("--min-periods", type=int, default=None, help="min_periods for rolling (defaults to window size if omitted)")
    args = p.parse_args(argv)

    windows = [int(x) for x in args.windows.split(",") if x.strip()]
    symbols_filter = None
    if args.symbols:
        symbols_filter = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    eng = engine_from_reporting()
    with eng.begin() as conn:
        ensure_table(conn, windows)

        # load symbol list
        q = "SELECT DISTINCT symbol FROM nse_equity_bhavcopy_full ORDER BY symbol"
        if symbols_filter:
            # parameterize
            rows = conn.execute(text(q)).scalars().all()
            syms = [s for s in rows if s in symbols_filter]
        else:
            rows = conn.execute(text(q)).scalars().all()
            syms = [s for s in rows]

        print(f"Found {len(syms)} symbols to process")
        count_total = 0
        for i, s in enumerate(syms, start=1):
            print(f"[{i}/{len(syms)}] Processing {s}...")
            try:
                n = compute_for_symbol(conn, s, windows, min_periods=args.min_periods or None)
                count_total += n
            except Exception as e:
                print(f"Error computing for {s}: {e}")
        print(f"Done. Upserted {count_total} moving-average rows.")


if __name__ == "__main__":
    main()
