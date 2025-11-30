"""
Mean Reversion Signal Generator

Generates signals for mean reversion trades at band extremes.
"""

from datetime import date
from typing import List, Optional, Tuple

from ..models.bb_models import BollingerBands
from ..models.signal_models import (
    SignalType, PatternType, BBSignal, SignalConfidence
)


class MeanReversionSignalGenerator:
    """
    Generate mean reversion signals at Bollinger Band extremes.
    
    Mean Reversion Trades:
    - Buy when %b < 0 (below lower band) - oversold
    - Sell when %b > 1 (above upper band) - overbought
    
    These are counter-trend trades requiring confirmation.
    """
    
    def __init__(self,
                 oversold_threshold: float = 0.0,
                 overbought_threshold: float = 1.0,
                 require_reversal: bool = True):
        """
        Initialize generator.
        
        Args:
            oversold_threshold: %b below this = oversold (default 0)
            overbought_threshold: %b above this = overbought (default 1)
            require_reversal: Require price to start reversing
        """
        self.oversold_threshold = oversold_threshold
        self.overbought_threshold = overbought_threshold
        self.require_reversal = require_reversal
    
    def generate_signal(self, bb_history: List[BollingerBands],
                        symbol: str,
                        volume_data: List[float] = None,
                        avg_volume: float = None) -> Optional[BBSignal]:
        """
        Check for mean reversion setup.
        
        Args:
            bb_history: List of BollingerBands (most recent first)
            symbol: Stock symbol
            volume_data: Recent volumes
            avg_volume: Average volume
            
        Returns:
            BBSignal if setup found
        """
        if len(bb_history) < 5:
            return None
        
        current = bb_history[0]
        
        # Check for oversold bounce
        if self._is_oversold_bounce(bb_history):
            return self._generate_long_reversion(
                bb_history, symbol, volume_data, avg_volume
            )
        
        # Check for overbought fade
        if self._is_overbought_fade(bb_history):
            return self._generate_short_reversion(
                bb_history, symbol, volume_data, avg_volume
            )
        
        return None
    
    def _is_oversold_bounce(self, bb_history: List[BollingerBands]) -> bool:
        """
        Check if we have oversold bounce setup.
        
        Criteria:
        1. Was recently below lower band (%b < 0)
        2. Now recovering (%b increasing)
        3. Not in strong downtrend (to avoid catching falling knife)
        """
        current = bb_history[0]
        
        # Was oversold recently?
        was_oversold = False
        for bb in bb_history[1:5]:
            if bb.percent_b < self.oversold_threshold:
                was_oversold = True
                break
        
        if not was_oversold:
            return False
        
        # Is recovering?
        if self.require_reversal:
            if len(bb_history) < 2:
                return False
            prev = bb_history[1]
            if current.percent_b <= prev.percent_b:
                return False
        else:
            # Just check currently oversold
            if current.percent_b >= 0.2:
                return False
        
        return True
    
    def _is_overbought_fade(self, bb_history: List[BollingerBands]) -> bool:
        """
        Check if we have overbought fade setup.
        
        Criteria:
        1. Was recently above upper band (%b > 1)
        2. Now declining (%b decreasing)
        3. Not in strong uptrend (to avoid shorting strong momentum)
        """
        current = bb_history[0]
        
        was_overbought = False
        for bb in bb_history[1:5]:
            if bb.percent_b > self.overbought_threshold:
                was_overbought = True
                break
        
        if not was_overbought:
            return False
        
        if self.require_reversal:
            if len(bb_history) < 2:
                return False
            prev = bb_history[1]
            if current.percent_b >= prev.percent_b:
                return False
        else:
            if current.percent_b <= 0.8:
                return False
        
        return True
    
    def _generate_long_reversion(self, bb_history: List[BollingerBands],
                                  symbol: str,
                                  volume_data: List[float],
                                  avg_volume: float) -> BBSignal:
        """Generate buy signal for oversold bounce."""
        current = bb_history[0]
        
        # Find how oversold it was
        min_pb = min(bb.percent_b for bb in bb_history[:10])
        
        confidence = SignalConfidence(base_score=50)
        
        # Extreme oversold bonus
        if min_pb < -0.2:
            confidence.pattern_bonus = 15
        elif min_pb < 0:
            confidence.pattern_bonus = 10
        
        # Volume confirmation - climactic volume on low is bullish
        volume_confirmed = False
        volume_ratio = 1.0
        if volume_data and avg_volume and len(volume_data) >= 3:
            # Check for volume spike at the low
            max_recent_vol = max(volume_data[:5])
            volume_ratio = max_recent_vol / avg_volume if avg_volume > 0 else 1.0
            if volume_ratio > 2.0:
                volume_confirmed = True
                confidence.volume_bonus = 20
            elif volume_ratio > 1.5:
                volume_confirmed = True
                confidence.volume_bonus = 15
        
        # Recovery strength
        if current.percent_b > 0.1:
            confidence.confirmation_bonus = 10
        
        # Calculate potential return to middle
        potential_return = ((current.middle - current.close) / current.close) * 100
        
        return BBSignal(
            symbol=symbol,
            signal_date=current.date,
            signal_type=SignalType.BUY,
            pattern=PatternType.LOWER_BAND_TOUCH,
            confidence=confidence,
            price_at_signal=current.close,
            percent_b=current.percent_b,
            bandwidth=current.bandwidth,
            volume_confirmed=volume_confirmed,
            volume_ratio=volume_ratio,
            description=f"Mean reversion: Oversold bounce (min %b: {min_pb:.2f})",
            target_price=current.middle,
            stop_loss=current.lower * 0.98
        )
    
    def _generate_short_reversion(self, bb_history: List[BollingerBands],
                                   symbol: str,
                                   volume_data: List[float],
                                   avg_volume: float) -> BBSignal:
        """Generate sell signal for overbought fade."""
        current = bb_history[0]
        
        max_pb = max(bb.percent_b for bb in bb_history[:10])
        
        confidence = SignalConfidence(base_score=50)
        
        if max_pb > 1.2:
            confidence.pattern_bonus = 15
        elif max_pb > 1.0:
            confidence.pattern_bonus = 10
        
        volume_confirmed = False
        volume_ratio = 1.0
        if volume_data and avg_volume and len(volume_data) >= 3:
            # Declining volume on fade is bearish confirmation
            recent_vol = sum(volume_data[:3]) / 3
            volume_ratio = recent_vol / avg_volume if avg_volume > 0 else 1.0
            if volume_ratio < 0.7:
                volume_confirmed = True
                confidence.volume_bonus = 15
        
        if current.percent_b < 0.9:
            confidence.confirmation_bonus = 10
        
        return BBSignal(
            symbol=symbol,
            signal_date=current.date,
            signal_type=SignalType.SELL,
            pattern=PatternType.UPPER_BAND_TOUCH,
            confidence=confidence,
            price_at_signal=current.close,
            percent_b=current.percent_b,
            bandwidth=current.bandwidth,
            volume_confirmed=volume_confirmed,
            volume_ratio=volume_ratio,
            description=f"Mean reversion: Overbought fade (max %b: {max_pb:.2f})",
            target_price=current.middle,
            stop_loss=current.upper * 1.02
        )
    
    def find_reversion_candidates(self, 
                                   all_bb_data: dict,
                                   direction: str = "both") -> List[dict]:
        """
        Scan for mean reversion candidates.
        
        Args:
            all_bb_data: Dict mapping symbol to BB history
            direction: "long", "short", or "both"
            
        Returns:
            List of candidate info dicts
        """
        candidates = []
        
        for symbol, bb_history in all_bb_data.items():
            if not bb_history or len(bb_history) < 5:
                continue
            
            current = bb_history[0]
            
            if direction in ("long", "both"):
                if current.percent_b < 0:
                    candidates.append({
                        "symbol": symbol,
                        "direction": "LONG",
                        "percent_b": current.percent_b,
                        "close": current.close,
                        "target": current.middle,
                        "potential_return": ((current.middle - current.close) / current.close) * 100,
                        "days_oversold": sum(1 for bb in bb_history[:10] if bb.percent_b < 0)
                    })
            
            if direction in ("short", "both"):
                if current.percent_b > 1:
                    candidates.append({
                        "symbol": symbol,
                        "direction": "SHORT",
                        "percent_b": current.percent_b,
                        "close": current.close,
                        "target": current.middle,
                        "potential_return": ((current.close - current.middle) / current.close) * 100,
                        "days_overbought": sum(1 for bb in bb_history[:10] if bb.percent_b > 1)
                    })
        
        # Sort by extremity
        candidates.sort(key=lambda x: abs(x["percent_b"] - 0.5), reverse=True)
        
        return candidates
