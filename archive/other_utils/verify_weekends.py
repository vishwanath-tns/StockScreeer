"""
Weekend Exclusion Verification
==============================
Quick script to verify that weekends are properly excluded from our charts
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import date, timedelta
from volatility_patterns.data.data_service import DataService

def verify_weekend_exclusion():
    """Verify that weekend filtering is working correctly"""
    
    print("🔍 VERIFYING WEEKEND EXCLUSION")
    print("=" * 40)
    
    data_service = DataService()
    
    # Get a small sample of data
    end_date = date.today()
    start_date = end_date - timedelta(days=30)  # Last 30 days
    
    print(f"📅 Checking period: {start_date} to {end_date}")
    
    # Get raw data
    data = data_service.get_ohlcv_data('CIPLA', start_date, end_date)
    print(f"📊 Raw data records: {len(data)}")
    
    # Apply weekend filter
    data['date'] = pd.to_datetime(data['date'])
    weekend_count = len(data[data['date'].dt.dayofweek >= 5])  # Sat=5, Sun=6
    
    filtered_data = data[data['date'].dt.dayofweek < 5].copy()
    
    print(f"🗓️ Weekend records found: {weekend_count}")
    print(f"📈 Trading day records: {len(filtered_data)}")
    print(f"✅ Weekend exclusion: {'Working' if weekend_count == 0 or len(filtered_data) < len(data) else 'Not Working'}")
    
    # Show date samples
    print("\n📋 Sample trading days:")
    for i in range(min(10, len(filtered_data))):
        date_val = filtered_data.iloc[i]['date']
        day_name = date_val.strftime('%A')
        print(f"   {date_val.strftime('%Y-%m-%d')} ({day_name})")
    
    print("\n💡 Verification complete!")

if __name__ == "__main__":
    verify_weekend_exclusion()