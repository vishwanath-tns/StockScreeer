"""
Volume Profile Calculator
=========================
Core calculation logic for Volume Profiles, VPOC, and Value Area.

Volume Profile shows the distribution of trading volume at different price levels.
This helps identify important support/resistance zones.

Key outputs:
- VPOC (Volume Point of Control): Price with highest traded volume
- VAH (Value Area High): Upper boundary of 70% volume concentration
- VAL (Value Area Low): Lower boundary of 70% volume concentration
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta
import yfinance as yf
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class VolumeProfile:
    """
    Represents a Volume Profile for a single trading session.
    """
    date: date
    price_levels: np.ndarray      # Price bins
    volume_at_price: np.ndarray   # Volume at each price level
    vpoc: float                   # Volume Point of Control
    vah: float                    # Value Area High
    val: float                    # Value Area Low
    total_volume: float           # Total volume for the day
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    tick_size: float              # Price bin size
    
    @property
    def value_area_pct(self) -> float:
        """Percentage of price range covered by Value Area."""
        if self.high_price == self.low_price:
            return 100.0
        return (self.vah - self.val) / (self.high_price - self.low_price) * 100
    
    @property
    def vpoc_volume_pct(self) -> float:
        """VPOC volume as percentage of total volume."""
        if self.total_volume == 0:
            return 0.0
        vpoc_idx = np.argmin(np.abs(self.price_levels - self.vpoc))
        return self.volume_at_price[vpoc_idx] / self.total_volume * 100
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'date': self.date.isoformat(),
            'vpoc': self.vpoc,
            'vah': self.vah,
            'val': self.val,
            'total_volume': self.total_volume,
            'open': self.open_price,
            'high': self.high_price,
            'low': self.low_price,
            'close': self.close_price,
            'value_area_pct': self.value_area_pct,
        }


class VolumeProfileCalculator:
    """
    Calculate Volume Profiles from intraday data.
    
    Features:
    - Fetch 1-minute data from Yahoo Finance
    - Build volume profile with configurable tick size
    - Calculate VPOC (highest volume price)
    - Calculate Value Area (70% volume concentration)
    """
    
    DEFAULT_VALUE_AREA_PCT = 70.0  # 70% of volume
    DEFAULT_NUM_BINS = 50         # Number of price bins
    
    def __init__(self, 
                 value_area_pct: float = DEFAULT_VALUE_AREA_PCT,
                 num_bins: int = DEFAULT_NUM_BINS):
        """
        Initialize the calculator.
        
        Args:
            value_area_pct: Percentage of volume for Value Area (default 70%)
            num_bins: Number of price bins for the profile
        """
        self.value_area_pct = value_area_pct
        self.num_bins = num_bins
    
    def fetch_intraday_data(self, 
                            symbol: str = "^NSEI",
                            days: int = 5,
                            retries: int = 3) -> pd.DataFrame:
        """
        Fetch 1-minute intraday data from Yahoo Finance.
        
        Args:
            symbol: Yahoo Finance symbol (default: ^NSEI for Nifty 50)
            days: Number of days to fetch (max ~7 for 1m data)
            retries: Number of retry attempts
            
        Returns:
            DataFrame with intraday OHLCV data
        """
        import time
        
        logger.info(f"Fetching {days} days of 1-min data for {symbol}...")
        
        # Yahoo allows max 7 days for 1m data
        days = min(days, 7)
        
        df = pd.DataFrame()
        
        for attempt in range(retries):
            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(period=f"{days}d", interval="1m")
                
                if not df.empty:
                    break
                    
                logger.warning(f"Attempt {attempt+1}: No data for {symbol}, retrying...")
                time.sleep(1)
                
            except Exception as e:
                logger.warning(f"Attempt {attempt+1} failed: {e}")
                time.sleep(1)
        
        if df.empty:
            logger.warning(f"No data returned for {symbol} after {retries} attempts")
            return df
        
        # Reset index to get datetime as column
        df = df.reset_index()
        df = df.rename(columns={
            'Datetime': 'datetime',
            'Date': 'datetime',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })
        
        # Ensure datetime is timezone-aware or naive consistently
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
            df['date'] = df['datetime'].dt.date
        
        logger.info(f"Fetched {len(df)} records from {df['date'].min()} to {df['date'].max()}")
        
        return df
    
    def calculate_profile(self, 
                         df: pd.DataFrame,
                         num_bins: Optional[int] = None) -> VolumeProfile:
        """
        Calculate volume profile for given OHLCV data.
        
        Args:
            df: DataFrame with columns: open, high, low, close, volume
            num_bins: Number of price bins (optional, uses default)
            
        Returns:
            VolumeProfile object
        """
        if df.empty:
            raise ValueError("Cannot calculate profile for empty DataFrame")
        
        num_bins = num_bins or self.num_bins
        
        # Get price range
        price_high = df['high'].max()
        price_low = df['low'].min()
        
        if price_high == price_low:
            price_high = price_low * 1.001  # Small adjustment
        
        # Create price bins
        tick_size = (price_high - price_low) / num_bins
        price_levels = np.linspace(price_low, price_high, num_bins + 1)
        
        # Calculate volume at each price level
        # We distribute each candle's volume across the price range it covers
        volume_at_price = np.zeros(num_bins)
        
        for _, row in df.iterrows():
            candle_low = row['low']
            candle_high = row['high']
            candle_volume = row['volume']
            
            if candle_volume == 0 or pd.isna(candle_volume):
                continue
            
            # Find which bins this candle spans
            low_bin = max(0, int((candle_low - price_low) / tick_size))
            high_bin = min(num_bins - 1, int((candle_high - price_low) / tick_size))
            
            # Distribute volume across covered bins
            bins_covered = high_bin - low_bin + 1
            volume_per_bin = candle_volume / bins_covered
            
            for b in range(low_bin, high_bin + 1):
                if 0 <= b < num_bins:
                    volume_at_price[b] += volume_per_bin
        
        # Calculate VPOC (price level with maximum volume)
        vpoc_idx = np.argmax(volume_at_price)
        vpoc = price_levels[vpoc_idx] + tick_size / 2  # Center of bin
        
        # Calculate Value Area (70% of volume)
        val, vah = self._calculate_value_area(
            price_levels, volume_at_price, tick_size
        )
        
        # Get OHLC for the period
        profile_date = df['date'].iloc[0] if 'date' in df.columns else date.today()
        
        return VolumeProfile(
            date=profile_date,
            price_levels=price_levels[:-1] + tick_size / 2,  # Bin centers
            volume_at_price=volume_at_price,
            vpoc=vpoc,
            vah=vah,
            val=val,
            total_volume=volume_at_price.sum(),
            open_price=df['open'].iloc[0],
            high_price=price_high,
            low_price=price_low,
            close_price=df['close'].iloc[-1],
            tick_size=tick_size
        )
    
    def _calculate_value_area(self,
                              price_levels: np.ndarray,
                              volume_at_price: np.ndarray,
                              tick_size: float) -> Tuple[float, float]:
        """
        Calculate Value Area - the price range containing X% of volume.
        
        Uses the TPO (Time Price Opportunity) method:
        1. Start at VPOC
        2. Add prices above and below based on which has more volume
        3. Continue until we reach the target volume percentage
        
        Args:
            price_levels: Array of price bin edges
            volume_at_price: Volume at each price level
            tick_size: Size of each price bin
            
        Returns:
            Tuple of (VAL, VAH)
        """
        total_volume = volume_at_price.sum()
        target_volume = total_volume * (self.value_area_pct / 100.0)
        
        if total_volume == 0:
            return price_levels[0], price_levels[-1]
        
        # Start at VPOC
        vpoc_idx = np.argmax(volume_at_price)
        
        current_volume = volume_at_price[vpoc_idx]
        low_idx = vpoc_idx
        high_idx = vpoc_idx
        
        # Expand outward until we capture target volume
        while current_volume < target_volume:
            # Check volume at adjacent levels
            vol_above = volume_at_price[high_idx + 1] if high_idx + 1 < len(volume_at_price) else 0
            vol_below = volume_at_price[low_idx - 1] if low_idx - 1 >= 0 else 0
            
            if vol_above == 0 and vol_below == 0:
                break
            
            # Expand in direction with more volume
            if vol_above >= vol_below and high_idx + 1 < len(volume_at_price):
                high_idx += 1
                current_volume += vol_above
            elif low_idx - 1 >= 0:
                low_idx -= 1
                current_volume += vol_below
            elif high_idx + 1 < len(volume_at_price):
                high_idx += 1
                current_volume += vol_above
            else:
                break
        
        # Convert indices to prices
        val = price_levels[low_idx]
        vah = price_levels[min(high_idx + 1, len(price_levels) - 1)]
        
        return val, vah
    
    def calculate_daily_profiles(self,
                                 symbol: str = "^NSEI",
                                 days: int = 5) -> List[VolumeProfile]:
        """
        Calculate volume profiles for each trading day.
        
        Args:
            symbol: Yahoo Finance symbol
            days: Number of days to analyze
            
        Returns:
            List of VolumeProfile objects, one per day
        """
        # Fetch data
        df = self.fetch_intraday_data(symbol, days)
        
        if df.empty:
            return []
        
        # Group by date and calculate profile for each day
        profiles = []
        
        for trade_date, day_df in df.groupby('date'):
            try:
                profile = self.calculate_profile(day_df)
                profiles.append(profile)
                logger.info(f"  {trade_date}: VPOC={profile.vpoc:.2f}, "
                          f"VAL={profile.val:.2f}, VAH={profile.vah:.2f}")
            except Exception as e:
                logger.warning(f"Could not calculate profile for {trade_date}: {e}")
        
        return sorted(profiles, key=lambda p: p.date)
    
    def get_profiles_summary(self, profiles: List[VolumeProfile]) -> pd.DataFrame:
        """
        Create summary DataFrame of all profiles.
        
        Args:
            profiles: List of VolumeProfile objects
            
        Returns:
            DataFrame with profile summaries
        """
        data = []
        for p in profiles:
            data.append({
                'Date': p.date,
                'Open': p.open_price,
                'High': p.high_price,
                'Low': p.low_price,
                'Close': p.close_price,
                'VPOC': p.vpoc,
                'VAH': p.vah,
                'VAL': p.val,
                'VA Range': p.vah - p.val,
                'VA %': p.value_area_pct,
                'Total Volume': p.total_volume,
            })
        
        return pd.DataFrame(data)


def main():
    """Test the calculator."""
    calc = VolumeProfileCalculator(value_area_pct=70, num_bins=50)
    
    print("=" * 70)
    print("   VOLUME PROFILE CALCULATOR")
    print("=" * 70)
    print()
    
    # Calculate profiles for Nifty
    profiles = calc.calculate_daily_profiles("^NSEI", days=5)
    
    if profiles:
        print("\n" + "=" * 70)
        print("   DAILY PROFILES SUMMARY")
        print("=" * 70)
        
        summary = calc.get_profiles_summary(profiles)
        print(summary.to_string(index=False))
        
        print("\n✅ Volume profiles calculated successfully!")
    else:
        print("❌ No profiles could be calculated")


if __name__ == "__main__":
    main()
