"""
Trend Analyzer for Bollinger Bands

Analyzes trend direction and strength using %b position.
"""

import pandas as pd
import numpy as np
from datetime import date
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from ..models.bb_models import BollingerBands, TrendDirection
from ..models.scan_models import TrendInfo


@dataclass
class TrendState:
    """Current trend state for a stock."""
    symbol: str
    direction: TrendDirection
    strength: float  # 0-100
    days_in_trend: int
    is_walking_band: bool
    band_walking: str  # "upper", "lower", "none"
    percent_b: float
    percent_b_slope: float  # Rate of change in %b


class TrendAnalyzer:
    """
    Analyze trends using Bollinger Bands position.
    
    Trend Classification based on %b:
    - Strong Uptrend: %b consistently > 0.8 (walking upper band)
    - Uptrend: %b consistently > 0.5
    - Neutral: %b oscillating around 0.5
    - Downtrend: %b consistently < 0.5
    - Strong Downtrend: %b consistently < 0.2 (walking lower band)
    
    Walking the Bands:
    - Consecutive touches of upper/lower band indicate strong trend
    - Price "walks" along the band as it rides the trend
    """
    
    # Thresholds
    STRONG_UPTREND_THRESHOLD = 0.8
    UPTREND_THRESHOLD = 0.5
    DOWNTREND_THRESHOLD = 0.5
    STRONG_DOWNTREND_THRESHOLD = 0.2
    
    # Minimum days to confirm trend
    MIN_TREND_DAYS = 5
    MIN_WALKING_DAYS = 3
    
    def __init__(self,
                 uptrend_threshold: float = 0.8,
                 downtrend_threshold: float = 0.2,
                 min_trend_days: int = 5):
        """
        Initialize analyzer.
        
        Args:
            uptrend_threshold: %b threshold for strong uptrend (default 0.8)
            downtrend_threshold: %b threshold for strong downtrend (default 0.2)
            min_trend_days: Minimum days to confirm trend (default 5)
        """
        self.uptrend_threshold = uptrend_threshold
        self.downtrend_threshold = downtrend_threshold
        self.min_trend_days = min_trend_days
    
    def classify_trend(self, percent_b_history: List[float], 
                       lookback: int = 20) -> TrendDirection:
        """
        Classify trend direction from %b history.
        
        Args:
            percent_b_history: List of %b values (most recent first)
            lookback: Days to analyze
            
        Returns:
            TrendDirection enum
        """
        if not percent_b_history:
            return TrendDirection.NEUTRAL
        
        recent = percent_b_history[:min(len(percent_b_history), lookback)]
        avg_percent_b = np.mean(recent)
        
        # Check for strong trends (walking bands)
        above_upper = sum(1 for pb in recent if pb >= self.uptrend_threshold)
        below_lower = sum(1 for pb in recent if pb <= self.downtrend_threshold)
        
        if above_upper >= self.min_trend_days:
            return TrendDirection.STRONG_UPTREND
        elif below_lower >= self.min_trend_days:
            return TrendDirection.STRONG_DOWNTREND
        elif avg_percent_b >= 0.6:
            return TrendDirection.UPTREND
        elif avg_percent_b <= 0.4:
            return TrendDirection.DOWNTREND
        else:
            return TrendDirection.NEUTRAL
    
    def analyze_trend(self, bb_history: List[BollingerBands],
                      symbol: str = "UNKNOWN") -> TrendState:
        """
        Full trend analysis from BB history.
        
        Args:
            bb_history: List of BollingerBands (most recent first)
            symbol: Stock symbol
            
        Returns:
            TrendState with full analysis
        """
        if not bb_history:
            return TrendState(
                symbol=symbol,
                direction=TrendDirection.NEUTRAL,
                strength=50.0,
                days_in_trend=0,
                is_walking_band=False,
                band_walking="none",
                percent_b=0.5,
                percent_b_slope=0.0
            )
        
        # Extract %b history
        percent_b_history = [bb.percent_b for bb in bb_history]
        
        # Classify trend
        direction = self.classify_trend(percent_b_history)
        
        # Calculate days in current trend
        days_in_trend = self._count_trend_days(percent_b_history, direction)
        
        # Check for walking bands
        is_walking, band = self._check_walking_band(bb_history)
        
        # Calculate trend strength (0-100)
        strength = self._calculate_trend_strength(percent_b_history, direction)
        
        # Calculate %b slope (momentum)
        percent_b_slope = self._calculate_slope(percent_b_history, 5)
        
        return TrendState(
            symbol=symbol,
            direction=direction,
            strength=strength,
            days_in_trend=days_in_trend,
            is_walking_band=is_walking,
            band_walking=band,
            percent_b=bb_history[0].percent_b,
            percent_b_slope=percent_b_slope
        )
    
    def _count_trend_days(self, percent_b_history: List[float],
                          direction: TrendDirection) -> int:
        """Count consecutive days in the current trend."""
        if not percent_b_history:
            return 0
        
        days = 0
        for pb in percent_b_history:
            if direction in (TrendDirection.STRONG_UPTREND, TrendDirection.UPTREND):
                if pb >= self.UPTREND_THRESHOLD:
                    days += 1
                else:
                    break
            elif direction in (TrendDirection.STRONG_DOWNTREND, TrendDirection.DOWNTREND):
                if pb <= self.DOWNTREND_THRESHOLD:
                    days += 1
                else:
                    break
            else:
                # Neutral - count days in middle zone
                if 0.3 <= pb <= 0.7:
                    days += 1
                else:
                    break
        
        return days
    
    def _check_walking_band(self, bb_history: List[BollingerBands]) -> Tuple[bool, str]:
        """
        Check if price is walking along a band.
        
        Walking = consecutive touches/near-touches of the same band.
        """
        if len(bb_history) < self.MIN_WALKING_DAYS:
            return False, "none"
        
        recent = bb_history[:10]
        
        # Count touches
        upper_touches = 0
        lower_touches = 0
        
        for bb in recent:
            # Walking upper band: %b >= 0.9 or actually above upper
            if bb.percent_b >= 0.9:
                upper_touches += 1
            # Walking lower band: %b <= 0.1 or actually below lower
            elif bb.percent_b <= 0.1:
                lower_touches += 1
        
        if upper_touches >= self.MIN_WALKING_DAYS:
            return True, "upper"
        elif lower_touches >= self.MIN_WALKING_DAYS:
            return True, "lower"
        
        return False, "none"
    
    def _calculate_trend_strength(self, percent_b_history: List[float],
                                   direction: TrendDirection) -> float:
        """
        Calculate trend strength (0-100).
        
        Based on:
        - Average distance from neutral (0.5)
        - Consistency of %b readings
        - Momentum (slope)
        """
        if not percent_b_history or len(percent_b_history) < 3:
            return 50.0
        
        recent = percent_b_history[:20]
        avg_pb = np.mean(recent)
        
        # Distance from neutral
        if direction in (TrendDirection.STRONG_UPTREND, TrendDirection.UPTREND):
            distance = (avg_pb - 0.5) / 0.5  # 0 to 1 for uptrends
        elif direction in (TrendDirection.STRONG_DOWNTREND, TrendDirection.DOWNTREND):
            distance = (0.5 - avg_pb) / 0.5  # 0 to 1 for downtrends
        else:
            distance = 1 - abs(avg_pb - 0.5) / 0.5  # Closer to 0.5 = stronger neutral
        
        distance = max(0, min(1, distance))
        
        # Consistency (low std dev = consistent)
        std_pb = np.std(recent)
        consistency = 1 - min(std_pb / 0.3, 1)  # Max std = 0.3 for full penalty
        
        # Combine
        strength = (distance * 0.6 + consistency * 0.4) * 100
        
        return round(max(0, min(100, strength)), 1)
    
    def _calculate_slope(self, values: List[float], periods: int = 5) -> float:
        """Calculate slope (rate of change) of a series."""
        if len(values) < periods:
            return 0.0
        
        recent = values[:periods]
        # Simple linear regression slope
        x = np.arange(len(recent))
        slope, _ = np.polyfit(x, recent, 1)
        
        return round(slope, 4)
    
    def find_uptrend_stocks(self, 
                            all_bb_data: Dict[str, List[BollingerBands]],
                            min_strength: float = 60,
                            require_walking: bool = False) -> List[TrendInfo]:
        """
        Find stocks in strong uptrends.
        
        Args:
            all_bb_data: Dict mapping symbol to BB history
            min_strength: Minimum trend strength (default 60)
            require_walking: Only include stocks walking upper band
            
        Returns:
            List of TrendInfo sorted by trend strength
        """
        results = []
        
        for symbol, bb_history in all_bb_data.items():
            if not bb_history:
                continue
            
            state = self.analyze_trend(bb_history, symbol)
            
            if state.direction not in (TrendDirection.STRONG_UPTREND, TrendDirection.UPTREND):
                continue
            
            if state.strength < min_strength:
                continue
            
            if require_walking and not state.is_walking_band:
                continue
            
            current = bb_history[0]
            
            info = TrendInfo(
                symbol=symbol,
                scan_date=current.date,
                percent_b=current.percent_b,
                close_price=current.close,
                trend_direction=state.direction.value,
                trend_strength=state.strength,
                days_in_trend=state.days_in_trend,
                is_walking_upper=state.band_walking == "upper",
                is_walking_lower=False,
                days_walking=state.days_in_trend if state.is_walking_band else 0,
                distance_from_upper=((current.upper - current.close) / current.close) * 100,
                distance_from_middle=((current.close - current.middle) / current.middle) * 100,
                distance_from_lower=((current.close - current.lower) / current.close) * 100,
                percent_b_slope=state.percent_b_slope,
                price_momentum=0  # Would need price data to calculate
            )
            results.append(info)
        
        # Sort by trend strength
        results.sort(key=lambda x: x.trend_strength, reverse=True)
        
        return results
    
    def find_downtrend_stocks(self,
                               all_bb_data: Dict[str, List[BollingerBands]],
                               min_strength: float = 60,
                               require_walking: bool = False) -> List[TrendInfo]:
        """
        Find stocks in strong downtrends.
        
        Args:
            all_bb_data: Dict mapping symbol to BB history
            min_strength: Minimum trend strength (default 60)
            require_walking: Only include stocks walking lower band
            
        Returns:
            List of TrendInfo sorted by trend strength
        """
        results = []
        
        for symbol, bb_history in all_bb_data.items():
            if not bb_history:
                continue
            
            state = self.analyze_trend(bb_history, symbol)
            
            if state.direction not in (TrendDirection.STRONG_DOWNTREND, TrendDirection.DOWNTREND):
                continue
            
            if state.strength < min_strength:
                continue
            
            if require_walking and not state.is_walking_band:
                continue
            
            current = bb_history[0]
            
            info = TrendInfo(
                symbol=symbol,
                scan_date=current.date,
                percent_b=current.percent_b,
                close_price=current.close,
                trend_direction=state.direction.value,
                trend_strength=state.strength,
                days_in_trend=state.days_in_trend,
                is_walking_upper=False,
                is_walking_lower=state.band_walking == "lower",
                days_walking=state.days_in_trend if state.is_walking_band else 0,
                distance_from_upper=((current.upper - current.close) / current.close) * 100,
                distance_from_middle=((current.close - current.middle) / current.middle) * 100,
                distance_from_lower=((current.close - current.lower) / current.close) * 100,
                percent_b_slope=state.percent_b_slope,
                price_momentum=0
            )
            results.append(info)
        
        # Sort by trend strength
        results.sort(key=lambda x: x.trend_strength, reverse=True)
        
        return results
