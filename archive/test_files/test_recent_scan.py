#!/usr/bin/env python3
"""Test the date range scanning with a recent date that might not be processed yet."""

from datetime import date
from services.trends_service import scan_historical_trends_for_range, get_trend_analysis_for_range

def test_recent_date_range():
    """Test scanning a very recent date range."""
    print("Testing date range scanning...")
    
    # Try a date we know has trading data (from our earlier tests)
    start_date = date(2025, 11, 6)  # We know this date has data
    end_date = date(2025, 11, 6)
    
    print(f"Testing date range: {start_date} to {end_date}")
    
    try:
        # First check if there's existing data
        existing_df = get_trend_analysis_for_range(start_date, end_date)
        print(f"Existing data: {len(existing_df) if existing_df is not None else 0} records")
        
        # Try scanning (will skip if already processed)
        print(f"Attempting to scan range {start_date} to {end_date}...")
        results_df = scan_historical_trends_for_range(start_date, end_date)
        
        if results_df is not None and not results_df.empty:
            print(f"Scan completed: {len(results_df)} records found")
            print("\nSample results:")
            print(results_df.head(3).to_string(index=False))
        else:
            print("No results from scan (likely already processed or no trading data)")
            
    except Exception as e:
        print(f"Error during scan: {e}")

if __name__ == "__main__":
    test_recent_date_range()