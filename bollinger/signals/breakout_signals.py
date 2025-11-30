"""
Breakout Signal Generator

Generates signals for squeeze breakout trades.
"""

from datetime import date
from typing import List, Optional, Tuple

from ..models.bb_models import BollingerBands
from ..models.signal_models import (
    SignalType, PatternType, BBSignal, SignalConfidence
)


class BreakoutSignalGenerator:
    """
    Generate breakout signals from Bollinger Band squeezes.
    
    Squeeze Breakout Strategy:
    1. Identify squeeze (low BandWidth)
    2. Wait for expansion
    3. Trade in direction of breakout
    4. Watch for headfake (false breakout)
    """
    
    def __init__(self,
                 squeeze_threshold: float = 10.0,
                 breakout_threshold: float = 0.7,
                 headfake_lookback: int = 5):
        """
        Initialize generator.
        
        Args:
            squeeze_threshold: BandWidth percentile for squeeze (default 10)
            breakout_threshold: %b level for breakout confirmation
            headfake_lookback: Days to check for headfake
        """
        self.squeeze_threshold = squeeze_threshold
        self.breakout_threshold = breakout_threshold
        self.headfake_lookback = headfake_lookback
    
    def generate_signal(self, bb_history: List[BollingerBands],
                        symbol: str,
                        volume_data: List[float] = None,
                        avg_volume: float = None) -> Optional[BBSignal]:
        """
        Check for breakout signal.
        
        Args:
            bb_history: List of BollingerBands (most recent first)
            symbol: Stock symbol
            volume_data: Recent volumes
            avg_volume: Average volume
            
        Returns:
            BBSignal if breakout found
        """
        if len(bb_history) < 10:
            return None
        
        # Check for headfake first
        headfake = self._check_headfake(bb_history)
        if headfake:
            return self._generate_headfake_signal(
                bb_history, symbol, headfake, volume_data, avg_volume
            )
        
        # Check for regular breakout
        breakout = self._check_breakout(bb_history)
        if breakout:
            direction, squeeze_days = breakout
            return self._generate_breakout_signal(
                bb_history, symbol, direction, squeeze_days,
                volume_data, avg_volume
            )
        
        return None
    
    def _check_breakout(self, bb_history: List[BollingerBands]) -> Optional[Tuple[str, int]]:
        """
        Check for squeeze breakout.
        
        Returns:
            Tuple of (direction, squeeze_days) or None
        """
        current = bb_history[0]
        prev = bb_history[1] if len(bb_history) > 1 else current
        
        # Was in squeeze recently?
        squeeze_days = 0
        for bb in bb_history[1:15]:
            if bb.bandwidth_percentile <= self.squeeze_threshold:
                squeeze_days += 1
            else:
                break
        
        if squeeze_days < 3:
            return None
        
        # Is bandwidth expanding?
        if current.bandwidth <= prev.bandwidth:
            return None
        
        # Check breakout direction
        if current.percent_b >= self.breakout_threshold:
            return ("up", squeeze_days)
        elif current.percent_b <= (1 - self.breakout_threshold):
            return ("down", squeeze_days)
        
        return None
    
    def _check_headfake(self, bb_history: List[BollingerBands]) -> Optional[str]:
        """
        Check for headfake pattern.
        
        Headfake: Initial breakout fails, price reverses in opposite direction.
        This is Bollinger's favorite squeeze trade.
        
        Returns:
            Direction of true move ("up" or "down") or None
        """
        if len(bb_history) < self.headfake_lookback + 3:
            return None
        
        current = bb_history[0]
        
        # Look for squeeze followed by fake breakout followed by reversal
        
        # Step 1: Find squeeze period
        squeeze_end = None
        for i in range(2, self.headfake_lookback + 3):
            if bb_history[i].bandwidth_percentile <= self.squeeze_threshold:
                squeeze_end = i
                break
        
        if squeeze_end is None:
            return None
        
        # Step 2: Check for initial breakout after squeeze
        first_move = bb_history[squeeze_end - 1]
        
        # Step 3: Check for reversal
        initial_direction = None
        if first_move.percent_b > 0.7:
            initial_direction = "up"
        elif first_move.percent_b < 0.3:
            initial_direction = "down"
        else:
            return None
        
        # Step 4: Current should be opposite
        if initial_direction == "up" and current.percent_b < 0.4:
            # Fake up, real move down
            if current.close < first_move.close:
                return "down"
        elif initial_direction == "down" and current.percent_b > 0.6:
            # Fake down, real move up
            if current.close > first_move.close:
                return "up"
        
        return None
    
    def _generate_breakout_signal(self, bb_history: List[BollingerBands],
                                   symbol: str,
                                   direction: str,
                                   squeeze_days: int,
                                   volume_data: List[float],
                                   avg_volume: float) -> BBSignal:
        """Generate breakout signal."""
        current = bb_history[0]
        
        signal_type = SignalType.BUY if direction == "up" else SignalType.SELL
        pattern = PatternType.SQUEEZE_BREAKOUT_UP if direction == "up" else PatternType.SQUEEZE_BREAKOUT_DOWN
        
        confidence = SignalConfidence(base_score=55)
        
        # Squeeze quality bonus
        if squeeze_days >= 10:
            confidence.pattern_bonus = 15
        elif squeeze_days >= 5:
            confidence.pattern_bonus = 10
        
        # Volume confirmation - want surge on breakout
        volume_confirmed = False
        volume_ratio = 1.0
        if volume_data and avg_volume:
            current_vol = volume_data[0]
            volume_ratio = current_vol / avg_volume if avg_volume > 0 else 1.0
            if volume_ratio >= 1.5:
                volume_confirmed = True
                confidence.volume_bonus = 20
            elif volume_ratio >= 1.2:
                confidence.volume_bonus = 10
        
        # Trend alignment
        if direction == "up" and current.percent_b > 0.8:
            confidence.trend_bonus = 10
        elif direction == "down" and current.percent_b < 0.2:
            confidence.trend_bonus = 10
        
        # Calculate targets based on bandwidth expansion potential
        expected_expansion = current.bandwidth * 2  # Expect bandwidth to double
        if direction == "up":
            target = current.close * (1 + expected_expansion / 100)
            stop = current.middle
        else:
            target = current.close * (1 - expected_expansion / 100)
            stop = current.middle
        
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
            description=f"Squeeze breakout {direction} after {squeeze_days} day squeeze",
            target_price=target,
            stop_loss=stop
        )
    
    def _generate_headfake_signal(self, bb_history: List[BollingerBands],
                                   symbol: str,
                                   true_direction: str,
                                   volume_data: List[float],
                                   avg_volume: float) -> BBSignal:
        """Generate headfake reversal signal."""
        current = bb_history[0]
        
        signal_type = SignalType.BUY if true_direction == "up" else SignalType.SELL
        pattern = PatternType.HEADFAKE_DOWN if true_direction == "up" else PatternType.HEADFAKE_UP
        
        confidence = SignalConfidence(base_score=65)  # Headfake is high-probability
        
        # Volume on reversal
        volume_confirmed = False
        volume_ratio = 1.0
        if volume_data and avg_volume:
            current_vol = volume_data[0]
            volume_ratio = current_vol / avg_volume if avg_volume > 0 else 1.0
            if volume_ratio >= 1.3:
                volume_confirmed = True
                confidence.volume_bonus = 15
        
        # Pattern is inherently strong
        confidence.pattern_bonus = 15
        
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
            description=f"Headfake pattern: True direction is {true_direction}",
            target_price=current.upper if true_direction == "up" else current.lower,
            stop_loss=current.lower if true_direction == "up" else current.upper
        )
    
    def find_squeeze_candidates(self, all_bb_data: dict) -> List[dict]:
        """
        Find stocks in squeeze (potential breakout candidates).
        
        Args:
            all_bb_data: Dict mapping symbol to BB history
            
        Returns:
            List of squeeze candidate info dicts
        """
        candidates = []
        
        for symbol, bb_history in all_bb_data.items():
            if not bb_history or len(bb_history) < 10:
                continue
            
            current = bb_history[0]
            
            if current.bandwidth_percentile <= self.squeeze_threshold:
                # Count squeeze duration
                squeeze_days = 1
                for bb in bb_history[1:20]:
                    if bb.bandwidth_percentile <= self.squeeze_threshold:
                        squeeze_days += 1
                    else:
                        break
                
                # Determine bias from %b position
                if current.percent_b > 0.55:
                    bias = "BULLISH"
                elif current.percent_b < 0.45:
                    bias = "BEARISH"
                else:
                    bias = "NEUTRAL"
                
                candidates.append({
                    "symbol": symbol,
                    "bandwidth_percentile": current.bandwidth_percentile,
                    "squeeze_days": squeeze_days,
                    "percent_b": current.percent_b,
                    "bias": bias,
                    "close": current.close,
                    "squeeze_intensity": 10 - current.bandwidth_percentile
                })
        
        # Sort by squeeze tightness
        candidates.sort(key=lambda x: x["bandwidth_percentile"])
        
        return candidates
