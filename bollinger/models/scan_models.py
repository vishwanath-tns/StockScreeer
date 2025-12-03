"""
Scanner Models for Bollinger Bands System

Defines scan types and result structures.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class ScanType(Enum):
    """Types of scans available."""
    SQUEEZE = "squeeze"              # Volatility contraction
    BULGE = "bulge"                  # Volatility expansion/exhaustion
    STRONG_UPTREND = "strong_uptrend"      # Walking upper band
    STRONG_DOWNTREND = "strong_downtrend"  # Walking lower band
    PULLBACK_BUY = "pullback_buy"    # Pullback to middle in uptrend
    PULLBACK_SELL = "pullback_sell"  # Rally to middle in downtrend
    MEAN_REVERSION_LONG = "mean_reversion_long"   # Oversold bounce
    MEAN_REVERSION_SHORT = "mean_reversion_short" # Overbought fade
    BREAKOUT_UP = "breakout_up"      # Squeeze breakout upward
    BREAKOUT_DOWN = "breakout_down"  # Squeeze breakout downward


@dataclass
class SqueezeInfo:
    """
    Information about a stock in squeeze state.
    
    Used for squeeze and bulge scanner results.
    """
    symbol: str
    scan_date: date
    
    # Current state
    bandwidth: float
    bandwidth_percentile: float
    percent_b: float
    
    # Squeeze metrics
    days_in_squeeze: int = 0
    squeeze_intensity: float = 0.0  # How tight (0-100, 100=tightest)
    
    # Historical context
    avg_bandwidth_6m: float = 0.0
    min_bandwidth_6m: float = 0.0
    max_bandwidth_6m: float = 0.0
    
    # Price context
    close_price: float = 0.0
    distance_from_middle: float = 0.0  # Percentage
    
    # Expected volatility expansion
    expected_move: float = 0.0  # Expected % move when squeeze releases
    
    @property
    def is_extreme_squeeze(self) -> bool:
        """Squeeze in bottom 2% of historical range."""
        return self.bandwidth_percentile <= 2.0


@dataclass
class SqueezeScanResult:
    """
    Result for a single stock from squeeze scanner.
    """
    symbol: str
    scan_date: date
    bandwidth: float
    bandwidth_percentile: float
    squeeze_days: int
    squeeze_intensity: float
    percent_b: float
    bias: str  # "BULLISH", "BEARISH", "NEUTRAL"
    close: float
    middle_band: float
    
    @property
    def is_extreme(self) -> bool:
        """In extreme squeeze (bottom 5%)."""
        return self.bandwidth_percentile <= 5.0
    
    @property
    def expected_move(self) -> float:
        """Estimated % move based on squeeze duration."""
        # Longer squeeze = bigger move expected
        return min(self.squeeze_days * 0.5, 15.0)  # Cap at 15%


@dataclass
class TrendInfo:
    """
    Information about a stock's trend based on BB position.
    
    Used for trend scanner results.
    """
    symbol: str
    scan_date: date
    
    # Current position
    percent_b: float
    close_price: float
    
    # Trend metrics
    trend_direction: str  # "uptrend", "downtrend", "neutral"
    trend_strength: float  # 0-100
    days_in_trend: int = 0
    
    # Band walking
    is_walking_upper: bool = False
    is_walking_lower: bool = False
    days_walking: int = 0
    
    # Price vs bands
    distance_from_upper: float = 0.0  # Percentage
    distance_from_middle: float = 0.0
    distance_from_lower: float = 0.0
    
    # Momentum
    percent_b_slope: float = 0.0  # Rate of change in %b
    price_momentum: float = 0.0   # Price ROC


@dataclass
class TrendScanResult:
    """
    Result for a single stock from trend scanner.
    """
    symbol: str
    scan_date: date
    trend_direction: str  # "UPTREND" or "DOWNTREND"
    trend_strength: float  # 0-100
    trend_days: int
    percent_b: float
    avg_percent_b: float
    upper_touches: int
    lower_touches: int
    trend_phase: str  # "HEALTHY", "EXTENDED", "PULLBACK", etc.
    close: float
    middle_band: float
    distance_from_middle_pct: float
    
    @property
    def is_strong_trend(self) -> bool:
        """Trend strength above 70."""
        return self.trend_strength >= 70.0


@dataclass
class PullbackScanResult:
    """
    Result for a single stock from pullback scanner.
    """
    symbol: str
    scan_date: date
    pullback_type: str  # "BULLISH" or "BEARISH"
    trend_strength: float
    trend_days: int
    percent_b: float
    pullback_depth: float  # How far pulled back
    setup_quality: float  # 0-100, higher = better setup
    close: float
    middle_band: float
    target_band: float
    stop_band: float
    risk_reward: float
    
    @property
    def is_high_quality(self) -> bool:
        """Setup quality above 70."""
        return self.setup_quality >= 70.0


@dataclass
class PullbackInfo:
    """
    Information about a pullback candidate.
    
    Used for pullback scanner results.
    """
    symbol: str
    scan_date: date
    
    # Current position
    percent_b: float
    close_price: float
    
    # Trend context
    trend_direction: str
    trend_strength: float
    
    # Pullback metrics
    pullback_depth: float  # How far pulled back (%)
    distance_to_middle: float  # Distance to middle band
    at_middle_band: bool  # Within 2% of middle
    
    # Quality score
    pullback_quality: float  # 0-100, higher = better setup
    
    # Supporting indicators
    volume_declining: bool = False
    rsi_not_oversold: bool = True
    
    # Entry context
    suggested_entry: float = 0.0
    suggested_stop: float = 0.0
    risk_reward: float = 0.0


@dataclass
class ReversionInfo:
    """
    Information about a mean reversion candidate.
    
    Used for reversion scanner results.
    """
    symbol: str
    scan_date: date
    
    # Current position
    percent_b: float
    close_price: float
    
    # Extremity
    is_oversold: bool = False   # %b < 0
    is_overbought: bool = False # %b > 1
    extreme_duration: int = 0   # Days at extreme
    
    # Reversion potential
    reversion_target: float = 0.0  # Expected target (middle band)
    potential_return: float = 0.0  # Expected % return
    
    # Historical context
    times_at_extreme_6m: int = 0
    avg_reversion_time: float = 0.0  # Days to revert
    avg_reversion_return: float = 0.0
    
    # Quality score
    reversion_quality: float = 0.0  # 0-100


@dataclass
class ScanResult:
    """
    Result of a scanner run.
    
    Contains the list of matching stocks and metadata.
    """
    scan_type: ScanType
    scan_date: date
    scan_time: datetime = field(default_factory=datetime.now)
    
    # Results
    total_scanned: int = 0
    matches_found: int = 0
    
    # Result lists (populated based on scan type)
    squeeze_results: List[SqueezeInfo] = field(default_factory=list)
    trend_results: List[TrendInfo] = field(default_factory=list)
    pullback_results: List[PullbackInfo] = field(default_factory=list)
    reversion_results: List[ReversionInfo] = field(default_factory=list)
    
    # Generic symbol list for simple scans
    symbols: List[str] = field(default_factory=list)
    
    # Execution info
    execution_time_ms: float = 0.0
    success: bool = True
    error: str = ""
    
    @property
    def results(self) -> List[Any]:
        """Get the appropriate result list based on scan type."""
        if self.scan_type == ScanType.SQUEEZE:
            return self.squeeze_results
        elif self.scan_type == ScanType.BULGE:
            return self.squeeze_results  # Same structure
        elif self.scan_type in (ScanType.STRONG_UPTREND, ScanType.STRONG_DOWNTREND):
            return self.trend_results
        elif self.scan_type in (ScanType.PULLBACK_BUY, ScanType.PULLBACK_SELL):
            return self.pullback_results
        elif self.scan_type in (ScanType.MEAN_REVERSION_LONG, ScanType.MEAN_REVERSION_SHORT):
            return self.reversion_results
        else:
            return self.symbols
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for caching/storage."""
        return {
            "scan_type": self.scan_type.value,
            "scan_date": self.scan_date.isoformat(),
            "scan_time": self.scan_time.isoformat(),
            "total_scanned": self.total_scanned,
            "matches_found": self.matches_found,
            "symbols": self.symbols,
            "execution_time_ms": self.execution_time_ms,
            "success": self.success,
            "error": self.error,
        }


@dataclass
class ScannerConfig:
    """Configuration for scanner thresholds."""
    # Squeeze thresholds
    squeeze_percentile: float = 10.0     # Bottom X% of BandWidth
    extreme_squeeze_percentile: float = 5.0
    
    # Bulge thresholds
    bulge_percentile: float = 90.0       # Top X% of BandWidth
    
    # Trend thresholds
    uptrend_min_percent_b: float = 0.8   # %b >= this for uptrend
    downtrend_max_percent_b: float = 0.2 # %b <= this for downtrend
    min_trend_days: int = 5              # Minimum days in trend
    
    # Pullback thresholds
    pullback_zone_low: float = 0.4       # %b between these for pullback
    pullback_zone_high: float = 0.6
    
    # Reversion thresholds
    oversold_threshold: float = 0.0      # %b <= this = oversold
    overbought_threshold: float = 1.0    # %b >= this = overbought
    
    # Volume thresholds
    volume_surge_ratio: float = 1.5      # Volume >= avg * this = surge
    
    # Lookback periods
    bandwidth_lookback: int = 126        # 6 months for percentile calc
    trend_lookback: int = 20             # Days to check for trend
