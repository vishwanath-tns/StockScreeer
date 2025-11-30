"""
Pullback Scanner

Scans for pullback trading opportunities in trending stocks.
"""

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

from ..models.bb_models import BollingerBands
from ..models.scan_models import PullbackScanResult


class PullbackScanner:
    """
    Scan for pullback opportunities in trending stocks.
    
    Pullback trades:
    - Uptrend pullback: Strong trend, price pulls back to middle band
    - Downtrend rally: Weak trend, price rallies to middle band
    """
    
    def __init__(self,
                 trend_lookback: int = 20,
                 pullback_zone_low: float = 0.4,
                 pullback_zone_high: float = 0.6,
                 min_trend_strength: float = 60.0):
        """
        Initialize scanner.
        
        Args:
            trend_lookback: Days to assess trend
            pullback_zone_low: Lower %b boundary for pullback zone
            pullback_zone_high: Upper %b boundary for pullback zone
            min_trend_strength: Minimum trend strength to qualify
        """
        self.trend_lookback = trend_lookback
        self.pullback_zone_low = pullback_zone_low
        self.pullback_zone_high = pullback_zone_high
        self.min_trend_strength = min_trend_strength
    
    def scan_bullish_pullbacks(self,
                                all_bb_data: Dict[str, List[BollingerBands]]) -> List[PullbackScanResult]:
        """
        Scan for bullish pullback opportunities.
        
        Criteria:
        1. Stock is in uptrend
        2. Currently pulled back to middle band area
        3. Volume declining on pullback
        
        Args:
            all_bb_data: Dict mapping symbol to BB history
            
        Returns:
            List of PullbackScanResult sorted by setup quality
        """
        results = []
        
        for symbol, bb_history in all_bb_data.items():
            result = self._check_bullish_pullback(symbol, bb_history)
            if result:
                results.append(result)
        
        # Sort by setup quality
        results.sort(key=lambda x: x.setup_quality, reverse=True)
        
        return results
    
    def scan_bearish_rallies(self,
                              all_bb_data: Dict[str, List[BollingerBands]]) -> List[PullbackScanResult]:
        """
        Scan for bearish rally (short) opportunities.
        
        Criteria:
        1. Stock is in downtrend
        2. Currently rallied to middle band area
        3. Volume declining on rally
        
        Args:
            all_bb_data: Dict mapping symbol to BB history
            
        Returns:
            List of PullbackScanResult sorted by setup quality
        """
        results = []
        
        for symbol, bb_history in all_bb_data.items():
            result = self._check_bearish_rally(symbol, bb_history)
            if result:
                results.append(result)
        
        results.sort(key=lambda x: x.setup_quality, reverse=True)
        
        return results
    
    def _check_bullish_pullback(self, symbol: str,
                                 bb_history: List[BollingerBands]) -> Optional[PullbackScanResult]:
        """Check for bullish pullback setup."""
        if not bb_history or len(bb_history) < self.trend_lookback:
            return None
        
        current = bb_history[0]
        
        # Must be in pullback zone
        if not (self.pullback_zone_low <= current.percent_b <= self.pullback_zone_high):
            return None
        
        # Assess trend strength
        trend_data = self._assess_uptrend(bb_history)
        if not trend_data or trend_data['strength'] < self.min_trend_strength:
            return None
        
        # Check pullback quality
        pullback_quality = self._assess_pullback_quality(bb_history, "bullish")
        
        # Calculate setup quality
        setup_quality = (trend_data['strength'] * 0.5) + (pullback_quality * 0.5)
        
        return PullbackScanResult(
            symbol=symbol,
            scan_date=current.date,
            pullback_type="BULLISH",
            trend_strength=trend_data['strength'],
            trend_days=trend_data['days'],
            percent_b=current.percent_b,
            pullback_depth=trend_data['pullback_depth'],
            setup_quality=setup_quality,
            close=current.close,
            middle_band=current.middle,
            target_band=current.upper,
            stop_band=current.lower,
            risk_reward=self._calculate_risk_reward(current, "bullish")
        )
    
    def _check_bearish_rally(self, symbol: str,
                              bb_history: List[BollingerBands]) -> Optional[PullbackScanResult]:
        """Check for bearish rally setup."""
        if not bb_history or len(bb_history) < self.trend_lookback:
            return None
        
        current = bb_history[0]
        
        # Must be in pullback zone (rally zone for downtrend)
        if not (self.pullback_zone_low <= current.percent_b <= self.pullback_zone_high):
            return None
        
        # Assess downtrend strength
        trend_data = self._assess_downtrend(bb_history)
        if not trend_data or trend_data['strength'] < self.min_trend_strength:
            return None
        
        # Check rally quality
        rally_quality = self._assess_pullback_quality(bb_history, "bearish")
        
        # Calculate setup quality
        setup_quality = (trend_data['strength'] * 0.5) + (rally_quality * 0.5)
        
        return PullbackScanResult(
            symbol=symbol,
            scan_date=current.date,
            pullback_type="BEARISH",
            trend_strength=trend_data['strength'],
            trend_days=trend_data['days'],
            percent_b=current.percent_b,
            pullback_depth=trend_data['pullback_depth'],
            setup_quality=setup_quality,
            close=current.close,
            middle_band=current.middle,
            target_band=current.lower,
            stop_band=current.upper,
            risk_reward=self._calculate_risk_reward(current, "bearish")
        )
    
    def _assess_uptrend(self, bb_history: List[BollingerBands]) -> Optional[dict]:
        """Assess uptrend strength."""
        lookback = min(self.trend_lookback, len(bb_history))
        recent = bb_history[:lookback]
        
        # Count days with high %b
        days_above_60 = sum(1 for bb in recent if bb.percent_b > 0.6)
        upper_touches = sum(1 for bb in recent if bb.percent_b >= 0.9)
        
        # Need at least 50% of days above 0.6
        if days_above_60 < lookback * 0.5:
            return None
        
        strength = min(100, (days_above_60 / lookback * 70) + (upper_touches * 5))
        
        # Calculate pullback depth (how far from recent high %b)
        max_pb = max(bb.percent_b for bb in recent)
        current_pb = bb_history[0].percent_b
        pullback_depth = max_pb - current_pb
        
        return {
            'strength': strength,
            'days': days_above_60,
            'upper_touches': upper_touches,
            'pullback_depth': pullback_depth
        }
    
    def _assess_downtrend(self, bb_history: List[BollingerBands]) -> Optional[dict]:
        """Assess downtrend strength."""
        lookback = min(self.trend_lookback, len(bb_history))
        recent = bb_history[:lookback]
        
        days_below_40 = sum(1 for bb in recent if bb.percent_b < 0.4)
        lower_touches = sum(1 for bb in recent if bb.percent_b <= 0.1)
        
        if days_below_40 < lookback * 0.5:
            return None
        
        strength = min(100, (days_below_40 / lookback * 70) + (lower_touches * 5))
        
        min_pb = min(bb.percent_b for bb in recent)
        current_pb = bb_history[0].percent_b
        pullback_depth = current_pb - min_pb
        
        return {
            'strength': strength,
            'days': days_below_40,
            'lower_touches': lower_touches,
            'pullback_depth': pullback_depth
        }
    
    def _assess_pullback_quality(self, bb_history: List[BollingerBands],
                                  direction: str) -> float:
        """
        Assess pullback/rally quality.
        
        Good pullback: Orderly, declining volume, stops at support
        Bad pullback: Sharp, high volume, breaks support
        
        Returns quality score 0-100.
        """
        if len(bb_history) < 5:
            return 50
        
        current = bb_history[0]
        
        # Check if pullback is orderly (gradual %b change)
        pb_changes = []
        for i in range(min(5, len(bb_history) - 1)):
            change = abs(bb_history[i].percent_b - bb_history[i + 1].percent_b)
            pb_changes.append(change)
        
        avg_change = sum(pb_changes) / len(pb_changes)
        
        # Orderly = small changes
        if avg_change < 0.1:
            orderly_score = 100
        elif avg_change < 0.2:
            orderly_score = 70
        elif avg_change < 0.3:
            orderly_score = 40
        else:
            orderly_score = 20
        
        # Check pullback depth is ideal (0.4-0.6)
        if 0.45 <= current.percent_b <= 0.55:
            depth_score = 100
        elif 0.4 <= current.percent_b <= 0.6:
            depth_score = 80
        else:
            depth_score = 50
        
        return (orderly_score * 0.6) + (depth_score * 0.4)
    
    def _calculate_risk_reward(self, current: BollingerBands,
                                direction: str) -> float:
        """Calculate risk/reward ratio."""
        if direction == "bullish":
            reward = current.upper - current.close
            risk = current.close - current.lower
        else:
            reward = current.close - current.lower
            risk = current.upper - current.close
        
        if risk <= 0:
            return 0
        
        return reward / risk
