"""Debug NSE report download structure"""
import requests
import json

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Referer': 'https://www.nseindia.com/all-reports'
})

# Get cookies
print("Getting cookies from NSE...")
session.get("https://www.nseindia.com")

# Try the reports API
date_str = "21-Nov-2025"

print(f"\n=== Testing Reports API for {date_str} ===\n")

# Test different API endpoints
endpoints = [
    f"/api/reports?archives=%5B%7B%22name%22:%22CM%20-%20Bulk%20and%20block%20deals%22,%22type%22:%22block-deals%22,%22category%22:%22capital-market%22,%22section%22:%22equities%22%7D%5D&date={date_str}&type=block-deals&mode=single",
    f"/api/reports?archives=%5B%7B%22name%22:%22CM%20-%20Bulk%20and%20block%20deals%22,%22type%22:%22bulk-deals%22,%22category%22:%22capital-market%22,%22section%22:%22equities%22%7D%5D&date={date_str}&type=bulk-deals&mode=single",
    f"/archives/equities/mkt/block_deal_21112025.csv",
    f"/archives/equities/mkt/bulk_deal_21112025.csv",
    f"/archives/equities/block/block_deal_21112025.csv",
    f"/content/historical/EQUITIES/2025/NOV/block_deal_21112025.csv",
    f"/content/historical/EQUITIES/2025/NOV/bulk_deal_21112025.csv",
]

for endpoint in endpoints:
    url = f"https://www.nseindia.com{endpoint}"
    print(f"Trying: {endpoint[:80]}...")
    
    try:
        response = session.get(url, timeout=10)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            print(f"  Content-Type: {content_type}")
            print(f"  Content length: {len(response.content)} bytes")
            
            if 'json' in content_type:
                data = response.json()
                print(f"  JSON keys: {list(data.keys()) if isinstance(data, dict) else 'list'}")
            elif 'csv' in content_type or 'text' in content_type:
                print(f"  First 200 chars: {response.text[:200]}")
            
            print("  ✅ SUCCESS!")
            break
        else:
            print(f"  ❌ Failed")
            
    except Exception as e:
        print(f"  ❌ Error: {str(e)[:60]}")
    
    print()
