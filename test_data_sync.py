#!/usr/bin/env python3
"""Test script to verify data synchronization functionality."""

import datetime
from services.market_breadth_service import get_nifty_with_breadth_chart_data, get_engine
from sqlalchemy import text

def test_data_availability():
    """Check what data is available in the database."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # Check market breadth data range
        breadth_result = conn.execute(text("""
            SELECT MIN(trade_date) as earliest, MAX(trade_date) as latest, COUNT(*) as total 
            FROM trend_analysis WHERE trade_date IS NOT NULL
        """)).fetchall()
        
        print("Market Breadth Data:")
        if breadth_result:
            earliest, latest, total = breadth_result[0]
            print(f"  Range: {earliest} to {latest}")
            print(f"  Total records: {total:,}")
        else:
            print("  No data found")
        
        # Check Nifty data range
        nifty_result = conn.execute(text("""
            SELECT MIN(trade_date) as earliest, MAX(trade_date) as latest, COUNT(*) as total 
            FROM indices_daily WHERE index_name = 'NIFTY 50' AND trade_date IS NOT NULL
        """)).fetchall()
        
        print("\nNifty Data:")
        if nifty_result:
            earliest, latest, total = nifty_result[0]
            print(f"  Range: {earliest} to {latest}")
            print(f"  Total records: {total:,}")
        else:
            print("  No data found")

def test_synchronization():
    """Test data synchronization with a known date range."""
    # Use a date range that should have both datasets - June 2025 based on the data ranges
    start_date = datetime.date(2025, 6, 1)
    end_date = datetime.date(2025, 6, 30)
    
    print(f"\nTesting synchronization for {start_date} to {end_date}:")
    
    result = get_nifty_with_breadth_chart_data(start_date, end_date)
    
    nifty_data = result['nifty_data']
    breadth_data = result['breadth_data']
    combined_data = result['combined_data']
    
    print(f"  Nifty data: {len(nifty_data)} rows")
    print(f"  Breadth data: {len(breadth_data)} rows")
    print(f"  Combined data: {len(combined_data)} rows")
    
    if len(combined_data) > 0:
        if hasattr(combined_data.index, 'min'):
            print(f"  Combined date range: {combined_data.index.min()} to {combined_data.index.max()}")
        print("  Sample combined data:")
        print(combined_data.head())
        
        # Check if we have both nifty and breadth columns
        nifty_cols = [col for col in combined_data.columns if col in ['open', 'high', 'low', 'close']]
        breadth_cols = [col for col in combined_data.columns if col in ['bullish_count', 'bearish_count', 'neutral_count']]
        
        print(f"  Nifty columns present: {nifty_cols}")
        print(f"  Breadth columns present: {breadth_cols}")
    
    return result

if __name__ == "__main__":
    test_data_availability()
    test_synchronization()