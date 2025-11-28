"""fractal_breaks.py

Scan latest fractals vs latest prices and report symbols whose latest price
has broken above the fractal high or below the fractal low.

Provides:
- scan_fractal_breaks(engine=None) -> pandas.DataFrame with columns:
  symbol, break_date, fractal_date, fractal_type, fractal_high, fractal_low, close_price, break_type ('BUY'/'SELL')

"""
from __future__ import annotations
from sqlalchemy import text
import pandas as pd
import datetime


def _ensure_engine():
    try:
        from import_nifty_index import build_engine
        return build_engine()
    except Exception:
        try:
            import rsi_fractals as rf
            return rf._ensure_engine()
        except Exception:
            raise RuntimeError('No engine builder available')


def scan_fractal_breaks(engine=None):
    """Return DataFrame of symbols where latest price breaks the latest fractal.
    """
    if engine is None:
        engine = _ensure_engine()

    # get latest fractal per symbol
    q_fr = text(
        "SELECT f.symbol, f.fractal_date, f.fractal_type, f.fractal_high, f.fractal_low "
        "FROM nse_fractals f JOIN (SELECT symbol, MAX(fractal_date) AS d FROM nse_fractals GROUP BY symbol) t "
        "ON f.symbol = t.symbol AND f.fractal_date = t.d"
    )

    # get latest bhav per symbol (EQ series)
    q_bhav = text(
        "SELECT b.symbol, b.trade_date, b.close_price "
        "FROM nse_equity_bhavcopy_full b JOIN (SELECT symbol, MAX(trade_date) AS dt FROM nse_equity_bhavcopy_full WHERE series = 'EQ' GROUP BY symbol) t "
        "ON b.symbol = t.symbol AND b.trade_date = t.dt WHERE b.series = 'EQ'"
    )

    with engine.connect() as conn:
        fr_rows = conn.execute(q_fr).fetchall()
        bhav_rows = conn.execute(q_bhav).fetchall()

    if not fr_rows or not bhav_rows:
        return pd.DataFrame()

    df_fr = pd.DataFrame(fr_rows, columns=[c for c in fr_rows[0]._fields])
    df_b = pd.DataFrame(bhav_rows, columns=[c for c in bhav_rows[0]._fields])

    # normalize column names
    df_fr['fractal_date'] = pd.to_datetime(df_fr['fractal_date'])
    df_b['trade_date'] = pd.to_datetime(df_b['trade_date'])
    df_b['close_price'] = pd.to_numeric(df_b['close_price'], errors='coerce')
    df_fr['fractal_high'] = pd.to_numeric(df_fr['fractal_high'], errors='coerce')
    df_fr['fractal_low'] = pd.to_numeric(df_fr['fractal_low'], errors='coerce')

    # join on symbol
    merged = pd.merge(df_b, df_fr, on='symbol', how='inner', suffixes=('_bh', '_fr'))

    # determine breaks
    def classify(row):
        close = row['close_price']
        hi = row['fractal_high']
        lo = row['fractal_low']
        if pd.isna(close) or (pd.isna(hi) and pd.isna(lo)):
            return None
        if not pd.isna(hi) and close > hi:
            return 'BUY'
        if not pd.isna(lo) and close < lo:
            return 'SELL'
        return None

    merged['break_type'] = merged.apply(classify, axis=1)
    res = merged[merged['break_type'].notna()].copy()
    if res.empty:
        return pd.DataFrame()
    # select and rename columns
    out = res[['symbol', 'trade_date', 'fractal_date', 'fractal_type', 'fractal_high', 'fractal_low', 'close_price', 'break_type']]
    out = out.rename(columns={'trade_date': 'break_date'})
    # ensure types
    out['break_date'] = pd.to_datetime(out['break_date']).dt.date
    out['fractal_date'] = pd.to_datetime(out['fractal_date']).dt.date
    return out.sort_values(['break_date', 'symbol'], ascending=[False, True]).reset_index(drop=True)
