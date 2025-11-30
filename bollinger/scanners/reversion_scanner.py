"""
Mean Reversion Scanner

Scans for mean reversion trading opportunities.
"""

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Tuple

from ..models.bb_models import BollingerBands


@dataclass
class ReversionScanResult:
    """Result from mean reversion scan."""
    symbol: str
    scan_date: date
    reversion_type: str  # "OVERSOLD" or "OVERBOUGHT"
    percent_b: float
    days_extreme: int
    extremity_score: float  # How extreme (0-100)
    close: float
    target: float  # Middle band
    potential_return_pct: float
    bandwidth: float
    bandwidth_percentile: float


class MeanReversionScanner:
    """
    Scan for mean reversion opportunities.
    
    Mean reversion trades work best when:
    1. Price is at band extremes (%b < 0 or %b > 1)
    2. Volatility is high (bands wide)
    3. Showing reversal signs
    """
    
    def __init__(self,
                 oversold_threshold: float = 0.0,
                 overbought_threshold: float = 1.0,
                 min_extremity: float = 30.0):
        """
        Initialize scanner.
        
        Args:
            oversold_threshold: %b below this = oversold
            overbought_threshold: %b above this = overbought
            min_extremity: Minimum extremity score to include
        """
        self.oversold_threshold = oversold_threshold
        self.overbought_threshold = overbought_threshold
        self.min_extremity = min_extremity
    
    def scan_oversold(self,
                      all_bb_data: Dict[str, List[BollingerBands]]) -> List[ReversionScanResult]:
        """
        Scan for oversold stocks (potential bounce candidates).
        
        Args:
            all_bb_data: Dict mapping symbol to BB history
            
        Returns:
            List of ReversionScanResult sorted by extremity
        """
        results = []
        
        for symbol, bb_history in all_bb_data.items():
            result = self._check_oversold(symbol, bb_history)
            if result:
                results.append(result)
        
        # Sort by extremity (most extreme first)
        results.sort(key=lambda x: x.extremity_score, reverse=True)
        
        return results
    
    def scan_overbought(self,
                        all_bb_data: Dict[str, List[BollingerBands]]) -> List[ReversionScanResult]:
        """
        Scan for overbought stocks (potential fade candidates).
        
        Args:
            all_bb_data: Dict mapping symbol to BB history
            
        Returns:
            List of ReversionScanResult sorted by extremity
        """
        results = []
        
        for symbol, bb_history in all_bb_data.items():
            result = self._check_overbought(symbol, bb_history)
            if result:
                results.append(result)
        
        results.sort(key=lambda x: x.extremity_score, reverse=True)
        
        return results
    
    def scan_all(self,
                 all_bb_data: Dict[str, List[BollingerBands]]) -> Dict[str, List[ReversionScanResult]]:
        """
        Scan for all reversion opportunities.
        
        Returns:
            Dict with 'oversold' and 'overbought' lists
        """
        return {
            'oversold': self.scan_oversold(all_bb_data),
            'overbought': self.scan_overbought(all_bb_data)
        }
    
    def _check_oversold(self, symbol: str,
                        bb_history: List[BollingerBands]) -> Optional[ReversionScanResult]:
        """Check for oversold condition."""
        if not bb_history or len(bb_history) < 5:
            return None
        
        current = bb_history[0]
        
        # Must be oversold
        if current.percent_b > self.oversold_threshold:
            return None
        
        # Count days extreme
        days_extreme = self._count_extreme_days(bb_history, "oversold")
        
        # Calculate extremity score
        extremity = self._calculate_extremity(current.percent_b, "oversold")
        
        if extremity < self.min_extremity:
            return None
        
        # Calculate potential return
        potential_return = ((current.middle - current.close) / current.close) * 100
        
        return ReversionScanResult(
            symbol=symbol,
            scan_date=current.date,
            reversion_type="OVERSOLD",
            percent_b=current.percent_b,
            days_extreme=days_extreme,
            extremity_score=extremity,
            close=current.close,
            target=current.middle,
            potential_return_pct=potential_return,
            bandwidth=current.bandwidth,
            bandwidth_percentile=current.bandwidth_percentile
        )
    
    def _check_overbought(self, symbol: str,
                          bb_history: List[BollingerBands]) -> Optional[ReversionScanResult]:
        """Check for overbought condition."""
        if not bb_history or len(bb_history) < 5:
            return None
        
        current = bb_history[0]
        
        # Must be overbought
        if current.percent_b < self.overbought_threshold:
            return None
        
        days_extreme = self._count_extreme_days(bb_history, "overbought")
        extremity = self._calculate_extremity(current.percent_b, "overbought")
        
        if extremity < self.min_extremity:
            return None
        
        potential_return = ((current.close - current.middle) / current.close) * 100
        
        return ReversionScanResult(
            symbol=symbol,
            scan_date=current.date,
            reversion_type="OVERBOUGHT",
            percent_b=current.percent_b,
            days_extreme=days_extreme,
            extremity_score=extremity,
            close=current.close,
            target=current.middle,
            potential_return_pct=potential_return,
            bandwidth=current.bandwidth,
            bandwidth_percentile=current.bandwidth_percentile
        )
    
    def _count_extreme_days(self, bb_history: List[BollingerBands],
                            direction: str) -> int:
        """Count consecutive days at extreme."""
        count = 0
        threshold = self.oversold_threshold if direction == "oversold" else self.overbought_threshold
        
        for bb in bb_history:
            if direction == "oversold":
                if bb.percent_b <= threshold:
                    count += 1
                else:
                    break
            else:
                if bb.percent_b >= threshold:
                    count += 1
                else:
                    break
        
        return count
    
    def _calculate_extremity(self, percent_b: float, direction: str) -> float:
        """
        Calculate extremity score (0-100).
        
        More extreme %b = higher score.
        """
        if direction == "oversold":
            # %b of 0 = 50 points, %b of -0.5 = 100 points
            if percent_b >= 0:
                return 50
            else:
                return min(100, 50 + abs(percent_b) * 100)
        else:
            # %b of 1 = 50 points, %b of 1.5 = 100 points
            if percent_b <= 1:
                return 50
            else:
                return min(100, 50 + (percent_b - 1) * 100)
    
    def find_extreme_reversals(self,
                               all_bb_data: Dict[str, List[BollingerBands]],
                               min_extremity: float = 70.0) -> Tuple[List[ReversionScanResult], List[ReversionScanResult]]:
        """
        Find stocks at extreme levels for high-probability reversals.
        
        Args:
            all_bb_data: BB data for all symbols
            min_extremity: Minimum extremity score
            
        Returns:
            Tuple of (oversold list, overbought list)
        """
        old_min = self.min_extremity
        self.min_extremity = min_extremity
        
        results = self.scan_all(all_bb_data)
        
        self.min_extremity = old_min
        
        return results['oversold'], results['overbought']
    
    def find_reversal_with_confirmation(self,
                                         all_bb_data: Dict[str, List[BollingerBands]]) -> Dict[str, List[ReversionScanResult]]:
        """
        Find reversals with price confirmation (price starting to turn).
        
        Confirmation: %b moving back toward middle after extreme.
        
        Returns:
            Dict with 'oversold_bouncing' and 'overbought_fading' lists
        """
        confirmed = {
            'oversold_bouncing': [],
            'overbought_fading': []
        }
        
        for symbol, bb_history in all_bb_data.items():
            if len(bb_history) < 3:
                continue
            
            current = bb_history[0]
            prev = bb_history[1]
            
            # Check for oversold bounce
            if prev.percent_b < 0 and current.percent_b > prev.percent_b:
                result = self._check_oversold(symbol, bb_history)
                if result:
                    confirmed['oversold_bouncing'].append(result)
            
            # Check for overbought fade
            if prev.percent_b > 1 and current.percent_b < prev.percent_b:
                result = self._check_overbought(symbol, bb_history)
                if result:
                    confirmed['overbought_fading'].append(result)
        
        # Sort by extremity
        for key in confirmed:
            confirmed[key].sort(key=lambda x: x.extremity_score, reverse=True)
        
        return confirmed
