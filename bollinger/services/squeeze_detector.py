"""
Squeeze Detector for Bollinger Bands

Detects volatility contraction (squeeze) and expansion (bulge) states.
"""

import pandas as pd
import numpy as np
from datetime import date
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from ..models.bb_models import BollingerBands, VolatilityState
from ..models.scan_models import SqueezeInfo


@dataclass
class SqueezeState:
    """Current squeeze/bulge state for a stock."""
    symbol: str
    state: VolatilityState
    bandwidth: float
    bandwidth_percentile: float
    days_in_state: int
    squeeze_intensity: float  # 0-100, higher = tighter squeeze
    expected_move: float  # Expected % move when squeeze releases
    
    @property
    def is_squeeze(self) -> bool:
        return self.state == VolatilityState.SQUEEZE
    
    @property
    def is_bulge(self) -> bool:
        return self.state == VolatilityState.BULGE


class SqueezeDetector:
    """
    Detect Bollinger Bands squeeze and bulge conditions.
    
    Squeeze: BandWidth in bottom 5% of historical range
    - Indicates low volatility, potential for big move
    - Look for breakout direction confirmation
    
    Bulge: BandWidth in top 5% of historical range  
    - Indicates high volatility, potential exhaustion
    - Often marks end of a trend or start of consolidation
    """
    
    # Default thresholds (percentiles)
    SQUEEZE_THRESHOLD = 5.0      # Bottom 5% = squeeze
    LOW_VOL_THRESHOLD = 25.0     # Bottom 25% = low volatility
    HIGH_VOL_THRESHOLD = 75.0    # Top 25% = high volatility
    BULGE_THRESHOLD = 95.0       # Top 5% = bulge
    
    def __init__(self, 
                 squeeze_threshold: float = 5.0,
                 bulge_threshold: float = 95.0,
                 lookback_days: int = 126):
        """
        Initialize detector.
        
        Args:
            squeeze_threshold: Percentile threshold for squeeze (default 5)
            bulge_threshold: Percentile threshold for bulge (default 95)
            lookback_days: Days for historical percentile (default 126 = 6 months)
        """
        self.squeeze_threshold = squeeze_threshold
        self.bulge_threshold = bulge_threshold
        self.lookback_days = lookback_days
    
    def classify_volatility(self, bandwidth_percentile: float) -> VolatilityState:
        """
        Classify volatility state based on BandWidth percentile.
        
        Args:
            bandwidth_percentile: Current BandWidth percentile (0-100)
            
        Returns:
            VolatilityState enum
        """
        if bandwidth_percentile <= self.squeeze_threshold:
            return VolatilityState.SQUEEZE
        elif bandwidth_percentile <= self.LOW_VOL_THRESHOLD:
            return VolatilityState.LOW
        elif bandwidth_percentile >= self.bulge_threshold:
            return VolatilityState.BULGE
        elif bandwidth_percentile >= self.HIGH_VOL_THRESHOLD:
            return VolatilityState.HIGH
        else:
            return VolatilityState.NORMAL
    
    def detect_squeeze(self, bb_history: List[BollingerBands]) -> Optional[SqueezeState]:
        """
        Detect squeeze state from BB history.
        
        Args:
            bb_history: List of BollingerBands (most recent first)
            
        Returns:
            SqueezeState or None if no history
        """
        if not bb_history:
            return None
        
        current = bb_history[0]
        symbol = "UNKNOWN"  # Would need to pass symbol
        
        # Classify current state
        state = self.classify_volatility(current.bandwidth_percentile)
        
        # Count consecutive days in same state
        days_in_state = 1
        for bb in bb_history[1:]:
            bb_state = self.classify_volatility(bb.bandwidth_percentile)
            if bb_state == state:
                days_in_state += 1
            else:
                break
        
        # Calculate squeeze intensity (inverse of percentile, scaled)
        if state == VolatilityState.SQUEEZE:
            # Lower percentile = tighter squeeze = higher intensity
            squeeze_intensity = 100 - (current.bandwidth_percentile * 20)  # Scale 0-5% to 0-100
            squeeze_intensity = max(0, min(100, squeeze_intensity))
        else:
            squeeze_intensity = 0
        
        # Estimate expected move based on historical bandwidth range
        if len(bb_history) >= self.lookback_days:
            bandwidths = [bb.bandwidth for bb in bb_history[:self.lookback_days]]
            avg_bandwidth = np.mean(bandwidths)
            max_bandwidth = max(bandwidths)
            # Expected move = potential bandwidth expansion from current
            expected_move = (avg_bandwidth - current.bandwidth) / current.bandwidth * 100
            expected_move = max(0, expected_move)
        else:
            expected_move = 0
        
        return SqueezeState(
            symbol=symbol,
            state=state,
            bandwidth=current.bandwidth,
            bandwidth_percentile=current.bandwidth_percentile,
            days_in_state=days_in_state,
            squeeze_intensity=squeeze_intensity,
            expected_move=expected_move
        )
    
    def find_squeeze_stocks(self, 
                            all_bb_data: Dict[str, List[BollingerBands]],
                            max_percentile: float = None) -> List[SqueezeInfo]:
        """
        Find all stocks currently in squeeze.
        
        Args:
            all_bb_data: Dict mapping symbol to BB history
            max_percentile: Optional filter for maximum bandwidth percentile
            
        Returns:
            List of SqueezeInfo sorted by squeeze intensity
        """
        max_pct = max_percentile or self.squeeze_threshold
        results = []
        
        for symbol, bb_history in all_bb_data.items():
            if not bb_history:
                continue
            
            current = bb_history[0]
            
            if current.bandwidth_percentile <= max_pct:
                # Count days in squeeze
                days_in_squeeze = 1
                for bb in bb_history[1:]:
                    if bb.bandwidth_percentile <= max_pct:
                        days_in_squeeze += 1
                    else:
                        break
                
                # Calculate 6-month bandwidth stats
                lookback = min(len(bb_history), self.lookback_days)
                bandwidths = [bb.bandwidth for bb in bb_history[:lookback]]
                
                info = SqueezeInfo(
                    symbol=symbol,
                    scan_date=current.date,
                    bandwidth=current.bandwidth,
                    bandwidth_percentile=current.bandwidth_percentile,
                    percent_b=current.percent_b,
                    days_in_squeeze=days_in_squeeze,
                    squeeze_intensity=100 - (current.bandwidth_percentile * 20),
                    avg_bandwidth_6m=np.mean(bandwidths),
                    min_bandwidth_6m=min(bandwidths),
                    max_bandwidth_6m=max(bandwidths),
                    close_price=current.close,
                    distance_from_middle=((current.close - current.middle) / current.middle) * 100,
                    expected_move=(np.mean(bandwidths) - current.bandwidth) / current.bandwidth * 100 if current.bandwidth > 0 else 0
                )
                results.append(info)
        
        # Sort by squeeze intensity (tightest first)
        results.sort(key=lambda x: x.bandwidth_percentile)
        
        return results
    
    def find_bulge_stocks(self,
                          all_bb_data: Dict[str, List[BollingerBands]],
                          min_percentile: float = None) -> List[SqueezeInfo]:
        """
        Find all stocks currently in bulge (high volatility).
        
        Args:
            all_bb_data: Dict mapping symbol to BB history
            min_percentile: Optional filter for minimum bandwidth percentile
            
        Returns:
            List of SqueezeInfo sorted by bandwidth percentile (highest first)
        """
        min_pct = min_percentile or self.bulge_threshold
        results = []
        
        for symbol, bb_history in all_bb_data.items():
            if not bb_history:
                continue
            
            current = bb_history[0]
            
            if current.bandwidth_percentile >= min_pct:
                # Count days in bulge
                days_in_bulge = 1
                for bb in bb_history[1:]:
                    if bb.bandwidth_percentile >= min_pct:
                        days_in_bulge += 1
                    else:
                        break
                
                # Calculate stats
                lookback = min(len(bb_history), self.lookback_days)
                bandwidths = [bb.bandwidth for bb in bb_history[:lookback]]
                
                info = SqueezeInfo(
                    symbol=symbol,
                    scan_date=current.date,
                    bandwidth=current.bandwidth,
                    bandwidth_percentile=current.bandwidth_percentile,
                    percent_b=current.percent_b,
                    days_in_squeeze=days_in_bulge,  # Reusing field for days in bulge
                    squeeze_intensity=current.bandwidth_percentile - 95,  # Distance above bulge threshold
                    avg_bandwidth_6m=np.mean(bandwidths),
                    min_bandwidth_6m=min(bandwidths),
                    max_bandwidth_6m=max(bandwidths),
                    close_price=current.close,
                    distance_from_middle=((current.close - current.middle) / current.middle) * 100,
                    expected_move=0  # Bulge usually means volatility contraction expected
                )
                results.append(info)
        
        # Sort by bandwidth percentile (highest first)
        results.sort(key=lambda x: x.bandwidth_percentile, reverse=True)
        
        return results
    
    def is_squeeze_release(self, bb_history: List[BollingerBands], 
                           lookback: int = 5) -> Tuple[bool, str]:
        """
        Detect if a squeeze is releasing (breakout starting).
        
        Args:
            bb_history: List of BollingerBands (most recent first)
            lookback: Days to check for squeeze
            
        Returns:
            Tuple of (is_releasing, direction)
            direction is "up", "down", or "none"
        """
        if len(bb_history) < lookback + 1:
            return False, "none"
        
        # Check if we were in squeeze recently
        was_in_squeeze = False
        for bb in bb_history[1:lookback + 1]:
            if bb.bandwidth_percentile <= self.squeeze_threshold:
                was_in_squeeze = True
                break
        
        if not was_in_squeeze:
            return False, "none"
        
        current = bb_history[0]
        prev = bb_history[1]
        
        # Squeeze release = bandwidth expanding + price breakout
        bandwidth_expanding = current.bandwidth > prev.bandwidth
        
        if not bandwidth_expanding:
            return False, "none"
        
        # Determine breakout direction
        if current.percent_b > 0.8 and current.close > prev.close:
            return True, "up"
        elif current.percent_b < 0.2 and current.close < prev.close:
            return True, "down"
        
        return False, "none"
    
    def detect_headfake(self, bb_history: List[BollingerBands],
                        lookback: int = 10) -> Tuple[bool, str]:
        """
        Detect headfake pattern (false breakout from squeeze).
        
        Headfake: Initial breakout in one direction, then reversal.
        This is Bollinger's favorite squeeze trade pattern.
        
        Args:
            bb_history: List of BollingerBands (most recent first)
            lookback: Days to check for pattern
            
        Returns:
            Tuple of (is_headfake, direction)
            direction is the TRUE direction ("up" or "down" - opposite of fake)
        """
        if len(bb_history) < lookback:
            return False, "none"
        
        # Look for pattern: squeeze -> breakout -> reversal
        # 1. Find squeeze period
        squeeze_end = None
        for i in range(1, lookback):
            if bb_history[i].bandwidth_percentile <= self.squeeze_threshold:
                squeeze_end = i
                break
        
        if squeeze_end is None:
            return False, "none"
        
        # 2. Check for initial breakout
        post_squeeze = bb_history[:squeeze_end]
        if len(post_squeeze) < 3:
            return False, "none"
        
        # Initial breakout direction
        first_breakout = post_squeeze[-1]  # First bar after squeeze
        current = post_squeeze[0]
        
        # Headfake up (fake breakout up, real move down)
        if first_breakout.percent_b > 0.8 and current.percent_b < 0.5:
            if current.close < first_breakout.close:
                return True, "down"  # True direction is down
        
        # Headfake down (fake breakout down, real move up)
        if first_breakout.percent_b < 0.2 and current.percent_b > 0.5:
            if current.close > first_breakout.close:
                return True, "up"  # True direction is up
        
        return False, "none"
