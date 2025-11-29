"""
Technical Score Calculator

Scores a stock based on its price position relative to key SMAs.

Components (each 25 points max):
- Price vs 50-day SMA position
- Price vs 150-day SMA position
- Price vs 200-day SMA position
- SMA alignment bonus

Total: 0-100 scale
"""

from dataclasses import dataclass
from datetime import date
from typing import Dict, Optional
import pandas as pd


@dataclass
class TechnicalResult:
    """Result of technical score calculation."""
    symbol: str
    technical_score: float
    rank: int = 0
    percentile: float = 0
    score_vs_50sma: float = 0
    score_vs_150sma: float = 0
    score_vs_200sma: float = 0
    score_alignment: float = 0
    price: float = 0
    sma_50: float = 0
    sma_150: float = 0
    sma_200: float = 0
    pct_above_50sma: float = 0
    pct_above_150sma: float = 0
    pct_above_200sma: float = 0
    success: bool = True
    error: str = ""


class TechnicalScoreService:
    """Calculate technical position score."""
    
    def __init__(self):
        self.name = "Technical Score"
        self.score_type = "technical_score"
    
    def calculate_sma(self, df: pd.DataFrame, period: int) -> Optional[float]:
        if len(df) < period:
            return None
        return df["close"].iloc[-period:].mean()
    
    def score_price_vs_sma(
        self, price: float, sma: float, max_points: float = 25, optimal_pct: float = 10
    ) -> tuple[float, float]:
        """Score price position vs SMA. Returns (score, pct_above_sma)."""
        if sma <= 0:
            return 0, 0
        
        pct_above = ((price - sma) / sma) * 100
        
        if pct_above >= 0:
            if pct_above <= optimal_pct:
                score = max_points * (0.5 + 0.5 * (pct_above / optimal_pct))
            elif pct_above <= 20:
                score = max_points
            else:
                overshoot = pct_above - 20
                penalty = min(overshoot / 20, 0.5)
                score = max_points * (1 - penalty)
        else:
            if pct_above >= -10:
                score = max_points * (0.5 + pct_above / 20)
            else:
                score = max(0, max_points * (0.25 + pct_above / 40))
        
        return round(score, 2), round(pct_above, 2)
    
    def score_sma_alignment(
        self, sma_50: float, sma_150: float, sma_200: float, max_points: float = 25
    ) -> float:
        """Score SMA alignment (bullish stack)."""
        score = 0
        if sma_50 > sma_150:
            score += max_points * 0.4
        if sma_150 > sma_200:
            score += max_points * 0.4
        if sma_50 > sma_200:
            score += max_points * 0.2
        return round(score, 2)
    
    def calculate_single(
        self, symbol: str, df: pd.DataFrame, calculation_date: date
    ) -> TechnicalResult:
        """Calculate technical score for a single stock."""
        try:
            if df.empty or len(df) < 200:
                return TechnicalResult(
                    symbol=symbol, technical_score=0, success=False,
                    error="Insufficient data (need 200 days)"
                )
            
            df = df.copy()
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date")
            df = df[df["date"] <= pd.Timestamp(calculation_date)]
            
            if len(df) < 200:
                return TechnicalResult(
                    symbol=symbol, technical_score=0, success=False,
                    error="Insufficient data after date filter"
                )
            
            price = df["close"].iloc[-1]
            sma_50 = self.calculate_sma(df, 50)
            sma_150 = self.calculate_sma(df, 150)
            sma_200 = self.calculate_sma(df, 200)
            
            if any(x is None for x in [sma_50, sma_150, sma_200]):
                return TechnicalResult(
                    symbol=symbol, technical_score=0, success=False,
                    error="Could not calculate SMAs"
                )
            
            score_50, pct_50 = self.score_price_vs_sma(price, sma_50)
            score_150, pct_150 = self.score_price_vs_sma(price, sma_150)
            score_200, pct_200 = self.score_price_vs_sma(price, sma_200)
            score_align = self.score_sma_alignment(sma_50, sma_150, sma_200)
            
            total_score = score_50 + score_150 + score_200 + score_align
            
            return TechnicalResult(
                symbol=symbol, technical_score=round(total_score, 2),
                score_vs_50sma=score_50, score_vs_150sma=score_150,
                score_vs_200sma=score_200, score_alignment=score_align,
                price=round(price, 2), sma_50=round(sma_50, 2),
                sma_150=round(sma_150, 2), sma_200=round(sma_200, 2),
                pct_above_50sma=pct_50, pct_above_150sma=pct_150, pct_above_200sma=pct_200,
            )
        except Exception as e:
            return TechnicalResult(symbol=symbol, technical_score=0, success=False, error=str(e))
    
    def calculate_batch(
        self, data: Dict[str, pd.DataFrame], calculation_date: date
    ) -> Dict[str, TechnicalResult]:
        """Calculate technical scores for all stocks."""
        results = {}
        scores = []
        
        for symbol, df in data.items():
            result = self.calculate_single(symbol, df, calculation_date)
            results[symbol] = result
            if result.success:
                scores.append((symbol, result.technical_score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        total = len(scores)
        
        for rank, (symbol, _) in enumerate(scores, start=1):
            results[symbol].rank = rank
            results[symbol].percentile = round((total - rank + 1) / total * 100, 1)
        
        return results
