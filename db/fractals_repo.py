"""Repository helpers for fractal-related data access.
These functions encapsulate SQL access so service layer doesn't run direct SQL
spread across the GUI.
"""
from sqlalchemy import text
from typing import Optional
import pandas as pd


def fetch_fractal_breaks(engine):
    """Delegate to existing scan implementation if present; otherwise try a
    basic query. Returns a pandas.DataFrame.
    """
    try:
        import fractal_breaks as fb
        eng = engine if engine is not None else fb._ensure_engine()
        return fb.scan_fractal_breaks(eng)
    except Exception:
        # fallback: return empty DataFrame
        return pd.DataFrame()


def fetch_recent_ohlcv(engine, symbol: str, days: Optional[int] = 120):
    """Fetch recent OHLCV rows for symbol (sorted ascending by date).
    Returns a pandas.DataFrame with trade_date as DatetimeIndex.
    """
    with engine.connect() as conn:
        if days is None:
            # no LIMIT clause when days is not provided
            q = text("SELECT trade_date as dt, open_price as Open, high_price as High, low_price as Low, close_price as Close, ttl_trd_qnty as Volume, turnover_lacs FROM nse_equity_bhavcopy_full WHERE symbol = :s AND series = 'EQ' ORDER BY trade_date DESC")
            rows = conn.execute(q, {"s": symbol}).fetchall()
        else:
            q = text("SELECT trade_date as dt, open_price as Open, high_price as High, low_price as Low, close_price as Close, ttl_trd_qnty as Volume, turnover_lacs FROM nse_equity_bhavcopy_full WHERE symbol = :s AND series = 'EQ' ORDER BY trade_date DESC LIMIT :n")
            rows = conn.execute(q, {"s": symbol, "n": days}).fetchall()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=[c for c in rows[0]._fields])
    df['dt'] = pd.to_datetime(df['dt'])
    df = df.set_index('dt').sort_index()
    return df


def fetch_rsi_range(engine, symbol: str, period: int, start_date, end_date):
    """Fetch RSI values for symbol between start_date and end_date (inclusive).
    Returns DataFrame indexed by trade_date.
    """
    with engine.connect() as conn:
        q = text("SELECT trade_date, rsi FROM nse_rsi_daily WHERE symbol = :s AND period = :p AND trade_date BETWEEN :a AND :b ORDER BY trade_date")
        rows = conn.execute(q, {"s": symbol, "p": period, "a": start_date, "b": end_date}).fetchall()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=[c for c in rows[0]._fields])
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    df = df.set_index('trade_date').sort_index()
    return df
