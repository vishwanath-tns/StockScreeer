"""Service layer for fractals-related business logic.
This module provides functions the GUI can call without touching DB details.
"""
from typing import Tuple
import pandas as pd

from db.connection import ensure_engine
from db.fractals_repo import fetch_fractal_breaks, fetch_recent_ohlcv, fetch_rsi_range


def scan_fractal_breaks(engine=None) -> pd.DataFrame:
    """Return a DataFrame of fractal breaks. Accepts an optional engine.

    Delegates to the repository which may call existing implementations.
    """
    eng = engine if engine is not None else ensure_engine()
    return fetch_fractal_breaks(eng)


def fetch_price_and_rsi(symbol: str, days: int = 120, period: int = 14, engine=None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch recent OHLCV and RSI for symbol for the last `days` days.

    Returns tuple (ohlcv_df, rsi_df) where each is a pandas.DataFrame.
    """
    eng = engine if engine is not None else ensure_engine()
    ohlcv = fetch_recent_ohlcv(eng, symbol, days)
    if ohlcv.empty:
        return ohlcv, pd.DataFrame()
    # determine RSI window bounds
    start = ohlcv.index.min().strftime('%Y-%m-%d')
    end = ohlcv.index.max().strftime('%Y-%m-%d')
    rsi_df = fetch_rsi_range(eng, symbol, period=period, start_date=start, end_date=end)
    return ohlcv, rsi_df
