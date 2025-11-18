"""
Demo: Enhanced Candlestick Pattern Detection with Timeframe Support
=================================================================

This script demonstrates the enhanced pattern detection system supporting
Daily, Weekly, and Monthly timeframes using existing database tables.
"""

import sys
import os
from datetime import datetime, timedelta

# Add project path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.candlestick_patterns_enhanced import (
    CandleDataService, 
    PatternScannerService,
    test_timeframe_data_availability,
    demo_pattern_detection_all_timeframes
)

def demo_timeframe_selection():
    """Demo the timeframe selection feature"""
    print("🎯 Enhanced Pattern Detection Demo - Timeframe Selection")
    print("=" * 70)
    
    # Initialize services
    data_service = CandleDataService()
    scanner = PatternScannerService()
    
    # Test symbols
    test_symbols = ['RELIANCE', 'TCS', 'HDFC']
    
    print(f"\n🔍 Testing with symbols: {', '.join(test_symbols)}")
    
    # Test each timeframe
    timeframes = ['Daily', 'Weekly', 'Monthly']
    
    for timeframe in timeframes:
        print(f"\n📊 {timeframe} Timeframe Analysis:")
        print("-" * 50)
        
        # Check data availability
        freshness = data_service.check_data_freshness(timeframe)
        print(f"   📈 Data Status: {freshness['status']}")
        print(f"   📅 Latest Date: {freshness['latest_date']}")
        print(f"   📊 Symbols: {freshness['symbol_count']:,}")
        print(f"   💾 Records: {freshness['total_records']:,}")
        print(f"   ⏱️ Days Behind: {freshness['days_behind']}")
        
        # Test data fetching for one symbol
        if test_symbols:
            symbol = test_symbols[0]
            print(f"\n   🔍 Testing {timeframe} data for {symbol}:")
            
            # Get last 6 months of data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=180)
            
            df = data_service.get_candle_data(symbol, start_date, end_date, timeframe)
            
            if not df.empty:
                print(f"   ✅ Found {len(df)} {timeframe.lower()} candles")
                print(f"   📅 Date range: {df['date'].min()} to {df['date'].max()}")
                print(f"   💹 Price range: {df['low'].min():.2f} - {df['high'].max():.2f}")
            else:
                print(f"   ❌ No {timeframe.lower()} data found")

def demo_pattern_detection_comparison():
    """Compare pattern detection across timeframes"""
    print("\n" + "=" * 70)
    print("🕯️ Pattern Detection Comparison Across Timeframes")
    print("=" * 70)
    
    def progress_callback(message, progress):
        print(f"   📈 {message} ({progress:.1f}%)")
    
    scanner = PatternScannerService()
    
    # Test with a small set of symbols
    test_symbols = ['RELIANCE', 'TCS']
    pattern_types = ['NR4', 'NR7']
    
    results_summary = {}
    
    for timeframe in ['Monthly', 'Weekly', 'Daily']:
        print(f"\n🎯 {timeframe} Pattern Detection:")
        print("-" * 40)
        
        patterns = scanner.scan_patterns(
            symbols=test_symbols,
            timeframe=timeframe,
            pattern_types=pattern_types,
            batch_size=1,
            max_workers=1,
            progress_callback=progress_callback
        )
        
        results_summary[timeframe] = len(patterns)
        print(f"   ✅ Found {len(patterns)} patterns")
        
        # Show sample patterns
        for pattern in patterns[:2]:
            print(f"      🔍 {pattern['symbol']}: {pattern['pattern_type']} on {pattern['detection_date']}")
    
    # Summary
    print(f"\n📊 Pattern Detection Summary:")
    print("-" * 30)
    for timeframe, count in results_summary.items():
        print(f"   {timeframe}: {count} patterns")

def demo_data_freshness_check():
    """Demo data freshness checking across timeframes"""
    print("\n" + "=" * 70)
    print("📊 Data Freshness Check Across Timeframes")
    print("=" * 70)
    
    service = CandleDataService()
    
    timeframes = ['Daily', 'Weekly', 'Monthly']
    
    print(f"{'Timeframe':<10} {'Status':<15} {'Latest Date':<12} {'Symbols':<8} {'Records':<10} {'Days Behind':<12}")
    print("-" * 75)
    
    for timeframe in timeframes:
        freshness = service.check_data_freshness(timeframe)
        
        status_icon = "✅" if "Current" in freshness['status'] else "⚠️" if "Behind" in freshness['status'] else "❌"
        latest = freshness['latest_date'].strftime('%Y-%m-%d') if freshness['latest_date'] else 'N/A'
        symbols = f"{freshness['symbol_count']:,}"
        records = f"{freshness['total_records']:,}"
        days_behind = str(freshness['days_behind'])
        
        print(f"{timeframe:<10} {status_icon} {freshness['status']:<13} {latest:<12} {symbols:<8} {records:<10} {days_behind:<12}")

def main():
    """Run all demos"""
    try:
        # Demo 1: Timeframe selection
        demo_timeframe_selection()
        
        # Demo 2: Data freshness check
        demo_data_freshness_check()
        
        # Demo 3: Pattern detection comparison
        demo_pattern_detection_comparison()
        
        print("\n" + "=" * 70)
        print("🎉 Enhanced Timeframe Demo Completed Successfully!")
        print("✅ Features demonstrated:")
        print("   • Multi-timeframe data access (Daily, Weekly, Monthly)")
        print("   • Data freshness checking")
        print("   • Pattern detection across timeframes")
        print("   • Database schema compatibility")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()