"""Generate correct Nifty 50 symbol mapping from CSV."""

# Symbols from the latest Nifty 50 CSV (NSE trading data)
NIFTY50_SYMBOLS_FROM_CSV = [
    'ETERNAL', 'TATASTEEL', 'HINDALCO', 'SHRIRAMFIN', 'MARUTI',
    'KOTAKBANK', 'EICHERMOT', 'DRREDDY', 'JSWSTEEL', 'INFY',
    'CIPLA', 'ADANIENT', 'COALINDIA', 'WIPRO', 'HDFCBANK',
    'ADANIPORTS', 'BEL', 'JIOFIN', 'M&M', 'ONGC',
    'BAJAJ-AUTO', 'SBIN', 'ULTRACEMCO', 'LT', 'GRASIM',
    'APOLLOHOSP', 'HINDUNILVR', 'TMPV', 'NTPC', 'BAJFINANCE',
    'NESTLEIND', 'TECHM', 'AXISBANK', 'TATACONSUM', 'POWERGRID',
    'SUNPHARMA', 'BAJAJFINSV', 'ITC', 'RELIANCE', 'HCLTECH',
    'ICICIBANK', 'TCS', 'TRENT', 'BHARTIARTL', 'SBILIFE',
    'HDFCLIFE', 'ASIANPAINT', 'TITAN'
]

# Symbols found in NSE_EQ (46/50)
FOUND_IN_NSE_EQ = [
    'ETERNAL', 'TATASTEEL', 'HINDALCO', 'SHRIRAMFIN', 'MARUTI',
    'KOTAKBANK', 'EICHERMOT', 'DRREDDY', 'JSWSTEEL', 'INFY',
    'CIPLA', 'COALINDIA', 'WIPRO', 'HDFCBANK',
    'ADANIPORTS', 'BEL', 'JIOFIN', 'M&M', 'ONGC',
    'BAJAJ-AUTO', 'SBIN', 'ULTRACEMCO', 'LT', 'GRASIM',
    'APOLLOHOSP', 'HINDUNILVR', 'TMPV', 'NTPC', 'BAJFINANCE',
    'NESTLEIND', 'TECHM', 'AXISBANK', 'TATACONSUM', 'POWERGRID',
    'SUNPHARMA', 'BAJAJFINSV', 'ITC', 'RELIANCE', 'HCLTECH',
    'ICICIBANK', 'TCS', 'TRENT', 'BHARTIARTL', 'SBILIFE',
    'ASIANPAINT', 'TITAN'
]

# Only in BSE_EQ (2/50)
ONLY_IN_BSE_EQ = [
    'ADANIENT', 'HDFCLIFE'
]

print("=" * 60)
print("NIFTY 50 SYMBOL MAPPING")
print("=" * 60)
print(f"\nTotal symbols in CSV: {len(NIFTY50_SYMBOLS_FROM_CSV)}")
print(f"Found in NSE_EQ: {len(FOUND_IN_NSE_EQ)}")
print(f"Only in BSE_EQ: {len(ONLY_IN_BSE_EQ)}")

print("\n" + "=" * 60)
print("NIFTY50 SYMBOLS FOR NIFTY 50 TRACKING (50/50)")
print("=" * 60)
print("\nPython list format:")
print("[")
for i, sym in enumerate(NIFTY50_SYMBOLS_FROM_CSV):
    if i % 5 == 4:
        print(f"    '{sym}',")
    else:
        print(f"    '{sym}',", end=" ")
print("\n]")

print("\n" + "=" * 60)
print("RECOMMENDED ACTION")
print("=" * 60)
print("""
The market_breadth_chart.py currently uses get_nifty50_stocks() which queries
for NSE_EQ segment. However, ADANIENT and HDFCLIFE are only available in BSE_EQ
in the current database.

Options:
1. Use the 46 NSE_EQ symbols (current market data from Dhan for NSE)
2. Use a separate query that includes BSE_EQ for the 2 missing symbols
3. Update the database to include NSE_EQ versions of ADANIENT and HDFCLIFE

Current code will show 46 stocks. To show all 50, we need to handle the
2 BSE_EQ symbols separately or modify the query.
""")
