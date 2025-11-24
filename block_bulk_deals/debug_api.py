"""Debug NSE API response structure"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from datetime import datetime
import json

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Referer': 'https://www.nseindia.com/market-data/bulk-block-deals'
})

# Get cookies
print("Getting cookies...")
session.get("https://www.nseindia.com")

date_str = "15-11-2025"

# Test Block Deals
print(f"\n=== Testing Block Deals API for {date_str} ===")
url = f"https://www.nseindia.com/api/block-deal?from={date_str}&to={date_str}"
print(f"URL: {url}")

response = session.get(url, timeout=10)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"Response type: {type(data)}")
    print(f"Response length: {len(data) if isinstance(data, (list, dict)) else 'N/A'}")
    print("\nSample data:")
    print(json.dumps(data if isinstance(data, list) else [data], indent=2)[:1000])

# Test Bulk Deals
print(f"\n=== Testing Bulk Deals API for {date_str} ===")
url = f"https://www.nseindia.com/api/bulk-deal?from={date_str}&to={date_str}"
print(f"URL: {url}")

response = session.get(url, timeout=10)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"Response type: {type(data)}")
    print(f"Response length: {len(data) if isinstance(data, (list, dict)) else 'N/A'}")
    print("\nSample data:")
    print(json.dumps(data if isinstance(data, list) else [data], indent=2)[:1000])
else:
    print(f"Error: {response.text[:500]}")
