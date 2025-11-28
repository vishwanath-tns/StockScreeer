"""
Fixed Complete Nifty 50 Momentum Scanner with Proper Storage
===========================================================

This version properly stores the calculated momentum data to the database.
"""

import sys
import os
from datetime import datetime
import time

sys.path.append('.')

from services.momentum.momentum_calculator import MomentumCalculator, MomentumDuration
from services.market_breadth_service import get_engine
from sqlalchemy import text
import pandas as pd

def run_complete_nifty50_scan_with_storage():
    """Run complete momentum scan for all Nifty 50 stocks with proper storage"""
    
    print("NIFTY 50 COMPLETE MOMENTUM DATABASE POPULATION (WITH STORAGE)")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    
    # Complete Nifty 50 list
    nifty50_stocks = [
        # Banking (6)
        'AXISBANK', 'HDFCBANK', 'ICICIBANK', 'INDUSINDBK', 'KOTAKBANK', 'SBIN',
        
        # Financial Services (4)
        'BAJFINANCE', 'BAJAJFINSV', 'HDFCLIFE', 'SBILIFE',
        
        # IT Services (5)
        'INFY', 'TCS', 'TECHM', 'HCLTECH', 'WIPRO',
        
        # Oil & Gas (3)
        'RELIANCE', 'ONGC', 'BPCL',
        
        # Metals & Mining (4)
        'TATASTEEL', 'JSWSTEEL', 'HINDALCO', 'COALINDIA',
        
        # Automotive (5)
        'MARUTI', 'BAJAJ-AUTO', 'M&M', 'HEROMOTOCO', 'EICHERMOT',
        
        # Pharmaceuticals (4)
        'SUNPHARMA', 'DRREDDY', 'CIPLA', 'DIVISLAB',
        
        # FMCG (5)
        'HINDUNILVR', 'BRITANNIA', 'NESTLEIND', 'ITC', 'TATACONSUM',
        
        # Others (14)
        'BHARTIARTL', 'NTPC', 'POWERGRID', 'ULTRACEMCO', 'GRASIM',
        'LT', 'ASIANPAINT', 'UPL', 'TITAN', 'ADANIPORTS'
    ]
    
    print(f"Total Nifty 50 stocks to process: {len(nifty50_stocks)}")
    print("")
    
    # Initialize calculator
    calculator = MomentumCalculator()
    
    # Durations to calculate
    durations = [MomentumDuration.ONE_WEEK, MomentumDuration.ONE_MONTH]
    print(f"Calculating momentum for timeframes: {[d.value for d in durations]}")
    print("")
    
    # Process in smaller batches for more reliable storage
    batch_size = 8  # Smaller batches for better error handling
    batches = [nifty50_stocks[i:i+batch_size] for i in range(0, len(nifty50_stocks), batch_size)]
    
    print(f"Processing in {len(batches)} batches of up to {batch_size} stocks each")
    print("")
    
    total_successful_calculations = 0
    total_stored_records = 0
    successful_stocks = set()
    
    # Process each batch
    for batch_num, batch_stocks in enumerate(batches, 1):
        print(f"BATCH {batch_num}/{len(batches)}: Processing {len(batch_stocks)} stocks")
        print(f"Stocks: {', '.join(batch_stocks)}")
        
        try:
            # Calculate momentum for this batch
            print(f"  Calculating momentum...")
            results = calculator.calculate_momentum_batch(
                symbols=batch_stocks,
                durations=durations,
                max_workers=3  # Conservative threading
            )
            
            if results:
                # Count calculations
                calculation_count = sum(len(symbol_results) for symbol_results in results.values())
                total_successful_calculations += calculation_count
                successful_stocks.update(results.keys())
                
                print(f"  ✅ Calculations: {calculation_count} momentum values for {len(results)} stocks")
                
                # Store results to database
                print(f"  💾 Storing to database...")
                stored_count = calculator.store_momentum_results(results)
                total_stored_records += stored_count
                
                print(f"  ✅ Storage: {stored_count} records stored")
                
                # Show sample results
                if results:
                    sample_symbol = list(results.keys())[0]
                    sample_results = results[sample_symbol]
                    if sample_results:
                        sample = sample_results[0]
                        print(f"  📊 Sample: {sample.symbol} {sample.duration_type} = {sample.percentage_change:+.2f}%")
                
            else:
                print(f"  ❌ No calculation results returned")
                
        except Exception as e:
            print(f"  ❌ Batch {batch_num} error: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"  Batch {batch_num} completed")
        print("")
        
        # Small delay between batches
        time.sleep(0.5)
    
    # Verify final database status
    print("VERIFYING FINAL DATABASE STATUS")
    print("=" * 40)
    
    try:
        engine = get_engine()
        
        with engine.connect() as conn:
            # Check today's records
            today_query = text("""
                SELECT COUNT(*) as total_records,
                       COUNT(DISTINCT symbol) as unique_symbols
                FROM momentum_analysis 
                WHERE DATE(calculation_date) = CURDATE()
            """)
            
            stats = conn.execute(today_query).fetchone()
            total_records = stats[0]
            unique_symbols = stats[1]
            
            print(f"Final database status:")
            print(f"  Records inserted today: {total_records}")
            print(f"  Unique symbols with data: {unique_symbols}")
            print(f"  Expected maximum: {len(nifty50_stocks) * len(durations)} records")
            
            # Show recent sample
            sample_query = text("""
                SELECT symbol, duration_type, percentage_change, calculation_date
                FROM momentum_analysis 
                WHERE DATE(calculation_date) = CURDATE()
                ORDER BY calculation_date DESC, symbol
                LIMIT 10
            """)
            
            sample_data = conn.execute(sample_query).fetchall()
            
            if sample_data:
                print(f"\n📊 Recent database entries:")
                for row in sample_data:
                    symbol, duration, pct_change, calc_date = row
                    print(f"  {symbol:12} | {duration:2} | {pct_change:+.2f}% | {calc_date}")
            
            # Success assessment
            coverage_rate = unique_symbols / len(nifty50_stocks) * 100
            print(f"\n📈 FINAL ASSESSMENT:")
            print(f"  Total calculations performed: {total_successful_calculations}")
            print(f"  Total records stored: {total_stored_records}")
            print(f"  Unique stocks with data: {unique_symbols}/{len(nifty50_stocks)}")
            print(f"  Coverage rate: {coverage_rate:.1f}%")
            
            if coverage_rate >= 90:
                print("  🎉 EXCELLENT: Outstanding coverage achieved!")
            elif coverage_rate >= 75:
                print("  ✅ VERY GOOD: High coverage achieved!")
            elif coverage_rate >= 60:
                print("  👍 GOOD: Satisfactory coverage achieved!")
            elif coverage_rate >= 40:
                print("  ⚠️  PARTIAL: Partial coverage, some stocks need attention")
            else:
                print("  ❌ LIMITED: Many stocks need attention")
    
    except Exception as e:
        print(f"❌ Database verification error: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n🏁 Scan completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    print("🚀 DATABASE READY FOR REPORTING!")
    print("   You can now run the sector report again to see comprehensive data.")


if __name__ == "__main__":
    run_complete_nifty50_scan_with_storage()