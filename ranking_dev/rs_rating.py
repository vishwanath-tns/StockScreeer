"""
RS Rating Calculator

Calculates Relative Strength Rating based on 12-month price performance.
RS Rating is a percentile ranking (1-99) where 99 = top 1% performer.

Formula:
- Calculate 12-month return for each stock
- Rank all stocks by return
- Convert rank to percentile (1-99)
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np


@dataclass
class RSResult:
    """Result of RS Rating calculation."""
    symbol: str
    return_12m: float  # 12-month return percentage
    rs_rating: float   # 1-99 scale
    rank: int          # Rank (1 = best)
    success: bool = True
    error: str = ""


class RSRatingCalculator:
    """
    Calculate Relative Strength Rating for stocks.
    
    RS Rating compares a stock's 12-month price performance
    against all other stocks and converts to a 1-99 scale.
    """
    
    def __init__(self):
        self.name = "RS Rating"
        self.score_type = "rs_rating"
    
    def calculate_return(
        self,
        df: pd.DataFrame,
        calculation_date: date,
        lookback_months: int = 12,
    ) -> Optional[float]:
        """
        Calculate return over lookback period.
        
        Args:
            df: DataFrame with 'date' and 'close' columns.
            calculation_date: End date for calculation.
            lookback_months: Months to look back (default 12).
            
        Returns:
            Percentage return or None if insufficient data.
        """
        if df.empty:
            return None
        
        # Ensure date column is datetime
        if "date" in df.columns:
            df = df.copy()
            df["date"] = pd.to_datetime(df["date"])
        
        # Get end price (latest available up to calculation_date)
        df_sorted = df.sort_values("date")
        df_valid = df_sorted[df_sorted["date"] <= pd.Timestamp(calculation_date)]
        
        if df_valid.empty:
            return None
        
        end_price = df_valid["close"].iloc[-1]
        end_date = df_valid["date"].iloc[-1]
        
        # Calculate start date (approximately 12 months ago)
        start_date = end_date - timedelta(days=lookback_months * 30)
        
        # Get start price (closest to start_date)
        df_start = df_sorted[df_sorted["date"] <= start_date]
        if df_start.empty:
            # Try to get earliest available
            df_start = df_sorted[df_sorted["date"] >= start_date - timedelta(days=30)]
            if df_start.empty:
                return None
        
        start_price = df_start["close"].iloc[-1] if not df_start.empty else df_sorted["close"].iloc[0]
        
        if start_price <= 0:
            return None
        
        # Calculate return percentage
        return_pct = ((end_price - start_price) / start_price) * 100
        return round(return_pct, 2)
    
    def calculate_single(
        self,
        symbol: str,
        df: pd.DataFrame,
        calculation_date: date,
    ) -> RSResult:
        """
        Calculate RS data for a single stock.
        
        Note: RS Rating requires batch calculation for ranking.
        This returns the 12M return; rating is set in batch.
        """
        try:
            return_12m = self.calculate_return(df, calculation_date)
            if return_12m is None:
                return RSResult(
                    symbol=symbol,
                    return_12m=0,
                    rs_rating=0,
                    rank=0,
                    success=False,
                    error="Insufficient data for 12M return"
                )
            
            return RSResult(
                symbol=symbol,
                return_12m=return_12m,
                rs_rating=0,  # Set in batch
                rank=0,       # Set in batch
            )
        except Exception as e:
            return RSResult(
                symbol=symbol,
                return_12m=0,
                rs_rating=0,
                rank=0,
                success=False,
                error=str(e)
            )
    
    def calculate_batch(
        self,
        data: Dict[str, pd.DataFrame],
        calculation_date: date,
    ) -> Dict[str, RSResult]:
        """
        Calculate RS Rating for all stocks.
        
        Args:
            data: Dict mapping symbol to price DataFrame.
            calculation_date: Date to calculate for.
            
        Returns:
            Dict mapping symbol to RSResult with ratings.
        """
        # Step 1: Calculate 12M returns for all stocks
        results = {}
        returns_list = []
        
        for symbol, df in data.items():
            result = self.calculate_single(symbol, df, calculation_date)
            results[symbol] = result
            if result.success:
                returns_list.append((symbol, result.return_12m))
        
        if not returns_list:
            return results
        
        # Step 2: Rank by return (higher is better)
        returns_list.sort(key=lambda x: x[1], reverse=True)
        total = len(returns_list)
        
        # Step 3: Assign ranks and RS ratings
        for rank, (symbol, _) in enumerate(returns_list, start=1):
            results[symbol].rank = rank
            # RS Rating: percentile (99 = top 1%, 1 = bottom 1%)
            # Formula: ((total - rank + 1) / total) * 98 + 1
            percentile = ((total - rank + 1) / total) * 98 + 1
            results[symbol].rs_rating = round(percentile, 0)
        
        return results


# Standalone test
if __name__ == "__main__":
    # Create sample data
    import random
    
    calc = RSRatingCalculator()
    today = date.today()
    
    # Generate test data for 10 stocks
    test_data = {}
    for i in range(10):
        symbol = f"STOCK{i+1}"
        dates = pd.date_range(end=today, periods=300, freq="D")
        # Random price with trend
        trend = random.uniform(-0.5, 1.5)  # -50% to +150%
        start_price = 100
        prices = [start_price * (1 + trend * j/300 + random.uniform(-0.02, 0.02)) 
                  for j in range(300)]
        test_data[symbol] = pd.DataFrame({
            "date": dates,
            "close": prices
        })
    
    # Calculate
    results = calc.calculate_batch(test_data, today)
    
    # Print results
    print("RS Rating Results:")
    print("-" * 50)
    sorted_results = sorted(results.values(), key=lambda r: r.rank if r.rank > 0 else 999)
    for r in sorted_results:
        print(f"{r.symbol:10} | 12M Return: {r.return_12m:+7.1f}% | RS Rating: {r.rs_rating:3.0f} | Rank: {r.rank}")
