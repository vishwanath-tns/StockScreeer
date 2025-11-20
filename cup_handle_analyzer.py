"""
Cup and Handle Pattern Analyzer
===============================

Analyzes why cup and handle patterns might not be detected and provides
relaxed scanning with detailed diagnostics.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import date, timedelta
from volatility_patterns.data.data_service import DataService

class CupHandleAnalyzer:
    """Analyze market for potential cup and handle formations with diagnostics"""
    
    def __init__(self):
        self.data_service = DataService()
    
    def analyze_market_for_patterns(self, symbols=None):
        """Analyze market conditions for cup and handle formation potential"""
        
        if symbols is None:
            symbols = ['HDFCBANK', 'RELIANCE', 'TCS', 'INFY', 'ICICIBANK', 
                      'SBIN', 'BAJAJFINSV', 'ASIANPAINT', 'BHARTIARTL', 'MARUTI']
        
        print("🔍 CUP AND HANDLE MARKET ANALYSIS")
        print("=" * 60)
        print("Analyzing market conditions and potential setups...")
        
        results = []
        
        for symbol in symbols:
            try:
                analysis = self._analyze_single_stock(symbol)
                if analysis:
                    results.append(analysis)
                    
            except Exception as e:
                print(f"⚠️ Error analyzing {symbol}: {e}")
        
        # Display results
        self._display_analysis_results(results)
        
        # Show relaxed patterns if any
        relaxed_patterns = self._find_relaxed_patterns(symbols)
        if relaxed_patterns:
            self._display_relaxed_patterns(relaxed_patterns)
    
    def _analyze_single_stock(self, symbol):
        """Analyze a single stock for cup and handle potential"""
        
        # Get 18 months of data
        end_date = date.today()
        start_date = end_date - timedelta(days=550)
        
        data = self.data_service.get_ohlcv_data(symbol, start_date, end_date)
        data = self._filter_trading_days(data)
        
        if len(data) < 100:
            return None
        
        print(f"\n📊 Analyzing {symbol}:")
        print("-" * 30)
        
        current_price = data.iloc[-1]['close']
        print(f"   💰 Current Price: ₹{current_price:.2f}")
        
        # Check for recent significant highs
        high_points = self._find_recent_highs(data)
        
        if not high_points:
            print(f"   📉 No significant highs found in recent period")
            return None
        
        best_high = max(high_points, key=lambda x: x['price'])
        
        # Analyze potential cup formation from this high
        cup_analysis = self._analyze_potential_cup(data, best_high)
        
        if cup_analysis:
            print(f"   ✅ Potential cup formation found:")
            print(f"      📅 From: {cup_analysis['start_date']} (₹{cup_analysis['start_price']:.2f})")
            print(f"      📉 Bottom: {cup_analysis['bottom_date']} (₹{cup_analysis['bottom_price']:.2f})")
            print(f"      📏 Depth: {cup_analysis['depth_percent']:.1f}%")
            print(f"      ⏱️ Duration: {cup_analysis['duration_days']} days")
            
            # Check for handle formation
            handle_analysis = self._analyze_potential_handle(data, cup_analysis)
            
            if handle_analysis:
                print(f"   🏆 Handle formation detected:")
                print(f"      📉 Handle depth: {handle_analysis['depth_percent']:.1f}%")
                print(f"      ⏱️ Duration: {handle_analysis['duration_days']} days")
                print(f"      🎯 Breakout level: ₹{handle_analysis['breakout_level']:.2f}")
                print(f"      📏 Distance: {handle_analysis['distance_to_breakout']:.1f}%")
                
                return {
                    'symbol': symbol,
                    'current_price': current_price,
                    'cup': cup_analysis,
                    'handle': handle_analysis,
                    'has_pattern': True
                }
            else:
                print(f"   ❌ No valid handle formation found")
                return {
                    'symbol': symbol,
                    'current_price': current_price,
                    'cup': cup_analysis,
                    'handle': None,
                    'has_pattern': False
                }
        else:
            print(f"   ❌ No valid cup formation found")
            return {
                'symbol': symbol,
                'current_price': current_price,
                'cup': None,
                'handle': None,
                'has_pattern': False
            }
    
    def _filter_trading_days(self, data):
        """Filter out weekends"""
        data['date'] = pd.to_datetime(data['date'])
        data = data[data['date'].dt.dayofweek < 5].copy()
        return data.reset_index(drop=True)
    
    def _find_recent_highs(self, data):
        """Find significant highs in the data"""
        
        highs = []
        window = 15
        
        for i in range(window, len(data) - window):
            current_high = data.iloc[i]['high']
            
            # Check if this is a local high
            left_max = data.iloc[i-window:i]['high'].max()
            right_max = data.iloc[i+1:i+window+1]['high'].max()
            
            if current_high > left_max * 1.05 and current_high > right_max * 1.05:
                highs.append({
                    'idx': i,
                    'date': data.iloc[i]['date'].date(),
                    'price': current_high
                })
        
        # Filter for recent highs (last 12 months)
        cutoff_date = date.today() - timedelta(days=365)
        recent_highs = [h for h in highs if h['date'] >= cutoff_date]
        
        return recent_highs[-3:] if len(recent_highs) > 3 else recent_highs  # Last 3 highs
    
    def _analyze_potential_cup(self, data, high_point):
        """Analyze potential cup formation from a high point"""
        
        start_idx = high_point['idx']
        start_price = high_point['price']
        start_date = high_point['date']
        
        # Look ahead for potential bottom
        search_start = start_idx + 20  # At least 20 days later
        search_end = min(len(data) - 10, start_idx + 250)  # Maximum 1 year
        
        if search_start >= len(data) - 10:
            return None
        
        # Find lowest point in search range
        search_data = data.iloc[search_start:search_end]
        bottom_idx = search_data['low'].idxmin()
        bottom_global_idx = data.index.get_loc(bottom_idx)
        bottom_price = data.iloc[bottom_global_idx]['low']
        bottom_date = data.iloc[bottom_global_idx]['date'].date()
        
        # Calculate cup depth
        cup_depth = ((start_price - bottom_price) / start_price) * 100
        
        # More relaxed criteria
        if cup_depth < 10 or cup_depth > 70:  # Relaxed depth range
            return None
        
        # Look for recovery (less strict)
        recovery_start = bottom_global_idx + 5
        recovery_end = len(data) - 1  # Current data
        
        if recovery_start >= len(data):
            return None
        
        recovery_data = data.iloc[recovery_start:recovery_end+1]
        
        # Check if price has recovered to at least 70% of start
        target_recovery = start_price * 0.7
        recovery_points = recovery_data[recovery_data['high'] >= target_recovery]
        
        if len(recovery_points) == 0:
            return None
        
        # Use current price as cup end
        cup_end_idx = len(data) - 1
        cup_end_price = data.iloc[cup_end_idx]['close']
        cup_end_date = data.iloc[cup_end_idx]['date'].date()
        
        cup_duration = cup_end_idx - start_idx
        
        return {
            'start_idx': start_idx,
            'bottom_idx': bottom_global_idx,
            'end_idx': cup_end_idx,
            'start_price': start_price,
            'bottom_price': bottom_price,
            'end_price': cup_end_price,
            'start_date': start_date,
            'bottom_date': bottom_date,
            'end_date': cup_end_date,
            'depth_percent': cup_depth,
            'duration_days': cup_duration
        }
    
    def _analyze_potential_handle(self, data, cup_analysis):
        """Analyze potential handle formation"""
        
        cup_end_idx = cup_analysis['end_idx']
        cup_end_price = cup_analysis['end_price']
        
        # Look for recent pullback (last 30 days)
        recent_data = data.tail(30)
        
        if len(recent_data) < 5:
            return None
        
        recent_high = recent_data['high'].max()
        recent_low = recent_data['low'].min()
        current_price = data.iloc[-1]['close']
        
        # Calculate handle depth from recent high
        if recent_high <= recent_low:
            return None
            
        handle_depth = ((recent_high - recent_low) / recent_high) * 100
        
        # Relaxed handle criteria
        if handle_depth < 3 or handle_depth > 50:  # Very relaxed
            return None
        
        # Estimate breakout level
        resistance_level = max(recent_high, cup_analysis['start_price'] * 0.95)
        breakout_level = resistance_level * 1.02
        
        distance_to_breakout = ((breakout_level - current_price) / current_price) * 100
        
        return {
            'start_price': recent_high,
            'low_price': recent_low,
            'end_price': current_price,
            'depth_percent': handle_depth,
            'duration_days': len(recent_data),
            'breakout_level': breakout_level,
            'distance_to_breakout': distance_to_breakout
        }
    
    def _display_analysis_results(self, results):
        """Display analysis results"""
        
        print(f"\n📊 MARKET ANALYSIS RESULTS:")
        print("=" * 60)
        
        patterns_found = [r for r in results if r['has_pattern']]
        potential_cups = [r for r in results if r['cup'] and not r['has_pattern']]
        
        if patterns_found:
            print(f"\n🏆 COMPLETE CUP & HANDLE PATTERNS FOUND: {len(patterns_found)}")
            for result in patterns_found:
                handle = result['handle']
                print(f"   📈 {result['symbol']}: Breakout ₹{handle['breakout_level']:.2f} "
                      f"({handle['distance_to_breakout']:.1f}% away)")
        
        if potential_cups:
            print(f"\n🔄 POTENTIAL CUPS (Need Handle): {len(potential_cups)}")
            for result in potential_cups:
                cup = result['cup']
                print(f"   📊 {result['symbol']}: Cup depth {cup['depth_percent']:.1f}%, "
                      f"Duration {cup['duration_days']}d")
        
        no_patterns = len([r for r in results if not r['cup']])
        if no_patterns > 0:
            print(f"\n❌ NO PATTERNS DETECTED: {no_patterns} stocks")
    
    def _find_relaxed_patterns(self, symbols):
        """Find patterns with very relaxed criteria"""
        
        relaxed_patterns = []
        
        print(f"\n🔍 SCANNING WITH RELAXED CRITERIA:")
        print("-" * 50)
        
        for symbol in symbols[:5]:  # Limit to first 5 for demo
            try:
                end_date = date.today()
                start_date = end_date - timedelta(days=300)  # 10 months
                
                data = self.data_service.get_ohlcv_data(symbol, start_date, end_date)
                data = self._filter_trading_days(data)
                
                if len(data) < 50:
                    continue
                
                # Very simple pattern detection
                high_price = data['high'].max()
                high_idx = data['high'].idxmax()
                high_global_idx = data.index.get_loc(high_idx)
                
                low_price = data['low'].min()
                low_idx = data['low'].idxmin()
                low_global_idx = data.index.get_loc(low_idx)
                
                current_price = data.iloc[-1]['close']
                
                # Check if low came after high (basic cup shape)
                if low_global_idx > high_global_idx:
                    depth = ((high_price - low_price) / high_price) * 100
                    
                    # Very relaxed: any depth between 8-80%
                    if 8 <= depth <= 80:
                        # Check recent recovery
                        recent_data = data.tail(30)
                        recent_high = recent_data['high'].max()
                        
                        recovery_pct = ((recent_high - low_price) / (high_price - low_price)) * 100
                        
                        if recovery_pct >= 40:  # At least 40% recovery
                            pattern = {
                                'symbol': symbol,
                                'high_price': high_price,
                                'low_price': low_price,
                                'current_price': current_price,
                                'depth_percent': depth,
                                'recovery_percent': recovery_pct,
                                'breakout_level': recent_high * 1.02,
                                'distance_to_breakout': ((recent_high * 1.02 - current_price) / current_price) * 100
                            }
                            relaxed_patterns.append(pattern)
                            
                            print(f"   📊 {symbol}: Depth {depth:.1f}%, Recovery {recovery_pct:.1f}%")
                
            except Exception as e:
                continue
        
        return relaxed_patterns
    
    def _display_relaxed_patterns(self, patterns):
        """Display relaxed pattern results"""
        
        print(f"\n🎯 RELAXED CUP-LIKE FORMATIONS FOUND: {len(patterns)}")
        print("=" * 70)
        
        if patterns:
            print(f"{'Symbol':<12} {'Depth':<8} {'Recovery':<10} {'Breakout':<10} {'Distance':<10}")
            print("-" * 70)
            
            for pattern in patterns:
                print(f"{pattern['symbol']:<12} {pattern['depth_percent']:<7.1f}% "
                      f"{pattern['recovery_percent']:<9.1f}% ₹{pattern['breakout_level']:<9.0f} "
                      f"{pattern['distance_to_breakout']:<9.1f}%")
            
            print(f"\n💡 NOTE: These are relaxed patterns that may develop into proper cup & handle formations")

def main():
    """Run cup and handle analysis"""
    analyzer = CupHandleAnalyzer()
    analyzer.analyze_market_for_patterns()

if __name__ == "__main__":
    main()