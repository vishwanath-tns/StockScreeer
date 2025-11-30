"""
Core Bollinger Bands Data Models

Defines dataclasses for BB calculations, configurations, and results.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Dict, Any, List
from enum import Enum


@dataclass
class BBConfig:
    """Configuration for Bollinger Bands calculation."""
    period: int = 20           # SMA period (default: 20)
    std_dev: float = 2.0       # Standard deviation multiplier (default: 2.0)
    
    def __str__(self) -> str:
        return f"BB({self.period}, {self.std_dev})"


# Preset configurations
BB_PRESETS = {
    "standard": BBConfig(20, 2.0),   # John Bollinger's default
    "tight": BBConfig(20, 1.5),      # Tighter bands for less volatile stocks
    "wide": BBConfig(20, 2.5),       # Wider bands for volatile stocks
    "short": BBConfig(10, 1.5),      # Short-term trading
    "long": BBConfig(50, 2.5),       # Long-term trends
}


@dataclass
class BollingerBands:
    """
    Bollinger Bands values for a single date.
    
    Attributes:
        upper: Upper band value
        middle: Middle band (SMA) value
        lower: Lower band value
        percent_b: %b indicator - position within bands (0=lower, 1=upper)
        bandwidth: BandWidth indicator - volatility measure
        bandwidth_percentile: Where current BW falls in historical range (0-100)
    """
    date: date
    close: float
    upper: float
    middle: float
    lower: float
    percent_b: float           # %b = (close - lower) / (upper - lower)
    bandwidth: float           # BW = (upper - lower) / middle * 100
    bandwidth_percentile: float = 50.0  # Historical percentile of BW
    
    @property
    def is_above_upper(self) -> bool:
        """Price is above upper band."""
        return self.percent_b > 1.0
    
    @property
    def is_below_lower(self) -> bool:
        """Price is below lower band."""
        return self.percent_b < 0.0
    
    @property
    def is_in_squeeze(self) -> bool:
        """BandWidth in bottom 5% (low volatility)."""
        return self.bandwidth_percentile <= 5.0
    
    @property
    def is_in_bulge(self) -> bool:
        """BandWidth in top 5% (high volatility)."""
        return self.bandwidth_percentile >= 95.0
    
    @property
    def zone(self) -> str:
        """Get the %b zone classification."""
        if self.percent_b > 1.0:
            return "overbought"
        elif self.percent_b >= 0.8:
            return "strong"
        elif self.percent_b >= 0.5:
            return "neutral_high"
        elif self.percent_b >= 0.2:
            return "neutral_low"
        elif self.percent_b >= 0.0:
            return "weak"
        else:
            return "oversold"


@dataclass
class BBResult:
    """
    Result of BB calculation for a single stock.
    
    Contains the full time series of BB values plus summary statistics.
    """
    symbol: str
    config: BBConfig
    calculation_date: date
    
    # Latest values
    current: Optional[BollingerBands] = None
    
    # Time series (most recent first)
    history: List[BollingerBands] = field(default_factory=list)
    
    # Summary statistics
    avg_bandwidth: float = 0.0
    min_bandwidth: float = 0.0
    max_bandwidth: float = 0.0
    days_in_squeeze: int = 0
    days_above_upper: int = 0
    days_below_lower: int = 0
    
    # Calculation status
    success: bool = True
    error: str = ""
    
    @classmethod
    def failure(cls, symbol: str, error: str, config: BBConfig = None) -> "BBResult":
        """Create a failed result."""
        return cls(
            symbol=symbol,
            config=config or BBConfig(),
            calculation_date=date.today(),
            success=False,
            error=error
        )


@dataclass
class BBRating:
    """
    Composite Bollinger Bands rating for a stock.
    
    Components:
    - Squeeze Score (25%): Position in volatility cycle
    - Trend Score (35%): Position within bands indicating trend
    - Momentum Score (20%): Rate of change in %b
    - Pattern Score (20%): Recognition of key patterns
    """
    symbol: str
    rating_date: date
    
    # Component scores (0-100)
    squeeze_score: float = 50.0
    trend_score: float = 50.0
    momentum_score: float = 50.0
    pattern_score: float = 50.0
    
    # Composite score (0-100)
    composite_score: float = 50.0
    
    # Ranking among all stocks
    rank: int = 0
    percentile: float = 50.0
    total_stocks: int = 0
    
    # Current state
    percent_b: float = 0.5
    bandwidth: float = 0.0
    bandwidth_percentile: float = 50.0
    is_squeeze: bool = False
    is_bulge: bool = False
    trend_direction: str = "neutral"  # "uptrend", "downtrend", "neutral"
    
    # Metadata
    success: bool = True
    error: str = ""
    
    @property
    def letter_grade(self) -> str:
        """Get letter grade from composite score."""
        return get_letter_grade(self.composite_score)


def get_letter_grade(score: float) -> str:
    """Convert numeric score (0-100) to letter grade."""
    if score >= 90:
        return "A+"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B+"
    elif score >= 60:
        return "B"
    elif score >= 50:
        return "C+"
    elif score >= 40:
        return "C"
    elif score >= 30:
        return "D"
    else:
        return "F"


class BBZone(Enum):
    """Enumeration of %b zones."""
    OVERBOUGHT = "overbought"      # %b > 1.0
    STRONG = "strong"              # 0.8 <= %b <= 1.0
    NEUTRAL_HIGH = "neutral_high"  # 0.5 <= %b < 0.8
    NEUTRAL_LOW = "neutral_low"    # 0.2 <= %b < 0.5
    WEAK = "weak"                  # 0.0 <= %b < 0.2
    OVERSOLD = "oversold"          # %b < 0.0


class TrendDirection(Enum):
    """Trend direction based on BB position."""
    STRONG_UPTREND = "strong_uptrend"      # Walking upper band
    UPTREND = "uptrend"                    # Consistently > 0.5
    NEUTRAL = "neutral"                    # Oscillating around middle
    DOWNTREND = "downtrend"                # Consistently < 0.5
    STRONG_DOWNTREND = "strong_downtrend"  # Walking lower band


class VolatilityState(Enum):
    """Volatility state based on BandWidth."""
    SQUEEZE = "squeeze"          # Very low volatility (bottom 5%)
    LOW = "low"                  # Low volatility (5-25%)
    NORMAL = "normal"            # Normal volatility (25-75%)
    HIGH = "high"                # High volatility (75-95%)
    BULGE = "bulge"              # Very high volatility (top 5%)
