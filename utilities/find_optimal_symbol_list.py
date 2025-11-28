import os
from dotenv import load_dotenv
import mysql.connector

load_dotenv()

conn = mysql.connector.connect(
    host=os.getenv('MYSQL_HOST', 'localhost'),
    port=int(os.getenv('MYSQL_PORT', 3306)),
    user=os.getenv('MYSQL_USER', 'root'),
    password=os.getenv('MYSQL_PASSWORD', ''),
    database='marketdata'
)

cursor = conn.cursor()

# Get previous trading date
cursor.execute("SELECT MAX(date) FROM yfinance_daily_quotes WHERE date < CURDATE()")
prev_date = cursor.fetchone()[0]
print(f'Previous trading date: {prev_date}')

# Get all .NS symbols that have data for the previous date
cursor.execute("""
    SELECT symbol, close
    FROM yfinance_daily_quotes
    WHERE symbol LIKE '%.NS'
    AND date = %s
    ORDER BY symbol
""", (prev_date,))

symbols_with_prevclose = cursor.fetchall()

print(f'\n=== Available Symbols with Previous Close ===')
print(f'Total .NS symbols with prev close: {len(symbols_with_prevclose)}')

# Check how many of these are in Nifty 500
from utilities.nifty500_stocks_list import NIFTY_500_STOCKS
nifty500_yahoo = [f"{s}.NS" for s in NIFTY_500_STOCKS]
symbols_dict = {row[0]: row[1] for row in symbols_with_prevclose}

nifty500_with_data = [s for s in nifty500_yahoo if s in symbols_dict]
print(f'Nifty 500 symbols with prev close: {len(nifty500_with_data)}')

# Get ALL symbols with .NS that have recent data (last 30 days)
cursor.execute("""
    SELECT DISTINCT symbol
    FROM yfinance_daily_quotes
    WHERE symbol LIKE '%.NS'
    AND date >= DATE_SUB(CURDATE(), INTERVAL 30 DAYS)
    AND symbol NOT IN ('^NSEI', '^NSEBANK', '^BSESN')
    ORDER BY symbol
""")

all_active_symbols = [row[0] for row in cursor.fetchall()]
print(f'\nTotal active .NS symbols (traded in last 30 days): {len(all_active_symbols)}')

# How many have prev close?
active_with_prevclose = [s for s in all_active_symbols if s in symbols_dict]
print(f'Active symbols with prev close: {len(active_with_prevclose)}')

# Sample some symbols
print(f'\n=== Sample Active Symbols ===')
for sym in active_with_prevclose[:20]:
    nse = sym.replace('.NS', '')
    close_price = symbols_dict.get(sym, 'N/A')
    print(f'  {nse:15} - Close: ₹{close_price}')

conn.close()

print(f'\n=== RECOMMENDATION ===')
print(f'Use all {len(active_with_prevclose)} active symbols that have previous close data')
print(f'This includes the {len(nifty500_with_data)} Nifty 500 stocks that have data')
print(f'Plus {len(active_with_prevclose) - len(nifty500_with_data)} additional actively traded stocks')
