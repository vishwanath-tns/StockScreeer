"""
Bollinger Bands Calculator

Core calculation service for Bollinger Bands, %b, and BandWidth.
"""

import pandas as pd
import numpy as np
from datetime import date
from typing import Dict, List, Optional, Tuple

from ..models.bb_models import (
    BBConfig, BollingerBands, BBResult, BB_PRESETS
)


class BBCalculator:
    """
    Calculate Bollinger Bands and related indicators.
    
    Formulas:
    - Middle Band = 20-day SMA
    - Upper Band = Middle + (2 × 20-day StdDev)
    - Lower Band = Middle - (2 × 20-day StdDev)
    - %b = (Close - Lower) / (Upper - Lower)
    - BandWidth = (Upper - Lower) / Middle × 100
    """
    
    def __init__(self, config: BBConfig = None):
        """
        Initialize calculator with configuration.
        
        Args:
            config: BBConfig with period and std_dev. Default: standard (20, 2.0)
        """
        self.config = config or BB_PRESETS["standard"]
        self.name = "Bollinger Bands Calculator"
    
    def calculate(self, df: pd.DataFrame, 
                  bandwidth_lookback: int = 126) -> BBResult:
        """
        Calculate Bollinger Bands for a DataFrame.
        
        Args:
            df: DataFrame with 'date', 'close' columns (and optionally 'high', 'low')
            bandwidth_lookback: Days for BandWidth percentile calculation (default 126 = 6 months)
            
        Returns:
            BBResult with full time series and summary statistics
        """
        if df.empty or len(df) < self.config.period:
            return BBResult.failure(
                symbol=df.get("symbol", ["UNKNOWN"])[0] if not df.empty else "UNKNOWN",
                error=f"Insufficient data. Need at least {self.config.period} rows.",
                config=self.config
            )
        
        try:
            # Ensure sorted by date
            df = df.copy()
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date").reset_index(drop=True)
            
            symbol = df["symbol"].iloc[0] if "symbol" in df.columns else "UNKNOWN"
            
            # Calculate bands
            df = self._calculate_bands(df)
            
            # Calculate %b
            df = self._calculate_percent_b(df)
            
            # Calculate BandWidth and percentile
            df = self._calculate_bandwidth(df, bandwidth_lookback)
            
            # Build result
            return self._build_result(df, symbol)
            
        except Exception as e:
            return BBResult.failure(
                symbol=df.get("symbol", ["UNKNOWN"])[0] if not df.empty else "UNKNOWN",
                error=str(e),
                config=self.config
            )
    
    def _calculate_bands(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate upper, middle, lower bands."""
        period = self.config.period
        std_mult = self.config.std_dev
        
        # Middle band = SMA
        df["bb_middle"] = df["close"].rolling(window=period).mean()
        
        # Standard deviation
        df["bb_std"] = df["close"].rolling(window=period).std()
        
        # Upper and lower bands
        df["bb_upper"] = df["bb_middle"] + (std_mult * df["bb_std"])
        df["bb_lower"] = df["bb_middle"] - (std_mult * df["bb_std"])
        
        return df
    
    def _calculate_percent_b(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate %b indicator.
        
        %b = (Close - Lower Band) / (Upper Band - Lower Band)
        
        Interpretation:
        - %b > 1.0: Price above upper band (overbought)
        - %b = 1.0: Price at upper band
        - %b = 0.5: Price at middle band
        - %b = 0.0: Price at lower band
        - %b < 0.0: Price below lower band (oversold)
        """
        band_width = df["bb_upper"] - df["bb_lower"]
        
        # Avoid division by zero
        band_width = band_width.replace(0, np.nan)
        
        df["percent_b"] = (df["close"] - df["bb_lower"]) / band_width
        
        return df
    
    def _calculate_bandwidth(self, df: pd.DataFrame, 
                              lookback: int = 126) -> pd.DataFrame:
        """
        Calculate BandWidth and its historical percentile.
        
        BandWidth = (Upper - Lower) / Middle × 100
        
        Low BandWidth = low volatility = potential squeeze
        High BandWidth = high volatility = potential exhaustion
        """
        # BandWidth as percentage
        df["bandwidth"] = ((df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]) * 100
        
        # Calculate rolling percentile of bandwidth
        def rolling_percentile(series, value, window):
            """Calculate what percentile the current value is in the rolling window."""
            result = []
            for i in range(len(series)):
                if i < window - 1:
                    result.append(50.0)  # Default to 50 if not enough data
                else:
                    window_data = series.iloc[i - window + 1:i + 1]
                    current = series.iloc[i]
                    percentile = (window_data < current).sum() / len(window_data) * 100
                    result.append(percentile)
            return result
        
        df["bandwidth_percentile"] = rolling_percentile(
            df["bandwidth"], df["bandwidth"], lookback
        )
        
        return df
    
    def _build_result(self, df: pd.DataFrame, symbol: str) -> BBResult:
        """Build BBResult from calculated DataFrame."""
        # Filter to valid rows (where BB values exist)
        valid_df = df.dropna(subset=["bb_middle", "bb_upper", "bb_lower"])
        
        if valid_df.empty:
            return BBResult.failure(symbol, "No valid BB values calculated", self.config)
        
        # Build history list (most recent first)
        history = []
        for _, row in valid_df.iloc[::-1].iterrows():
            bb = BollingerBands(
                date=row["date"].date() if hasattr(row["date"], "date") else row["date"],
                close=row["close"],
                upper=row["bb_upper"],
                middle=row["bb_middle"],
                lower=row["bb_lower"],
                percent_b=row["percent_b"],
                bandwidth=row["bandwidth"],
                bandwidth_percentile=row["bandwidth_percentile"]
            )
            history.append(bb)
        
        # Calculate summary statistics
        bw_series = valid_df["bandwidth"]
        
        # Count specific conditions
        days_in_squeeze = (valid_df["bandwidth_percentile"] <= 5).sum()
        days_above_upper = (valid_df["percent_b"] > 1.0).sum()
        days_below_lower = (valid_df["percent_b"] < 0.0).sum()
        
        return BBResult(
            symbol=symbol,
            config=self.config,
            calculation_date=history[0].date if history else date.today(),
            current=history[0] if history else None,
            history=history,
            avg_bandwidth=bw_series.mean(),
            min_bandwidth=bw_series.min(),
            max_bandwidth=bw_series.max(),
            days_in_squeeze=int(days_in_squeeze),
            days_above_upper=int(days_above_upper),
            days_below_lower=int(days_below_lower),
            success=True,
            error=""
        )
    
    def calculate_single_day(self, prices: List[float], 
                              current_close: float) -> Optional[BollingerBands]:
        """
        Calculate BB for a single day given price history.
        
        Args:
            prices: List of closing prices (at least 'period' values)
            current_close: Current day's close price
            
        Returns:
            BollingerBands for current day or None
        """
        period = self.config.period
        
        if len(prices) < period:
            return None
        
        # Use the last 'period' prices
        recent = prices[-period:]
        
        # Calculate bands
        middle = np.mean(recent)
        std = np.std(recent, ddof=1)  # Sample std dev
        upper = middle + (self.config.std_dev * std)
        lower = middle - (self.config.std_dev * std)
        
        # Calculate %b
        band_range = upper - lower
        if band_range == 0:
            percent_b = 0.5
        else:
            percent_b = (current_close - lower) / band_range
        
        # Calculate bandwidth
        bandwidth = (band_range / middle) * 100 if middle != 0 else 0
        
        return BollingerBands(
            date=date.today(),
            close=current_close,
            upper=upper,
            middle=middle,
            lower=lower,
            percent_b=percent_b,
            bandwidth=bandwidth,
            bandwidth_percentile=50.0  # Would need history for real percentile
        )
    
    def calculate_batch(self, data: Dict[str, pd.DataFrame],
                        bandwidth_lookback: int = 126) -> Dict[str, BBResult]:
        """
        Calculate BB for multiple symbols.
        
        Args:
            data: Dict mapping symbol to price DataFrame
            bandwidth_lookback: Days for BandWidth percentile
            
        Returns:
            Dict mapping symbol to BBResult
        """
        results = {}
        
        for symbol, df in data.items():
            # Add symbol column if not present
            if "symbol" not in df.columns:
                df = df.copy()
                df["symbol"] = symbol
            
            result = self.calculate(df, bandwidth_lookback)
            results[symbol] = result
        
        return results


def calculate_bb_from_series(closes: pd.Series, 
                              period: int = 20,
                              std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Convenience function to calculate BB from a price series.
    
    Returns:
        Tuple of (upper, middle, lower) Series
    """
    middle = closes.rolling(window=period).mean()
    std = closes.rolling(window=period).std()
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)
    
    return upper, middle, lower


def calculate_percent_b(close: float, upper: float, lower: float) -> float:
    """
    Calculate %b for a single price.
    
    Returns:
        %b value (can be < 0 or > 1)
    """
    if upper == lower:
        return 0.5
    return (close - lower) / (upper - lower)


def calculate_bandwidth(upper: float, middle: float, lower: float) -> float:
    """
    Calculate BandWidth as percentage.
    
    Returns:
        BandWidth percentage
    """
    if middle == 0:
        return 0.0
    return ((upper - lower) / middle) * 100
