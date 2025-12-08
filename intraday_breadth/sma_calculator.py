"""
Intraday SMA Breadth Calculator
===============================
Calculates % of Nifty 50 stocks above various SMAs (10, 20, 50, 200)
at each 5-minute interval.

Performance optimized using vectorized operations and pre-computed SMAs.
"""

import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class IntradaySMACalculator:
    """
    High-performance SMA breadth calculator.
    
    Calculates:
    - SMA 10, 20, 50, 200 for each stock
    - % of stocks above each SMA at each timestamp
    - Index SMAs for overlay on chart
    """
    
    SMA_PERIODS = [10, 20, 50, 200]
    
    def __init__(self):
        """Initialize the calculator."""
        # Cache for computed SMAs
        self._stock_smas: Dict[str, pd.DataFrame] = {}
        self._index_smas: Optional[pd.DataFrame] = None
        self._breadth_data: Optional[pd.DataFrame] = None
        
    def calculate_smas(self, df: pd.DataFrame, periods: List[int] = None) -> pd.DataFrame:
        """
        Calculate multiple SMAs for a price series.
        
        Args:
            df: DataFrame with 'close' column
            periods: List of SMA periods (default: [10, 20, 50, 200])
            
        Returns:
            DataFrame with SMA columns added
        """
        periods = periods or self.SMA_PERIODS
        result = df.copy()
        
        for period in periods:
            col_name = f'sma_{period}'
            result[col_name] = result['close'].rolling(window=period, min_periods=period).mean()
        
        return result
    
    def calculate_index_smas(self, index_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate SMAs for Nifty index (for chart overlay).
        
        Args:
            index_df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with price and SMA columns
        """
        if index_df.empty:
            return pd.DataFrame()
        
        result = self.calculate_smas(index_df, [10, 20, 50])  # Only short SMAs for index overlay
        self._index_smas = result
        return result
    
    def calculate_all_stock_smas(self, 
                                  stock_data: Dict[str, pd.DataFrame],
                                  progress_callback=None) -> Dict[str, pd.DataFrame]:
        """
        Calculate SMAs for all stocks.
        
        Args:
            stock_data: Dict mapping symbol to DataFrame
            progress_callback: Optional callback(current, total, symbol)
            
        Returns:
            Dict mapping symbol to DataFrame with SMAs
        """
        results = {}
        total = len(stock_data)
        
        for i, (symbol, df) in enumerate(stock_data.items()):
            if df.empty:
                continue
            
            results[symbol] = self.calculate_smas(df)
            
            if progress_callback:
                progress_callback(i + 1, total, symbol)
        
        self._stock_smas = results
        logger.info(f"Calculated SMAs for {len(results)} stocks")
        return results
    
    def calculate_breadth(self, stock_smas: Dict[str, pd.DataFrame] = None) -> pd.DataFrame:
        """
        Calculate % of stocks above each SMA at each timestamp.
        
        Args:
            stock_smas: Dict of stock DataFrames with SMAs (uses cache if None)
            
        Returns:
            DataFrame with columns: datetime, pct_above_sma10, pct_above_sma20, etc.
        """
        stock_smas = stock_smas or self._stock_smas
        
        if not stock_smas:
            logger.warning("No stock SMA data available")
            return pd.DataFrame()
        
        # Get union of all timestamps
        all_timestamps = set()
        for df in stock_smas.values():
            all_timestamps.update(df.index.tolist())
        
        all_timestamps = sorted(all_timestamps)
        
        # Initialize result arrays
        n_timestamps = len(all_timestamps)
        results = {
            'datetime': all_timestamps,
            'total_stocks': np.zeros(n_timestamps),
        }
        
        for period in self.SMA_PERIODS:
            results[f'above_sma_{period}'] = np.zeros(n_timestamps)
            results[f'pct_above_sma_{period}'] = np.zeros(n_timestamps)
        
        # Create timestamp to index mapping for fast lookup
        ts_to_idx = {ts: i for i, ts in enumerate(all_timestamps)}
        
        # Count stocks above each SMA at each timestamp
        for symbol, df in stock_smas.items():
            for ts in df.index:
                if ts not in ts_to_idx:
                    continue
                    
                idx = ts_to_idx[ts]
                close = df.loc[ts, 'close']
                
                if pd.isna(close):
                    continue
                
                results['total_stocks'][idx] += 1
                
                for period in self.SMA_PERIODS:
                    sma_col = f'sma_{period}'
                    if sma_col in df.columns:
                        sma_val = df.loc[ts, sma_col]
                        if not pd.isna(sma_val) and close > sma_val:
                            results[f'above_sma_{period}'][idx] += 1
        
        # Calculate percentages
        for period in self.SMA_PERIODS:
            above_col = f'above_sma_{period}'
            pct_col = f'pct_above_sma_{period}'
            
            # Avoid division by zero
            mask = results['total_stocks'] > 0
            results[pct_col][mask] = (
                results[above_col][mask] / results['total_stocks'][mask] * 100
            )
        
        # Create DataFrame
        breadth_df = pd.DataFrame(results)
        breadth_df.set_index('datetime', inplace=True)
        
        self._breadth_data = breadth_df
        logger.info(f"Calculated breadth for {len(breadth_df)} timestamps")
        
        return breadth_df
    
    def calculate_breadth_fast(self, stock_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Fast vectorized breadth calculation using pandas alignment.
        More efficient for large datasets.
        
        Args:
            stock_data: Dict mapping symbol to DataFrame with OHLCV data
            
        Returns:
            DataFrame with breadth indicators
        """
        if not stock_data:
            return pd.DataFrame()
        
        # Get common datetime index (union of all)
        all_indices = [df.index for df in stock_data.values() if not df.empty]
        if not all_indices:
            return pd.DataFrame()
        
        common_index = all_indices[0]
        for idx in all_indices[1:]:
            common_index = common_index.union(idx)
        common_index = common_index.sort_values()
        
        # Build matrices: rows = timestamps, cols = stocks
        n_times = len(common_index)
        n_stocks = len(stock_data)
        
        # Close prices matrix
        close_matrix = np.full((n_times, n_stocks), np.nan)
        
        # SMA matrices
        sma_matrices = {period: np.full((n_times, n_stocks), np.nan) for period in self.SMA_PERIODS}
        
        # Fill matrices
        for j, (symbol, df) in enumerate(stock_data.items()):
            if df.empty:
                continue
            
            # Reindex to common index
            df_aligned = df.reindex(common_index)
            
            close_matrix[:, j] = df_aligned['close'].values
            
            # Calculate SMAs
            close_series = df_aligned['close']
            for period in self.SMA_PERIODS:
                sma = close_series.rolling(window=period, min_periods=period).mean()
                sma_matrices[period][:, j] = sma.values
        
        # Calculate % above each SMA
        results = {'datetime': common_index}
        
        for period in self.SMA_PERIODS:
            # Boolean matrix: close > SMA
            above_mask = close_matrix > sma_matrices[period]
            
            # Valid counts (not NaN in both close and SMA)
            valid_mask = ~np.isnan(close_matrix) & ~np.isnan(sma_matrices[period])
            
            # Count above and total
            above_count = np.nansum(above_mask & valid_mask, axis=1)
            total_count = np.nansum(valid_mask, axis=1)
            
            # Calculate percentage
            pct = np.where(total_count > 0, above_count / total_count * 100, 0)
            
            results[f'count_above_sma_{period}'] = above_count.astype(int)
            results[f'total_valid_sma_{period}'] = total_count.astype(int)
            results[f'pct_above_sma_{period}'] = pct
        
        # Total stocks with valid close
        results['total_stocks'] = np.nansum(~np.isnan(close_matrix), axis=1).astype(int)
        
        breadth_df = pd.DataFrame(results)
        breadth_df.set_index('datetime', inplace=True)
        
        self._breadth_data = breadth_df
        logger.info(f"Fast breadth calculation: {len(breadth_df)} timestamps, {n_stocks} stocks")
        
        return breadth_df
    
    def update_incremental(self, 
                           index_df: pd.DataFrame,
                           stock_data: Dict[str, pd.DataFrame]) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Perform incremental update of SMAs and breadth using existing data plus new bars.
        More efficient than full recalculation - reuses existing SMA values where possible.
        
        Args:
            index_df: Full index DataFrame (merged old + new)
            stock_data: Full stock data dict (merged old + new)
            
        Returns:
            Tuple of (index_with_smas, breadth_df)
        """
        # Recalculate index SMAs
        index_with_smas = self.calculate_index_smas(index_df) if not index_df.empty else pd.DataFrame()
        
        # Recalculate breadth using the fast method
        breadth_df = self.calculate_breadth_fast(stock_data)
        
        return index_with_smas, breadth_df

    def get_current_breadth(self) -> Dict:
        """
        Get the most recent breadth values.
        
        Returns:
            Dict with current % above each SMA
        """
        if self._breadth_data is None or self._breadth_data.empty:
            return {}
        
        latest = self._breadth_data.iloc[-1]
        
        return {
            'timestamp': latest.name,
            'pct_above_sma_10': latest.get('pct_above_sma_10', 0),
            'pct_above_sma_20': latest.get('pct_above_sma_20', 0),
            'pct_above_sma_50': latest.get('pct_above_sma_50', 0),
            'pct_above_sma_200': latest.get('pct_above_sma_200', 0),
            'total_stocks': latest.get('total_stocks', 0),
        }
    
    def get_breadth_for_date(self, target_date: date) -> pd.DataFrame:
        """
        Get breadth data for a specific date.
        
        Args:
            target_date: The date to filter
            
        Returns:
            DataFrame filtered to the specified date
        """
        if self._breadth_data is None or self._breadth_data.empty:
            return pd.DataFrame()
        
        mask = self._breadth_data.index.date == target_date
        return self._breadth_data[mask].copy()
    
    def get_index_smas(self) -> Optional[pd.DataFrame]:
        """Get cached index SMA data."""
        return self._index_smas
    
    def get_breadth_data(self) -> Optional[pd.DataFrame]:
        """Get cached breadth data."""
        return self._breadth_data
    
    def clear_cache(self):
        """Clear all cached data."""
        self._stock_smas = {}
        self._index_smas = None
        self._breadth_data = None


# Quick test
if __name__ == "__main__":
    from data_fetcher import IntradayDataFetcher
    
    print("Testing SMA Calculator...")
    
    # Fetch data
    fetcher = IntradayDataFetcher(use_cache=False, max_workers=10)
    
    print("\nFetching Nifty index...")
    index_df = fetcher.fetch_nifty_index()
    print(f"Index: {len(index_df)} bars")
    
    print("\nFetching stocks (this may take a minute)...")
    def progress(cur, total, sym):
        print(f"  {cur}/{total}", end='\r')
    
    stock_data = fetcher.fetch_all_stocks(progress_callback=progress)
    print(f"\nFetched {len(stock_data)} stocks")
    
    # Calculate breadth
    calculator = IntradaySMACalculator()
    
    print("\nCalculating index SMAs...")
    index_smas = calculator.calculate_index_smas(index_df)
    print(index_smas.tail())
    
    print("\nCalculating breadth (fast method)...")
    breadth = calculator.calculate_breadth_fast(stock_data)
    print(breadth.tail())
    
    print("\nCurrent breadth:")
    current = calculator.get_current_breadth()
    for key, value in current.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.1f}%")
        else:
            print(f"  {key}: {value}")
