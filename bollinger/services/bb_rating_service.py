"""
BB Rating Service

Calculates composite Bollinger Bands ratings for stocks.
"""

import pandas as pd
import numpy as np
from datetime import date
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..models.bb_models import (
    BBConfig, BollingerBands, BBResult, BBRating, 
    TrendDirection, VolatilityState, get_letter_grade
)
from .bb_calculator import BBCalculator
from .squeeze_detector import SqueezeDetector
from .trend_analyzer import TrendAnalyzer


class BBRatingService:
    """
    Calculate composite BB ratings for stocks.
    
    Rating Components:
    - Squeeze Score (25%): Position in volatility cycle
    - Trend Score (35%): Trend strength from %b position
    - Momentum Score (20%): Rate of change in %b
    - Pattern Score (20%): Recognition of key patterns
    
    Output: 0-100 composite score with rankings
    """
    
    # Component weights
    WEIGHTS = {
        "squeeze": 0.25,
        "trend": 0.35,
        "momentum": 0.20,
        "pattern": 0.20,
    }
    
    def __init__(self, config: BBConfig = None):
        """
        Initialize rating service.
        
        Args:
            config: BB configuration to use
        """
        self.config = config or BBConfig()
        self.calculator = BBCalculator(config)
        self.squeeze_detector = SqueezeDetector()
        self.trend_analyzer = TrendAnalyzer()
    
    def calculate_rating(self, bb_result: BBResult) -> BBRating:
        """
        Calculate BB rating from a BBResult.
        
        Args:
            bb_result: Calculated BB data
            
        Returns:
            BBRating with component and composite scores
        """
        if not bb_result.success or not bb_result.history:
            return BBRating(
                symbol=bb_result.symbol,
                rating_date=bb_result.calculation_date,
                success=False,
                error=bb_result.error or "No BB data"
            )
        
        current = bb_result.current
        history = bb_result.history
        
        # Calculate component scores
        squeeze_score = self._calculate_squeeze_score(history)
        trend_score = self._calculate_trend_score(history)
        momentum_score = self._calculate_momentum_score(history)
        pattern_score = self._calculate_pattern_score(history)
        
        # Calculate composite
        composite = (
            squeeze_score * self.WEIGHTS["squeeze"] +
            trend_score * self.WEIGHTS["trend"] +
            momentum_score * self.WEIGHTS["momentum"] +
            pattern_score * self.WEIGHTS["pattern"]
        )
        
        # Determine trend direction
        trend_state = self.trend_analyzer.analyze_trend(history, bb_result.symbol)
        
        # Determine volatility state
        vol_state = self.squeeze_detector.classify_volatility(current.bandwidth_percentile)
        
        return BBRating(
            symbol=bb_result.symbol,
            rating_date=bb_result.calculation_date,
            squeeze_score=round(squeeze_score, 2),
            trend_score=round(trend_score, 2),
            momentum_score=round(momentum_score, 2),
            pattern_score=round(pattern_score, 2),
            composite_score=round(composite, 2),
            percent_b=round(current.percent_b, 4),
            bandwidth=round(current.bandwidth, 4),
            bandwidth_percentile=round(current.bandwidth_percentile, 2),
            is_squeeze=vol_state == VolatilityState.SQUEEZE,
            is_bulge=vol_state == VolatilityState.BULGE,
            trend_direction=trend_state.direction.value,
            success=True
        )
    
    def _calculate_squeeze_score(self, history: List[BollingerBands]) -> float:
        """
        Calculate squeeze score (0-100).
        
        High score = in squeeze with potential for breakout
        - Squeeze present: +40 base
        - Days in squeeze: +20 max (more days = higher)
        - Squeeze intensity: +40 max (tighter = higher)
        
        Low score = bulge/high volatility (trend exhaustion)
        """
        if not history:
            return 50.0
        
        current = history[0]
        bw_pct = current.bandwidth_percentile
        
        if bw_pct <= 5:
            # In squeeze - high score opportunity
            base = 70
            # Bonus for tighter squeeze
            intensity_bonus = (5 - bw_pct) * 6  # Up to 30 points
            
            # Bonus for days in squeeze
            days_in_squeeze = sum(1 for bb in history[:20] if bb.bandwidth_percentile <= 10)
            duration_bonus = min(days_in_squeeze * 2, 20)
            
            score = base + intensity_bonus + duration_bonus
        
        elif bw_pct <= 25:
            # Low volatility - moderate opportunity
            score = 50 + (25 - bw_pct) * 0.8  # 50-70
        
        elif bw_pct >= 95:
            # Bulge - potential exhaustion, lower score
            score = 30 - (bw_pct - 95) * 2  # 20-30
        
        elif bw_pct >= 75:
            # High volatility
            score = 40 - (bw_pct - 75) * 0.5  # 30-40
        
        else:
            # Normal volatility
            score = 50
        
        return max(0, min(100, score))
    
    def _calculate_trend_score(self, history: List[BollingerBands]) -> float:
        """
        Calculate trend score (0-100).
        
        High score = strong uptrend
        - Walking upper band: 80-100
        - Consistently above middle: 60-80
        
        Low score = strong downtrend
        - Walking lower band: 0-20
        - Consistently below middle: 20-40
        
        Neutral = oscillating around middle: 40-60
        """
        if not history:
            return 50.0
        
        # Use trend analyzer
        trend_state = self.trend_analyzer.analyze_trend(history)
        
        direction = trend_state.direction
        strength = trend_state.strength
        
        if direction == TrendDirection.STRONG_UPTREND:
            # 80-100 based on strength
            base = 80
            bonus = strength * 0.2
            score = base + bonus
        
        elif direction == TrendDirection.UPTREND:
            # 60-80 based on strength
            score = 60 + strength * 0.2
        
        elif direction == TrendDirection.NEUTRAL:
            # 40-60 based on how neutral
            score = 50
        
        elif direction == TrendDirection.DOWNTREND:
            # 20-40 based on strength
            score = 40 - strength * 0.2
        
        else:  # STRONG_DOWNTREND
            # 0-20 based on strength
            score = 20 - strength * 0.2
        
        return max(0, min(100, score))
    
    def _calculate_momentum_score(self, history: List[BollingerBands]) -> float:
        """
        Calculate momentum score (0-100).
        
        Based on rate of change in %b over recent periods.
        Positive momentum = %b increasing = bullish
        Negative momentum = %b decreasing = bearish
        """
        if len(history) < 5:
            return 50.0
        
        # Short-term momentum (5-day)
        pb_5d = [bb.percent_b for bb in history[:5]]
        slope_5d = self._calculate_slope(pb_5d)
        
        # Medium-term momentum (10-day)
        pb_10d = [bb.percent_b for bb in history[:min(10, len(history))]]
        slope_10d = self._calculate_slope(pb_10d)
        
        # Combined momentum
        combined_slope = slope_5d * 0.6 + slope_10d * 0.4
        
        # Convert slope to score
        # Slope of 0.05 per day = very bullish = 100
        # Slope of -0.05 per day = very bearish = 0
        score = 50 + (combined_slope * 1000)  # Scale factor
        
        # Add bonus for %b position
        current_pb = history[0].percent_b
        if current_pb > 0.5 and combined_slope > 0:
            score += 10  # Upside momentum confirmed
        elif current_pb < 0.5 and combined_slope < 0:
            score -= 10  # Downside momentum confirmed
        
        return max(0, min(100, score))
    
    def _calculate_pattern_score(self, history: List[BollingerBands]) -> float:
        """
        Calculate pattern score (0-100).
        
        Looks for favorable patterns:
        - W-bottom forming: High score
        - Squeeze breakout setup: High score
        - M-top forming: Low score
        
        This is a simplified pattern detection.
        Full pattern detection is in signal_generator.py
        """
        if len(history) < 20:
            return 50.0
        
        score = 50.0
        current = history[0]
        
        # Check for W-bottom potential
        # %b made lower low but price made higher low
        pb_lows = self._find_local_extremes([bb.percent_b for bb in history[:20]], "min")
        if len(pb_lows) >= 2:
            if history[pb_lows[0]].percent_b > history[pb_lows[1]].percent_b:
                # Potential W-bottom (%b divergence)
                score += 20
        
        # Check for squeeze breakout setup
        if current.bandwidth_percentile <= 10 and current.percent_b > 0.5:
            # Squeeze with bullish bias
            score += 15
        
        # Check for trend continuation
        if current.percent_b > 0.8 and len([bb for bb in history[:5] if bb.percent_b > 0.7]) >= 3:
            # Strong momentum continuation
            score += 10
        
        # Check for M-top warning
        if current.percent_b < 0.5 and len([bb for bb in history[:10] if bb.percent_b > 1.0]) >= 2:
            # Potential M-top forming
            score -= 15
        
        return max(0, min(100, score))
    
    def _calculate_slope(self, values: List[float]) -> float:
        """Calculate linear regression slope."""
        if len(values) < 2:
            return 0.0
        x = np.arange(len(values))
        slope, _ = np.polyfit(x, values, 1)
        return slope
    
    def _find_local_extremes(self, values: List[float], 
                              extreme_type: str = "min") -> List[int]:
        """Find local minima or maxima indices."""
        extremes = []
        for i in range(1, len(values) - 1):
            if extreme_type == "min":
                if values[i] < values[i-1] and values[i] < values[i+1]:
                    extremes.append(i)
            else:
                if values[i] > values[i-1] and values[i] > values[i+1]:
                    extremes.append(i)
        return extremes
    
    def calculate_ratings_batch(self, 
                                 bb_results: Dict[str, BBResult],
                                 rating_date: date = None) -> Dict[str, BBRating]:
        """
        Calculate ratings for multiple stocks with ranking.
        
        Args:
            bb_results: Dict mapping symbol to BBResult
            rating_date: Date for the ratings
            
        Returns:
            Dict mapping symbol to BBRating with ranks
        """
        rating_date = rating_date or date.today()
        
        # Calculate individual ratings
        ratings = {}
        scores = []
        
        for symbol, bb_result in bb_results.items():
            rating = self.calculate_rating(bb_result)
            ratings[symbol] = rating
            
            if rating.success:
                scores.append((symbol, rating.composite_score))
        
        # Assign ranks
        scores.sort(key=lambda x: x[1], reverse=True)
        total = len(scores)
        
        for rank, (symbol, _) in enumerate(scores, start=1):
            ratings[symbol].rank = rank
            ratings[symbol].percentile = round((total - rank + 1) / total * 100, 2)
            ratings[symbol].total_stocks = total
        
        return ratings
    
    def calculate_from_price_data(self, 
                                   price_data: Dict[str, pd.DataFrame],
                                   rating_date: date = None) -> Dict[str, BBRating]:
        """
        Calculate ratings directly from price data.
        
        Args:
            price_data: Dict mapping symbol to price DataFrame
            rating_date: Date for the ratings
            
        Returns:
            Dict mapping symbol to BBRating with ranks
        """
        # First calculate BB for all stocks
        bb_results = self.calculator.calculate_batch(price_data)
        
        # Then calculate ratings
        return self.calculate_ratings_batch(bb_results, rating_date)
