"""
RS Rating Calculator

Calculates Relative Strength Rating based on 12-month price performance.
RS Rating is a percentile ranking (1-99) where 99 = top 1% performer.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional
import pandas as pd


@dataclass
class RSResult:
    """Result of RS Rating calculation."""
    symbol: str
    return_12m: float
    rs_rating: float
    rank: int
    success: bool = True
    error: str = ""


class RSRatingService:
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
        """Calculate return over lookback period."""
        if df.empty:
            return None
        
        if "date" in df.columns:
            df = df.copy()
            df["date"] = pd.to_datetime(df["date"])
        
        df_sorted = df.sort_values("date")
        df_valid = df_sorted[df_sorted["date"] <= pd.Timestamp(calculation_date)]
        
        if df_valid.empty:
            return None
        
        end_price = df_valid["close"].iloc[-1]
        end_date = df_valid["date"].iloc[-1]
        
        start_date = end_date - timedelta(days=lookback_months * 30)
        
        df_start = df_sorted[df_sorted["date"] <= start_date]
        if df_start.empty:
            df_start = df_sorted[df_sorted["date"] >= start_date - timedelta(days=30)]
            if df_start.empty:
                return None
        
        start_price = df_start["close"].iloc[-1] if not df_start.empty else df_sorted["close"].iloc[0]
        
        if start_price <= 0:
            return None
        
        return round(((end_price - start_price) / start_price) * 100, 2)
    
    def calculate_single(
        self,
        symbol: str,
        df: pd.DataFrame,
        calculation_date: date,
    ) -> RSResult:
        """Calculate RS data for a single stock."""
        try:
            return_12m = self.calculate_return(df, calculation_date)
            if return_12m is None:
                return RSResult(
                    symbol=symbol, return_12m=0, rs_rating=0, rank=0,
                    success=False, error="Insufficient data for 12M return"
                )
            
            return RSResult(symbol=symbol, return_12m=return_12m, rs_rating=0, rank=0)
        except Exception as e:
            return RSResult(
                symbol=symbol, return_12m=0, rs_rating=0, rank=0,
                success=False, error=str(e)
            )
    
    def calculate_batch(
        self,
        data: Dict[str, pd.DataFrame],
        calculation_date: date,
    ) -> Dict[str, RSResult]:
        """Calculate RS Rating for all stocks with ranks and percentiles."""
        results = {}
        returns_list = []
        
        for symbol, df in data.items():
            result = self.calculate_single(symbol, df, calculation_date)
            results[symbol] = result
            if result.success:
                returns_list.append((symbol, result.return_12m))
        
        if not returns_list:
            return results
        
        returns_list.sort(key=lambda x: x[1], reverse=True)
        total = len(returns_list)
        
        for rank, (symbol, _) in enumerate(returns_list, start=1):
            results[symbol].rank = rank
            percentile = ((total - rank + 1) / total) * 98 + 1
            results[symbol].rs_rating = round(percentile, 0)
        
        return results
