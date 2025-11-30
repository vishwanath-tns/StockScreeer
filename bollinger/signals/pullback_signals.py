"""
Pullback Signal Generator

Generates signals for pullback-to-middle-band trades.
"""

from datetime import date
from typing import List, Optional, Tuple

from ..models.bb_models import BollingerBands
from ..models.signal_models import (
    SignalType, PatternType, BBSignal, SignalConfidence
)


class PullbackSignalGenerator:
    """
    Generate pullback trading signals.
    
    Pullback Trade (Trend Continuation):
    - In uptrend: Buy when price pulls back to middle band
    - In downtrend: Sell when price rallies to middle band
    
    This is Method 3 from John Bollinger's methodology.
    """
    
    def __init__(self,
                 pullback_zone_low: float = 0.4,
                 pullback_zone_high: float = 0.6,
                 trend_lookback: int = 20):
        """
        Initialize generator.
        
        Args:
            pullback_zone_low: Lower %b threshold for pullback zone
            pullback_zone_high: Upper %b threshold for pullback zone
            trend_lookback: Days to assess trend
        """
        self.pullback_zone_low = pullback_zone_low
        self.pullback_zone_high = pullback_zone_high
        self.trend_lookback = trend_lookback
    
    def generate_signal(self, bb_history: List[BollingerBands],
                        symbol: str,
                        volume_data: List[float] = None,
                        avg_volume: float = None) -> Optional[BBSignal]:
        """
        Check for pullback trade setup.
        
        Args:
            bb_history: List of BollingerBands (most recent first)
            symbol: Stock symbol
            volume_data: Recent volumes
            avg_volume: Average volume
            
        Returns:
            BBSignal if setup found, None otherwise
        """
        if len(bb_history) < self.trend_lookback:
            return None
        
        current = bb_history[0]
        
        # Check if in pullback zone
        if not (self.pullback_zone_low <= current.percent_b <= self.pullback_zone_high):
            return None
        
        # Determine trend
        trend, trend_strength = self._assess_trend(bb_history)
        
        if trend == "uptrend":
            return self._generate_buy_pullback(
                bb_history, symbol, trend_strength, volume_data, avg_volume
            )
        elif trend == "downtrend":
            return self._generate_sell_pullback(
                bb_history, symbol, trend_strength, volume_data, avg_volume
            )
        
        return None
    
    def _assess_trend(self, bb_history: List[BollingerBands]) -> Tuple[str, float]:
        """
        Assess the prevailing trend.
        
        Returns:
            Tuple of (trend_direction, trend_strength)
        """
        lookback = min(len(bb_history), self.trend_lookback)
        recent = bb_history[:lookback]
        
        # Count days above/below middle
        above_middle = sum(1 for bb in recent if bb.percent_b > 0.5)
        below_middle = sum(1 for bb in recent if bb.percent_b < 0.5)
        
        # Check for upper band touches (strong uptrend indicator)
        upper_touches = sum(1 for bb in recent if bb.percent_b >= 0.9)
        lower_touches = sum(1 for bb in recent if bb.percent_b <= 0.1)
        
        # Calculate average %b
        avg_pb = sum(bb.percent_b for bb in recent) / lookback
        
        # Determine trend
        if above_middle >= lookback * 0.6 or upper_touches >= 3:
            strength = min(100, (above_middle / lookback * 100) + (upper_touches * 10))
            return "uptrend", strength
        elif below_middle >= lookback * 0.6 or lower_touches >= 3:
            strength = min(100, (below_middle / lookback * 100) + (lower_touches * 10))
            return "downtrend", strength
        
        return "neutral", 50
    
    def _generate_buy_pullback(self, bb_history: List[BollingerBands],
                                symbol: str,
                                trend_strength: float,
                                volume_data: List[float],
                                avg_volume: float) -> Optional[BBSignal]:
        """Generate buy signal for uptrend pullback."""
        current = bb_history[0]
        prev = bb_history[1] if len(bb_history) > 1 else current
        
        # Check pullback quality
        # Good pullback: Coming from above, volume declining
        was_above = prev.percent_b > current.percent_b and prev.percent_b > 0.6
        
        if not was_above:
            # Not a real pullback, could be just hovering
            return None
        
        confidence = SignalConfidence(base_score=55)
        
        # Trend strength bonus
        if trend_strength > 70:
            confidence.trend_bonus = 15
        elif trend_strength > 50:
            confidence.trend_bonus = 10
        
        # Volume analysis - want declining volume on pullback
        volume_confirmed = False
        volume_ratio = 1.0
        if volume_data and avg_volume and len(volume_data) >= 3:
            recent_vol = sum(volume_data[:3]) / 3
            volume_ratio = recent_vol / avg_volume if avg_volume > 0 else 1.0
            # Declining volume on pullback is bullish
            if volume_ratio < 0.8:
                volume_confirmed = True
                confidence.volume_bonus = 15
        
        # Pattern bonus for clean pullback
        pullback_depth = 0.6 - current.percent_b  # How far from 0.6
        if 0.1 <= pullback_depth <= 0.2:
            confidence.pattern_bonus = 15  # Perfect depth
        elif pullback_depth < 0.1:
            confidence.pattern_bonus = 10  # Shallow but ok
        
        return BBSignal(
            symbol=symbol,
            signal_date=current.date,
            signal_type=SignalType.BUY,
            pattern=PatternType.MIDDLE_BAND_PULLBACK,
            confidence=confidence,
            price_at_signal=current.close,
            percent_b=current.percent_b,
            bandwidth=current.bandwidth,
            volume_confirmed=volume_confirmed,
            volume_ratio=volume_ratio,
            description=f"Uptrend pullback to middle band (trend strength: {trend_strength:.0f}%)",
            target_price=current.upper,  # Target upper band
            stop_loss=current.lower  # Stop at lower band
        )
    
    def _generate_sell_pullback(self, bb_history: List[BollingerBands],
                                 symbol: str,
                                 trend_strength: float,
                                 volume_data: List[float],
                                 avg_volume: float) -> Optional[BBSignal]:
        """Generate sell signal for downtrend rally."""
        current = bb_history[0]
        prev = bb_history[1] if len(bb_history) > 1 else current
        
        # Check rally quality
        was_below = prev.percent_b < current.percent_b and prev.percent_b < 0.4
        
        if not was_below:
            return None
        
        confidence = SignalConfidence(base_score=55)
        
        if trend_strength > 70:
            confidence.trend_bonus = 15
        elif trend_strength > 50:
            confidence.trend_bonus = 10
        
        # Volume analysis - want declining volume on rally
        volume_confirmed = False
        volume_ratio = 1.0
        if volume_data and avg_volume and len(volume_data) >= 3:
            recent_vol = sum(volume_data[:3]) / 3
            volume_ratio = recent_vol / avg_volume if avg_volume > 0 else 1.0
            if volume_ratio < 0.8:
                volume_confirmed = True
                confidence.volume_bonus = 15
        
        rally_height = current.percent_b - 0.4
        if 0.1 <= rally_height <= 0.2:
            confidence.pattern_bonus = 15
        elif rally_height < 0.1:
            confidence.pattern_bonus = 10
        
        return BBSignal(
            symbol=symbol,
            signal_date=current.date,
            signal_type=SignalType.SELL,
            pattern=PatternType.MIDDLE_BAND_PULLBACK,
            confidence=confidence,
            price_at_signal=current.close,
            percent_b=current.percent_b,
            bandwidth=current.bandwidth,
            volume_confirmed=volume_confirmed,
            volume_ratio=volume_ratio,
            description=f"Downtrend rally to middle band (trend strength: {trend_strength:.0f}%)",
            target_price=current.lower,
            stop_loss=current.upper
        )
