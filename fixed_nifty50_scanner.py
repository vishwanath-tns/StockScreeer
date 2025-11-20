"""
Fixed Complete Nifty 50 Momentum Scanner
=======================================

This uses the proven working approach from quick_nifty50_scan.py to populate
the database with momentum data for all Nifty 50 stocks.
"""

import sys
import os
from datetime import datetime
import time

sys.path.append('.')

# Import the working quick scan functionality
from services.momentum.momentum_calculator import MomentumCalculator, MomentumDuration
from services.market_breadth_service import get_engine
import pandas as pd

def run_complete_nifty50_scan():
    """Run complete momentum scan for all Nifty 50 stocks"""
    
    print("NIFTY 50 COMPLETE MOMENTUM DATABASE POPULATION")
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
    
    # Durations to calculate
    durations = [MomentumDuration.ONE_WEEK, MomentumDuration.ONE_MONTH]
    print(f"Calculating momentum for timeframes: {[d.value for d in durations]}")
    print("")
    
    # Split into smaller batches for reliability
    batch_size = 5
    batches = [nifty50_stocks[i:i+batch_size] for i in range(0, len(nifty50_stocks), batch_size)]
    
    print(f"Processing in {len(batches)} batches of {batch_size} stocks each")
    print("")
    
    total_successful = 0
    total_calculations = 0
    successful_stocks = []
    
    # Process each batch
    for batch_num, batch_stocks in enumerate(batches, 1):
        print(f"BATCH {batch_num}/{len(batches)}: Processing {len(batch_stocks)} stocks")
        print(f"Stocks: {', '.join(batch_stocks)}")
        
        # Process each duration
        for duration in durations:
            print(f"  Calculating {duration.value} momentum...")
            
            try:
                # Use the proven working batch calculation
                results = calculator.calculate_momentum_batch(batch_stocks, [duration])
                
                if results:
                    successful_count = len([r for r in results if r is not None])
                    print(f"    Success: {successful_count}/{len(batch_stocks)} stocks calculated")
                    total_calculations += successful_count
                    
                    # Track unique successful stocks
                    for result in results:
                        if result and hasattr(result, 'symbol'):
                            if result.symbol not in successful_stocks:
                                successful_stocks.append(result.symbol)
                                total_successful += 1
                else:
                    print(f"    No results returned")
                    
            except Exception as e:
                print(f"    Error: {e}")
        
        print(f"  Batch {batch_num} completed")
        print("")
        
        # Small delay between batches
        time.sleep(0.5)
    
    # Check database status
    print("VERIFYING DATABASE STATUS")
    print("=" * 30)
    
    try:
        engine = get_engine()
        
        with engine.connect() as conn:
            # Get today's records
            query = """
            SELECT COUNT(*) as total_records,
                   COUNT(DISTINCT symbol) as unique_symbols
            FROM momentum_analysis 
            WHERE DATE(calculation_date) = CURDATE()
            """
            
            stats = pd.read_sql(query, conn)
            total_records = stats.iloc[0]['total_records']
            unique_symbols = stats.iloc[0]['unique_symbols']
            
            print(f"Database records today: {total_records}")
            print(f"Unique symbols: {unique_symbols}")
            print(f"Expected maximum: {len(nifty50_stocks) * len(durations)} records")
            
            # Show sample of latest records
            sample_query = """
            SELECT symbol, duration_type, percentage_change, calculation_date
            FROM momentum_analysis 
            WHERE DATE(calculation_date) = CURDATE()
            ORDER BY calculation_date DESC, symbol
            LIMIT 10
            """
            
            sample_data = pd.read_sql(sample_query, conn)
            
            if len(sample_data) > 0:
                print(f"\nLatest database entries:")
                for _, row in sample_data.iterrows():
                    print(f"  {row['symbol']:12} | {row['duration_type']:2} | {row['percentage_change']:+.2f}%")
            
            # Check which stocks have data
            symbols_query = """
            SELECT DISTINCT symbol 
            FROM momentum_analysis 
            WHERE DATE(calculation_date) = CURDATE()
            ORDER BY symbol
            """
            
            symbols_with_data = pd.read_sql(symbols_query, conn)['symbol'].tolist()
            
            print(f"\nStocks with momentum data: {len(symbols_with_data)}")
            if symbols_with_data:
                print("Symbols with data:", ", ".join(symbols_with_data[:10]))
                if len(symbols_with_data) > 10:
                    print(f"... and {len(symbols_with_data) - 10} more")
            
            # Check missing stocks
            missing_stocks = [stock for stock in nifty50_stocks if stock not in symbols_with_data]
            
            if missing_stocks:
                print(f"\nStocks needing attention: {len(missing_stocks)}")
                print("Missing symbols:", ", ".join(missing_stocks[:10]))
                if len(missing_stocks) > 10:
                    print(f"... and {len(missing_stocks) - 10} more")
    
    except Exception as e:
        print(f"Error checking database: {e}")
    
    # Final summary
    print(f"\nFINAL SCAN SUMMARY")
    print("=" * 25)
    print(f"Total stocks processed: {len(nifty50_stocks)}")
    print(f"Successful calculations: {total_calculations}")
    print(f"Unique stocks with data: {len(successful_stocks)}")
    print(f"Completion rate: {len(successful_stocks)/len(nifty50_stocks)*100:.1f}%")
    print(f"Scan completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if len(successful_stocks) >= 40:
        print("SUCCESS: Excellent coverage achieved!")
    elif len(successful_stocks) >= 30:
        print("GOOD: Good coverage, some stocks may need attention")
    elif len(successful_stocks) >= 20:
        print("PARTIAL: Partial coverage achieved")
    else:
        print("LIMITED: Many stocks need attention")
    
    print(f"\nDatabase is now populated with momentum data.")
    print(f"You can run the report generator again to see updated results.")


if __name__ == "__main__":
    run_complete_nifty50_scan()