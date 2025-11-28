import os
from dotenv import load_dotenv
import mysql.connector
from nifty500_stocks_list import NIFTY_500_STOCKS

load_dotenv()

conn = mysql.connector.connect(
    host=os.getenv('MYSQL_HOST', 'localhost'),
    port=int(os.getenv('MYSQL_PORT', 3306)),
    user=os.getenv('MYSQL_USER', 'root'),
    password=os.getenv('MYSQL_PASSWORD', ''),
    database='marketdata'
)

cursor = conn.cursor()

print(f'\n=== Checking Previous Close Coverage for Nifty 500 ===')
print(f'Total Nifty 500 stocks: {len(NIFTY_500_STOCKS)}')

# Convert to Yahoo format
yahoo_symbols = [f"{symbol}.NS" for symbol in NIFTY_500_STOCKS]

# Get the most recent date before today
cursor.execute("""
    SELECT MAX(date) 
    FROM yfinance_daily_quotes 
    WHERE date < CURDATE()
""")
prev_date = cursor.fetchone()[0]
print(f'Previous trading date: {prev_date}')

# Check how many symbols have data for that date
symbols_tuple = tuple(yahoo_symbols)
query = f"""
    SELECT symbol, close
    FROM yfinance_daily_quotes
    WHERE symbol IN ({','.join(['%s'] * len(symbols_tuple))})
    AND date = %s
"""

cursor.execute(query, symbols_tuple + (prev_date,))
results = cursor.fetchall()

print(f'\n=== Results ===')
print(f'Symbols with previous close data: {len(results)} / {len(yahoo_symbols)}')
print(f'Missing: {len(yahoo_symbols) - len(results)} symbols')
print(f'Coverage: {len(results)/len(yahoo_symbols)*100:.1f}%')

# Find missing symbols
symbols_with_data = {row[0] for row in results}
missing_symbols = [s for s in yahoo_symbols if s not in symbols_with_data]

print(f'\n=== First 20 Missing Symbols ===')
for sym in missing_symbols[:20]:
    # Remove .NS to show NSE symbol
    nse_symbol = sym.replace('.NS', '')
    # Check if symbol has ANY data
    cursor.execute('SELECT COUNT(*), MAX(date) FROM yfinance_daily_quotes WHERE symbol = %s', (sym,))
    count, max_date = cursor.fetchone()
    if count > 0:
        print(f'  {nse_symbol:15} - Has {count} records, latest: {max_date} (not updated for prev date)')
    else:
        print(f'  {nse_symbol:15} - NO DATA AT ALL')

# Check if these symbols exist without .NS suffix
print(f'\n=== Checking Alternative Symbol Formats ===')
alternative_found = 0
for sym in missing_symbols[:10]:
    nse_symbol = sym.replace('.NS', '')
    cursor.execute('SELECT COUNT(*) FROM yfinance_daily_quotes WHERE symbol = %s AND date = %s', (nse_symbol, prev_date))
    count = cursor.fetchone()[0]
    if count > 0:
        print(f'  ✅ {nse_symbol} exists WITHOUT .NS suffix!')
        alternative_found += 1

if alternative_found > 0:
    print(f'\n⚠️ Found {alternative_found} symbols stored without .NS suffix!')
    print(f'The dashboard needs to handle both formats.')

conn.close()
