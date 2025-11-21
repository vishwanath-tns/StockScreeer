#!/usr/bin/env python3
"""
Simple test to verify Yahoo Finance connectivity and data access
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def test_yfinance_connectivity():
    """Test basic Yahoo Finance connectivity"""
    print("🧪 Testing Basic Yahoo Finance Connectivity")
    print("=" * 50)
    
    # Test symbols
    symbols = ['RELIANCE.NS', 'TCS.NS', 'INFY.NS']
    
    # Date range - last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    print(f"📅 Test Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print()
    
    for symbol in symbols:
        try:
            print(f"📊 Testing {symbol}...")
            
            # Create ticker object
            ticker = yf.Ticker(symbol)
            
            # Download data
            data = ticker.history(start=start_date, end=end_date)
            
            if not data.empty:
                print(f"✅ {symbol}: {len(data)} records downloaded")
                print(f"   Columns: {list(data.columns)}")
                print(f"   Last close: ₹{data['Close'].iloc[-1]:.2f}")
                print(f"   Date range: {data.index[0].strftime('%Y-%m-%d')} to {data.index[-1].strftime('%Y-%m-%d')}")
            else:
                print(f"❌ {symbol}: No data returned")
                
        except Exception as e:
            print(f"❌ {symbol}: Error - {e}")
        
        print()
    
    print("🔍 Testing 5-year data for RELIANCE.NS...")
    try:
        end_date_5y = datetime.now()
        start_date_5y = end_date_5y - timedelta(days=5*365)
        
        ticker = yf.Ticker('RELIANCE.NS')
        data_5y = ticker.history(start=start_date_5y, end=end_date_5y)
        
        if not data_5y.empty:
            print(f"✅ 5-year RELIANCE.NS: {len(data_5y)} records")
            print(f"   Data range: {data_5y.index[0].strftime('%Y-%m-%d')} to {data_5y.index[-1].strftime('%Y-%m-%d')}")
            print(f"   Sample data columns: {list(data_5y.columns)}")
            print(f"   First close: ₹{data_5y['Close'].iloc[0]:.2f}")
            print(f"   Last close: ₹{data_5y['Close'].iloc[-1]:.2f}")
        else:
            print("❌ No 5-year data available")
            
    except Exception as e:
        print(f"❌ 5-year test failed: {e}")

if __name__ == "__main__":
    test_yfinance_connectivity()