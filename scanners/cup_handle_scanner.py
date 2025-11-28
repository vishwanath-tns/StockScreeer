"""
Cup and Handle Formation Scanner
===============================

Detects cup and handle patterns in daily charts using William O'Neil's methodology.

Cup and Handle Pattern Criteria:
1. Cup Formation: 30-65% correction from highs, rounded bottom (not V-shaped)
2. Cup Duration: 7 weeks to 65 weeks (35-325 trading days)
3. Handle Formation: 10-40% pullback from cup rim, 1-4 weeks duration
4. Volume: Should dry up in cup, increase on handle breakout
5. Base Depth: Prefer 15-35% correction for optimal patterns
6. Price Level: Above $15 (avoid penny stocks)
7. Market Context: Works best in bull markets
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from volatility_patterns.data.data_service import DataService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CupHandlePattern:
    """Cup and Handle pattern data structure"""
    symbol: str
    
    # Cup formation data
    cup_start_date: date
    cup_bottom_date: date
    cup_end_date: date
    cup_start_price: float
    cup_bottom_price: float
    cup_end_price: float
    cup_depth_percent: float
    cup_duration_days: int
    
    # Handle formation data
    handle_start_date: date
    handle_end_date: date
    handle_start_price: float
    handle_low_price: float
    handle_end_price: float
    handle_depth_percent: float
    handle_duration_days: int
    
    # Pattern validation
    is_valid_cup: bool
    is_valid_handle: bool
    cup_shape_quality: float  # 0-100, higher = more rounded
    volume_confirmation: bool
    
    # Trading levels
    breakout_level: float
    stop_loss_level: float
    target_level: float
    current_price: float
    distance_to_breakout: float
    
    # Pattern scoring
    pattern_score: float  # 0-100 overall quality score
    recommendation: str
    
    def is_complete(self) -> bool:
        """Check if pattern is complete and valid"""
        return self.is_valid_cup and self.is_valid_handle
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for export/display"""
        return {
            'Symbol': self.symbol,
            'Current_Price': f'₹{self.current_price:.2f}',
            'Cup_Depth': f'{self.cup_depth_percent:.1f}%',
            'Handle_Depth': f'{self.handle_depth_percent:.1f}%',
            'Cup_Duration': f'{self.cup_duration_days}d',
            'Handle_Duration': f'{self.handle_duration_days}d',
            'Breakout_Level': f'₹{self.breakout_level:.2f}',
            'Stop_Loss': f'₹{self.stop_loss_level:.2f}',
            'Target': f'₹{self.target_level:.2f}',
            'Distance_to_BO': f'{self.distance_to_breakout:.1f}%',
            'Pattern_Score': f'{self.pattern_score:.1f}',
            'Shape_Quality': f'{self.cup_shape_quality:.1f}',
            'Volume_OK': '✅' if self.volume_confirmation else '❌',
            'Recommendation': self.recommendation,
            'Cup_Period': f'{self.cup_start_date} to {self.cup_end_date}',
            'Handle_Period': f'{self.handle_start_date} to {self.handle_end_date}'
        }

class CupHandleScanner:
    """Scan for cup and handle formations in daily charts"""
    
    def __init__(self):
        self.data_service = DataService()
        
        # Pattern criteria (adjustable parameters)
        self.min_price = 15.0  # Minimum stock price
        self.min_cup_depth = 15.0  # Minimum cup depth %
        self.max_cup_depth = 65.0  # Maximum cup depth %
        self.optimal_cup_depth_min = 20.0  # Optimal range start
        self.optimal_cup_depth_max = 35.0  # Optimal range end
        
        self.min_cup_duration = 35  # Minimum cup duration in trading days (7 weeks)
        self.max_cup_duration = 325  # Maximum cup duration in trading days (65 weeks)
        
        self.min_handle_depth = 5.0   # Minimum handle pullback %
        self.max_handle_depth = 40.0  # Maximum handle pullback %
        self.optimal_handle_depth_max = 25.0  # Prefer handles <25%
        
        self.min_handle_duration = 5   # Minimum handle duration (1 week)
        self.max_handle_duration = 20  # Maximum handle duration (4 weeks)
        
        # Data requirements
        self.lookback_days = 500  # Look back period for pattern detection
    
    def scan_stocks(self, symbols: Optional[List[str]] = None) -> List[CupHandlePattern]:
        """Scan stocks for cup and handle formations"""
        
        if symbols is None:
            symbols = self._get_screening_universe()
        
        logger.info(f"🏆 Starting Cup and Handle scan for {len(symbols)} stocks")
        logger.info(f"📊 Criteria: Cup depth {self.min_cup_depth}-{self.max_cup_depth}%, Duration {self.min_cup_duration}-{self.max_cup_duration}d")
        
        patterns = []
        processed = 0
        
        for symbol in symbols:
            try:
                pattern = self._detect_cup_handle_pattern(symbol)
                if pattern and pattern.is_complete():
                    patterns.append(pattern)
                    logger.info(f"✅ {symbol}: Found pattern (Score: {pattern.pattern_score:.1f})")
                
                processed += 1
                if processed % 10 == 0:
                    logger.info(f"📊 Processed {processed}/{len(symbols)}, Found {len(patterns)} patterns")
                    
            except Exception as e:
                logger.warning(f"⚠️ Error scanning {symbol}: {e}")
                continue
        
        # Sort by pattern score
        patterns.sort(key=lambda x: x.pattern_score, reverse=True)
        
        logger.info(f"🏆 Cup and Handle scan complete: Found {len(patterns)} valid patterns")
        return patterns
    
    def _get_screening_universe(self) -> List[str]:
        """Get stocks to scan for cup and handle patterns"""
        return [
            # Banking
            'HDFCBANK', 'ICICIBANK', 'SBIN', 'KOTAKBANK', 'AXISBANK', 'INDUSINDBK',
            
            # IT
            'TCS', 'INFY', 'WIPRO', 'HCLTECH', 'TECHM', 'LTI', 'LTIM',
            
            # Pharma
            'SUNPHARMA', 'DRREDDY', 'CIPLA', 'LUPIN', 'DIVISLAB', 'BIOCON', 'ALKEM',
            
            # FMCG
            'HINDUNILVR', 'ITC', 'NESTLEIND', 'BRITANNIA', 'DABUR', 'GODREJCP', 'MARICO',
            
            # Auto
            'MARUTI', 'HYUNDAI', 'TATAMOTORS', 'M&M', 'BAJAJ-AUTO', 'TVSMOTORS', 'EICHERMOT',
            
            # Financials
            'BAJFINANCE', 'BAJAJFINSV', 'SBILIFE', 'HDFCLIFE', 'ICICIPRULI',
            
            # Metals & Energy
            'TATASTEEL', 'JSWSTEEL', 'HINDALCO', 'VEDL', 'RELIANCE', 'ONGC', 'IOC', 'BPCL',
            
            # Others
            'NTPC', 'BHARTIARTL', 'ADANIENT', 'ASIANPAINT'
        ]
    
    def _detect_cup_handle_pattern(self, symbol: str) -> Optional[CupHandlePattern]:
        """Detect cup and handle pattern for a single stock"""
        
        # Get data
        end_date = date.today()
        start_date = end_date - timedelta(days=self.lookback_days)
        
        data = self.data_service.get_ohlcv_data(symbol, start_date, end_date)
        data = self._filter_trading_days(data)
        
        if len(data) < 100:
            return None
        
        current_price = data.iloc[-1]['close']
        
        # Price filter
        if current_price < self.min_price:
            return None
        
        # Find potential cup formations
        cup_patterns = self._find_cup_formations(data)
        
        if not cup_patterns:
            return None
        
        # For each cup, look for handle formation
        for cup in cup_patterns:
            handle = self._find_handle_formation(data, cup)
            
            if handle:
                # Validate complete pattern
                pattern = self._create_cup_handle_pattern(symbol, data, cup, handle, current_price)
                
                if pattern and pattern.is_complete():
                    return pattern
        
        return None
    
    def _filter_trading_days(self, data: pd.DataFrame) -> pd.DataFrame:
        """Filter out weekends"""
        data['date'] = pd.to_datetime(data['date'])
        data = data[data['date'].dt.dayofweek < 5].copy()
        return data.reset_index(drop=True)
    
    def _find_cup_formations(self, data: pd.DataFrame) -> List[Dict]:
        """Find potential cup formations in the data"""
        
        cups = []
        
        # Look for significant highs (potential cup starts)
        highs = self._find_significant_highs(data, window=10, strength=0.05)
        
        for i, high_point in enumerate(highs):
            start_idx = high_point['idx']
            start_price = high_point['price']
            start_date = data.iloc[start_idx]['date'].date()
            
            # Look for potential cup bottom after this high
            search_start = start_idx + self.min_cup_duration // 3  # Look ahead
            search_end = min(len(data) - 20, start_idx + self.max_cup_duration)
            
            if search_start >= len(data) - 20:
                continue
            
            # Find the lowest point in search range
            search_data = data.iloc[search_start:search_end]
            if len(search_data) == 0:
                continue
                
            bottom_idx = search_data['low'].idxmin()
            bottom_global_idx = data.index.get_loc(bottom_idx)
            bottom_price = data.iloc[bottom_global_idx]['low']
            bottom_date = data.iloc[bottom_global_idx]['date'].date()
            
            # Calculate cup depth
            cup_depth = ((start_price - bottom_price) / start_price) * 100
            
            # Check cup depth criteria
            if not (self.min_cup_depth <= cup_depth <= self.max_cup_depth):
                continue
            
            # Look for cup rim (recovery to near starting level)
            recovery_start = bottom_global_idx + 5
            recovery_end = min(len(data) - 5, bottom_global_idx + (self.max_cup_duration // 2))
            
            if recovery_start >= len(data) - 5:
                continue
            
            # Find point where price recovers to within 10% of start
            target_recovery = start_price * 0.9  # Allow 10% below start
            recovery_data = data.iloc[recovery_start:recovery_end]
            
            recovery_points = recovery_data[recovery_data['high'] >= target_recovery]
            
            if len(recovery_points) == 0:
                continue
            
            # Take first recovery point as cup end
            cup_end_idx = recovery_points.index[0]
            cup_end_global_idx = data.index.get_loc(cup_end_idx)
            cup_end_price = data.iloc[cup_end_global_idx]['close']
            cup_end_date = data.iloc[cup_end_global_idx]['date'].date()
            
            cup_duration = cup_end_global_idx - start_idx
            
            # Validate cup duration
            if not (self.min_cup_duration <= cup_duration <= self.max_cup_duration):
                continue
            
            # Check cup shape quality (should be rounded, not V-shaped)
            shape_quality = self._assess_cup_shape_quality(data, start_idx, bottom_global_idx, cup_end_global_idx)
            
            if shape_quality < 30:  # Minimum shape quality
                continue
            
            cup = {
                'start_idx': start_idx,
                'bottom_idx': bottom_global_idx,
                'end_idx': cup_end_global_idx,
                'start_price': start_price,
                'bottom_price': bottom_price,
                'end_price': cup_end_price,
                'start_date': start_date,
                'bottom_date': bottom_date,
                'end_date': cup_end_date,
                'depth_percent': cup_depth,
                'duration_days': cup_duration,
                'shape_quality': shape_quality
            }
            
            cups.append(cup)
        
        return cups
    
    def _find_significant_highs(self, data: pd.DataFrame, window: int = 10, strength: float = 0.05) -> List[Dict]:
        """Find significant high points in the data"""
        
        highs = []
        
        for i in range(window, len(data) - window):
            current_high = data.iloc[i]['high']
            
            # Check if this is a local high
            left_max = data.iloc[i-window:i]['high'].max()
            right_max = data.iloc[i+1:i+window+1]['high'].max()
            
            # Must be higher than surrounding points by minimum strength
            if (current_high > left_max * (1 + strength) and 
                current_high > right_max * (1 + strength)):
                
                highs.append({
                    'idx': i,
                    'date': data.iloc[i]['date'],
                    'price': current_high
                })
        
        return highs
    
    def _assess_cup_shape_quality(self, data: pd.DataFrame, start_idx: int, 
                                 bottom_idx: int, end_idx: int) -> float:
        """Assess the quality of cup shape (0-100, higher = more rounded)"""
        
        cup_data = data.iloc[start_idx:end_idx+1]
        
        if len(cup_data) < 10:
            return 0
        
        # Calculate how "rounded" the bottom is
        left_half = cup_data.iloc[:len(cup_data)//2]
        right_half = cup_data.iloc[len(cup_data)//2:]
        
        # Check for V-shape (rapid decline and recovery)
        left_slope = self._calculate_avg_slope(left_half['low'].values)
        right_slope = self._calculate_avg_slope(right_half['low'].values)
        
        # Prefer gradual slopes over sharp V-shapes
        slope_score = 100 - min(abs(left_slope) + abs(right_slope), 100)
        
        # Check for time spent near bottom (good cups spend time at bottom)
        bottom_price = cup_data['low'].min()
        bottom_range = bottom_price * 1.1  # Within 10% of bottom
        
        time_near_bottom = len(cup_data[cup_data['low'] <= bottom_range])
        total_time = len(cup_data)
        
        bottom_time_score = min((time_near_bottom / total_time) * 200, 100)
        
        # Overall shape quality
        shape_quality = (slope_score * 0.6 + bottom_time_score * 0.4)
        
        return max(0, min(100, shape_quality))
    
    def _calculate_avg_slope(self, values: np.ndarray) -> float:
        """Calculate average slope of price series"""
        if len(values) < 2:
            return 0
        
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]
        
        return slope
    
    def _find_handle_formation(self, data: pd.DataFrame, cup: Dict) -> Optional[Dict]:
        """Find handle formation after a cup"""
        
        cup_end_idx = cup['end_idx']
        cup_end_price = cup['end_price']
        
        # Handle should start shortly after cup ends
        handle_search_start = cup_end_idx
        handle_search_end = min(len(data) - 1, cup_end_idx + self.max_handle_duration + 10)
        
        if handle_search_start >= len(data) - 5:
            return None
        
        # Look for a pullback from cup rim
        handle_data = data.iloc[handle_search_start:handle_search_end]
        
        if len(handle_data) < self.min_handle_duration:
            return None
        
        # Find the lowest point in potential handle period
        handle_low_idx = handle_data['low'].idxmin()
        handle_low_global_idx = data.index.get_loc(handle_low_idx)
        handle_low_price = data.iloc[handle_low_global_idx]['low']
        
        # Calculate handle depth
        handle_depth = ((cup_end_price - handle_low_price) / cup_end_price) * 100
        
        # Validate handle depth
        if not (self.min_handle_depth <= handle_depth <= self.max_handle_depth):
            return None
        
        # Find handle end (current data end or breakout point)
        handle_end_idx = len(data) - 1
        handle_end_price = data.iloc[handle_end_idx]['close']
        handle_end_date = data.iloc[handle_end_idx]['date'].date()
        
        handle_duration = handle_end_idx - handle_search_start
        
        # Validate handle duration
        if not (self.min_handle_duration <= handle_duration <= self.max_handle_duration * 2):
            # Be more flexible with current handles
            if handle_end_idx < len(data) - 1:  # Only strict if handle is complete
                return None
        
        handle = {
            'start_idx': handle_search_start,
            'low_idx': handle_low_global_idx,
            'end_idx': handle_end_idx,
            'start_price': cup_end_price,
            'low_price': handle_low_price,
            'end_price': handle_end_price,
            'start_date': cup['end_date'],
            'low_date': data.iloc[handle_low_global_idx]['date'].date(),
            'end_date': handle_end_date,
            'depth_percent': handle_depth,
            'duration_days': handle_duration
        }
        
        return handle
    
    def _create_cup_handle_pattern(self, symbol: str, data: pd.DataFrame, 
                                 cup: Dict, handle: Dict, current_price: float) -> CupHandlePattern:
        """Create a complete cup and handle pattern object"""
        
        # Volume analysis
        volume_confirmation = self._analyze_volume_pattern(data, cup, handle)
        
        # Trading levels
        rim_level = max(cup['start_price'], cup['end_price'])  # Cup rim resistance
        breakout_level = rim_level * 1.02  # 2% above rim
        stop_loss_level = handle['low_price'] * 0.97  # 3% below handle low
        
        # Target calculation: Measure cup depth and project upward
        cup_height = cup['start_price'] - cup['bottom_price']
        target_level = breakout_level + cup_height  # Add cup height to breakout
        
        # Distance to breakout
        distance_to_breakout = ((breakout_level - current_price) / current_price) * 100
        
        # Pattern scoring
        pattern_score = self._calculate_pattern_score(cup, handle, volume_confirmation, current_price, breakout_level)
        
        # Recommendation
        recommendation = self._get_recommendation(pattern_score, distance_to_breakout)
        
        # Validation
        is_valid_cup = self._validate_cup(cup)
        is_valid_handle = self._validate_handle(handle, cup)
        
        return CupHandlePattern(
            symbol=symbol,
            cup_start_date=cup['start_date'],
            cup_bottom_date=cup['bottom_date'],
            cup_end_date=cup['end_date'],
            cup_start_price=cup['start_price'],
            cup_bottom_price=cup['bottom_price'],
            cup_end_price=cup['end_price'],
            cup_depth_percent=cup['depth_percent'],
            cup_duration_days=cup['duration_days'],
            handle_start_date=handle['start_date'],
            handle_end_date=handle['end_date'],
            handle_start_price=handle['start_price'],
            handle_low_price=handle['low_price'],
            handle_end_price=handle['end_price'],
            handle_depth_percent=handle['depth_percent'],
            handle_duration_days=handle['duration_days'],
            is_valid_cup=is_valid_cup,
            is_valid_handle=is_valid_handle,
            cup_shape_quality=cup['shape_quality'],
            volume_confirmation=volume_confirmation,
            breakout_level=breakout_level,
            stop_loss_level=stop_loss_level,
            target_level=target_level,
            current_price=current_price,
            distance_to_breakout=distance_to_breakout,
            pattern_score=pattern_score,
            recommendation=recommendation
        )
    
    def _analyze_volume_pattern(self, data: pd.DataFrame, cup: Dict, handle: Dict) -> bool:
        """Analyze volume pattern for cup and handle validation"""
        
        # Cup phase: volume should generally decline
        cup_data = data.iloc[cup['start_idx']:cup['end_idx']+1]
        cup_early_vol = cup_data['volume'].iloc[:len(cup_data)//3].mean()
        cup_late_vol = cup_data['volume'].iloc[-len(cup_data)//3:].mean()
        
        cup_volume_decline = cup_late_vol < cup_early_vol * 1.2  # Allow some flexibility
        
        # Handle phase: volume should be relatively low
        handle_data = data.iloc[handle['start_idx']:handle['end_idx']+1]
        handle_avg_vol = handle_data['volume'].mean()
        
        # Compare to overall average
        overall_avg_vol = data['volume'].tail(100).mean()
        handle_volume_ok = handle_avg_vol <= overall_avg_vol * 1.3
        
        return cup_volume_decline and handle_volume_ok
    
    def _validate_cup(self, cup: Dict) -> bool:
        """Validate cup formation meets criteria"""
        
        depth_ok = self.min_cup_depth <= cup['depth_percent'] <= self.max_cup_depth
        duration_ok = self.min_cup_duration <= cup['duration_days'] <= self.max_cup_duration
        shape_ok = cup['shape_quality'] >= 30
        
        return depth_ok and duration_ok and shape_ok
    
    def _validate_handle(self, handle: Dict, cup: Dict) -> bool:
        """Validate handle formation meets criteria"""
        
        depth_ok = self.min_handle_depth <= handle['depth_percent'] <= self.max_handle_depth
        duration_ok = handle['duration_days'] >= self.min_handle_duration
        
        # Handle should be shallower than cup
        shallower_than_cup = handle['depth_percent'] < cup['depth_percent'] * 0.6
        
        return depth_ok and duration_ok and shallower_than_cup
    
    def _calculate_pattern_score(self, cup: Dict, handle: Dict, volume_ok: bool, 
                               current_price: float, breakout_level: float) -> float:
        """Calculate overall pattern quality score 0-100"""
        
        score = 0
        
        # Cup depth score (25 points) - prefer 20-35%
        if self.optimal_cup_depth_min <= cup['depth_percent'] <= self.optimal_cup_depth_max:
            score += 25
        elif self.min_cup_depth <= cup['depth_percent'] <= self.max_cup_depth:
            score += 15
        else:
            score += 5
        
        # Cup shape quality (20 points)
        score += min(cup['shape_quality'] * 0.2, 20)
        
        # Handle depth score (15 points) - prefer shallow handles
        if handle['depth_percent'] <= self.optimal_handle_depth_max:
            score += 15
        elif handle['depth_percent'] <= self.max_handle_depth:
            score += 10
        else:
            score += 5
        
        # Volume confirmation (15 points)
        if volume_ok:
            score += 15
        
        # Distance to breakout (15 points)
        distance = ((breakout_level - current_price) / current_price) * 100
        if distance <= 2:
            score += 15
        elif distance <= 5:
            score += 10
        elif distance <= 10:
            score += 5
        
        # Cup duration preference (10 points) - prefer 3-6 months
        optimal_duration_min = 65  # ~3 months
        optimal_duration_max = 130  # ~6 months
        
        if optimal_duration_min <= cup['duration_days'] <= optimal_duration_max:
            score += 10
        elif self.min_cup_duration <= cup['duration_days'] <= self.max_cup_duration:
            score += 5
        
        return min(score, 100)
    
    def _get_recommendation(self, score: float, distance: float) -> str:
        """Get trading recommendation based on pattern quality"""
        
        if score >= 80 and distance <= 3:
            return "🔥 Strong Buy"
        elif score >= 70 and distance <= 5:
            return "⚡ Buy Setup"
        elif score >= 60 and distance <= 8:
            return "👀 Watch"
        elif score >= 50:
            return "📋 Monitor"
        else:
            return "❌ Avoid"
    
    def display_results(self, patterns: List[CupHandlePattern], top_n: int = 15):
        """Display cup and handle scanning results"""
        
        if not patterns:
            print("📭 No cup and handle patterns found")
            return
        
        print(f"\n🏆 TOP {min(top_n, len(patterns))} CUP AND HANDLE PATTERNS")
        print("=" * 140)
        print(f"{'#':<3} {'Symbol':<12} {'Price':<8} {'CupDepth':<9} {'HandleDepth':<12} {'Breakout':<9} {'Target':<8} {'Dist%':<6} {'Score':<5} {'Rec':<12}")
        print("-" * 140)
        
        for i, pattern in enumerate(patterns[:top_n], 1):
            rec_emoji = "🔥" if "Strong" in pattern.recommendation else "⚡" if "Buy" in pattern.recommendation else "👀" if "Watch" in pattern.recommendation else "📋" if "Monitor" in pattern.recommendation else "❌"
            
            print(f"{i:<3} {pattern.symbol:<12} ₹{pattern.current_price:<7.0f} "
                  f"{pattern.cup_depth_percent:<8.1f}% {pattern.handle_depth_percent:<11.1f}% "
                  f"₹{pattern.breakout_level:<8.0f} ₹{pattern.target_level:<7.0f} "
                  f"{pattern.distance_to_breakout:<5.1f}% {pattern.pattern_score:<4.0f} "
                  f"{rec_emoji} {pattern.recommendation}")
        
        # Summary statistics
        strong_patterns = sum(1 for p in patterns if "Strong" in p.recommendation)
        buy_patterns = sum(1 for p in patterns if "Buy" in p.recommendation)
        watch_patterns = sum(1 for p in patterns if "Watch" in p.recommendation)
        
        print(f"\n📊 PATTERN BREAKDOWN:")
        print(f"   🔥 Strong Buy Patterns: {strong_patterns}")
        print(f"   ⚡ Buy Setup Patterns: {buy_patterns}")  
        print(f"   👀 Watch List Patterns: {watch_patterns}")
        
        # Pattern insights
        avg_cup_depth = sum(p.cup_depth_percent for p in patterns) / len(patterns)
        avg_score = sum(p.pattern_score for p in patterns) / len(patterns)
        
        print(f"\n💡 PATTERN INSIGHTS:")
        print(f"   📊 Average cup depth: {avg_cup_depth:.1f}%")
        print(f"   🎯 Average pattern score: {avg_score:.1f}")
        print(f"   📈 Cup & Handle patterns are powerful bullish continuation signals")
        print(f"   🏆 Best patterns: 20-35% cup depth, shallow handle, strong volume")

def main():
    """Run cup and handle pattern scanner"""
    
    print("🏆 CUP AND HANDLE FORMATION SCANNER")
    print("=" * 55)
    print("Scanning for William O'Neil cup and handle patterns...")
    
    # Initialize scanner
    scanner = CupHandleScanner()
    
    # Run scan
    patterns = scanner.scan_stocks()
    
    # Display results
    scanner.display_results(patterns, top_n=20)
    
    if patterns:
        # Export results
        results_data = [pattern.to_dict() for pattern in patterns]
        df = pd.DataFrame(results_data)
        
        filename = f"cup_handle_patterns_{date.today().strftime('%Y%m%d')}.csv"
        filepath = f"screener_results/{filename}"
        df.to_csv(filepath, index=False)
        
        print(f"\n💾 Results exported to: {filepath}")
        
        print(f"\n🏆 SCAN COMPLETE!")
        print(f"   📊 Total patterns found: {len(patterns)}")
        print(f"   🎯 High-quality patterns: {sum(1 for p in patterns if p.pattern_score >= 70)}")
        print(f"   🔥 Ready-to-breakout: {sum(1 for p in patterns if p.distance_to_breakout <= 3)}")

if __name__ == "__main__":
    main()