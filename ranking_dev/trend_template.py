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

Score: 0-8 (number of conditions passed)
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np


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
    score: int  # 0-8
    conditions: List[TrendCondition] = field(default_factory=list)
    # Actual values for reference
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


class TrendTemplateCalculator:
    """
    Evaluate Trend Template conditions for stocks.
    
    Based on Mark Minervini's criteria for identifying
    stocks in Stage 2 uptrends.
    """
    
    def __init__(self):
        self.name = "Trend Template"
        self.score_type = "trend_template"
    
    def calculate_sma(self, df: pd.DataFrame, period: int) -> Optional[float]:
        """Calculate simple moving average."""
        if len(df) < period:
            return None
        return df["close"].iloc[-period:].mean()
    
    def is_sma_trending_up(
        self,
        df: pd.DataFrame,
        sma_period: int,
        check_days: int = 30,
    ) -> bool:
        """
        Check if SMA has been trending up over check_days.
        
        Compares current SMA to SMA from check_days ago.
        """
        if len(df) < sma_period + check_days:
            return False
        
        # Current SMA
        current_sma = df["close"].iloc[-sma_period:].mean()
        
        # SMA from check_days ago
        past_end = -check_days
        past_start = past_end - sma_period
        past_sma = df["close"].iloc[past_start:past_end].mean()
        
        return current_sma > past_sma
    
    def calculate_single(
        self,
        symbol: str,
        df: pd.DataFrame,
        calculation_date: date,
    ) -> TrendTemplateResult:
        """
        Evaluate trend template for a single stock.
        """
        try:
            if df.empty or len(df) < 252:
                return TrendTemplateResult(
                    symbol=symbol,
                    score=0,
                    success=False,
                    error="Insufficient data (need 252 days)"
                )
            
            # Prepare data
            df = df.copy()
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date")
            df = df[df["date"] <= pd.Timestamp(calculation_date)]
            
            if len(df) < 252:
                return TrendTemplateResult(
                    symbol=symbol,
                    score=0,
                    success=False,
                    error="Insufficient data after date filter"
                )
            
            # Calculate indicators
            price = df["close"].iloc[-1]
            sma_50 = self.calculate_sma(df, 50)
            sma_150 = self.calculate_sma(df, 150)
            sma_200 = self.calculate_sma(df, 200)
            high_52w = df["high"].iloc[-252:].max() if "high" in df.columns else df["close"].iloc[-252:].max()
            low_52w = df["low"].iloc[-252:].min() if "low" in df.columns else df["close"].iloc[-252:].min()
            
            if any(x is None for x in [sma_50, sma_150, sma_200]):
                return TrendTemplateResult(
                    symbol=symbol,
                    score=0,
                    success=False,
                    error="Could not calculate SMAs"
                )
            
            pct_from_high = ((price - high_52w) / high_52w) * 100
            pct_from_low = ((price - low_52w) / low_52w) * 100
            
            # Evaluate conditions
            conditions = []
            
            # 1. Price > 150-day SMA
            cond1 = price > sma_150
            conditions.append(TrendCondition(
                name="price_above_150sma",
                passed=cond1,
                description="Price above 150-day SMA",
                actual_value=price,
                threshold=sma_150
            ))
            
            # 2. Price > 200-day SMA
            cond2 = price > sma_200
            conditions.append(TrendCondition(
                name="price_above_200sma",
                passed=cond2,
                description="Price above 200-day SMA",
                actual_value=price,
                threshold=sma_200
            ))
            
            # 3. 150-day SMA > 200-day SMA
            cond3 = sma_150 > sma_200
            conditions.append(TrendCondition(
                name="150sma_above_200sma",
                passed=cond3,
                description="150-day SMA above 200-day SMA",
                actual_value=sma_150,
                threshold=sma_200
            ))
            
            # 4. 200-day SMA trending up
            cond4 = self.is_sma_trending_up(df, 200, 30)
            conditions.append(TrendCondition(
                name="200sma_trending_up",
                passed=cond4,
                description="200-day SMA trending up (30+ days)"
            ))
            
            # 5. 50-day SMA > 150-day SMA
            cond5 = sma_50 > sma_150
            conditions.append(TrendCondition(
                name="50sma_above_150sma",
                passed=cond5,
                description="50-day SMA above 150-day SMA",
                actual_value=sma_50,
                threshold=sma_150
            ))
            
            # 6. 50-day SMA > 200-day SMA
            cond6 = sma_50 > sma_200
            conditions.append(TrendCondition(
                name="50sma_above_200sma",
                passed=cond6,
                description="50-day SMA above 200-day SMA",
                actual_value=sma_50,
                threshold=sma_200
            ))
            
            # 7. Price > 50-day SMA
            cond7 = price > sma_50
            conditions.append(TrendCondition(
                name="price_above_50sma",
                passed=cond7,
                description="Price above 50-day SMA",
                actual_value=price,
                threshold=sma_50
            ))
            
            # 8. Price within 25% of 52-week high AND at least 30% above low
            within_high = pct_from_high >= -25
            above_low = pct_from_low >= 30
            cond8 = within_high and above_low
            conditions.append(TrendCondition(
                name="price_position",
                passed=cond8,
                description="Within 25% of 52w high and 30%+ above 52w low",
                actual_value=pct_from_high,
                threshold=-25
            ))
            
            score = sum(1 for c in conditions if c.passed)
            
            return TrendTemplateResult(
                symbol=symbol,
                score=score,
                conditions=conditions,
                price=round(price, 2),
                sma_50=round(sma_50, 2),
                sma_150=round(sma_150, 2),
                sma_200=round(sma_200, 2),
                high_52w=round(high_52w, 2),
                low_52w=round(low_52w, 2),
                pct_from_high=round(pct_from_high, 2),
                pct_from_low=round(pct_from_low, 2),
            )
            
        except Exception as e:
            return TrendTemplateResult(
                symbol=symbol,
                score=0,
                success=False,
                error=str(e)
            )
    
    def calculate_batch(
        self,
        data: Dict[str, pd.DataFrame],
        calculation_date: date,
    ) -> Dict[str, TrendTemplateResult]:
        """
        Calculate trend template for all stocks.
        """
        results = {}
        scores = []
        
        for symbol, df in data.items():
            result = self.calculate_single(symbol, df, calculation_date)
            results[symbol] = result
            if result.success:
                scores.append((symbol, result.score))
        
        # Rank by score (higher is better)
        scores.sort(key=lambda x: x[1], reverse=True)
        for rank, (symbol, _) in enumerate(scores, start=1):
            results[symbol].rank = rank
        
        return results


# Standalone test
if __name__ == "__main__":
    import random
    
    calc = TrendTemplateCalculator()
    today = date.today()
    
    # Generate test data
    test_data = {}
    for i in range(5):
        symbol = f"STOCK{i+1}"
        dates = pd.date_range(end=today, periods=300, freq="D")
        
        # Create price series with varying trends
        if i < 2:
            # Strong uptrend
            trend = 0.5
        elif i < 4:
            # Weak uptrend
            trend = 0.1
        else:
            # Downtrend
            trend = -0.2
        
        start_price = 100
        prices = []
        for j in range(300):
            p = start_price * (1 + trend * j/300 + random.uniform(-0.02, 0.02))
            prices.append(p)
        
        test_data[symbol] = pd.DataFrame({
            "date": dates,
            "close": prices,
            "high": [p * 1.02 for p in prices],
            "low": [p * 0.98 for p in prices],
        })
    
    # Calculate
    results = calc.calculate_batch(test_data, today)
    
    # Print
    print("Trend Template Results:")
    print("-" * 60)
    
    for symbol, r in sorted(results.items(), key=lambda x: x[1].score, reverse=True):
        if r.success:
            passed = [c.name for c in r.conditions if c.passed]
            print(f"\n{symbol}: Score {r.score}/8 | Rank {r.rank}")
            print(f"  Price: {r.price} | 50SMA: {r.sma_50} | 150SMA: {r.sma_150} | 200SMA: {r.sma_200}")
            print(f"  52W: {r.pct_from_high:+.1f}% from high, {r.pct_from_low:+.1f}% from low")
            print(f"  Passed: {', '.join(passed) if passed else 'None'}")
        else:
            print(f"\n{symbol}: FAILED - {r.error}")
