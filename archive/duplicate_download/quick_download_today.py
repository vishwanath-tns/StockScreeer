#!/usr/bin/env python3
"""
Quick script to run bulk stock downloader with today's date
"""
import sys
import os
from datetime import date, timedelta

# Add yahoo_finance_service to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'yahoo_finance_service'))

from bulk_stock_downloader import BulkStockDataDownloader

def main():
    print("🚀 Quick Bulk Download - Today's Data")
    print("=" * 60)
    
    # Use yesterday and today as date range
    end_date = date.today()
    start_date = end_date - timedelta(days=1)
    
    print(f"📅 Date range: {start_date} to {end_date}")
    print(f"📊 Downloading all verified symbols")
    print()
    
    downloader = BulkStockDataDownloader()
    
    try:
        stats = downloader.download_bulk_data(
            start_date=start_date,
            end_date=end_date,
            max_symbols=None  # Download all
        )
        
        print("\n" + "=" * 60)
        print("📊 Download Complete!")
        print("=" * 60)
        print(f"✅ Success: {stats.get('success', 0)}")
        print(f"❌ Failed: {stats.get('failed', 0)}")
        print(f"⏭️  Skipped: {stats.get('skipped', 0)}")
        print(f"⏱️  Total time: {stats.get('total_time', 0):.2f}s")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
