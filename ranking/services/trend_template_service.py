"""
Trend Template Calculator

Checks Mark Minervini's 8 Trend Template conditions:

1. Price > 150-day SMA
2. Price > 200-day SMA
3. 150-day SMA > 200-day SMA
4. 200-day SMA trending up (30+ days)
5. 50-day SMA > 150-day SMA
6. 50-day SMA > 200-day SMA
7. Price > 50-day SMA
8. Price within 25% of 52-week high (at least 30% above 52-week low)
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional
import pandas as pd


@dataclass
class TrendCondition:
    """Single trend template condition."""
    name: str
    passed: bool
    description: str
    actual_value: Optional[float] = None
    threshold: Optional[float] = None


@dataclass
class TrendTemplateResult:
    """Result of trend template evaluation."""
    symbol: str
    score: int
    conditions: List[TrendCondition] = field(default_factory=list)
    price: float = 0
    sma_50: float = 0
    sma_150: float = 0
    sma_200: float = 0
    high_52w: float = 0
    low_52w: float = 0
    pct_from_high: float = 0
    pct_from_low: float = 0
    rank: int = 0
    success: bool = True
    error: str = ""


class TrendTemplateService:
    """Evaluate Trend Template conditions for stocks."""
    
    def __init__(self):
        self.name = "Trend Template"
        self.score_type = "trend_template"
    
    def calculate_sma(self, df: pd.DataFrame, period: int) -> Optional[float]:
        if len(df) < period:
            return None
        return df["close"].iloc[-period:].mean()
    
    def is_sma_trending_up(self, df: pd.DataFrame, sma_period: int, check_days: int = 30) -> bool:
        if len(df) < sma_period + check_days:
            return False
        current_sma = df["close"].iloc[-sma_period:].mean()
        past_end = -check_days
        past_start = past_end - sma_period
        past_sma = df["close"].iloc[past_start:past_end].mean()
        return current_sma > past_sma
    
    def calculate_single(
        self, symbol: str, df: pd.DataFrame, calculation_date: date
    ) -> TrendTemplateResult:
        """Evaluate trend template for a single stock."""
        try:
            if df.empty or len(df) < 252:
                return TrendTemplateResult(
                    symbol=symbol, score=0, success=False,
                    error="Insufficient data (need 252 days)"
                )
            
            df = df.copy()
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date")
            df = df[df["date"] <= pd.Timestamp(calculation_date)]
            
            if len(df) < 252:
                return TrendTemplateResult(
                    symbol=symbol, score=0, success=False,
                    error="Insufficient data after date filter"
                )
            
            price = df["close"].iloc[-1]
            sma_50 = self.calculate_sma(df, 50)
            sma_150 = self.calculate_sma(df, 150)
            sma_200 = self.calculate_sma(df, 200)
            high_52w = df["high"].iloc[-252:].max() if "high" in df.columns else df["close"].iloc[-252:].max()
            low_52w = df["low"].iloc[-252:].min() if "low" in df.columns else df["close"].iloc[-252:].min()
            
            if any(x is None for x in [sma_50, sma_150, sma_200]):
                return TrendTemplateResult(
                    symbol=symbol, score=0, success=False,
                    error="Could not calculate SMAs"
                )
            
            pct_from_high = ((price - high_52w) / high_52w) * 100
            pct_from_low = ((price - low_52w) / low_52w) * 100
            
            conditions = [
                TrendCondition("price_above_150sma", price > sma_150, "Price above 150-day SMA", price, sma_150),
                TrendCondition("price_above_200sma", price > sma_200, "Price above 200-day SMA", price, sma_200),
                TrendCondition("150sma_above_200sma", sma_150 > sma_200, "150-day SMA above 200-day SMA", sma_150, sma_200),
                TrendCondition("200sma_trending_up", self.is_sma_trending_up(df, 200, 30), "200-day SMA trending up"),
                TrendCondition("50sma_above_150sma", sma_50 > sma_150, "50-day SMA above 150-day SMA", sma_50, sma_150),
                TrendCondition("50sma_above_200sma", sma_50 > sma_200, "50-day SMA above 200-day SMA", sma_50, sma_200),
                TrendCondition("price_above_50sma", price > sma_50, "Price above 50-day SMA", price, sma_50),
                TrendCondition("price_position", pct_from_high >= -25 and pct_from_low >= 30, 
                              "Within 25% of 52w high and 30%+ above 52w low", pct_from_high, -25),
            ]
            
            score = sum(1 for c in conditions if c.passed)
            
            return TrendTemplateResult(
                symbol=symbol, score=score, conditions=conditions,
                price=round(price, 2), sma_50=round(sma_50, 2),
                sma_150=round(sma_150, 2), sma_200=round(sma_200, 2),
                high_52w=round(high_52w, 2), low_52w=round(low_52w, 2),
                pct_from_high=round(pct_from_high, 2), pct_from_low=round(pct_from_low, 2),
            )
        except Exception as e:
            return TrendTemplateResult(symbol=symbol, score=0, success=False, error=str(e))
    
    def calculate_batch(
        self, data: Dict[str, pd.DataFrame], calculation_date: date
    ) -> Dict[str, TrendTemplateResult]:
        """Calculate trend template for all stocks."""
        results = {}
        scores = []
        
        for symbol, df in data.items():
            result = self.calculate_single(symbol, df, calculation_date)
            results[symbol] = result
            if result.success:
                scores.append((symbol, result.score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        for rank, (symbol, _) in enumerate(scores, start=1):
            results[symbol].rank = rank
        
        return results
