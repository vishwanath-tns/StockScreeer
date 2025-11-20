"""
Quick Nifty 50 Momentum Scan - Fixed Version
============================================

Fixed version that focuses on properly saving momentum data to database
for all Nifty 50 stocks.
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict
import pandas as pd
import time

# Add current directory to Python path
sys.path.append('.')

# Import our momentum system
from services.momentum.momentum_calculator import MomentumCalculator, MomentumDuration
from services.momentum.momentum_reporting_service import (
    MomentumReportingService, ReportConfig, ReportType, ReportFormat
)

def quick_nifty50_scan():
    """Run a quick momentum scan for Nifty 50 stocks with proper data saving"""
    
    # Nifty 50 stocks (excluding TATAMOTORS - not available in our DB)
    nifty50_stocks = [
        'ADANIPORTS', 'ASIANPAINT', 'AXISBANK', 'BAJAJ-AUTO', 'BAJFINANCE',
        'BAJAJFINSV', 'BPCL', 'BHARTIARTL', 'BRITANNIA', 'CIPLA', 'COALINDIA',
        'DIVISLAB', 'DRREDDY', 'EICHERMOT', 'GRASIM', 'HCLTECH', 'HDFCBANK',
        'HDFCLIFE', 'HEROMOTOCO', 'HINDALCO', 'HINDUNILVR', 'ICICIBANK',
        'ITC', 'INDUSINDBK', 'INFY', 'JSWSTEEL', 'KOTAKBANK', 'LT', 'M&M',
        'MARUTI', 'NTPC', 'NESTLEIND', 'ONGC', 'POWERGRID', 'RELIANCE',
        'SBILIFE', 'SBIN', 'SUNPHARMA', 'TCS', 'TATACONSUM', 'TATASTEEL',
        'TECHM', 'TITAN', 'ULTRACEMCO', 'UPL', 'WIPRO'
    ]
    
    # Focus on key durations
    durations = [MomentumDuration.ONE_WEEK, MomentumDuration.ONE_MONTH]
    
    print(f"🚀 Quick Nifty 50 Momentum Scan")
    print(f"📊 Stocks: {len(nifty50_stocks)}")
    print(f"⏱️  Durations: {[d.value for d in durations]}")
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    calculator = MomentumCalculator()
    
    # Process in smaller batches to ensure data is saved properly
    batch_size = 5
    total_saved = 0
    
    for i in range(0, len(nifty50_stocks), batch_size):
        batch_stocks = nifty50_stocks[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(nifty50_stocks) + batch_size - 1) // batch_size
        
        print(f"\n📦 Processing batch {batch_num}/{total_batches}: {batch_stocks}")
        
        try:
            batch_results = calculator.calculate_momentum_batch(
                symbols=batch_stocks,
                durations=durations
            )
            
            # batch_results is a dict with symbol keys and lists of MomentumResult objects
            batch_saved = len(batch_results)
            total_saved += batch_saved
            
            print(f"✅ Batch {batch_num} completed: {batch_saved}/{len(batch_stocks)} stocks processed")
            
            # Show sample results
            for symbol, momentum_list in list(batch_results.items())[:2]:  # Show first 2 symbols
                if momentum_list:
                    for momentum in momentum_list[:1]:  # Show first duration
                        print(f"   💹 {symbol}: {momentum.percentage_change:.2f}% ({momentum.duration.value})")
                        
        except Exception as e:
            print(f"❌ Error processing batch {batch_num}: {e}")
            continue
            
        # Small delay to ensure database operations complete
        time.sleep(0.1)
    
    print(f"\n🎉 Quick Scan Complete!")
    print(f"✅ Processed: {total_saved} symbols")
    print(f"🕐 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return total_saved

def generate_quick_reports():
    """Generate quick reports for the momentum data"""
    
    print(f"\n📊 Generating Quick Momentum Reports")
    print("=" * 50)
    
    reporter = MomentumReportingService()
    
    # Market Summary
    config = ReportConfig(
        report_type=ReportType.MOMENTUM_SUMMARY,
        duration_types=[MomentumDuration.ONE_WEEK, MomentumDuration.ONE_MONTH]
    )
    
    try:
        report = reporter.generate_report(config)
        print(report)
    except Exception as e:
        print(f"❌ Error generating summary: {e}")
    
    # Top Performers
    config = ReportConfig(
        report_type=ReportType.TOP_PERFORMERS,
        duration_types=[MomentumDuration.ONE_WEEK, MomentumDuration.ONE_MONTH],
        top_n=20
    )
    
    try:
        report = reporter.generate_report(config)
        print(f"\n{report}")
    except Exception as e:
        print(f"❌ Error generating top performers: {e}")

def main():
    """Main execution"""
    
    print("🎯 NIFTY 50 QUICK MOMENTUM ANALYSIS")
    print("=" * 50)
    
    # Run the scan
    processed_count = quick_nifty50_scan()
    
    # Wait a moment for database operations to complete
    time.sleep(1)
    
    # Generate reports
    if processed_count > 0:
        generate_quick_reports()
    else:
        print("❌ No data processed, skipping reports")
    
    print(f"\n💡 Analysis complete! Check the database for {processed_count} symbols.")

if __name__ == "__main__":
    main()