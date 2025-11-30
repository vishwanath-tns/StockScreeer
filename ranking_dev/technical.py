"""
Technical Score Calculator

Scores a stock based on its price position relative to key SMAs.

Components:
- Price vs 50-day SMA position (25 points max)
- Price vs 150-day SMA position (25 points max)
- Price vs 200-day SMA position (25 points max)
- SMA alignment bonus (25 points max)

Total: 0-100 scale
"""

from dataclasses import dataclass
from datetime import date
from typing import Dict, Optional
import pandas as pd
import numpy as np


@dataclass
class TechnicalResult:
    """Result of technical score calculation."""
    symbol: str
    technical_score: float  # 0-100
    rank: int = 0
    percentile: float = 0
    # Component scores
    score_vs_50sma: float = 0
    score_vs_150sma: float = 0
    score_vs_200sma: float = 0
    score_alignment: float = 0
    # Actual values
    price: float = 0
    sma_50: float = 0
    sma_150: float = 0
    sma_200: float = 0
    pct_above_50sma: float = 0
    pct_above_150sma: float = 0
    pct_above_200sma: float = 0
    success: bool = True
    error: str = ""


class TechnicalScoreCalculator:
    """
    Calculate technical position score.
    
    Evaluates how well-positioned a stock is technically
    based on price relationship to moving averages.
    """
    
    def __init__(self):
        self.name = "Technical Score"
        self.score_type = "technical_score"
    
    def calculate_sma(self, df: pd.DataFrame, period: int) -> Optional[float]:
        """Calculate SMA for given period."""
        if len(df) < period:
            return None
        return df["close"].iloc[-period:].mean()
    
    def score_price_vs_sma(
        self,
        price: float,
        sma: float,
        max_points: float = 25,
        optimal_pct: float = 10,
    ) -> tuple[float, float]:
        """
        Score price position vs SMA.
        
        Returns (score, pct_above_sma)
        
        Scoring:
        - At SMA: 12.5 points (half)
        - 0-10% above: Linear 12.5 to 25
        - 10-20% above: 25 points (optimal)
        - 20%+ above: Gradually decreases (extended)
        - Below SMA: Linear decrease to 0
        """
        if sma <= 0:
            return 0, 0
        
        pct_above = ((price - sma) / sma) * 100
        
        if pct_above >= 0:
            if pct_above <= optimal_pct:
                # 0 to optimal: 50% to 100% of max
                score = max_points * (0.5 + 0.5 * (pct_above / optimal_pct))
            elif pct_above <= 20:
                # optimal to 20%: full points
                score = max_points
            else:
                # Over-extended: gradual decrease
                overshoot = pct_above - 20
                penalty = min(overshoot / 20, 0.5)  # Max 50% penalty
                score = max_points * (1 - penalty)
        else:
            # Below SMA: linear decrease
            if pct_above >= -10:
                score = max_points * (0.5 + pct_above / 20)  # 0% to 50%
            else:
                score = max(0, max_points * (0.25 + pct_above / 40))
        
        return round(score, 2), round(pct_above, 2)
    
    def score_sma_alignment(
        self,
        sma_50: float,
        sma_150: float,
        sma_200: float,
        max_points: float = 25,
    ) -> float:
        """
        Score SMA alignment (bullish stack).
        
        Perfect alignment: 50 > 150 > 200
        """
        score = 0
        
        # 50 > 150
        if sma_50 > sma_150:
            score += max_points * 0.4
        
        # 150 > 200
        if sma_150 > sma_200:
            score += max_points * 0.4
        
        # 50 > 200
        if sma_50 > sma_200:
            score += max_points * 0.2
        
        return round(score, 2)
    
    def calculate_single(
        self,
        symbol: str,
        df: pd.DataFrame,
        calculation_date: date,
    ) -> TechnicalResult:
        """
        Calculate technical score for a single stock.
        """
        try:
            if df.empty or len(df) < 200:
                return TechnicalResult(
                    symbol=symbol,
                    technical_score=0,
                    success=False,
                    error="Insufficient data (need 200 days)"
                )
            
            # Prepare data
            df = df.copy()
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date")
            df = df[df["date"] <= pd.Timestamp(calculation_date)]
            
            if len(df) < 200:
                return TechnicalResult(
                    symbol=symbol,
                    technical_score=0,
                    success=False,
                    error="Insufficient data after date filter"
                )
            
            # Get values
            price = df["close"].iloc[-1]
            sma_50 = self.calculate_sma(df, 50)
            sma_150 = self.calculate_sma(df, 150)
            sma_200 = self.calculate_sma(df, 200)
            
            if any(x is None for x in [sma_50, sma_150, sma_200]):
                return TechnicalResult(
                    symbol=symbol,
                    technical_score=0,
                    success=False,
                    error="Could not calculate SMAs"
                )
            
            # Score each component
            score_50, pct_50 = self.score_price_vs_sma(price, sma_50)
            score_150, pct_150 = self.score_price_vs_sma(price, sma_150)
            score_200, pct_200 = self.score_price_vs_sma(price, sma_200)
            score_align = self.score_sma_alignment(sma_50, sma_150, sma_200)
            
            total_score = score_50 + score_150 + score_200 + score_align
            
            return TechnicalResult(
                symbol=symbol,
                technical_score=round(total_score, 2),
                score_vs_50sma=score_50,
                score_vs_150sma=score_150,
                score_vs_200sma=score_200,
                score_alignment=score_align,
                price=round(price, 2),
                sma_50=round(sma_50, 2),
                sma_150=round(sma_150, 2),
                sma_200=round(sma_200, 2),
                pct_above_50sma=pct_50,
                pct_above_150sma=pct_150,
                pct_above_200sma=pct_200,
            )
            
        except Exception as e:
            return TechnicalResult(
                symbol=symbol,
                technical_score=0,
                success=False,
                error=str(e)
            )
    
    def calculate_batch(
        self,
        data: Dict[str, pd.DataFrame],
        calculation_date: date,
    ) -> Dict[str, TechnicalResult]:
        """
        Calculate technical scores for all stocks.
        """
        results = {}
        scores = []
        
        for symbol, df in data.items():
            result = self.calculate_single(symbol, df, calculation_date)
            results[symbol] = result
            if result.success:
                scores.append((symbol, result.technical_score))
        
        # Rank
        scores.sort(key=lambda x: x[1], reverse=True)
        total = len(scores)
        
        for rank, (symbol, _) in enumerate(scores, start=1):
            results[symbol].rank = rank
            results[symbol].percentile = round((total - rank + 1) / total * 100, 1)
        
        return results


# Standalone test
if __name__ == "__main__":
    import random
    
    calc = TechnicalScoreCalculator()
    today = date.today()
    
    # Generate test data
    test_data = {}
    for i in range(5):
        symbol = f"STOCK{i+1}"
        dates = pd.date_range(end=today, periods=300, freq="D")
        
        # Varying trends
        trend = 0.5 - i * 0.2  # 0.5, 0.3, 0.1, -0.1, -0.3
        
        start_price = 100
        prices = [start_price * (1 + trend * j/300 + random.uniform(-0.01, 0.01)) 
                  for j in range(300)]
        
        test_data[symbol] = pd.DataFrame({
            "date": dates,
            "close": prices,
        })
    
    # Calculate
    results = calc.calculate_batch(test_data, today)
    
    # Print
    print("Technical Score Results:")
    print("-" * 90)
    print(f"{'Symbol':10} | {'Score':>6} | {'Rank':>4} | {'50SMA':>7} | {'150SMA':>7} | {'200SMA':>7} | {'Align':>6}")
    print("-" * 90)
    
    for symbol, r in sorted(results.items(), key=lambda x: x[1].technical_score, reverse=True):
        if r.success:
            print(f"{symbol:10} | {r.technical_score:6.1f} | {r.rank:4} | "
                  f"{r.score_vs_50sma:7.1f} | {r.score_vs_150sma:7.1f} | "
                  f"{r.score_vs_200sma:7.1f} | {r.score_alignment:6.1f}")
            print(f"           | Price: {r.price:.1f} | 50SMA: {r.sma_50:.1f} | "
                  f"150SMA: {r.sma_150:.1f} | 200SMA: {r.sma_200:.1f}")
        else:
            print(f"{symbol:10} | FAILED - {r.error}")
