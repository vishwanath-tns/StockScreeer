"""Test NSE CSV downloader with real URLs"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from block_bulk_deals.nse_deals_csv_downloader import NSEDealsCSVDownloader
from datetime import datetime

downloader = NSEDealsCSVDownloader(rate_limit=2.0)

# Test with 21-Nov-2025 (we have sample CSVs for this date)
date = datetime(2025, 11, 21)

print("=" * 80)
print(f"Testing CSV Download for {date.strftime('%d-%b-%Y')}")
print("=" * 80)

# Test Block Deals
print("\n📊 BLOCK DEALS:")
print("-" * 80)
df = downloader.download_block_deals(date)
if df is not None:
    print(f"✅ Downloaded {len(df)} records")
    if not df.empty:
        print("\nSample records:")
        print(df.head())
        print("\nColumns:", df.columns.tolist())
        print("\nData types:")
        print(df.dtypes)
else:
    print("❌ Download failed")

# Test Bulk Deals
print("\n📊 BULK DEALS:")
print("-" * 80)
df = downloader.download_bulk_deals(date)
if df is not None:
    print(f"✅ Downloaded {len(df)} records")
    if not df.empty:
        print("\nSample records:")
        print(df.head())
        print("\nColumns:", df.columns.tolist())
else:
    print("❌ Download failed")

downloader.close()

print("\n" + "=" * 80)
print("Test Complete!")
print("=" * 80)
