"""
Bulge Scanner

Scans for stocks in Bollinger Band bulge (high volatility).
"""

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

from ..models.bb_models import BollingerBands
from ..models.scan_models import ScanResult


@dataclass
class BulgeScanResult:
    """Result from bulge scan."""
    symbol: str
    scan_date: date
    bandwidth: float
    bandwidth_percentile: float
    bulge_days: int
    percent_b: float
    trend_direction: str  # "UP", "DOWN", "CHOPPY"
    close: float
    upper_band: float
    lower_band: float
    band_range: float  # Upper - Lower


class BulgeScanner:
    """
    Scan for stocks in volatility bulge (high volatility).
    
    A bulge occurs when BandWidth is at historically high levels,
    indicating high volatility often at trend extremes.
    """
    
    def __init__(self,
                 bulge_threshold: float = 90.0,
                 min_bulge_days: int = 1):
        """
        Initialize scanner.
        
        Args:
            bulge_threshold: BandWidth percentile above which = bulge
            min_bulge_days: Minimum days in bulge to qualify
        """
        self.bulge_threshold = bulge_threshold
        self.min_bulge_days = min_bulge_days
    
    def scan(self, all_bb_data: Dict[str, List[BollingerBands]]) -> List[BulgeScanResult]:
        """
        Scan all symbols for bulge conditions.
        
        Args:
            all_bb_data: Dict mapping symbol to BB history
            
        Returns:
            List of BulgeScanResult sorted by volatility
        """
        results = []
        
        for symbol, bb_history in all_bb_data.items():
            result = self.check_symbol(symbol, bb_history)
            if result:
                results.append(result)
        
        # Sort by bandwidth percentile (highest first)
        results.sort(key=lambda x: x.bandwidth_percentile, reverse=True)
        
        return results
    
    def check_symbol(self, symbol: str,
                     bb_history: List[BollingerBands]) -> Optional[BulgeScanResult]:
        """
        Check if a single symbol is in bulge.
        
        Args:
            symbol: Stock symbol
            bb_history: BB history (most recent first)
            
        Returns:
            BulgeScanResult if in bulge, None otherwise
        """
        if not bb_history or len(bb_history) < 10:
            return None
        
        current = bb_history[0]
        
        # Must be in bulge
        if current.bandwidth_percentile < self.bulge_threshold:
            return None
        
        # Count bulge duration
        bulge_days = self._count_bulge_days(bb_history)
        
        if bulge_days < self.min_bulge_days:
            return None
        
        # Determine trend direction
        trend = self._determine_trend(bb_history)
        
        # Calculate band range
        band_range = current.upper - current.lower
        
        return BulgeScanResult(
            symbol=symbol,
            scan_date=current.date,
            bandwidth=current.bandwidth,
            bandwidth_percentile=current.bandwidth_percentile,
            bulge_days=bulge_days,
            percent_b=current.percent_b,
            trend_direction=trend,
            close=current.close,
            upper_band=current.upper,
            lower_band=current.lower,
            band_range=band_range
        )
    
    def _count_bulge_days(self, bb_history: List[BollingerBands]) -> int:
        """Count consecutive days in bulge."""
        count = 0
        for bb in bb_history:
            if bb.bandwidth_percentile >= self.bulge_threshold:
                count += 1
            else:
                break
        return count
    
    def _determine_trend(self, bb_history: List[BollingerBands]) -> str:
        """
        Determine trend direction during bulge.
        
        Returns: "UP", "DOWN", or "CHOPPY"
        """
        if len(bb_history) < 10:
            return "CHOPPY"
        
        # Check %b behavior
        recent_pb = [bb.percent_b for bb in bb_history[:10]]
        
        # Uptrend: Consistent %b above 0.7
        above_upper = sum(1 for pb in recent_pb if pb > 0.7)
        below_lower = sum(1 for pb in recent_pb if pb < 0.3)
        
        if above_upper >= 6:
            return "UP"
        elif below_lower >= 6:
            return "DOWN"
        else:
            return "CHOPPY"
    
    def find_volatility_extremes(self,
                                  all_bb_data: Dict[str, List[BollingerBands]],
                                  percentile_threshold: float = 95.0) -> List[BulgeScanResult]:
        """
        Find stocks at extreme volatility levels.
        
        Extreme volatility often marks trend reversals.
        
        Args:
            all_bb_data: BB data for all symbols
            percentile_threshold: Minimum bandwidth percentile
            
        Returns:
            List of extreme volatility stocks
        """
        old_threshold = self.bulge_threshold
        self.bulge_threshold = percentile_threshold
        
        results = self.scan(all_bb_data)
        
        self.bulge_threshold = old_threshold
        
        return results
    
    def find_mean_reversion_candidates(self,
                                        all_bb_data: Dict[str, List[BollingerBands]]) -> List[BulgeScanResult]:
        """
        Find bulge stocks that may be setting up for mean reversion.
        
        High volatility + extreme %b = potential reversal.
        
        Returns:
            List of mean reversion candidates
        """
        results = self.scan(all_bb_data)
        
        # Filter for extreme %b readings
        candidates = [
            r for r in results
            if r.percent_b > 1.0 or r.percent_b < 0.0
        ]
        
        # Sort by extremity
        candidates.sort(key=lambda x: abs(x.percent_b - 0.5), reverse=True)
        
        return candidates
