"""
VCP Market Scanner - Show Current Market Patterns
=================================================

A broader scanner to understand what VCP-like patterns exist in the current market,
even if they don't meet strict Minervini criteria.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import date, timedelta
from volatility_patterns.data.data_service import DataService
from volatility_patterns.core.vcp_detector import VCPDetector

class VCPMarketScanner:
    """Broader scanner to understand current market VCP patterns"""
    
    def __init__(self):
        self.data_service = DataService()
        self.detector = VCPDetector()
    
    def scan_market_patterns(self):
        """Scan market to show what patterns exist"""
        
        symbols = ['HDFCBANK', 'CIPLA', 'BAJAJFINSV', 'BIOCON', 'BRITANNIA', 
                  'TCS', 'INFY', 'RELIANCE', 'ICICIBANK', 'SBIN']
        
        print("🔍 VCP MARKET PATTERN ANALYSIS")
        print("=" * 60)
        print("Showing current market conditions and any VCP-like patterns...")
        
        end_date = date.today()
        start_date = end_date - timedelta(days=365)  # Look back 1 year
        
        for symbol in symbols:
            try:
                print(f"\n📊 Analyzing {symbol}:")
                print("-" * 30)
                
                # Get data
                data = self.data_service.get_ohlcv_data(symbol, start_date, end_date)
                data = self._filter_trading_days(data)
                
                if len(data) < 100:
                    print(f"   ❌ Insufficient data: {len(data)} records")
                    continue
                
                # Detect patterns
                patterns = self.detector.detect_vcp_patterns(data, symbol)
                
                current_price = data.iloc[-1]['close']
                print(f"   💰 Current Price: ₹{current_price:.2f}")
                
                if not patterns:
                    print(f"   📉 No VCP patterns detected")
                    
                    # Show recent volatility
                    recent_data = data.tail(60)
                    volatility = (recent_data['high'].max() - recent_data['low'].min()) / recent_data['low'].min() * 100
                    print(f"   📊 Recent 60-day volatility: {volatility:.1f}%")
                    continue
                
                # Show patterns found
                print(f"   ✅ Found {len(patterns)} VCP patterns")
                
                # Get best recent pattern
                recent_patterns = [p for p in patterns if p.end_date >= end_date - timedelta(days=120)]
                
                if recent_patterns:
                    best_recent = max(recent_patterns, key=lambda p: p.quality_score)
                    
                    print(f"   🎯 Best Recent Pattern:")
                    print(f"      Quality: {best_recent.quality_score:.1f}")
                    print(f"      Contractions: {len(best_recent.contractions)}")
                    print(f"      Period: {best_recent.base_start_date} to {best_recent.end_date}")
                    print(f"      Days: {(best_recent.end_date - best_recent.base_start_date).days}")
                    
                    if best_recent.contractions:
                        latest = best_recent.contractions[-1]
                        print(f"      Latest contraction: {latest.range_percent:.1f}%")
                        
                        # Calculate trading levels
                        pattern_start = pd.to_datetime(best_recent.base_start_date)
                        pattern_end = pd.to_datetime(best_recent.end_date)
                        pattern_data = data[(data['date'] >= pattern_start) & (data['date'] <= pattern_end)]
                        
                        if len(pattern_data) > 0:
                            resistance = pattern_data['high'].max()
                            support = pattern_data['low'].max()  # Highest low as support
                            
                            breakout_level = resistance * 1.02
                            distance_to_breakout = ((breakout_level - current_price) / current_price) * 100
                            
                            print(f"      📈 Resistance: ₹{resistance:.2f}")
                            print(f"      📉 Support: ₹{support:.2f}")
                            print(f"      🎯 Breakout level: ₹{breakout_level:.2f}")
                            print(f"      📏 Distance to breakout: {distance_to_breakout:.1f}%")
                            
                            if distance_to_breakout <= 3:
                                print(f"      🔥 STATUS: Close to breakout!")
                            elif distance_to_breakout <= 8:
                                print(f"      ⏳ STATUS: Worth watching")
                            else:
                                print(f"      💤 STATUS: Early stage")
                else:
                    print(f"   📅 No recent patterns (last 120 days)")
                    
                    # Show older patterns
                    if patterns:
                        latest_pattern = max(patterns, key=lambda p: p.end_date)
                        days_ago = (end_date - latest_pattern.end_date).days
                        print(f"   📊 Last pattern was {days_ago} days ago (Quality: {latest_pattern.quality_score:.1f})")
                
            except Exception as e:
                print(f"   ❌ Error analyzing {symbol}: {e}")
        
        print(f"\n💡 MARKET INSIGHTS:")
        print(f"   📅 Analysis period: {start_date} to {end_date}")
        print(f"   🔍 Patterns become rare in trending/volatile markets")
        print(f"   🎯 VCP patterns work best in consolidating markets")
        print(f"   📊 Current market may be in trending phase")
    
    def _filter_trading_days(self, data):
        """Filter out weekends"""
        data['date'] = pd.to_datetime(data['date'])
        data = data[data['date'].dt.dayofweek < 5].copy()
        return data.reset_index(drop=True)

def main():
    """Run market pattern analysis"""
    scanner = VCPMarketScanner()
    scanner.scan_market_patterns()

if __name__ == "__main__":
    main()