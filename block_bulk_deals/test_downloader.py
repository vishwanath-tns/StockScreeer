"""Quick test of NSE deals downloader"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from block_bulk_deals.nse_deals_downloader import NSEDealsDownloader
from datetime import datetime

d = NSEDealsDownloader(rate_limit=2.0)

# Test with a recent date
date = datetime(2025, 11, 15)

print("Testing Block Deals for", date.strftime("%d-%b-%Y"))
df = d.download_block_deals(date)
print(f"Block Deals Result: {len(df) if df is not None else 'None'} records")
if df is not None and not df.empty:
    print(df.head())

print("\nTesting Bulk Deals for", date.strftime("%d-%b-%Y"))
df = d.download_bulk_deals(date)
print(f"Bulk Deals Result: {len(df) if df is not None else 'None'} records")
if df is not None and not df.empty:
    print(df.head())

d.close()
