"""
Accumulation/Distribution Detector
===================================

Detect accumulation and distribution patterns in stock data to identify
potential breakout candidates before significant price moves.

Accumulation Patterns (Bullish):
- Rising OBV with sideways price (institutions buying quietly)
- Positive CMF (> 0) with consolidating price
- Volume dry-up followed by price holding support
- Higher lows on declining volume

Distribution Patterns (Bearish):
- Falling OBV with sideways/rising price (institutions selling)
- Negative CMF (< 0) with price near highs
- Volume surge on down days
- Lower highs on increasing volume
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum
import logging

from ..core.volume_indicators import VolumeIndicators

logger = logging.getLogger(__name__)


class PhaseType(Enum):
    """Market phase classification."""
    ACCUMULATION = "accumulation"
    DISTRIBUTION = "distribution"
    MARKUP = "markup"
    MARKDOWN = "markdown"
    NEUTRAL = "neutral"


class SignalStrength(Enum):
    """Signal strength classification."""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NONE = "none"


@dataclass
class AccumulationSignal:
    """
    Represents an accumulation or distribution signal.
    
    Attributes:
        symbol: Stock symbol
        phase: Current market phase
        strength: Signal strength (strong/moderate/weak)
        score: Composite score (0-100)
        obv_score: OBV component score
        ad_score: A/D Line component score
        cmf_score: CMF component score
        volume_score: Volume pattern score
        price_action_score: Price action score
        details: Dictionary with detailed analysis
    """
    symbol: str
    phase: PhaseType
    strength: SignalStrength
    score: float
    obv_score: float
    ad_score: float
    cmf_score: float
    volume_score: float
    price_action_score: float
    details: dict = field(default_factory=dict)
    
    def __str__(self):
        phase_emoji = "🟢" if self.phase == PhaseType.ACCUMULATION else "🔴" if self.phase == PhaseType.DISTRIBUTION else "⚪"
        return f"{phase_emoji} {self.symbol}: {self.phase.value.title()} ({self.strength.value}) - Score: {self.score:.1f}"


class AccumulationDetector:
    """
    Detect accumulation and distribution patterns.
    
    Uses multiple volume indicators and price patterns to identify
    institutional buying (accumulation) or selling (distribution)
    before significant price moves.
    """
    
    def __init__(self, 
                 lookback_period: int = 60,
                 short_period: int = 10,
                 cmf_period: int = 20):
        """
        Initialize the detector.
        
        Args:
            lookback_period: Days to analyze for patterns (default 60)
            short_period: Short-term lookback for recent signals (default 10)
            cmf_period: Period for CMF calculation (default 20)
        """
        self.lookback_period = lookback_period
        self.short_period = short_period
        self.cmf_period = cmf_period
        self.volume_indicators = VolumeIndicators()
    
    def analyze(self, df: pd.DataFrame, symbol: str = "UNKNOWN") -> AccumulationSignal:
        """
        Analyze a stock for accumulation/distribution signals.
        
        Args:
            df: DataFrame with OHLCV data
            symbol: Stock symbol for reporting
            
        Returns:
            AccumulationSignal with analysis results
        """
        # Ensure we have enough data
        if len(df) < self.lookback_period:
            return self._create_neutral_signal(symbol, "Insufficient data")
        
        # Calculate all volume indicators
        data = self.volume_indicators.calculate_all(df, cmf_period=self.cmf_period)
        
        # Detect volume patterns
        data = self.volume_indicators.detect_volume_dryup(data)
        data = self.volume_indicators.detect_volume_surge(data)
        
        # Use most recent data
        data = data.tail(self.lookback_period).copy()
        
        # Calculate component scores
        obv_score, obv_details = self._analyze_obv(data)
        ad_score, ad_details = self._analyze_ad_line(data)
        cmf_score, cmf_details = self._analyze_cmf(data)
        volume_score, volume_details = self._analyze_volume_patterns(data)
        price_score, price_details = self._analyze_price_action(data)
        
        # Calculate composite score
        # Weight: OBV (25%), A/D (25%), CMF (20%), Volume (15%), Price (15%)
        composite_score = (
            obv_score * 0.25 +
            ad_score * 0.25 +
            cmf_score * 0.20 +
            volume_score * 0.15 +
            price_score * 0.15
        )
        
        # Determine phase
        phase = self._determine_phase(composite_score, obv_score, ad_score, cmf_score)
        
        # Determine strength
        strength = self._determine_strength(composite_score)
        
        # Compile details
        details = {
            'obv': obv_details,
            'ad_line': ad_details,
            'cmf': cmf_details,
            'volume': volume_details,
            'price_action': price_details,
            'latest_close': data['close'].iloc[-1],
            'latest_volume': data['volume'].iloc[-1],
            'avg_volume_20d': data['volume'].tail(20).mean(),
        }
        
        return AccumulationSignal(
            symbol=symbol,
            phase=phase,
            strength=strength,
            score=composite_score,
            obv_score=obv_score,
            ad_score=ad_score,
            cmf_score=cmf_score,
            volume_score=volume_score,
            price_action_score=price_score,
            details=details
        )
    
    def _analyze_obv(self, df: pd.DataFrame) -> Tuple[float, dict]:
        """
        Analyze OBV for accumulation/distribution.
        
        Bullish (Accumulation):
        - OBV making higher highs while price consolidates
        - OBV above its moving average
        - OBV trend positive
        
        Bearish (Distribution):
        - OBV making lower lows while price holds
        - OBV below its moving average
        - OBV trend negative
        """
        score = 50.0  # Neutral starting point
        
        recent = df.tail(self.short_period)
        
        # Get OBV values
        obv_current = df['obv'].iloc[-1]
        obv_20d_ago = df['obv'].iloc[-20] if len(df) >= 20 else df['obv'].iloc[0]
        obv_change = (obv_current - obv_20d_ago) / abs(obv_20d_ago) * 100 if obv_20d_ago != 0 else 0
        
        # OBV trend
        obv_trend = df['obv_trend'].iloc[-1]
        obv_trending_up = obv_trend > 0
        
        # Recent OBV direction (last 10 days)
        recent_obv_slope = self._calculate_slope(recent['obv'])
        
        # Price change for divergence detection
        price_change_20d = (df['close'].iloc[-1] - df['close'].iloc[-20]) / df['close'].iloc[-20] * 100 if len(df) >= 20 else 0
        
        details = {
            'current': obv_current,
            'change_20d_pct': obv_change,
            'trending_up': obv_trending_up,
            'recent_slope': recent_obv_slope,
            'divergence': None
        }
        
        # Score calculation
        
        # 1. OBV above/below SMA (±15 points)
        if obv_trending_up:
            score += 15
        else:
            score -= 15
        
        # 2. OBV 20-day change (±20 points)
        if obv_change > 10:
            score += 20
        elif obv_change > 5:
            score += 10
        elif obv_change < -10:
            score -= 20
        elif obv_change < -5:
            score -= 10
        
        # 3. Bullish divergence: OBV up, price flat/down (accumulation)
        #    Bearish divergence: OBV down, price flat/up (distribution)
        if obv_change > 5 and price_change_20d < 2:
            # Bullish divergence - strong accumulation signal
            score += 15
            details['divergence'] = 'bullish (accumulation)'
        elif obv_change < -5 and price_change_20d > -2:
            # Bearish divergence - distribution signal
            score -= 15
            details['divergence'] = 'bearish (distribution)'
        
        # Clamp score
        score = max(0, min(100, score))
        
        return score, details
    
    def _analyze_ad_line(self, df: pd.DataFrame) -> Tuple[float, dict]:
        """
        Analyze A/D Line for accumulation/distribution.
        """
        score = 50.0
        
        recent = df.tail(self.short_period)
        
        ad_current = df['ad_line'].iloc[-1]
        ad_20d_ago = df['ad_line'].iloc[-20] if len(df) >= 20 else df['ad_line'].iloc[0]
        ad_change = ad_current - ad_20d_ago
        
        ad_trend = df['ad_trend'].iloc[-1]
        ad_trending_up = ad_trend > 0
        
        # Recent MFM average (close location within range)
        recent_mfm_avg = recent['mfm'].mean()
        
        details = {
            'current': ad_current,
            'change_20d': ad_change,
            'trending_up': ad_trending_up,
            'recent_mfm_avg': recent_mfm_avg
        }
        
        # Score calculation
        
        # 1. A/D trend (±15 points)
        if ad_trending_up:
            score += 15
        else:
            score -= 15
        
        # 2. A/D change direction (±15 points)
        if ad_change > 0:
            score += 15
        else:
            score -= 15
        
        # 3. Money Flow Multiplier (shows close position in range)
        # Positive MFM = closes near high (buying pressure)
        # Negative MFM = closes near low (selling pressure)
        if recent_mfm_avg > 0.3:
            score += 15
        elif recent_mfm_avg > 0:
            score += 5
        elif recent_mfm_avg < -0.3:
            score -= 15
        elif recent_mfm_avg < 0:
            score -= 5
        
        score = max(0, min(100, score))
        
        return score, details
    
    def _analyze_cmf(self, df: pd.DataFrame) -> Tuple[float, dict]:
        """
        Analyze Chaikin Money Flow for accumulation/distribution.
        
        CMF > 0: Buying pressure (accumulation)
        CMF > 0.25: Strong buying pressure
        CMF < 0: Selling pressure (distribution)
        CMF < -0.25: Strong selling pressure
        """
        score = 50.0
        
        recent = df.tail(self.short_period)
        
        cmf_current = df['cmf'].iloc[-1]
        cmf_avg_recent = recent['cmf'].mean()
        
        # CMF trend (improving or deteriorating)
        cmf_5d_avg = df['cmf'].tail(5).mean()
        cmf_20d_avg = df['cmf'].tail(20).mean()
        cmf_improving = cmf_5d_avg > cmf_20d_avg
        
        details = {
            'current': cmf_current,
            'avg_10d': cmf_avg_recent,
            'avg_5d': cmf_5d_avg,
            'avg_20d': cmf_20d_avg,
            'improving': cmf_improving
        }
        
        # Score calculation
        
        # 1. Current CMF value (±25 points)
        if cmf_current > 0.25:
            score += 25
        elif cmf_current > 0.1:
            score += 15
        elif cmf_current > 0:
            score += 5
        elif cmf_current < -0.25:
            score -= 25
        elif cmf_current < -0.1:
            score -= 15
        elif cmf_current < 0:
            score -= 5
        
        # 2. CMF trend (±10 points)
        if cmf_improving:
            score += 10
        else:
            score -= 10
        
        # 3. Consistency - recent average (±10 points)
        if cmf_avg_recent > 0.1:
            score += 10
        elif cmf_avg_recent < -0.1:
            score -= 10
        
        score = max(0, min(100, score))
        
        return score, details
    
    def _analyze_volume_patterns(self, df: pd.DataFrame) -> Tuple[float, dict]:
        """
        Analyze volume patterns.
        
        Bullish patterns:
        - Volume dry-up followed by accumulation (quiet before storm)
        - Volume surge on up days
        - Declining volume on pullbacks
        
        Bearish patterns:
        - Volume surge on down days
        - Increasing volume on rallies that fail
        """
        score = 50.0
        
        recent = df.tail(self.short_period)
        
        # Volume ratio
        avg_volume_ratio = recent['volume_ratio'].mean()
        
        # Volume dry-up detection
        has_volume_dryup = recent['volume_dryup'].any()
        
        # Volume surge detection
        has_volume_surge = recent['volume_surge'].any()
        
        # Volume on up days vs down days
        up_days = recent[recent['close'] > recent['close'].shift(1)]
        down_days = recent[recent['close'] < recent['close'].shift(1)]
        
        avg_up_volume = up_days['volume'].mean() if len(up_days) > 0 else 0
        avg_down_volume = down_days['volume'].mean() if len(down_days) > 0 else 0
        
        # Volume trend
        volume_trend = df['volume_trend'].iloc[-1] if 'volume_trend' in df.columns else 0
        
        details = {
            'avg_volume_ratio': avg_volume_ratio,
            'has_dryup': has_volume_dryup,
            'has_surge': has_volume_surge,
            'avg_up_day_volume': avg_up_volume,
            'avg_down_day_volume': avg_down_volume,
            'volume_trend': volume_trend
        }
        
        # Score calculation
        
        # 1. Volume on up vs down days (±15 points)
        if avg_up_volume > 0 and avg_down_volume > 0:
            up_down_ratio = avg_up_volume / avg_down_volume
            if up_down_ratio > 1.3:
                score += 15  # More volume on up days = accumulation
            elif up_down_ratio < 0.77:
                score -= 15  # More volume on down days = distribution
        
        # 2. Volume dry-up (potential breakout setup) (+10 points)
        if has_volume_dryup:
            score += 10
        
        # 3. Recent volume surge
        if has_volume_surge:
            # Check if surge was on up or down day
            surge_days = recent[recent['volume_surge']]
            if len(surge_days) > 0:
                last_surge = surge_days.iloc[-1]
                if last_surge['close'] > last_surge.get('open', last_surge['close']):
                    score += 10  # Surge on up day = bullish
                else:
                    score -= 10  # Surge on down day = bearish
        
        score = max(0, min(100, score))
        
        return score, details
    
    def _analyze_price_action(self, df: pd.DataFrame) -> Tuple[float, dict]:
        """
        Analyze price action patterns.
        
        Bullish (Accumulation):
        - Price forming higher lows
        - Tight consolidation near highs
        - Price above moving averages
        
        Bearish (Distribution):
        - Price forming lower highs
        - Consolidation near lows
        - Price below moving averages
        """
        score = 50.0
        
        recent = df.tail(self.short_period)
        
        # Price position
        current_close = df['close'].iloc[-1]
        high_20d = df['high'].tail(20).max()
        low_20d = df['low'].tail(20).min()
        range_20d = high_20d - low_20d
        
        # Position within range (0-1, where 1 = at high)
        price_position = (current_close - low_20d) / range_20d if range_20d > 0 else 0.5
        
        # Price change
        price_change_20d = (current_close - df['close'].iloc[-20]) / df['close'].iloc[-20] * 100 if len(df) >= 20 else 0
        
        # Volatility (consolidation detection)
        recent_volatility = (recent['high'] - recent['low']).mean() / current_close * 100
        
        # Higher lows / lower highs detection
        lows = recent['low'].values
        highs = recent['high'].values
        
        higher_lows = all(lows[i] >= lows[i-1] * 0.99 for i in range(1, min(5, len(lows))))
        lower_highs = all(highs[i] <= highs[i-1] * 1.01 for i in range(1, min(5, len(highs))))
        
        details = {
            'current_close': current_close,
            'position_in_range': price_position,
            'change_20d_pct': price_change_20d,
            'volatility_pct': recent_volatility,
            'higher_lows': higher_lows,
            'lower_highs': lower_highs
        }
        
        # Score calculation
        
        # 1. Price position (±15 points)
        if price_position > 0.8:
            score += 10  # Near highs
        elif price_position > 0.5:
            score += 5
        elif price_position < 0.2:
            score -= 10  # Near lows
        
        # 2. Higher lows / lower highs (±15 points)
        if higher_lows:
            score += 15  # Accumulation pattern
        if lower_highs:
            score -= 15  # Distribution pattern
        
        # 3. Tight consolidation (low volatility) is often bullish when combined with accumulation
        if recent_volatility < 2:
            score += 5  # Tight consolidation
        
        score = max(0, min(100, score))
        
        return score, details
    
    def _determine_phase(self, composite_score: float, 
                         obv_score: float, 
                         ad_score: float,
                         cmf_score: float) -> PhaseType:
        """
        Determine market phase based on scores.
        """
        # Strong accumulation
        if composite_score >= 65 and cmf_score >= 60:
            return PhaseType.ACCUMULATION
        
        # Strong distribution
        if composite_score <= 35 and cmf_score <= 40:
            return PhaseType.DISTRIBUTION
        
        # Moderate accumulation
        if composite_score >= 55 and (obv_score >= 55 or ad_score >= 55):
            return PhaseType.ACCUMULATION
        
        # Moderate distribution
        if composite_score <= 45 and (obv_score <= 45 or ad_score <= 45):
            return PhaseType.DISTRIBUTION
        
        return PhaseType.NEUTRAL
    
    def _determine_strength(self, score: float) -> SignalStrength:
        """
        Determine signal strength from score.
        """
        if score >= 75 or score <= 25:
            return SignalStrength.STRONG
        elif score >= 60 or score <= 40:
            return SignalStrength.MODERATE
        elif score >= 55 or score <= 45:
            return SignalStrength.WEAK
        else:
            return SignalStrength.NONE
    
    def _calculate_slope(self, series: pd.Series) -> float:
        """
        Calculate the slope of a series using linear regression.
        """
        if len(series) < 2:
            return 0.0
        
        x = np.arange(len(series))
        y = series.values
        
        # Handle NaN
        mask = ~np.isnan(y)
        if mask.sum() < 2:
            return 0.0
        
        x, y = x[mask], y[mask]
        slope = np.polyfit(x, y, 1)[0]
        
        return slope
    
    def _create_neutral_signal(self, symbol: str, reason: str) -> AccumulationSignal:
        """
        Create a neutral signal when analysis cannot be performed.
        """
        return AccumulationSignal(
            symbol=symbol,
            phase=PhaseType.NEUTRAL,
            strength=SignalStrength.NONE,
            score=50.0,
            obv_score=50.0,
            ad_score=50.0,
            cmf_score=50.0,
            volume_score=50.0,
            price_action_score=50.0,
            details={'reason': reason}
        )
    
    def get_top_accumulation(self, signals: List[AccumulationSignal], 
                             top_n: int = 20) -> List[AccumulationSignal]:
        """
        Get top accumulation candidates from a list of signals.
        
        Args:
            signals: List of AccumulationSignal objects
            top_n: Number of top candidates to return
            
        Returns:
            List of top accumulation signals sorted by score
        """
        accumulation_signals = [
            s for s in signals 
            if s.phase == PhaseType.ACCUMULATION and s.strength != SignalStrength.NONE
        ]
        
        return sorted(accumulation_signals, key=lambda x: x.score, reverse=True)[:top_n]
    
    def get_top_distribution(self, signals: List[AccumulationSignal],
                             top_n: int = 20) -> List[AccumulationSignal]:
        """
        Get top distribution candidates from a list of signals.
        
        Args:
            signals: List of AccumulationSignal objects
            top_n: Number of top candidates to return
            
        Returns:
            List of top distribution signals sorted by score (lowest first)
        """
        distribution_signals = [
            s for s in signals
            if s.phase == PhaseType.DISTRIBUTION and s.strength != SignalStrength.NONE
        ]
        
        return sorted(distribution_signals, key=lambda x: x.score)[:top_n]


if __name__ == "__main__":
    # Test with sample data
    import yfinance as yf
    
    print("Testing Accumulation Detector...")
    
    # Download sample data
    ticker = yf.Ticker("RELIANCE.NS")
    df = ticker.history(period="6mo")
    
    # Rename columns to lowercase
    df.columns = df.columns.str.lower()
    df = df.reset_index()
    df = df.rename(columns={'Date': 'date'})
    
    # Analyze
    detector = AccumulationDetector()
    signal = detector.analyze(df, "RELIANCE")
    
    print(f"\nResult: {signal}")
    print(f"\nComponent Scores:")
    print(f"  OBV Score: {signal.obv_score:.1f}")
    print(f"  A/D Score: {signal.ad_score:.1f}")
    print(f"  CMF Score: {signal.cmf_score:.1f}")
    print(f"  Volume Score: {signal.volume_score:.1f}")
    print(f"  Price Action Score: {signal.price_action_score:.1f}")
    print(f"\nDetails:")
    for key, value in signal.details.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        else:
            print(f"  {key}: {value}")
