"""
Trend Scanner

Scans for stocks in strong uptrends or downtrends using Bollinger Bands.
"""

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

from ..models.bb_models import BollingerBands
from ..models.scan_models import TrendScanResult


class TrendScanner:
    """
    Scan for stocks in strong trends using Bollinger Band analysis.
    
    Trend identification:
    - Uptrend: Price riding upper band (%b consistently > 0.7)
    - Downtrend: Price riding lower band (%b consistently < 0.3)
    """
    
    def __init__(self,
                 uptrend_pb_threshold: float = 0.7,
                 downtrend_pb_threshold: float = 0.3,
                 min_trend_days: int = 5,
                 consistency_threshold: float = 0.6):
        """
        Initialize scanner.
        
        Args:
            uptrend_pb_threshold: %b above this = uptrend
            downtrend_pb_threshold: %b below this = downtrend
            min_trend_days: Minimum days to qualify as trend
            consistency_threshold: Percent of days that must confirm trend
        """
        self.uptrend_pb_threshold = uptrend_pb_threshold
        self.downtrend_pb_threshold = downtrend_pb_threshold
        self.min_trend_days = min_trend_days
        self.consistency_threshold = consistency_threshold
    
    def scan_uptrends(self, 
                      all_bb_data: Dict[str, List[BollingerBands]]) -> List[TrendScanResult]:
        """
        Scan for stocks in strong uptrend.
        
        Args:
            all_bb_data: Dict mapping symbol to BB history
            
        Returns:
            List of TrendScanResult sorted by trend strength
        """
        results = []
        
        for symbol, bb_history in all_bb_data.items():
            result = self._check_uptrend(symbol, bb_history)
            if result:
                results.append(result)
        
        # Sort by trend strength
        results.sort(key=lambda x: x.trend_strength, reverse=True)
        
        return results
    
    def scan_downtrends(self,
                        all_bb_data: Dict[str, List[BollingerBands]]) -> List[TrendScanResult]:
        """
        Scan for stocks in strong downtrend.
        
        Args:
            all_bb_data: Dict mapping symbol to BB history
            
        Returns:
            List of TrendScanResult sorted by trend strength
        """
        results = []
        
        for symbol, bb_history in all_bb_data.items():
            result = self._check_downtrend(symbol, bb_history)
            if result:
                results.append(result)
        
        # Sort by trend strength
        results.sort(key=lambda x: x.trend_strength, reverse=True)
        
        return results
    
    def scan_all(self, 
                 all_bb_data: Dict[str, List[BollingerBands]]) -> Dict[str, List[TrendScanResult]]:
        """
        Scan for all trends.
        
        Returns:
            Dict with 'uptrend' and 'downtrend' lists
        """
        return {
            'uptrend': self.scan_uptrends(all_bb_data),
            'downtrend': self.scan_downtrends(all_bb_data)
        }
    
    def _check_uptrend(self, symbol: str,
                       bb_history: List[BollingerBands]) -> Optional[TrendScanResult]:
        """Check for uptrend."""
        if not bb_history or len(bb_history) < self.min_trend_days:
            return None
        
        current = bb_history[0]
        lookback = min(20, len(bb_history))
        recent = bb_history[:lookback]
        
        # Count days above threshold
        days_above = sum(
            1 for bb in recent 
            if bb.percent_b >= self.uptrend_pb_threshold
        )
        
        consistency = days_above / lookback
        
        if consistency < self.consistency_threshold:
            return None
        
        # Calculate trend strength
        avg_pb = sum(bb.percent_b for bb in recent) / lookback
        upper_touches = sum(1 for bb in recent if bb.percent_b >= 0.9)
        
        trend_strength = min(100, (consistency * 60) + (upper_touches * 4))
        
        # Check if currently in trend
        if current.percent_b < self.uptrend_pb_threshold:
            # Currently pulled back
            trend_phase = "PULLBACK"
        elif current.percent_b >= 0.9:
            trend_phase = "EXTENDED"
        else:
            trend_phase = "HEALTHY"
        
        return TrendScanResult(
            symbol=symbol,
            scan_date=current.date,
            trend_direction="UPTREND",
            trend_strength=trend_strength,
            trend_days=days_above,
            percent_b=current.percent_b,
            avg_percent_b=avg_pb,
            upper_touches=upper_touches,
            lower_touches=0,
            trend_phase=trend_phase,
            close=current.close,
            middle_band=current.middle,
            distance_from_middle_pct=((current.close - current.middle) / current.middle) * 100
        )
    
    def _check_downtrend(self, symbol: str,
                         bb_history: List[BollingerBands]) -> Optional[TrendScanResult]:
        """Check for downtrend."""
        if not bb_history or len(bb_history) < self.min_trend_days:
            return None
        
        current = bb_history[0]
        lookback = min(20, len(bb_history))
        recent = bb_history[:lookback]
        
        # Count days below threshold
        days_below = sum(
            1 for bb in recent 
            if bb.percent_b <= self.downtrend_pb_threshold
        )
        
        consistency = days_below / lookback
        
        if consistency < self.consistency_threshold:
            return None
        
        # Calculate trend strength
        avg_pb = sum(bb.percent_b for bb in recent) / lookback
        lower_touches = sum(1 for bb in recent if bb.percent_b <= 0.1)
        
        trend_strength = min(100, (consistency * 60) + (lower_touches * 4))
        
        # Check trend phase
        if current.percent_b > self.downtrend_pb_threshold:
            trend_phase = "BOUNCE"
        elif current.percent_b <= 0.1:
            trend_phase = "OVERSOLD"
        else:
            trend_phase = "WEAK"
        
        return TrendScanResult(
            symbol=symbol,
            scan_date=current.date,
            trend_direction="DOWNTREND",
            trend_strength=trend_strength,
            trend_days=days_below,
            percent_b=current.percent_b,
            avg_percent_b=avg_pb,
            upper_touches=0,
            lower_touches=lower_touches,
            trend_phase=trend_phase,
            close=current.close,
            middle_band=current.middle,
            distance_from_middle_pct=((current.close - current.middle) / current.middle) * 100
        )
    
    def find_band_walkers(self,
                          all_bb_data: Dict[str, List[BollingerBands]],
                          direction: str = "up") -> List[TrendScanResult]:
        """
        Find stocks "walking the band" - consistent riding of upper/lower band.
        
        Walking the band is a sign of strong trend momentum.
        
        Args:
            all_bb_data: BB data for all symbols
            direction: "up" for upper band, "down" for lower band
            
        Returns:
            List of band walker results
        """
        if direction == "up":
            results = self.scan_uptrends(all_bb_data)
            # Filter for very consistent trends
            walkers = [r for r in results if r.upper_touches >= 5 and r.trend_strength >= 70]
        else:
            results = self.scan_downtrends(all_bb_data)
            walkers = [r for r in results if r.lower_touches >= 5 and r.trend_strength >= 70]
        
        return walkers
