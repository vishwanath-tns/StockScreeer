"""
Momentum Score Calculator

Calculates multi-timeframe weighted momentum score.

Formula:
- 1 Week:   5% weight
- 1 Month: 15% weight
- 3 Month: 30% weight
- 6 Month: 30% weight
- 12 Month: 20% weight
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, Optional
import pandas as pd


@dataclass
class MomentumResult:
    """Result of momentum score calculation."""
    symbol: str
    momentum_score: float
    rank: int = 0
    percentile: float = 0
    return_1w: float = 0
    return_1m: float = 0
    return_3m: float = 0
    return_6m: float = 0
    return_12m: float = 0
    raw_score: float = 0
    success: bool = True
    error: str = ""


class MomentumScoreService:
    """
    Calculate weighted multi-timeframe momentum score.
    """
    
    DEFAULT_WEIGHTS = {
        "1w": 0.05, "1m": 0.15, "3m": 0.30, "6m": 0.30, "12m": 0.20,
    }
    
    TIMEFRAME_DAYS = {
        "1w": 5, "1m": 21, "3m": 63, "6m": 126, "12m": 252,
    }
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.name = "Momentum Score"
        self.score_type = "momentum_score"
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
    
    def calculate_return(
        self, df: pd.DataFrame, calculation_date: date, days: int
    ) -> Optional[float]:
        """Calculate return over a period."""
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
        
        if len(df_valid) > days:
            start_price = df_valid["close"].iloc[-days-1]
        else:
            start_price = df_valid["close"].iloc[0]
        
        if start_price <= 0:
            return None
        
        return ((end_price - start_price) / start_price) * 100
    
    def calculate_single(
        self, symbol: str, df: pd.DataFrame, calculation_date: date
    ) -> MomentumResult:
        """Calculate momentum score for a single stock."""
        try:
            returns = {}
            for tf, days in self.TIMEFRAME_DAYS.items():
                ret = self.calculate_return(df, calculation_date, days)
                returns[tf] = ret if ret is not None else 0
            
            raw_score = sum(returns[tf] * self.weights[tf] for tf in self.weights)
            
            return MomentumResult(
                symbol=symbol, momentum_score=0, raw_score=raw_score,
                return_1w=round(returns.get("1w", 0), 2),
                return_1m=round(returns.get("1m", 0), 2),
                return_3m=round(returns.get("3m", 0), 2),
                return_6m=round(returns.get("6m", 0), 2),
                return_12m=round(returns.get("12m", 0), 2),
            )
        except Exception as e:
            return MomentumResult(symbol=symbol, momentum_score=0, success=False, error=str(e))
    
    def calculate_batch(
        self, data: Dict[str, pd.DataFrame], calculation_date: date
    ) -> Dict[str, MomentumResult]:
        """Calculate momentum scores with normalization and ranks."""
        results = {}
        raw_scores = []
        
        for symbol, df in data.items():
            result = self.calculate_single(symbol, df, calculation_date)
            results[symbol] = result
            if result.success:
                raw_scores.append((symbol, result.raw_score))
        
        if not raw_scores:
            return results
        
        scores_only = [s[1] for s in raw_scores]
        min_score, max_score = min(scores_only), max(scores_only)
        score_range = max_score - min_score
        
        if score_range == 0:
            for symbol, _ in raw_scores:
                results[symbol].momentum_score = 50
        else:
            for symbol, raw in raw_scores:
                normalized = ((raw - min_score) / score_range) * 100
                results[symbol].momentum_score = round(normalized, 2)
        
        sorted_results = sorted(
            [(s, results[s].momentum_score) for s, _ in raw_scores],
            key=lambda x: x[1], reverse=True
        )
        
        total = len(sorted_results)
        for rank, (symbol, _) in enumerate(sorted_results, start=1):
            results[symbol].rank = rank
            results[symbol].percentile = round((total - rank + 1) / total * 100, 1)
        
        return results
