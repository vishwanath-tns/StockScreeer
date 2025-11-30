"""
Squeeze Scanner

Scans for stocks in Bollinger Band squeeze (low volatility).
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Optional

from ..models.bb_models import BollingerBands
from ..models.scan_models import ScanResult, SqueezeScanResult


class SqueezeScanner:
    """
    Scan for stocks in volatility squeeze.
    
    A squeeze occurs when BandWidth is at historically low levels,
    indicating a potential large move is coming.
    """
    
    def __init__(self,
                 squeeze_threshold: float = 10.0,
                 min_squeeze_days: int = 3):
        """
        Initialize scanner.
        
        Args:
            squeeze_threshold: BandWidth percentile below which = squeeze
            min_squeeze_days: Minimum days in squeeze to qualify
        """
        self.squeeze_threshold = squeeze_threshold
        self.min_squeeze_days = min_squeeze_days
    
    def scan(self, all_bb_data: Dict[str, List[BollingerBands]]) -> List[SqueezeScanResult]:
        """
        Scan all symbols for squeeze conditions.
        
        Args:
            all_bb_data: Dict mapping symbol to BB history
            
        Returns:
            List of SqueezeScanResult sorted by squeeze intensity
        """
        results = []
        
        for symbol, bb_history in all_bb_data.items():
            result = self.check_symbol(symbol, bb_history)
            if result:
                results.append(result)
        
        # Sort by squeeze intensity (tighter = better)
        results.sort(key=lambda x: x.bandwidth_percentile)
        
        return results
    
    def check_symbol(self, symbol: str, 
                     bb_history: List[BollingerBands]) -> Optional[SqueezeScanResult]:
        """
        Check if a single symbol is in squeeze.
        
        Args:
            symbol: Stock symbol
            bb_history: BB history (most recent first)
            
        Returns:
            SqueezeScanResult if in squeeze, None otherwise
        """
        if not bb_history or len(bb_history) < 10:
            return None
        
        current = bb_history[0]
        
        # Must be in squeeze
        if current.bandwidth_percentile > self.squeeze_threshold:
            return None
        
        # Count squeeze duration
        squeeze_days = self._count_squeeze_days(bb_history)
        
        if squeeze_days < self.min_squeeze_days:
            return None
        
        # Determine directional bias
        bias = self._determine_bias(bb_history)
        
        # Calculate squeeze intensity
        # Lower percentile = tighter squeeze = higher intensity
        intensity = 100 - current.bandwidth_percentile * 10
        
        return SqueezeScanResult(
            symbol=symbol,
            scan_date=current.date,
            bandwidth=current.bandwidth,
            bandwidth_percentile=current.bandwidth_percentile,
            squeeze_days=squeeze_days,
            squeeze_intensity=intensity,
            percent_b=current.percent_b,
            bias=bias,
            close=current.close,
            middle_band=current.middle
        )
    
    def _count_squeeze_days(self, bb_history: List[BollingerBands]) -> int:
        """Count consecutive days in squeeze."""
        count = 0
        for bb in bb_history:
            if bb.bandwidth_percentile <= self.squeeze_threshold:
                count += 1
            else:
                break
        return count
    
    def _determine_bias(self, bb_history: List[BollingerBands]) -> str:
        """
        Determine directional bias based on %b position.
        
        Returns: "BULLISH", "BEARISH", or "NEUTRAL"
        """
        if len(bb_history) < 5:
            return "NEUTRAL"
        
        # Check recent %b trend
        recent_pb = [bb.percent_b for bb in bb_history[:5]]
        avg_pb = sum(recent_pb) / len(recent_pb)
        
        # Also check %b trend direction
        pb_rising = recent_pb[0] > recent_pb[-1]
        
        if avg_pb > 0.55 or (avg_pb > 0.5 and pb_rising):
            return "BULLISH"
        elif avg_pb < 0.45 or (avg_pb < 0.5 and not pb_rising):
            return "BEARISH"
        else:
            return "NEUTRAL"
    
    def find_imminent_breakouts(self, 
                                 all_bb_data: Dict[str, List[BollingerBands]],
                                 min_squeeze_days: int = 10) -> List[SqueezeScanResult]:
        """
        Find stocks with extended squeeze (imminent breakout).
        
        Longer squeeze = bigger expected move.
        
        Args:
            all_bb_data: BB data for all symbols
            min_squeeze_days: Minimum days in squeeze
            
        Returns:
            List of results sorted by squeeze duration
        """
        results = self.scan(all_bb_data)
        
        # Filter by squeeze duration
        imminent = [r for r in results if r.squeeze_days >= min_squeeze_days]
        
        # Sort by duration (longest first)
        imminent.sort(key=lambda x: x.squeeze_days, reverse=True)
        
        return imminent
