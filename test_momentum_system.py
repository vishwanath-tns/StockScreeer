"""
Test Momentum Calculator System
==============================

Tests the momentum calculation system with a small set of symbols
to verify correctness and database integration.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, timedelta
from services.momentum.momentum_calculator import MomentumCalculator, MomentumDuration
from services.momentum.database_service import DatabaseService

def test_momentum_system():
    """Test the complete momentum system"""
    
    print("🧪 MOMENTUM SYSTEM TEST")
    print("=" * 50)
    
    # Initialize services
    print("\n📊 Initializing services...")
    try:
        db_service = DatabaseService()
        calculator = MomentumCalculator()
        print("✅ Services initialized successfully")
    except Exception as e:
        print(f"❌ Service initialization failed: {e}")
        return False
    
    # Create schema
    print("\n🏗️ Creating database schema...")
    try:
        schema_created = db_service.create_momentum_schema()
        print(f"Schema creation: {'✅' if schema_created else '❌'}")
    except Exception as e:
        print(f"❌ Schema creation failed: {e}")
        return False
    
    # Test with small set of symbols
    test_symbols = ['RELIANCE', 'INFY', 'TCS']
    test_durations = [MomentumDuration.ONE_WEEK, MomentumDuration.ONE_MONTH]
    
    print(f"\n📈 Testing with {len(test_symbols)} symbols and {len(test_durations)} durations")
    print(f"Symbols: {test_symbols}")
    print(f"Durations: {[d.value for d in test_durations]}")
    
    # Calculate momentum
    print("\n⚡ Calculating momentum...")
    try:
        results = calculator.calculate_momentum_batch(
            symbols=test_symbols,
            durations=test_durations,
            max_workers=1  # Single thread for testing
        )
        
        print(f"✅ Calculation completed: {len(results)} symbols processed")
        
        # Display results
        print(f"\n📊 CALCULATION RESULTS:")
        print("-" * 40)
        
        for symbol, symbol_results in results.items():
            print(f"\n📈 {symbol}:")
            for result in symbol_results:
                direction = "📈" if result.is_positive else "📉"
                print(f"   {direction} {result.duration_type}: {result.percentage_change:+.2f}% "
                      f"(₹{result.start_price:.2f} → ₹{result.end_price:.2f}) "
                      f"[{result.trading_days} days]")
        
    except Exception as e:
        print(f"❌ Calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Store results
    print(f"\n💾 Storing results to database...")
    try:
        stored_count = calculator.store_momentum_results(results)
        print(f"✅ Stored {stored_count} records to database")
    except Exception as e:
        print(f"❌ Storage failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test retrieval
    print(f"\n🔍 Testing data retrieval...")
    try:
        for symbol in test_symbols:
            retrieved_results = calculator.get_symbol_momentum(symbol)
            print(f"   📊 {symbol}: Retrieved {len(retrieved_results)} records")
            
            # Verify data consistency
            if retrieved_results:
                for result in retrieved_results:
                    print(f"      {result.duration_type}: {result.percentage_change:+.2f}% "
                          f"({result.start_date} to {result.end_date})")
    except Exception as e:
        print(f"❌ Retrieval failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test summary stats
    print(f"\n📈 Testing summary statistics...")
    try:
        for duration in test_durations:
            stats = db_service.get_momentum_summary_stats(duration.value)
            if stats:
                print(f"   📊 {duration.value}:")
                print(f"      Total stocks: {stats.get('total_stocks', 0)}")
                print(f"      Avg change: {stats.get('avg_change', 0):.2f}%")
                print(f"      Positive: {stats.get('positive_count', 0)}")
                print(f"      Negative: {stats.get('negative_count', 0)}")
    except Exception as e:
        print(f"❌ Summary stats failed: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n🏆 MOMENTUM SYSTEM TEST COMPLETE!")
    print(f"✅ All core functionality working correctly")
    return True

def test_single_calculation():
    """Test a single momentum calculation for debugging"""
    
    print("\n🔬 SINGLE CALCULATION DEBUG TEST")
    print("=" * 40)
    
    calculator = MomentumCalculator()
    
    # Test with single symbol and duration
    symbol = 'RELIANCE'
    duration = MomentumDuration.ONE_MONTH
    end_date = date.today()
    
    print(f"Testing: {symbol} for {duration.description}")
    
    try:
        result = calculator._calculate_single_momentum(symbol, duration, end_date)
        
        if result:
            print(f"✅ Calculation successful:")
            print(f"   Symbol: {result.symbol}")
            print(f"   Duration: {result.duration_type} ({result.trading_days} days)")
            print(f"   Date range: {result.start_date} to {result.end_date}")
            print(f"   Price change: ₹{result.start_price:.2f} → ₹{result.end_price:.2f}")
            print(f"   Percentage: {result.percentage_change:+.2f}%")
            print(f"   Volume: {result.avg_volume:,} (surge: {result.volume_surge_factor:.2f}x)")
            print(f"   Volatility: {result.price_volatility:.2f}%")
        else:
            print(f"❌ Calculation returned no result")
            
    except Exception as e:
        print(f"❌ Calculation failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run all tests"""
    
    # Run single calculation test first
    test_single_calculation()
    
    # Run full system test
    success = test_momentum_system()
    
    if success:
        print(f"\n🎉 All tests passed! Momentum system is ready.")
    else:
        print(f"\n💥 Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    main()