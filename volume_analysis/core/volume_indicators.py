"""
Volume Indicators
=================

Core volume-based technical indicators for accumulation/distribution analysis.

Indicators:
- OBV (On-Balance Volume) - Cumulative volume flow
- A/D Line (Accumulation/Distribution Line) - Money flow based on close location
- CMF (Chaikin Money Flow) - 20-period money flow ratio
- VWAP (Volume Weighted Average Price) - Volume-weighted price
- Volume SMA - Simple moving averages of volume
- Volume Ratio - Current volume vs average volume
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class VolumeIndicators:
    """
    Calculate volume-based technical indicators.
    
    All methods take a DataFrame with OHLCV data and return the same
    DataFrame with additional indicator columns added.
    
    Required columns: open, high, low, close, volume
    Optional columns: date (for VWAP reset)
    """
    
    def __init__(self):
        pass
    
    def calculate_all(self, df: pd.DataFrame, 
                      obv: bool = True,
                      ad_line: bool = True,
                      cmf: bool = True,
                      cmf_period: int = 20,
                      vwap: bool = True,
                      volume_sma: bool = True,
                      sma_periods: list = None) -> pd.DataFrame:
        """
        Calculate all volume indicators at once.
        
        Args:
            df: DataFrame with OHLCV data
            obv: Include On-Balance Volume
            ad_line: Include A/D Line
            cmf: Include Chaikin Money Flow
            cmf_period: Period for CMF calculation
            vwap: Include VWAP
            volume_sma: Include Volume SMAs
            sma_periods: Periods for Volume SMA (default: [10, 20, 50])
            
        Returns:
            DataFrame with all requested indicators added
        """
        result = df.copy()
        
        if sma_periods is None:
            sma_periods = [10, 20, 50]
        
        if obv:
            result = self.calculate_obv(result)
        
        if ad_line:
            result = self.calculate_ad_line(result)
        
        if cmf:
            result = self.calculate_cmf(result, period=cmf_period)
        
        if vwap:
            result = self.calculate_vwap(result)
        
        if volume_sma:
            result = self.calculate_volume_sma(result, periods=sma_periods)
            result = self.calculate_volume_ratio(result)
        
        return result
    
    def calculate_obv(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate On-Balance Volume (OBV).
        
        OBV is a cumulative indicator that adds volume on up days
        and subtracts volume on down days. It helps identify
        whether volume is flowing into or out of a security.
        
        Formula:
        - If close > previous close: OBV = Previous OBV + Volume
        - If close < previous close: OBV = Previous OBV - Volume
        - If close = previous close: OBV = Previous OBV
        
        Accumulation Signal: Rising OBV with flat/rising price
        Distribution Signal: Falling OBV with flat/falling price
        
        Args:
            df: DataFrame with 'close' and 'volume' columns
            
        Returns:
            DataFrame with 'obv' column added
        """
        result = df.copy()
        
        # Calculate price direction
        close_diff = result['close'].diff()
        
        # OBV calculation
        obv = pd.Series(index=result.index, dtype=float)
        obv.iloc[0] = 0
        
        for i in range(1, len(result)):
            if close_diff.iloc[i] > 0:
                obv.iloc[i] = obv.iloc[i-1] + result['volume'].iloc[i]
            elif close_diff.iloc[i] < 0:
                obv.iloc[i] = obv.iloc[i-1] - result['volume'].iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        
        result['obv'] = obv
        
        # OBV SMA for trend analysis
        result['obv_sma_20'] = result['obv'].rolling(window=20).mean()
        
        # OBV trend (positive = accumulation, negative = distribution)
        result['obv_trend'] = result['obv'] - result['obv_sma_20']
        
        return result
    
    def calculate_ad_line(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Accumulation/Distribution Line.
        
        The A/D Line uses the relationship between price and volume to
        determine if money is flowing into (accumulation) or out of
        (distribution) a security.
        
        Formula:
        1. Money Flow Multiplier (MFM) = [(Close - Low) - (High - Close)] / (High - Low)
        2. Money Flow Volume (MFV) = MFM × Volume
        3. A/D Line = Previous A/D + Current MFV
        
        The MFM ranges from -1 to +1:
        - Close at high: MFM = +1 (strong buying pressure)
        - Close at low: MFM = -1 (strong selling pressure)
        - Close at midpoint: MFM = 0
        
        Args:
            df: DataFrame with OHLC and volume columns
            
        Returns:
            DataFrame with 'ad_line', 'mfm', 'mfv' columns added
        """
        result = df.copy()
        
        # Money Flow Multiplier
        high_low_range = result['high'] - result['low']
        
        # Avoid division by zero
        high_low_range = high_low_range.replace(0, np.nan)
        
        mfm = ((result['close'] - result['low']) - (result['high'] - result['close'])) / high_low_range
        mfm = mfm.fillna(0)
        
        result['mfm'] = mfm
        
        # Money Flow Volume
        result['mfv'] = mfm * result['volume']
        
        # Cumulative A/D Line
        result['ad_line'] = result['mfv'].cumsum()
        
        # A/D Line SMA for trend
        result['ad_line_sma_20'] = result['ad_line'].rolling(window=20).mean()
        
        # A/D trend
        result['ad_trend'] = result['ad_line'] - result['ad_line_sma_20']
        
        return result
    
    def calculate_cmf(self, df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        """
        Calculate Chaikin Money Flow (CMF).
        
        CMF measures buying and selling pressure over a period.
        It oscillates between -1 and +1.
        
        Formula:
        CMF = Sum(MFV over N periods) / Sum(Volume over N periods)
        
        Where MFV = Money Flow Multiplier × Volume (from A/D Line calculation)
        
        Interpretation:
        - CMF > 0: Buying pressure (accumulation)
        - CMF < 0: Selling pressure (distribution)
        - CMF > 0.25: Strong buying pressure
        - CMF < -0.25: Strong selling pressure
        
        Args:
            df: DataFrame with OHLC and volume columns
            period: Lookback period (default 20)
            
        Returns:
            DataFrame with 'cmf' column added
        """
        result = df.copy()
        
        # Ensure MFV is calculated
        if 'mfv' not in result.columns:
            result = self.calculate_ad_line(result)
        
        # CMF = Sum(MFV) / Sum(Volume) over period
        mfv_sum = result['mfv'].rolling(window=period).sum()
        vol_sum = result['volume'].rolling(window=period).sum()
        
        # Avoid division by zero
        vol_sum = vol_sum.replace(0, np.nan)
        
        result['cmf'] = mfv_sum / vol_sum
        result['cmf'] = result['cmf'].fillna(0)
        
        return result
    
    def calculate_vwap(self, df: pd.DataFrame, reset_daily: bool = True) -> pd.DataFrame:
        """
        Calculate Volume Weighted Average Price (VWAP).
        
        VWAP is the average price weighted by volume, often used as
        a trading benchmark.
        
        Formula:
        VWAP = Cumulative(Typical Price × Volume) / Cumulative(Volume)
        
        Where Typical Price = (High + Low + Close) / 3
        
        Interpretation:
        - Price > VWAP: Bullish (buyers paying above average)
        - Price < VWAP: Bearish (sellers accepting below average)
        
        Args:
            df: DataFrame with OHLC and volume columns
            reset_daily: Reset VWAP calculation each day (requires 'date' column)
            
        Returns:
            DataFrame with 'vwap' column added
        """
        result = df.copy()
        
        # Typical price
        typical_price = (result['high'] + result['low'] + result['close']) / 3
        
        # Price × Volume
        result['_pv'] = typical_price * result['volume']
        
        if reset_daily and 'date' in result.columns:
            # Reset VWAP each day (for intraday analysis)
            try:
                result['vwap'] = result.groupby(result['date'].dt.date).apply(
                    lambda x: (x['_pv'].cumsum() / x['volume'].cumsum()).values
                ).explode().values
            except Exception:
                # Fallback to cumulative VWAP
                result['vwap'] = result['_pv'].cumsum() / result['volume'].cumsum()
        else:
            # Cumulative VWAP (for daily data)
            result['vwap'] = result['_pv'].cumsum() / result['volume'].cumsum()
        
        # Clean up temporary column
        result = result.drop(columns=['_pv'])
        
        # VWAP deviation
        result['vwap_deviation'] = (result['close'] - result['vwap']) / result['vwap'] * 100
        
        return result
    
    def calculate_volume_sma(self, df: pd.DataFrame, 
                              periods: list = None) -> pd.DataFrame:
        """
        Calculate Simple Moving Averages of Volume.
        
        Args:
            df: DataFrame with 'volume' column
            periods: List of SMA periods (default: [10, 20, 50])
            
        Returns:
            DataFrame with 'volume_sma_N' columns added
        """
        result = df.copy()
        
        if periods is None:
            periods = [10, 20, 50]
        
        for period in periods:
            result[f'volume_sma_{period}'] = result['volume'].rolling(window=period).mean()
        
        return result
    
    def calculate_volume_ratio(self, df: pd.DataFrame, 
                                period: int = 20) -> pd.DataFrame:
        """
        Calculate Volume Ratio (current volume vs average).
        
        Volume Ratio > 2.0 indicates significant volume surge,
        often preceding important price moves.
        
        Args:
            df: DataFrame with volume and volume SMA columns
            period: Reference period for average volume
            
        Returns:
            DataFrame with 'volume_ratio' column added
        """
        result = df.copy()
        
        sma_col = f'volume_sma_{period}'
        
        if sma_col not in result.columns:
            result[sma_col] = result['volume'].rolling(window=period).mean()
        
        # Avoid division by zero
        avg_vol = result[sma_col].replace(0, np.nan)
        
        result['volume_ratio'] = result['volume'] / avg_vol
        result['volume_ratio'] = result['volume_ratio'].fillna(1.0)
        
        return result
    
    def calculate_volume_trend(self, df: pd.DataFrame, 
                                period: int = 20) -> pd.DataFrame:
        """
        Calculate Volume Trend using linear regression slope.
        
        Positive slope indicates increasing volume interest.
        Negative slope indicates declining volume interest.
        
        Args:
            df: DataFrame with 'volume' column
            period: Lookback period for trend calculation
            
        Returns:
            DataFrame with 'volume_trend' column added
        """
        result = df.copy()
        
        def calculate_slope(series):
            """Calculate linear regression slope."""
            if len(series) < 2 or series.isna().all():
                return np.nan
            
            x = np.arange(len(series))
            y = series.values
            
            # Remove NaN values
            mask = ~np.isnan(y)
            if mask.sum() < 2:
                return np.nan
            
            x, y = x[mask], y[mask]
            
            # Linear regression
            slope = np.polyfit(x, y, 1)[0]
            
            # Normalize by mean volume
            mean_vol = np.mean(y)
            if mean_vol > 0:
                slope = slope / mean_vol * 100  # Percentage change per day
            
            return slope
        
        result['volume_trend'] = result['volume'].rolling(window=period).apply(
            calculate_slope, raw=False
        )
        
        return result
    
    def detect_volume_dryup(self, df: pd.DataFrame, 
                            threshold: float = 0.5,
                            period: int = 5) -> pd.DataFrame:
        """
        Detect volume dry-up patterns (potential breakout setup).
        
        Volume dry-up occurs when recent volume is significantly
        below average, often preceding explosive breakouts.
        
        Args:
            df: DataFrame with volume data
            threshold: Volume ratio threshold (0.5 = 50% of average)
            period: Number of consecutive low-volume days to check
            
        Returns:
            DataFrame with 'volume_dryup' column (True/False)
        """
        result = df.copy()
        
        if 'volume_ratio' not in result.columns:
            result = self.calculate_volume_ratio(result)
        
        # Check for consecutive low volume days
        low_volume = result['volume_ratio'] < threshold
        
        # Rolling sum of low volume days
        result['low_vol_streak'] = low_volume.rolling(window=period).sum()
        
        # Volume dry-up when all recent days are low volume
        result['volume_dryup'] = result['low_vol_streak'] >= period
        
        return result
    
    def detect_volume_surge(self, df: pd.DataFrame,
                            threshold: float = 2.0) -> pd.DataFrame:
        """
        Detect volume surge (breakout confirmation).
        
        Volume surge occurs when current volume is significantly
        above average, confirming price breakouts.
        
        Args:
            df: DataFrame with volume data
            threshold: Volume ratio threshold (2.0 = 200% of average)
            
        Returns:
            DataFrame with 'volume_surge' column (True/False)
        """
        result = df.copy()
        
        if 'volume_ratio' not in result.columns:
            result = self.calculate_volume_ratio(result)
        
        result['volume_surge'] = result['volume_ratio'] >= threshold
        
        return result
    
    def get_summary(self, df: pd.DataFrame) -> dict:
        """
        Get summary statistics for volume indicators.
        
        Args:
            df: DataFrame with calculated indicators
            
        Returns:
            Dictionary with summary statistics
        """
        result = df.copy()
        
        # Ensure all indicators are calculated
        if 'obv' not in result.columns:
            result = self.calculate_all(result)
        
        latest = result.iloc[-1]
        
        summary = {
            # OBV Analysis
            'obv_current': latest.get('obv', np.nan),
            'obv_trend': latest.get('obv_trend', np.nan),
            'obv_trending_up': latest.get('obv_trend', 0) > 0,
            
            # A/D Line Analysis
            'ad_line_current': latest.get('ad_line', np.nan),
            'ad_trend': latest.get('ad_trend', np.nan),
            'ad_trending_up': latest.get('ad_trend', 0) > 0,
            
            # CMF Analysis
            'cmf': latest.get('cmf', np.nan),
            'cmf_bullish': latest.get('cmf', 0) > 0,
            'cmf_strong_bullish': latest.get('cmf', 0) > 0.25,
            'cmf_strong_bearish': latest.get('cmf', 0) < -0.25,
            
            # Volume Analysis
            'volume_ratio': latest.get('volume_ratio', np.nan),
            'volume_surge': latest.get('volume_surge', False),
            'volume_dryup': latest.get('volume_dryup', False),
            
            # Recent averages (last 5 days)
            'cmf_5d_avg': result['cmf'].tail(5).mean() if 'cmf' in result.columns else np.nan,
            'volume_ratio_5d_avg': result['volume_ratio'].tail(5).mean() if 'volume_ratio' in result.columns else np.nan,
        }
        
        return summary


# Convenience functions
def calculate_obv(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate On-Balance Volume."""
    return VolumeIndicators().calculate_obv(df)


def calculate_ad_line(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate Accumulation/Distribution Line."""
    return VolumeIndicators().calculate_ad_line(df)


def calculate_cmf(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Calculate Chaikin Money Flow."""
    return VolumeIndicators().calculate_cmf(df, period)


if __name__ == "__main__":
    # Test with sample data
    import yfinance as yf
    
    print("Testing Volume Indicators...")
    
    # Download sample data
    ticker = yf.Ticker("RELIANCE.NS")
    df = ticker.history(period="6mo")
    
    # Rename columns to lowercase
    df.columns = df.columns.str.lower()
    df = df.reset_index()
    df = df.rename(columns={'Date': 'date'})
    
    # Calculate indicators
    vi = VolumeIndicators()
    result = vi.calculate_all(df)
    
    # Get summary
    summary = vi.get_summary(result)
    
    print("\nLatest Values:")
    print(f"  OBV Trend: {'↑ Bullish' if summary['obv_trending_up'] else '↓ Bearish'}")
    print(f"  A/D Trend: {'↑ Bullish' if summary['ad_trending_up'] else '↓ Bearish'}")
    print(f"  CMF: {summary['cmf']:.3f} ({'Buying Pressure' if summary['cmf_bullish'] else 'Selling Pressure'})")
    print(f"  Volume Ratio: {summary['volume_ratio']:.2f}x")
    
    print("\nLast 5 rows:")
    print(result[['date', 'close', 'volume', 'obv', 'ad_line', 'cmf', 'volume_ratio']].tail())
