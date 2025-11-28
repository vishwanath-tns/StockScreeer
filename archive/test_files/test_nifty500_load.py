from nifty500_stocks_list import NIFTY_500_STOCKS

# Convert to Yahoo format
yahoo_symbols = [f"{symbol}.NS" for symbol in NIFTY_500_STOCKS]
yahoo_symbols.append('^NSEI')

print(f'\n=== Nifty 500 Symbols for Dashboard ===')
print(f'Total NSE symbols: {len(NIFTY_500_STOCKS)}')
print(f'Total Yahoo symbols (with NIFTY): {len(yahoo_symbols)}')
print(f'\nFirst 10 Yahoo symbols:')
for sym in yahoo_symbols[:10]:
    print(f'  {sym}')
print(f'\nLast 10 Yahoo symbols:')
for sym in yahoo_symbols[-10:]:
    print(f'  {sym}')
