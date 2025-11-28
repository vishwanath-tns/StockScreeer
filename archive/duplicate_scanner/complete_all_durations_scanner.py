"""
Complete Nifty 50 All Durations Momentum Scanner
===============================================

This scanner calculates momentum for all 6 durations (1W, 1M, 3M, 6M, 9M, 12M)
to provide complete momentum analysis across all timeframes.
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

def run_complete_all_durations_scan():
    """Run complete momentum scan for all Nifty 50 stocks with all durations"""
    
    print("NIFTY 50 COMPLETE ALL DURATIONS MOMENTUM SCAN")
    print("=" * 60)
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
    
    # All durations to calculate
    durations = [
        MomentumDuration.ONE_WEEK,
        MomentumDuration.ONE_MONTH, 
        MomentumDuration.THREE_MONTHS,
        MomentumDuration.SIX_MONTHS,
        MomentumDuration.NINE_MONTHS,
        MomentumDuration.TWELVE_MONTHS
    ]
    print(f"Calculating momentum for timeframes: {[d.value for d in durations]}")
    print(f"Total calculations expected: {len(nifty50_stocks)} × {len(durations)} = {len(nifty50_stocks) * len(durations)}")
    print("")
    
    # Check current database status
    engine = get_engine()
    with engine.connect() as conn:
        check_query = text("""
            SELECT duration_type, COUNT(*) as count
            FROM momentum_analysis 
            WHERE DATE(calculation_date) = CURDATE()
            AND symbol IN ('AXISBANK', 'HDFCBANK', 'ICICIBANK', 'INDUSINDBK', 'KOTAKBANK', 'SBIN',
                          'BAJFINANCE', 'BAJAJFINSV', 'HDFCLIFE', 'SBILIFE',
                          'INFY', 'TCS', 'TECHM', 'HCLTECH', 'WIPRO',
                          'RELIANCE', 'ONGC', 'BPCL',
                          'TATASTEEL', 'JSWSTEEL', 'HINDALCO', 'COALINDIA',
                          'MARUTI', 'BAJAJ-AUTO', 'M&M', 'HEROMOTOCO', 'EICHERMOT',
                          'SUNPHARMA', 'DRREDDY', 'CIPLA', 'DIVISLAB',
                          'HINDUNILVR', 'BRITANNIA', 'NESTLEIND', 'ITC', 'TATACONSUM',
                          'BHARTIARTL', 'NTPC', 'POWERGRID', 'ULTRACEMCO', 'GRASIM',
                          'LT', 'ASIANPAINT', 'UPL', 'TITAN', 'ADANIPORTS')
            GROUP BY duration_type
            ORDER BY duration_type
        """)
        
        existing_data = conn.execute(check_query).fetchall()
        
        print("CURRENT DATABASE STATUS:")
        print("-" * 25)
        if existing_data:
            for duration, count in existing_data:
                print(f"  {duration:3}: {count:2} stocks")
            total_existing = sum(count for _, count in existing_data)
            print(f"  Total: {total_existing} records")
        else:
            print("  No data found for today")
        print("")
    
    # Calculate missing durations
    existing_durations = {duration for duration, _ in existing_data if _ > 40}  # Consider complete if >40 stocks
    missing_durations = [d for d in durations if d.value not in existing_durations]
    
    if not missing_durations:
        print("🎉 All durations already calculated! Database is complete.")
        return
    
    print(f"CALCULATING MISSING DURATIONS: {[d.value for d in missing_durations]}")
    print("")
    
    # Process in smaller batches for reliability
    batch_size = 6  # Smaller batches for longer duration calculations
    batches = [nifty50_stocks[i:i+batch_size] for i in range(0, len(nifty50_stocks), batch_size)]
    
    print(f"Processing in {len(batches)} batches of up to {batch_size} stocks each")
    print("")
    
    total_calculations = 0
    total_stored = 0
    successful_stocks = set()
    
    # Process each batch
    for batch_num, batch_stocks in enumerate(batches, 1):
        print(f"BATCH {batch_num}/{len(batches)}: Processing {len(batch_stocks)} stocks")
        print(f"Stocks: {', '.join(batch_stocks)}")
        
        try:
            # Calculate momentum for missing durations only
            print(f"  Calculating {len(missing_durations)} durations...")
            results = calculator.calculate_momentum_batch(
                symbols=batch_stocks,
                durations=missing_durations,
                max_workers=2  # Conservative for longer calculations
            )
            
            if results:
                # Count calculations
                calculation_count = sum(len(symbol_results) for symbol_results in results.values())
                total_calculations += calculation_count
                successful_stocks.update(results.keys())
                
                print(f"  ✅ Calculations: {calculation_count} momentum values for {len(results)} stocks")
                
                # Store results to database
                print(f"  💾 Storing to database...")
                stored_count = calculator.store_momentum_results(results)
                total_stored += stored_count
                
                print(f"  ✅ Storage: {stored_count} records stored")
                
                # Show sample results
                if results:
                    sample_symbol = list(results.keys())[0]
                    sample_results = results[sample_symbol]
                    if sample_results:
                        # Show a few samples
                        for i, sample in enumerate(sample_results[:2]):
                            print(f"  📊 Sample {i+1}: {sample.symbol} {sample.duration_type} = {sample.percentage_change:+.2f}%")
                
            else:
                print(f"  ❌ No calculation results returned")
                
        except Exception as e:
            print(f"  ❌ Batch {batch_num} error: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"  Batch {batch_num} completed")
        print("")
        
        # Delay between batches for longer calculations
        time.sleep(1.0)
    
    # Final verification
    print("FINAL DATABASE VERIFICATION")
    print("=" * 35)
    
    try:
        with engine.connect() as conn:
            # Check final status for all durations
            final_query = text("""
                SELECT duration_type, COUNT(*) as count
                FROM momentum_analysis 
                WHERE DATE(calculation_date) = CURDATE()
                AND symbol IN ('AXISBANK', 'HDFCBANK', 'ICICIBANK', 'INDUSINDBK', 'KOTAKBANK', 'SBIN',
                              'BAJFINANCE', 'BAJAJFINSV', 'HDFCLIFE', 'SBILIFE',
                              'INFY', 'TCS', 'TECHM', 'HCLTECH', 'WIPRO',
                              'RELIANCE', 'ONGC', 'BPCL',
                              'TATASTEEL', 'JSWSTEEL', 'HINDALCO', 'COALINDIA',
                              'MARUTI', 'BAJAJ-AUTO', 'M&M', 'HEROMOTOCO', 'EICHERMOT',
                              'SUNPHARMA', 'DRREDDY', 'CIPLA', 'DIVISLAB',
                              'HINDUNILVR', 'BRITANNIA', 'NESTLEIND', 'ITC', 'TATACONSUM',
                              'BHARTIARTL', 'NTPC', 'POWERGRID', 'ULTRACEMCO', 'GRASIM',
                              'LT', 'ASIANPAINT', 'UPL', 'TITAN', 'ADANIPORTS')
                GROUP BY duration_type
                ORDER BY duration_type
            """)
            
            final_data = conn.execute(final_query).fetchall()
            
            print("Final database status:")
            expected_per_duration = len(nifty50_stocks)
            total_final = 0
            
            for duration, count in final_data:
                coverage = count / expected_per_duration * 100
                status = "✅" if coverage >= 90 else "⚠️" if coverage >= 70 else "❌"
                print(f"  {duration:3}: {count:2}/{expected_per_duration} stocks ({coverage:5.1f}%) {status}")
                total_final += count
            
            print(f"  Total: {total_final} records")
            
            # Calculate completion rate
            max_possible = len(nifty50_stocks) * len(durations)
            completion_rate = total_final / max_possible * 100
            
            print(f"\n📊 COMPLETION SUMMARY:")
            print(f"  Calculations performed: {total_calculations}")
            print(f"  Records stored: {total_stored}")
            print(f"  Total records in DB: {total_final}/{max_possible}")
            print(f"  Overall completion: {completion_rate:.1f}%")
            
            if completion_rate >= 90:
                print("  🎉 EXCELLENT: Outstanding completion rate!")
            elif completion_rate >= 75:
                print("  ✅ VERY GOOD: High completion rate!")
            elif completion_rate >= 60:
                print("  👍 GOOD: Satisfactory completion!")
            else:
                print("  ⚠️ PARTIAL: Some durations need attention")
    
    except Exception as e:
        print(f"❌ Final verification error: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n🏁 All durations scan completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    print("🚀 DATABASE READY FOR COMPLETE MULTI-DURATION ANALYSIS!")
    print("   You can now generate reports with all 6 timeframes.")


if __name__ == "__main__":
    run_complete_all_durations_scan()