"""
Signal Models for Bollinger Bands System

Defines signal types, patterns, and confidence scoring.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, List
from enum import Enum


class SignalType(Enum):
    """Type of trading signal."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class PatternType(Enum):
    """
    Bollinger Bands pattern types.
    
    Based on John Bollinger's methodology.
    """
    # Reversal patterns
    W_BOTTOM = "W_BOTTOM"           # Double bottom with %b divergence
    M_TOP = "M_TOP"                 # Double top with %b divergence
    
    # Squeeze patterns
    SQUEEZE_BREAKOUT_UP = "SQUEEZE_BREAKOUT_UP"     # Squeeze release upward
    SQUEEZE_BREAKOUT_DOWN = "SQUEEZE_BREAKOUT_DOWN" # Squeeze release downward
    HEADFAKE_UP = "HEADFAKE_UP"     # False breakout up, reverse down
    HEADFAKE_DOWN = "HEADFAKE_DOWN" # False breakout down, reverse up
    
    # Trend patterns
    WALKING_UPPER = "WALKING_UPPER"   # Riding upper band in uptrend
    WALKING_LOWER = "WALKING_LOWER"   # Riding lower band in downtrend
    
    # Mean reversion patterns
    UPPER_BAND_TOUCH = "UPPER_BAND_TOUCH"   # Price touches/exceeds upper
    LOWER_BAND_TOUCH = "LOWER_BAND_TOUCH"   # Price touches/exceeds lower
    MIDDLE_BAND_PULLBACK = "MIDDLE_BAND_PULLBACK"  # Pullback to middle band
    
    # Volatility patterns
    SQUEEZE_FORMING = "SQUEEZE_FORMING"     # Entering squeeze
    BULGE_FORMING = "BULGE_FORMING"         # Volatility expanding
    
    # No specific pattern
    NONE = "NONE"


@dataclass
class SignalConfidence:
    """
    Breakdown of signal confidence scoring.
    
    Total confidence = base + volume + pattern + trend + confirmation
    Range: 0-100
    """
    base_score: float = 50.0          # Base confidence
    volume_bonus: float = 0.0         # +20 max for volume confirmation
    pattern_bonus: float = 0.0        # +15 max for pattern clarity
    trend_bonus: float = 0.0          # +15 max for trend alignment
    confirmation_bonus: float = 0.0   # +10 max for indicator confirmation
    
    @property
    def total(self) -> float:
        """Total confidence score (capped at 100)."""
        return min(100.0, max(0.0,
            self.base_score + 
            self.volume_bonus + 
            self.pattern_bonus + 
            self.trend_bonus + 
            self.confirmation_bonus
        ))
    
    def __str__(self) -> str:
        return f"{self.total:.0f}%"


@dataclass
class BBSignal:
    """
    A trading signal generated from Bollinger Bands analysis.
    
    Attributes:
        symbol: Stock symbol
        signal_type: BUY, SELL, or HOLD
        pattern: The pattern that triggered the signal
        confidence: Confidence scoring breakdown
        price_at_signal: Price when signal was generated
        percent_b: %b value at signal time
        bandwidth: BandWidth at signal time
    """
    symbol: str
    signal_date: date
    signal_type: SignalType
    pattern: PatternType
    confidence: SignalConfidence
    
    # Price data at signal
    price_at_signal: float
    percent_b: float
    bandwidth: float
    
    # Volume confirmation
    volume_confirmed: bool = False
    volume_ratio: float = 1.0  # Current volume / average volume
    
    # Additional context
    description: str = ""
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def confidence_score(self) -> float:
        """Get total confidence score."""
        return self.confidence.total
    
    @property
    def is_high_confidence(self) -> bool:
        """Signal has high confidence (>= 70)."""
        return self.confidence_score >= 70
    
    @property
    def is_actionable(self) -> bool:
        """Signal is actionable (>= 60 confidence, volume confirmed)."""
        return self.confidence_score >= 60 and self.volume_confirmed
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "symbol": self.symbol,
            "signal_date": self.signal_date.isoformat(),
            "signal_type": self.signal_type.value,
            "pattern": self.pattern.value,
            "confidence": self.confidence_score,
            "price_at_signal": self.price_at_signal,
            "percent_b": self.percent_b,
            "bandwidth": self.bandwidth,
            "volume_confirmed": self.volume_confirmed,
            "volume_ratio": self.volume_ratio,
            "description": self.description,
            "target_price": self.target_price,
            "stop_loss": self.stop_loss,
        }


@dataclass
class SignalSummary:
    """Summary of signals for a stock or period."""
    total_signals: int = 0
    buy_signals: int = 0
    sell_signals: int = 0
    high_confidence_signals: int = 0
    volume_confirmed_signals: int = 0
    
    # Performance (if tracked)
    signals_with_outcome: int = 0
    winning_signals: int = 0
    avg_return: float = 0.0
    
    @property
    def win_rate(self) -> float:
        """Win rate percentage."""
        if self.signals_with_outcome == 0:
            return 0.0
        return (self.winning_signals / self.signals_with_outcome) * 100


@dataclass 
class SignalAlert:
    """Alert configuration for signal notifications."""
    enabled: bool = True
    min_confidence: float = 70.0
    require_volume: bool = True
    signal_types: List[SignalType] = field(default_factory=lambda: [SignalType.BUY, SignalType.SELL])
    patterns: List[PatternType] = field(default_factory=list)  # Empty = all patterns
    symbols: List[str] = field(default_factory=list)  # Empty = all symbols
