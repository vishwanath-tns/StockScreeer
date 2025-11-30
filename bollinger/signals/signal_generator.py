"""
Signal Generator for Bollinger Bands

Generates buy/sell signals based on BB patterns.
"""

import pandas as pd
import numpy as np
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from ..models.bb_models import BollingerBands
from ..models.signal_models import (
    SignalType, PatternType, BBSignal, SignalConfidence
)


class SignalGenerator:
    """
    Generate trading signals from Bollinger Bands patterns.
    
    Key Patterns:
    - W-Bottom: Double bottom with %b divergence (BUY)
    - M-Top: Double top with %b divergence (SELL)
    - Squeeze Breakout: Volatility expansion from squeeze
    - Headfake: False breakout reversal
    - Band Walk: Trend continuation
    """
    
    def __init__(self, 
                 min_confidence: float = 50.0,
                 require_volume: bool = True):
        """
        Initialize signal generator.
        
        Args:
            min_confidence: Minimum confidence to generate signal
            require_volume: Require volume confirmation
        """
        self.min_confidence = min_confidence
        self.require_volume = require_volume
    
    def generate_signals(self, 
                         bb_history: List[BollingerBands],
                         symbol: str,
                         volume_data: List[float] = None,
                         avg_volume: float = None) -> List[BBSignal]:
        """
        Generate all applicable signals from BB history.
        
        Args:
            bb_history: List of BollingerBands (most recent first)
            symbol: Stock symbol
            volume_data: List of volumes (most recent first)
            avg_volume: Average volume for comparison
            
        Returns:
            List of BBSignal objects
        """
        if not bb_history or len(bb_history) < 20:
            return []
        
        signals = []
        
        # Check each pattern
        w_bottom = self._check_w_bottom(bb_history, symbol, volume_data, avg_volume)
        if w_bottom:
            signals.append(w_bottom)
        
        m_top = self._check_m_top(bb_history, symbol, volume_data, avg_volume)
        if m_top:
            signals.append(m_top)
        
        squeeze_breakout = self._check_squeeze_breakout(bb_history, symbol, volume_data, avg_volume)
        if squeeze_breakout:
            signals.append(squeeze_breakout)
        
        # Filter by minimum confidence
        signals = [s for s in signals if s.confidence_score >= self.min_confidence]
        
        return signals
    
    def _check_w_bottom(self, bb_history: List[BollingerBands], 
                        symbol: str,
                        volume_data: List[float] = None,
                        avg_volume: float = None) -> Optional[BBSignal]:
        """
        Check for W-bottom pattern.
        
        W-Bottom Setup:
        1. First low touches/breaks lower band (%b <= 0)
        2. Rally to middle or above
        3. Second low - price makes lower low OR equal low
        4. BUT %b makes higher low (divergence)
        5. Rally confirms pattern
        
        This is a classic reversal pattern.
        """
        if len(bb_history) < 20:
            return None
        
        # Find local lows in %b
        pb_values = [bb.percent_b for bb in bb_history[:20]]
        price_values = [bb.close for bb in bb_history[:20]]
        
        lows = self._find_local_lows(pb_values, 3)
        
        if len(lows) < 2:
            return None
        
        # Check most recent two lows
        first_low_idx = lows[1]  # Earlier low
        second_low_idx = lows[0]  # More recent low
        
        first_low_pb = pb_values[first_low_idx]
        second_low_pb = pb_values[second_low_idx]
        first_low_price = price_values[first_low_idx]
        second_low_price = price_values[second_low_idx]
        
        # W-bottom criteria:
        # 1. First low near lower band
        if first_low_pb > 0.2:
            return None
        
        # 2. %b divergence: second low %b > first low %b
        if second_low_pb <= first_low_pb:
            return None
        
        # 3. Price made lower or equal low
        if second_low_price > first_low_price * 1.02:  # 2% tolerance
            return None
        
        # 4. Current %b recovering (above the second low)
        current = bb_history[0]
        if current.percent_b <= second_low_pb:
            return None
        
        # Pattern confirmed - calculate confidence
        confidence = SignalConfidence(base_score=60)
        
        # Volume confirmation
        volume_confirmed, volume_ratio = self._check_volume(
            volume_data, avg_volume, 
            look_for="surge"  # Want volume surge on confirmation
        )
        if volume_confirmed:
            confidence.volume_bonus = 20
        
        # Pattern clarity bonus
        pb_divergence = second_low_pb - first_low_pb
        if pb_divergence > 0.2:
            confidence.pattern_bonus = 15
        elif pb_divergence > 0.1:
            confidence.pattern_bonus = 10
        
        # Trend alignment (bullish divergence in downtrend = strong)
        if first_low_pb < 0:
            confidence.trend_bonus = 10
        
        return BBSignal(
            symbol=symbol,
            signal_date=current.date,
            signal_type=SignalType.BUY,
            pattern=PatternType.W_BOTTOM,
            confidence=confidence,
            price_at_signal=current.close,
            percent_b=current.percent_b,
            bandwidth=current.bandwidth,
            volume_confirmed=volume_confirmed,
            volume_ratio=volume_ratio,
            description=f"W-bottom: %b divergence ({first_low_pb:.2f} -> {second_low_pb:.2f})",
            target_price=current.middle,  # Target middle band
            stop_loss=second_low_price * 0.98  # Stop below second low
        )
    
    def _check_m_top(self, bb_history: List[BollingerBands],
                     symbol: str,
                     volume_data: List[float] = None,
                     avg_volume: float = None) -> Optional[BBSignal]:
        """
        Check for M-top pattern.
        
        M-Top Setup (inverse of W-bottom):
        1. First high touches/breaks upper band (%b >= 1)
        2. Pullback to middle or below
        3. Second high - price makes higher high OR equal high
        4. BUT %b makes lower high (divergence)
        5. Breakdown confirms pattern
        """
        if len(bb_history) < 20:
            return None
        
        pb_values = [bb.percent_b for bb in bb_history[:20]]
        price_values = [bb.close for bb in bb_history[:20]]
        
        highs = self._find_local_highs(pb_values, 3)
        
        if len(highs) < 2:
            return None
        
        first_high_idx = highs[1]
        second_high_idx = highs[0]
        
        first_high_pb = pb_values[first_high_idx]
        second_high_pb = pb_values[second_high_idx]
        first_high_price = price_values[first_high_idx]
        second_high_price = price_values[second_high_idx]
        
        # M-top criteria:
        if first_high_pb < 0.8:
            return None
        
        if second_high_pb >= first_high_pb:
            return None
        
        if second_high_price < first_high_price * 0.98:
            return None
        
        current = bb_history[0]
        if current.percent_b >= second_high_pb:
            return None
        
        # Pattern confirmed
        confidence = SignalConfidence(base_score=60)
        
        volume_confirmed, volume_ratio = self._check_volume(
            volume_data, avg_volume, "decline"
        )
        if volume_confirmed:
            confidence.volume_bonus = 15
        
        pb_divergence = first_high_pb - second_high_pb
        if pb_divergence > 0.2:
            confidence.pattern_bonus = 15
        elif pb_divergence > 0.1:
            confidence.pattern_bonus = 10
        
        if first_high_pb > 1:
            confidence.trend_bonus = 10
        
        return BBSignal(
            symbol=symbol,
            signal_date=current.date,
            signal_type=SignalType.SELL,
            pattern=PatternType.M_TOP,
            confidence=confidence,
            price_at_signal=current.close,
            percent_b=current.percent_b,
            bandwidth=current.bandwidth,
            volume_confirmed=volume_confirmed,
            volume_ratio=volume_ratio,
            description=f"M-top: %b divergence ({first_high_pb:.2f} -> {second_high_pb:.2f})",
            target_price=current.middle,
            stop_loss=second_high_price * 1.02
        )
    
    def _check_squeeze_breakout(self, bb_history: List[BollingerBands],
                                 symbol: str,
                                 volume_data: List[float] = None,
                                 avg_volume: float = None) -> Optional[BBSignal]:
        """
        Check for squeeze breakout.
        
        Squeeze Breakout:
        1. BandWidth was in bottom 10% (squeeze)
        2. BandWidth now expanding
        3. Price breaking in one direction
        """
        if len(bb_history) < 10:
            return None
        
        current = bb_history[0]
        
        # Check if we're releasing from squeeze
        was_in_squeeze = False
        for bb in bb_history[1:6]:
            if bb.bandwidth_percentile <= 10:
                was_in_squeeze = True
                break
        
        if not was_in_squeeze:
            return None
        
        # Check bandwidth expanding
        if current.bandwidth <= bb_history[1].bandwidth:
            return None
        
        # Determine direction
        if current.percent_b > 0.7:
            signal_type = SignalType.BUY
            pattern = PatternType.SQUEEZE_BREAKOUT_UP
        elif current.percent_b < 0.3:
            signal_type = SignalType.SELL
            pattern = PatternType.SQUEEZE_BREAKOUT_DOWN
        else:
            return None  # No clear direction
        
        confidence = SignalConfidence(base_score=55)
        
        volume_confirmed, volume_ratio = self._check_volume(
            volume_data, avg_volume, "surge"
        )
        if volume_confirmed:
            confidence.volume_bonus = 20
        
        # Bonus for tight squeeze
        min_bw_pct = min(bb.bandwidth_percentile for bb in bb_history[1:6])
        if min_bw_pct <= 5:
            confidence.pattern_bonus = 15
        elif min_bw_pct <= 10:
            confidence.pattern_bonus = 10
        
        # Trend alignment
        if signal_type == SignalType.BUY and current.percent_b > 0.8:
            confidence.trend_bonus = 10
        elif signal_type == SignalType.SELL and current.percent_b < 0.2:
            confidence.trend_bonus = 10
        
        return BBSignal(
            symbol=symbol,
            signal_date=current.date,
            signal_type=signal_type,
            pattern=pattern,
            confidence=confidence,
            price_at_signal=current.close,
            percent_b=current.percent_b,
            bandwidth=current.bandwidth,
            volume_confirmed=volume_confirmed,
            volume_ratio=volume_ratio,
            description=f"Squeeze breakout {'up' if signal_type == SignalType.BUY else 'down'}"
        )
    
    def _find_local_lows(self, values: List[float], 
                         min_distance: int = 3) -> List[int]:
        """Find indices of local minima."""
        lows = []
        for i in range(1, len(values) - 1):
            if values[i] < values[i-1] and values[i] <= values[i+1]:
                if not lows or (i - lows[-1]) >= min_distance:
                    lows.append(i)
        return lows
    
    def _find_local_highs(self, values: List[float],
                          min_distance: int = 3) -> List[int]:
        """Find indices of local maxima."""
        highs = []
        for i in range(1, len(values) - 1):
            if values[i] > values[i-1] and values[i] >= values[i+1]:
                if not highs or (i - highs[-1]) >= min_distance:
                    highs.append(i)
        return highs
    
    def _check_volume(self, volume_data: List[float],
                      avg_volume: float,
                      look_for: str = "surge") -> Tuple[bool, float]:
        """
        Check volume confirmation.
        
        Args:
            volume_data: Recent volume (most recent first)
            avg_volume: Average volume
            look_for: "surge" or "decline"
            
        Returns:
            Tuple of (is_confirmed, volume_ratio)
        """
        if not volume_data or not avg_volume or avg_volume == 0:
            return False, 1.0
        
        current_vol = volume_data[0]
        ratio = current_vol / avg_volume
        
        if look_for == "surge":
            return ratio >= 1.5, ratio
        else:  # decline
            return ratio <= 0.7, ratio
