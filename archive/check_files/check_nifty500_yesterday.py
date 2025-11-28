import os
from dotenv import load_dotenv
import mysql.connector
from nifty500_stocks_list import NIFTY_500_STOCKS
from datetime import date, timedelta

load_dotenv()

conn = mysql.connector.connect(
    host=os.getenv('MYSQL_HOST', 'localhost'),
    port=int(os.getenv('MYSQL_PORT', 3306)),
    user=os.getenv('MYSQL_USER', 'root'),
    password=os.getenv('MYSQL_PASSWORD', ''),
    database='marketdata'
)

cursor = conn.cursor()

# Get yesterday's date
yesterday = date.today() - timedelta(days=1)
print(f'Checking data for: {yesterday}')

# Convert to Yahoo format
yahoo_symbols = [f"{symbol}.NS" for symbol in NIFTY_500_STOCKS]

# Check which symbols have data for yesterday
symbols_tuple = tuple(yahoo_symbols)
query = f"""
    SELECT symbol, close, date
    FROM yfinance_daily_quotes
    WHERE symbol IN ({','.join(['%s'] * len(symbols_tuple))})
    AND date = %s
"""

cursor.execute(query, symbols_tuple + (yesterday,))
results = cursor.fetchall()

symbols_with_data = {row[0] for row in results}
missing_symbols = [s for s in yahoo_symbols if s not in symbols_with_data]

print(f'\n=== Nifty 500 Coverage for {yesterday} ===')
print(f'Total Nifty 500: {len(NIFTY_500_STOCKS)}')
print(f'With data: {len(results)}')
print(f'Missing: {len(missing_symbols)}')
print(f'Coverage: {len(results)/len(NIFTY_500_STOCKS)*100:.1f}%')

# Check if missing symbols exist with different dates or not at all
print(f'\n=== Status of Missing Symbols ===')
never_downloaded = []
outdated = []

for sym in missing_symbols[:50]:  # Check first 50
    cursor.execute('SELECT COUNT(*), MAX(date) FROM yfinance_daily_quotes WHERE symbol = %s', (sym,))
    count, max_date = cursor.fetchone()
    
    if count == 0:
        never_downloaded.append(sym.replace('.NS', ''))
    else:
        outdated.append((sym.replace('.NS', ''), max_date))

print(f'\nNever downloaded ({len(never_downloaded)} symbols):')
for sym in never_downloaded[:20]:
    print(f'  {sym}')

print(f'\nOutdated ({len(outdated)} symbols):')
for sym, last_date in outdated[:20]:
    print(f'  {sym:15} - last: {last_date}')

print(f'\n=== SOLUTION ===')
print(f'Run the Nifty 500 bulk downloader to get all missing data:')
print(f'  python download_nifty500_bulk.py')

conn.close()
