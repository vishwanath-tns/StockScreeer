#!/usr/bin/env python3
"""
Test the new trend analysis features:
1. Stock-specific trend analysis
2. Date range scanning
"""

from datetime import date
from services.trends_service import get_stock_trend_analysis, get_trend_analysis_for_range

def test_stock_trend_analysis():
    """Test getting trend analysis for a specific stock."""
    print("Testing stock trend analysis...")
    
    # Test with a common stock symbol
    symbol = "RELIANCE"
    print(f"Getting trend analysis for {symbol}...")
    
    try:
        results_df = get_stock_trend_analysis(symbol)
        if results_df is not None and not results_df.empty:
            print(f"Found {len(results_df)} records for {symbol}")
            print("\nSample records:")
            print(results_df.head(3).to_string(index=False))
        else:
            print(f"No data found for {symbol}")
    except Exception as e:
        print(f"Error getting trend data for {symbol}: {e}")

def test_date_range_analysis():
    """Test getting trend analysis for a date range."""
    print("\n" + "="*50)
    print("Testing date range analysis...")
    
    # Test with a small date range from recent data
    start_date = date(2025, 11, 1)
    end_date = date(2025, 11, 10)
    
    print(f"Getting trend analysis from {start_date} to {end_date}...")
    
    try:
        results_df = get_trend_analysis_for_range(start_date, end_date)
        if results_df is not None and not results_df.empty:
            print(f"Found {len(results_df)} records in date range")
            print("\nSample records:")
            print(results_df.head(3).to_string(index=False))
            
            # Show unique symbols and dates
            unique_symbols = results_df['symbol'].nunique()
            unique_dates = results_df['trade_date'].nunique()
            print(f"\nUnique symbols: {unique_symbols}")
            print(f"Unique dates: {unique_dates}")
        else:
            print(f"No data found for date range {start_date} to {end_date}")
    except Exception as e:
        print(f"Error getting trend data for date range: {e}")

if __name__ == "__main__":
    test_stock_trend_analysis()
    test_date_range_analysis()
    print("\nTest completed!")