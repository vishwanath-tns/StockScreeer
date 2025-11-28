from nifty500_stocks_list import NIFTY_500_STOCKS

print(f'Total stocks in NIFTY_500_STOCKS list: {len(NIFTY_500_STOCKS)}')

# Convert to Yahoo format
yahoo_symbols = [f'{s}.NS' for s in NIFTY_500_STOCKS]
print(f'After adding .NS suffix: {len(yahoo_symbols)}')

# Check for duplicates
unique = set(yahoo_symbols)
print(f'Unique symbols: {len(unique)}')

if len(yahoo_symbols) != len(unique):
    print(f'\n⚠️ Found {len(yahoo_symbols) - len(unique)} duplicates!')
    # Find duplicates
    seen = set()
    duplicates = []
    for sym in yahoo_symbols:
        if sym in seen:
            duplicates.append(sym)
        seen.add(sym)
    print(f'Duplicate symbols: {duplicates}')
else:
    print('✅ No duplicates found')

# Check what the dashboard actually loads
print('\n=== Simulating Dashboard Load ===')
yahoo_symbols_with_nifty = yahoo_symbols.copy()
if '^NSEI' not in yahoo_symbols_with_nifty:
    yahoo_symbols_with_nifty.append('^NSEI')

print(f'Total symbols for dashboard: {len(yahoo_symbols_with_nifty)}')
print(f'Expected: 501 (500 stocks + NIFTY)')
