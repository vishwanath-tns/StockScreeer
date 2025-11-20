"""
VCP (Volatility Contracting Patterns) Detection Engine
======================================================

Implements Mark Minervini's Volatility Contracting Pattern detection based on:
- "Think & Trade Like a Champion" by Mark Minervini
- "Trade Like a Stock Market Wizard" by Mark Minervini

Key VCP Criteria:
1. Volatility Contraction: Each successive pullback shows lower volatility
2. Volume Dry-Up: Volume decreases during contractions
3. Price Base Formation: At least 3-4 contractions forming tighter ranges
4. Stage Analysis: Stock should be in Stage 2 uptrend
5. Relative Strength: Outperforming market during corrections

Author: GitHub Copilot
Date: November 2025
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from datetime import date, timedelta
import logging

from .technical_indicators import TechnicalIndicators


@dataclass
class VCPContraction:
    """Represents a single contraction within a VCP pattern"""
    start_date: date
    end_date: date
    duration_days: int
    high_price: float
    low_price: float
    range_percent: float
    volume_avg: float
    volume_decline: float  # % decline from previous contraction
    volatility_ratio: float  # ATR ratio vs previous contraction
    is_valid: bool
    
    
@dataclass
class VCPPattern:
    """Represents a complete VCP pattern with all contractions"""
    symbol: str
    pattern_start: date
    pattern_end: date
    base_duration: int
    contractions: List[VCPContraction]
    total_decline: float  # % from pattern high to low
    volatility_compression: float  # ratio of first to last contraction
    volume_compression: float  # volume decline ratio
    current_stage: int  # 1-4 Weinstein stage
    relative_strength: float  # vs market performance
    quality_score: float  # 0-100 pattern quality
    is_setup_complete: bool
    breakout_level: float
    stop_loss_level: float


class VCPDetector:
    """
    Main VCP Detection Engine
    
    Identifies Volatility Contracting Patterns following Mark Minervini's methodology.
    Designed for high accuracy with low false positives.
    """
    
    def __init__(self):
        self.indicators = TechnicalIndicators()
        self.logger = logging.getLogger(__name__)
        
        # VCP Detection Parameters (Minervini's criteria)
        self.min_contractions = 3
        self.max_contractions = 7
        self.min_base_weeks = 4
        self.max_base_weeks = 52
        self.min_volatility_compression = 1.2  # 20% volatility reduction
        self.min_volume_decline = 0.15  # 15% volume decline
        self.max_base_decline = 0.50  # Max 50% correction
        self.min_rs_rating = 70  # Relative strength requirement
        
    def detect_vcp_patterns(
        self, 
        data: pd.DataFrame, 
        symbol: str,
        lookback_days: int = 365
    ) -> List[VCPPattern]:
        """
        Main VCP detection method
        
        Args:
            data: OHLCV data with date index
            symbol: Stock symbol
            lookback_days: How far back to search for patterns
            
        Returns:
            List of detected VCP patterns, sorted by quality score
        """
        self.logger.info(f"Starting VCP detection for {symbol}")
        
        # Calculate all technical indicators
        data_with_indicators = self._calculate_indicators(data)
        
        # Identify potential base formations
        bases = self._identify_base_formations(data_with_indicators)
        
        vcp_patterns = []
        for base in bases:
            # Analyze contractions within each base
            contractions = self._analyze_contractions(data_with_indicators, base)
            
            if self._is_valid_vcp(contractions):
                pattern = self._create_vcp_pattern(
                    symbol, data_with_indicators, base, contractions
                )
                if pattern.quality_score >= 60:  # Minimum quality threshold
                    vcp_patterns.append(pattern)
        
        # Sort by quality score (best first)
        vcp_patterns.sort(key=lambda x: x.quality_score, reverse=True)
        
        self.logger.info(f"Detected {len(vcp_patterns)} VCP patterns for {symbol}")
        return vcp_patterns
    
    def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate all required technical indicators"""
        result = data.copy()
        
        # Calculate ATR for volatility measurement
        result = self.indicators.calculate_atr(result, period=14)
        result = self.indicators.calculate_atr(result, period=20)
        
        # Calculate Bollinger Bands for squeeze detection
        result = self.indicators.calculate_bollinger_bands(result, period=20)
        
        # Calculate Volume indicators
        result = self.indicators.calculate_volume_ma(result, period=20)
        result = self.indicators.calculate_volume_ma(result, period=50)
        
        # Calculate price range compression
        result = self.indicators.calculate_price_range_compression(result, period=20)
        
        # Detect squeezes
        result = self.indicators.detect_bollinger_squeeze(result)
        
        # Add moving averages for stage analysis
        result['sma_50'] = result['close'].rolling(50).mean()
        result['sma_150'] = result['close'].rolling(150).mean()
        result['sma_200'] = result['close'].rolling(200).mean()
        
        return result
    
    def _identify_base_formations(self, data: pd.DataFrame) -> List[Dict]:
        """
        Identify potential base formations (consolidation periods)
        
        A base is identified as:
        1. Price trading within a range for minimum period
        2. No new highs during the base period
        3. At least 4 weeks of consolidation
        """
        bases = []
        lookback_period = min(252, len(data))  # 1 year or available data
        
        for i in range(lookback_period, len(data)):
            # Look for potential base start
            current_high = data['high'].iloc[i-lookback_period:i].max()
            current_close = data['close'].iloc[i]
            
            # Check if we're potentially in a base (not making new highs)
            if current_close < current_high * 0.98:  # 2% below high
                base_start_idx = i - lookback_period
                base_end_idx = i
                
                # Verify base characteristics
                base_data = data.iloc[base_start_idx:base_end_idx+1]
                base_duration = len(base_data)
                
                if base_duration >= 20:  # Minimum 4 weeks
                    base_high = base_data['high'].max()
                    base_low = base_data['low'].min()
                    base_range = (base_high - base_low) / base_low * 100
                    
                    # Base should be reasonable range (not too tight or too wide)
                    if 5 <= base_range <= 50:
                        bases.append({
                            'start_idx': base_start_idx,
                            'end_idx': base_end_idx,
                            'start_date': data.iloc[base_start_idx]['date'],
                            'end_date': data.iloc[base_end_idx]['date'],
                            'duration': base_duration,
                            'high': base_high,
                            'low': base_low,
                            'range_percent': base_range
                        })
        
        return bases
    
    def _analyze_contractions(
        self, 
        data: pd.DataFrame, 
        base: Dict
    ) -> List[VCPContraction]:
        """
        Analyze individual contractions within a base formation
        
        Each contraction should show:
        1. Decreasing volatility vs previous contraction
        2. Decreasing volume vs previous contraction  
        3. Tighter price range vs previous contraction
        """
        base_data = data.iloc[base['start_idx']:base['end_idx']+1].copy()
        
        contractions = []
        
        # Find swing highs and lows to identify contractions
        swing_highs = self._find_swing_points(base_data, 'high', window=5)
        swing_lows = self._find_swing_points(base_data, 'low', window=5, find_highs=False)
        
        # Pair swing highs and lows to form contractions
        for i in range(len(swing_highs) - 1):
            # Find the low between this high and the next high
            start_idx = swing_highs[i]['idx']
            end_idx = swing_highs[i+1]['idx']
            
            # Find lowest point between the two highs
            contraction_data = base_data.iloc[start_idx:end_idx+1]
            low_idx = contraction_data['low'].idxmin()
            
            if low_idx in base_data.index:
                low_data_idx = base_data.index.get_loc(low_idx)
                
                contraction = self._create_contraction(
                    base_data,
                    start_idx,
                    low_data_idx,
                    len(contractions)
                )
                
                if contraction.is_valid:
                    contractions.append(contraction)
        
        return contractions
    
    def _find_swing_points(
        self, 
        data: pd.DataFrame, 
        price_col: str, 
        window: int = 5, 
        find_highs: bool = True
    ) -> List[Dict]:
        """Find swing highs or lows in price data"""
        swing_points = []
        
        for i in range(window, len(data) - window):
            current_price = data[price_col].iloc[i]
            
            if find_highs:
                # Check if this is a swing high
                left_max = data[price_col].iloc[i-window:i].max()
                right_max = data[price_col].iloc[i+1:i+window+1].max()
                
                if current_price > left_max and current_price > right_max:
                    swing_points.append({
                        'idx': i,
                        'date': data.iloc[i]['date'],
                        'price': current_price
                    })
            else:
                # Check if this is a swing low
                left_min = data[price_col].iloc[i-window:i].min()
                right_min = data[price_col].iloc[i+1:i+window+1].min()
                
                if current_price < left_min and current_price < right_min:
                    swing_points.append({
                        'idx': i,
                        'date': data.iloc[i]['date'],
                        'price': current_price
                    })
        
        return swing_points
    
    def _create_contraction(
        self, 
        data: pd.DataFrame, 
        start_idx: int, 
        end_idx: int, 
        contraction_num: int
    ) -> VCPContraction:
        """Create a VCPContraction object from price data"""
        contraction_data = data.iloc[start_idx:end_idx+1]
        
        # Basic metrics
        high_price = contraction_data['high'].max()
        low_price = contraction_data['low'].min()
        range_percent = (high_price - low_price) / low_price * 100
        duration_days = len(contraction_data)
        
        # Volume metrics
        volume_avg = contraction_data['volume'].mean()
        
        # Volume decline calculation (vs previous contraction)
        volume_decline = 0.0
        if contraction_num > 0:
            # This would need to be calculated against previous contraction
            # For now, use a placeholder calculation
            prev_period_volume = data['vol_ma_20'].iloc[start_idx]
            if prev_period_volume > 0:
                volume_decline = (prev_period_volume - volume_avg) / prev_period_volume
        
        # Volatility calculation
        volatility_ratio = 1.0
        if 'atr_20' in contraction_data.columns:
            current_volatility = contraction_data['atr_20'].mean()
            # Compare to previous period volatility
            prev_volatility = data['atr_20'].iloc[max(0, start_idx-20):start_idx].mean()
            if prev_volatility > 0:
                volatility_ratio = current_volatility / prev_volatility
        
        # Validation criteria
        is_valid = (
            duration_days >= 3 and  # Minimum 3 days
            range_percent >= 2 and  # Minimum 2% range
            range_percent <= 25  # Maximum 25% range
        )
        
        return VCPContraction(
            start_date=data.iloc[start_idx]['date'].date(),
            end_date=data.iloc[end_idx]['date'].date(),
            duration_days=duration_days,
            high_price=high_price,
            low_price=low_price,
            range_percent=range_percent,
            volume_avg=volume_avg,
            volume_decline=volume_decline,
            volatility_ratio=volatility_ratio,
            is_valid=is_valid
        )
    
    def _is_valid_vcp(self, contractions: List[VCPContraction]) -> bool:
        """
        Validate if contractions form a valid VCP pattern
        
        Criteria:
        1. At least 3 contractions
        2. Each contraction shows decreasing volatility
        3. Volume generally declining
        4. Range compression over time
        """
        if len(contractions) < self.min_contractions:
            return False
        
        # Check volatility compression
        volatility_trend = []
        for i in range(1, len(contractions)):
            volatility_trend.append(contractions[i].volatility_ratio)
        
        # At least 50% of contractions should show decreasing volatility
        decreasing_vol = sum(1 for v in volatility_trend if v < 1.0)
        vol_compression_ratio = decreasing_vol / len(volatility_trend)
        
        if vol_compression_ratio < 0.5:
            return False
        
        # Check volume decline trend
        volume_declines = [c.volume_decline for c in contractions[1:]]
        positive_declines = sum(1 for v in volume_declines if v > 0)
        volume_decline_ratio = positive_declines / len(volume_declines) if volume_declines else 0
        
        # At least 40% of contractions should show volume decline
        return volume_decline_ratio >= 0.4
    
    def _create_vcp_pattern(
        self,
        symbol: str,
        data: pd.DataFrame,
        base: Dict,
        contractions: List[VCPContraction]
    ) -> VCPPattern:
        """Create a complete VCP pattern object"""
        
        # Calculate pattern metrics
        first_contraction = contractions[0]
        last_contraction = contractions[-1]
        
        total_decline = (base['high'] - base['low']) / base['high'] * 100
        
        # Volatility compression ratio
        first_volatility = first_contraction.range_percent
        last_volatility = last_contraction.range_percent
        volatility_compression = first_volatility / last_volatility if last_volatility > 0 else 1.0
        
        # Volume compression
        volume_levels = [c.volume_avg for c in contractions]
        volume_compression = volume_levels[0] / volume_levels[-1] if len(volume_levels) > 1 else 1.0
        
        # Stage analysis (simplified)
        current_stage = self._determine_stage(data, base['end_idx'])
        
        # Relative strength (placeholder - would need market data)
        relative_strength = 75.0  # Placeholder
        
        # Quality score calculation
        quality_score = self._calculate_quality_score(
            contractions, volatility_compression, volume_compression, 
            total_decline, current_stage, relative_strength
        )
        
        # Setup completion check
        is_setup_complete = (
            len(contractions) >= self.min_contractions and
            volatility_compression >= self.min_volatility_compression and
            current_stage == 2  # Stage 2 uptrend
        )
        
        # Calculate breakout and stop levels
        breakout_level = base['high'] * 1.02  # 2% above base high
        stop_loss_level = base['low'] * 0.92   # 8% below base low
        
        return VCPPattern(
            symbol=symbol,
            pattern_start=base['start_date'].date(),
            pattern_end=base['end_date'].date(),
            base_duration=base['duration'],
            contractions=contractions,
            total_decline=total_decline,
            volatility_compression=volatility_compression,
            volume_compression=volume_compression,
            current_stage=current_stage,
            relative_strength=relative_strength,
            quality_score=quality_score,
            is_setup_complete=is_setup_complete,
            breakout_level=breakout_level,
            stop_loss_level=stop_loss_level
        )
    
    def _determine_stage(self, data: pd.DataFrame, idx: int) -> int:
        """
        Determine Weinstein stage (1-4) at given index
        
        Stage 1: Basing (Price near 200 SMA, sideways)
        Stage 2: Advancing (Price > 150 SMA > 200 SMA, both rising)
        Stage 3: Topping (Price above averages but averages flattening)
        Stage 4: Declining (Price < 150 SMA < 200 SMA, both falling)
        """
        if idx >= len(data) or idx < 200:
            return 1  # Insufficient data
        
        current_price = data['close'].iloc[idx]
        sma_50 = data['sma_50'].iloc[idx]
        sma_150 = data['sma_150'].iloc[idx]
        sma_200 = data['sma_200'].iloc[idx]
        
        # Check if moving averages are available
        if pd.isna(sma_150) or pd.isna(sma_200):
            return 1
        
        # Stage 2: Price > 150 SMA > 200 SMA, both rising
        if (current_price > sma_150 and 
            sma_150 > sma_200 and
            sma_150 > data['sma_150'].iloc[idx-20] and  # 150 SMA rising over 20 days
            sma_200 > data['sma_200'].iloc[idx-20]):    # 200 SMA rising over 20 days
            return 2
        
        # Stage 4: Price < 150 SMA and declining trend
        if (current_price < sma_150 and 
            sma_150 < data['sma_150'].iloc[idx-20]):  # 150 SMA declining
            return 4
        
        # Stage 3: Price above averages but flattening
        if current_price > sma_150:
            return 3
        
        # Default Stage 1: Basing
        return 1
    
    def _calculate_quality_score(
        self,
        contractions: List[VCPContraction],
        volatility_compression: float,
        volume_compression: float,
        total_decline: float,
        current_stage: int,
        relative_strength: float
    ) -> float:
        """
        Calculate VCP pattern quality score (0-100)
        
        Scoring factors:
        - Number of contractions (more = better, up to 5)
        - Volatility compression ratio
        - Volume compression 
        - Stage analysis (Stage 2 = best)
        - Relative strength rating
        - Base decline (smaller = better)
        """
        score = 0.0
        
        # Contractions count score (0-20 points)
        contraction_score = min(20, (len(contractions) / 5.0) * 20)
        score += contraction_score
        
        # Volatility compression score (0-25 points)
        vol_compression_score = min(25, (volatility_compression / 3.0) * 25)
        score += vol_compression_score
        
        # Volume compression score (0-20 points)
        volume_compression_score = min(20, (volume_compression / 2.0) * 20)
        score += volume_compression_score
        
        # Stage analysis score (0-15 points)
        stage_scores = {1: 5, 2: 15, 3: 8, 4: 0}
        score += stage_scores.get(current_stage, 0)
        
        # Relative strength score (0-15 points)
        rs_score = (relative_strength / 100) * 15
        score += rs_score
        
        # Base decline penalty (0-5 points, lower decline = higher score)
        decline_score = max(0, 5 - (total_decline / 10))
        score += decline_score
        
        return min(100, score)
    
    def get_pattern_summary(self, pattern: VCPPattern) -> Dict:
        """Get a summary dict of VCP pattern for easy analysis"""
        return {
            'symbol': pattern.symbol,
            'pattern_dates': f"{pattern.pattern_start} to {pattern.pattern_end}",
            'duration_days': pattern.base_duration,
            'contractions_count': len(pattern.contractions),
            'total_decline_pct': round(pattern.total_decline, 2),
            'volatility_compression': round(pattern.volatility_compression, 2),
            'volume_compression': round(pattern.volume_compression, 2),
            'current_stage': pattern.current_stage,
            'relative_strength': pattern.relative_strength,
            'quality_score': round(pattern.quality_score, 1),
            'is_setup_complete': pattern.is_setup_complete,
            'breakout_level': round(pattern.breakout_level, 2),
            'stop_loss_level': round(pattern.stop_loss_level, 2),
            'risk_reward_ratio': round(
                (pattern.breakout_level - pattern.stop_loss_level) / pattern.stop_loss_level * 100, 2
            )
        }