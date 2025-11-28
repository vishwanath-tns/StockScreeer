#!/usr/bin/env python3
"""
Nifty 500 Momentum Scanner
==========================

Comprehensive momentum analysis for all Nifty 500 equivalent stocks.
Calculates momentum across multiple timeframes and provides detailed reports.
"""

import sys
import os
sys.path.append('.')

from datetime import datetime
from services.momentum.momentum_calculator import MomentumCalculator, MomentumDuration
from nifty500_stocks_list import NIFTY_500_STOCKS
import time

def run_nifty500_momentum_scan():
    """Run complete momentum scan for all Nifty 500 stocks"""
    
    print("=" * 80)
    print("[*] NIFTY 500 COMPREHENSIVE MOMENTUM ANALYSIS")
    print("=" * 50)
    print(f"[*] Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[*] Total stocks to process: {len(NIFTY_500_STOCKS)}")
    print("")
    
    # Initialize calculator
    calculator = MomentumCalculator()
    
    # All available momentum durations
    all_durations = [
        MomentumDuration.ONE_WEEK,
        MomentumDuration.ONE_MONTH,
        MomentumDuration.THREE_MONTHS,
        MomentumDuration.SIX_MONTHS,
        MomentumDuration.NINE_MONTHS,
        MomentumDuration.TWELVE_MONTHS
    ]
    
    print(f"[*] Calculating momentum for timeframes: {[d.value for d in all_durations]}")
    print("")
    
    # Process in manageable batches
    batch_size = 25  # Smaller batches for Nifty 500
    batches = [NIFTY_500_STOCKS[i:i+batch_size] for i in range(0, len(NIFTY_500_STOCKS), batch_size)]
    
    print(f"[*] Processing in {len(batches)} batches of up to {batch_size} stocks each")
    print("")
    
    total_successful_calculations = 0
    total_stored_records = 0
    successful_stocks = set()
    failed_stocks = []
    
    # Process each batch
    for batch_num, batch_stocks in enumerate(batches, 1):
        print(f"[BATCH] {batch_num}/{len(batches)}: Processing {len(batch_stocks)} stocks")
        print(f"   Stocks: {', '.join(batch_stocks[:5])}{'...' if len(batch_stocks) > 5 else ''}")
        
        try:
            # Calculate momentum for this batch
            print(f"   [*] Calculating momentum...")
            batch_results = calculator.calculate_momentum_batch(batch_stocks, all_durations)
            
            if batch_results:
                # Count successful calculations
                batch_calculations = sum(len(stock_results) for stock_results in batch_results.values())
                total_successful_calculations += batch_calculations
                successful_stocks.update(batch_results.keys())
                
                print(f"   [OK] Calculated {batch_calculations} momentum values")
                
                # Store results
                print(f"   [SAVE] Storing results to database...")
                stored_count = calculator.store_momentum_results(batch_results)
                total_stored_records += stored_count
                
                print(f"   [OK] Stored {stored_count} records")
                
                # Show sample results
                if batch_results:
                    sample_symbol = list(batch_results.keys())[0]
                    sample_results = batch_results[sample_symbol]
                    if sample_results:
                        print(f"   [SAMPLE] ({sample_symbol}): {sample_results[0].duration_type} = {sample_results[0].percentage_change:+.2f}%")
            else:
                print(f"   [ERROR] No results for this batch")
                failed_stocks.extend(batch_stocks)
                
        except Exception as e:
            print(f"   [ERROR] Error processing batch {batch_num}: {e}")
            failed_stocks.extend(batch_stocks)
        
        print(f"   [TIME] Batch completed in {time.time():.1f}s")
        print("")
        
        # Brief pause to avoid overwhelming the database
        time.sleep(1)
    
    # Summary
    print("=" * 80)
    print("[SUMMARY] NIFTY 500 MOMENTUM SCAN SUMMARY")
    print("=" * 50)
    print(f"[OK] Total successful calculations: {total_successful_calculations}")
    print(f"[SAVE] Total records stored: {total_stored_records}")
    print(f"[*] Successful stocks: {len(successful_stocks)}")
    print(f"[ERROR] Failed stocks: {len(failed_stocks)}")
    print(f"[*] Success rate: {len(successful_stocks)/len(NIFTY_500_STOCKS)*100:.1f}%")
    print("")
    
    if failed_stocks:
        print(f"[WARNING] Failed stocks ({len(failed_stocks)}): {', '.join(failed_stocks[:10])}{'...' if len(failed_stocks) > 10 else ''}")
        print("")
    
    # Expected records calculation
    expected_records = len(NIFTY_500_STOCKS) * len(all_durations)
    completion_percentage = (total_stored_records / expected_records) * 100 if expected_records > 0 else 0
    
    print(f"[TARGET] Expected total records: {expected_records}")
    print(f"[*] Completion: {completion_percentage:.1f}%")
    
    if completion_percentage >= 90:
        print("[SUCCESS] Excellent! Nifty 500 momentum data is comprehensive")
    elif completion_percentage >= 70:
        print("[OK] Good coverage achieved for Nifty 500")
    else:
        print("[WARNING] More data collection needed")
    
    print("")
    print(f"[COMPLETE] Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    return {
        'total_calculations': total_successful_calculations,
        'total_stored': total_stored_records,
        'successful_stocks': len(successful_stocks),
        'failed_stocks': len(failed_stocks),
        'success_rate': len(successful_stocks)/len(NIFTY_500_STOCKS)*100,
        'completion_percentage': completion_percentage
    }

def quick_nifty500_momentum_sample():
    """Quick momentum calculation for a sample of Nifty 500 stocks"""
    
    print("[SAMPLE] QUICK NIFTY 500 MOMENTUM SAMPLE")
    print("=" * 50)
    
    # Take top 50 most active stocks
    sample_stocks = NIFTY_500_STOCKS[:50]
    print(f"[*] Analyzing top {len(sample_stocks)} most active stocks")
    print(f"[TARGET] Stocks: {', '.join(sample_stocks[:10])}...")
    print("")
    
    calculator = MomentumCalculator()
    durations = [MomentumDuration.ONE_WEEK, MomentumDuration.ONE_MONTH]
    
    try:
        results = calculator.calculate_momentum_batch(sample_stocks, durations)
        
        if results:
            total_calcs = sum(len(stock_results) for stock_results in results.values())
            print(f"[OK] Calculated {total_calcs} momentum values")
            
            # Store results
            stored_count = calculator.store_momentum_results(results)
            print(f"[SAVE] Stored {stored_count} records")
            
            # Show top performers
            print("\n[*] TOP PERFORMERS (1W Momentum):")
            print("-" * 40)
            
            week_performers = []
            for symbol, stock_results in results.items():
                for result in stock_results:
                    if result.duration_type == MomentumDuration.ONE_WEEK.value:
                        week_performers.append((symbol, result.percentage_change))
            
            week_performers.sort(key=lambda x: x[1], reverse=True)
            
            for i, (symbol, pct) in enumerate(week_performers[:10]):
                print(f"{i+1:2d}. {symbol:<12} {pct:+6.2f}%")
            
            print("\n[TARGET] Sample analysis completed!")
            return True
            
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False

if __name__ == "__main__":
    # Choose scan type based on command line argument
    if len(sys.argv) > 1 and sys.argv[1] == "sample":
        quick_nifty500_momentum_sample()
    else:
        run_nifty500_momentum_scan()