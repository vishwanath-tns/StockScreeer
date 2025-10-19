import pandas as pd
from rsi_calculator import compute_rsi


def test_compute_rsi_basic():
    rng = pd.date_range('2025-01-01', periods=30, freq='D')
    closes = pd.Series([100 + i for i in range(len(rng))], index=rng)
    rsi = compute_rsi(closes, period=9)
    # RSI should be a Series with same index and some non-null values towards the end
    assert isinstance(rsi, pd.Series)
    assert len(rsi) == len(closes)
    assert rsi.dropna().shape[0] > 0
