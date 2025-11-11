"""
Test script to verify tooltip data access is working correctly.
This helps debug the actual data structure that tooltips are trying to access.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

import pandas as pd
from datetime import datetime, timedelta

# Import our modules
import reporting_adv_decl as rad
import sma50_scanner

def test_tooltip_data():
    """Test the data structure that tooltips are trying to access."""
    print("=== Testing Tooltip Data Access ===")
    
    # Get database connection
    engine = rad.engine()
    
    # Fetch recent SMA data (same as dashboard)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    
    print(f"Fetching SMA data from {start_date} to {end_date}...")
    sma_data = sma50_scanner.fetch_counts(engine, start=start_date, end=end_date)
    
    if sma_data.empty:
        print("❌ No SMA data found!")
        return
    
    print(f"✅ Loaded {len(sma_data)} days of SMA data")
    print(f"Columns: {list(sma_data.columns)}")
    
    # Test the data access pattern used in tooltips
    dates = sma_data['trade_date']
    
    print("\n=== Sample Data (First 3 rows) ===")
    for i in range(min(3, len(sma_data))):
        try:
            date_str = dates.iloc[i].strftime('%Y-%m-%d')
            above_count = int(sma_data['above_count'].iloc[i])
            below_count = int(sma_data['below_count'].iloc[i])
            pct_above = float(sma_data['pct_above'].iloc[i])
            total_count = int(sma_data['total_count'].iloc[i])
            
            print(f"Row {i}:")
            print(f"  Date: {date_str}")
            print(f"  Above 50 SMA: {above_count:,} stocks")
            print(f"  Below 50 SMA: {below_count:,} stocks") 
            print(f"  Percentage Above: {pct_above:.1f}%")
            print(f"  Total: {total_count:,} stocks")
            print()
            
        except Exception as e:
            print(f"❌ Error accessing row {i}: {e}")
    
    print("=== Sample Data (Last 3 rows) ===")
    for i in range(max(0, len(sma_data)-3), len(sma_data)):
        try:
            date_str = dates.iloc[i].strftime('%Y-%m-%d')
            above_count = int(sma_data['above_count'].iloc[i])
            below_count = int(sma_data['below_count'].iloc[i])
            pct_above = float(sma_data['pct_above'].iloc[i])
            total_count = int(sma_data['total_count'].iloc[i])
            
            print(f"Row {i}:")
            print(f"  Date: {date_str}")
            print(f"  Above 50 SMA: {above_count:,} stocks")
            print(f"  Below 50 SMA: {below_count:,} stocks") 
            print(f"  Percentage Above: {pct_above:.1f}%")
            print(f"  Total: {total_count:,} stocks")
            print()
            
        except Exception as e:
            print(f"❌ Error accessing row {i}: {e}")
    
    # Test data types
    print("=== Data Types ===")
    print(f"dates type: {type(dates)}")
    print(f"above_count type: {type(sma_data['above_count'])}")
    print(f"sample date type: {type(dates.iloc[0])}")
    print(f"sample count type: {type(sma_data['above_count'].iloc[0])}")
    
    print("\n✅ Tooltip data access test completed!")

if __name__ == "__main__":
    test_tooltip_data()