"""
Candlestick Pattern Detection System Demo
========================================

Demonstrates the complete candlestick pattern detection system with:
- NR4, NR7, NR13, NR21 pattern detection
- High-performance batch processing 
- Progress tracking and database storage
- GUI integration ready

Usage:
------
1. Run this script to see pattern detection in action
2. Launch scanner_gui.py to use the GUI interface
3. Check the "🕯️ Pattern Scanner" tab for interactive scanning
"""

from services.candlestick_patterns import (
    CandleDataService, 
    NarrowRangeDetector, 
    PatternStorageService,
    PatternScannerService
)
from datetime import datetime, timedelta
import time

def demo_pattern_detection():
    """Run a comprehensive demo of the pattern detection system"""
    print("🚀 Candlestick Pattern Detection System Demo")
    print("=" * 60)
    
    # Initialize services
    print("\n📊 Initializing services...")
    data_service = CandleDataService()
    detector = NarrowRangeDetector()
    storage_service = PatternStorageService()
    
    # Check available data
    symbols = data_service.get_available_symbols()
    print(f"✅ Found {len(symbols)} symbols available for analysis")
    
    # Test with a few well-known symbols
    test_symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFC', 'SBIN']
    available_test_symbols = [s for s in test_symbols if s in symbols]
    
    if not available_test_symbols:
        available_test_symbols = symbols[:5]  # Use first 5 if none of test symbols found
    
    print(f"🧪 Testing with symbols: {available_test_symbols}")
    
    # Pattern detection for individual symbols
    total_patterns = 0
    all_patterns = []
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)  # 2 years of data
    
    print(f"\n📈 Analyzing patterns from {start_date.date()} to {end_date.date()}")
    print("-" * 60)
    
    for symbol in available_test_symbols:
        print(f"🔍 Analyzing {symbol}...")
        
        # Get monthly candles
        candles = data_service.get_monthly_candles(symbol, start_date, end_date)
        
        if len(candles) < 21:
            print(f"   ⚠️  Insufficient data ({len(candles)} candles)")
            continue
        
        # Detect patterns
        patterns = detector.detect_narrow_range_patterns(candles)
        
        if patterns:
            print(f"   ✅ Found {len(patterns)} patterns:")
            
            # Group patterns by type
            pattern_counts = {}
            for pattern in patterns:
                pattern_type = pattern.pattern_type
                pattern_counts[pattern_type] = pattern_counts.get(pattern_type, 0) + 1
            
            for ptype, count in pattern_counts.items():
                print(f"      {ptype}: {count}")
            
            # Show most recent patterns
            recent_patterns = sorted(patterns, key=lambda x: x.pattern_date, reverse=True)[:3]
            for pattern in recent_patterns:
                print(f"      Latest: {pattern.pattern_date.date()} - {pattern.pattern_type} (Range: {pattern.current_range:.2f})")
            
            all_patterns.extend(patterns)
            total_patterns += len(patterns)
        else:
            print(f"   📝 No patterns detected")
    
    # Store patterns in database
    if all_patterns:
        print(f"\n💾 Storing {len(all_patterns)} patterns in database...")
        success = storage_service.store_patterns(all_patterns)
        
        if success:
            print("✅ Patterns stored successfully!")
            
            # Retrieve and verify storage
            stored_patterns = storage_service.get_patterns()
            print(f"📋 Total patterns in database: {len(stored_patterns)}")
        else:
            print("❌ Failed to store patterns")
    
    # Demo batch scanner
    print(f"\n🔍 Testing Batch Scanner (Limited Run)...")
    
    def progress_demo(processed, total, percentage, symbol):
        if processed % 5 == 0:  # Show progress every 5 symbols
            print(f"   Progress: {processed}/{total} ({percentage:.1f}%) - {symbol}")
    
    scanner = PatternScannerService(progress_callback=progress_demo)
    
    # Run a quick scan
    start_time = time.time()
    results = scanner.scan_all_symbols(
        start_date=end_date - timedelta(days=180),  # Last 6 months
        end_date=end_date,
        pattern_types=['NR4', 'NR7'],  # Limit to 2 pattern types for speed
        batch_size=20,  # Small batches
        max_workers=2   # Limited parallelism
    )
    end_time = time.time()
    
    # Report results
    print(f"\n📊 Batch Scan Results:")
    print(f"   ⏱️  Processing time: {end_time - start_time:.2f} seconds")
    print(f"   📈 Symbols processed: {results['processed']}")
    print(f"   🎯 Patterns found: {results['patterns_found']}")
    print(f"   ⚡ Processing speed: {results['processed']/(end_time - start_time):.1f} symbols/second")
    
    # GUI Information
    print(f"\n🖥️  GUI Usage:")
    print(f"   1. Run: python scanner_gui.py")
    print(f"   2. Navigate to '🕯️ Pattern Scanner' tab")
    print(f"   3. Configure date range and pattern types")
    print(f"   4. Click '🚀 Start Pattern Scan' for full analysis")
    print(f"   5. Use 'Scan Latest Only' for quick pattern check")
    
    # Pattern Analysis Summary
    print(f"\n📋 System Capabilities Summary:")
    print(f"   🎯 Pattern Types: NR4, NR7, NR13, NR21")
    print(f"   📊 Data Source: Monthly aggregated from daily bhavcopy")
    print(f"   🚀 Performance: High-performance batch processing")
    print(f"   💾 Storage: Persistent database with deduplication")
    print(f"   📈 Progress: Real-time progress tracking")
    print(f"   🖥️  Interface: Full GUI integration")
    print(f"   ⚡ Scalability: Multi-threaded processing")
    
    print(f"\n✅ Demo completed successfully!")
    print(f"🎉 Candlestick Pattern Detection System is ready for production use!")

if __name__ == "__main__":
    demo_pattern_detection()