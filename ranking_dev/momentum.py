"""
Momentum Score Calculator

Calculates multi-timeframe weighted momentum score.

Formula:
- 1 Week:   5% weight
- 1 Month: 15% weight
- 3 Month: 30% weight
- 6 Month: 30% weight
- 12 Month: 20% weight

Score normalized to 0-100 scale.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np


@dataclass
class MomentumResult:
    """Result of momentum score calculation."""
    symbol: str
    momentum_score: float  # 0-100 normalized
    rank: int = 0
    percentile: float = 0
    # Component returns
    return_1w: float = 0
    return_1m: float = 0
    return_3m: float = 0
    return_6m: float = 0
    return_12m: float = 0
    # Weighted score before normalization
    raw_score: float = 0
    success: bool = True
    error: str = ""


class MomentumScoreCalculator:
    """
    Calculate weighted multi-timeframe momentum score.
    
    Combines multiple timeframe returns with configurable weights
    and normalizes to 0-100 scale.
    """
    
    # Default weights for each timeframe
    DEFAULT_WEIGHTS = {
        "1w": 0.05,   # 5%
        "1m": 0.15,   # 15%
        "3m": 0.30,   # 30%
        "6m": 0.30,   # 30%
        "12m": 0.20,  # 20%
    }
    
    # Timeframe to days mapping
    TIMEFRAME_DAYS = {
        "1w": 5,
        "1m": 21,
        "3m": 63,
        "6m": 126,
        "12m": 252,
    }
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize with optional custom weights.
        
        Args:
            weights: Dict of timeframe to weight. Must sum to 1.0.
        """
        self.name = "Momentum Score"
        self.score_type = "momentum_score"
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        
        # Validate weights sum to 1
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total}")
    
    def calculate_return(
        self,
        df: pd.DataFrame,
        calculation_date: date,
        days: int,
    ) -> Optional[float]:
        """
        Calculate return over a period.
        
        Args:
            df: DataFrame with 'date' and 'close'.
            calculation_date: End date.
            days: Trading days to look back.
            
        Returns:
            Percentage return or None.
        """
        if df.empty or len(df) < days:
            return None
        
        df = df.copy()
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        
        df_sorted = df.sort_values("date")
        df_valid = df_sorted[df_sorted["date"] <= pd.Timestamp(calculation_date)]
        
        if len(df_valid) < 2:
            return None
        
        end_price = df_valid["close"].iloc[-1]
        
        # Get price from 'days' ago
        if len(df_valid) > days:
            start_price = df_valid["close"].iloc[-days-1]
        else:
            start_price = df_valid["close"].iloc[0]
        
        if start_price <= 0:
            return None
        
        return ((end_price - start_price) / start_price) * 100
    
    def calculate_single(
        self,
        symbol: str,
        df: pd.DataFrame,
        calculation_date: date,
    ) -> MomentumResult:
        """
        Calculate momentum score for a single stock.
        """
        try:
            # Calculate returns for each timeframe
            returns = {}
            for tf, days in self.TIMEFRAME_DAYS.items():
                ret = self.calculate_return(df, calculation_date, days)
                returns[tf] = ret if ret is not None else 0
            
            # Calculate weighted raw score
            raw_score = sum(
                returns[tf] * self.weights[tf]
                for tf in self.weights
            )
            
            return MomentumResult(
                symbol=symbol,
                momentum_score=0,  # Normalized in batch
                raw_score=raw_score,
                return_1w=round(returns.get("1w", 0), 2),
                return_1m=round(returns.get("1m", 0), 2),
                return_3m=round(returns.get("3m", 0), 2),
                return_6m=round(returns.get("6m", 0), 2),
                return_12m=round(returns.get("12m", 0), 2),
            )
        except Exception as e:
            return MomentumResult(
                symbol=symbol,
                momentum_score=0,
                success=False,
                error=str(e)
            )
    
    def calculate_batch(
        self,
        data: Dict[str, pd.DataFrame],
        calculation_date: date,
    ) -> Dict[str, MomentumResult]:
        """
        Calculate momentum scores for all stocks.
        
        Normalizes raw scores to 0-100 scale based on min/max.
        """
        # Step 1: Calculate raw scores
        results = {}
        raw_scores = []
        
        for symbol, df in data.items():
            result = self.calculate_single(symbol, df, calculation_date)
            results[symbol] = result
            if result.success:
                raw_scores.append((symbol, result.raw_score))
        
        if not raw_scores:
            return results
        
        # Step 2: Normalize to 0-100
        scores_only = [s[1] for s in raw_scores]
        min_score = min(scores_only)
        max_score = max(scores_only)
        score_range = max_score - min_score
        
        if score_range == 0:
            # All same score, set to 50
            for symbol, _ in raw_scores:
                results[symbol].momentum_score = 50
        else:
            for symbol, raw in raw_scores:
                normalized = ((raw - min_score) / score_range) * 100
                results[symbol].momentum_score = round(normalized, 2)
        
        # Step 3: Calculate ranks
        sorted_results = sorted(
            [(s, results[s].momentum_score) for s, _ in raw_scores],
            key=lambda x: x[1],
            reverse=True
        )
        
        total = len(sorted_results)
        for rank, (symbol, _) in enumerate(sorted_results, start=1):
            results[symbol].rank = rank
            results[symbol].percentile = round((total - rank + 1) / total * 100, 1)
        
        return results


# Standalone test
if __name__ == "__main__":
    import random
    
    calc = MomentumScoreCalculator()
    today = date.today()
    
    # Generate test data
    test_data = {}
    for i in range(10):
        symbol = f"STOCK{i+1}"
        dates = pd.date_range(end=today, periods=300, freq="D")
        trend = random.uniform(-0.3, 0.8)
        start_price = 100
        prices = [start_price * (1 + trend * j/300 + random.uniform(-0.02, 0.02)) 
                  for j in range(300)]
        test_data[symbol] = pd.DataFrame({
            "date": dates,
            "close": prices
        })
    
    # Calculate
    results = calc.calculate_batch(test_data, today)
    
    # Print
    print("Momentum Score Results:")
    print("-" * 80)
    print(f"{'Symbol':10} | {'Score':>6} | {'Rank':>4} | {'1W':>6} | {'1M':>6} | {'3M':>6} | {'6M':>6} | {'12M':>6}")
    print("-" * 80)
    
    sorted_results = sorted(results.values(), key=lambda r: r.rank if r.rank > 0 else 999)
    for r in sorted_results:
        print(f"{r.symbol:10} | {r.momentum_score:6.1f} | {r.rank:4} | "
              f"{r.return_1w:+6.1f} | {r.return_1m:+6.1f} | {r.return_3m:+6.1f} | "
              f"{r.return_6m:+6.1f} | {r.return_12m:+6.1f}")
