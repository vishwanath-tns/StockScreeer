"""
Compare NSE Official Nifty 500 with Yahoo Symbols List
"""
import sys
sys.path.insert(0, '.')

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
import os

load_dotenv()

url = URL.create(
    drivername='mysql+pymysql',
    username=os.getenv('MYSQL_USER', 'root'),
    password=os.getenv('MYSQL_PASSWORD', ''),
    host=os.getenv('MYSQL_HOST', '127.0.0.1'),
    port=int(os.getenv('MYSQL_PORT', '3306')),
    database=os.getenv('MYSQL_DB', 'marketdata'),
    query={'charset': 'utf8mb4'},
)
engine = create_engine(url)

# Get NSE official Nifty 500 symbols from DB
with engine.connect() as conn:
    result = conn.execute(text("SELECT symbol FROM nse_index_constituents WHERE index_name = 'NIFTY500'"))
    nse_symbols = set(row[0] for row in result.fetchall())

# Get Yahoo symbols list
from utilities.nifty500_stocks_list import NIFTY_500_STOCKS
yahoo_symbols = set(NIFTY_500_STOCKS)

print('=' * 70)
print('COMPARISON: NSE Official NIFTY500 vs Yahoo (NIFTY_500_STOCKS) List')
print('=' * 70)
print(f'NSE Official: {len(nse_symbols)} symbols')
print(f'Yahoo List (NIFTY_500_STOCKS): {len(yahoo_symbols)} symbols')

# In NSE but not in Yahoo list
missing_in_yahoo = sorted(nse_symbols - yahoo_symbols)
print(f'\n❌ IN NSE BUT MISSING IN YAHOO LIST ({len(missing_in_yahoo)} symbols):')
for s in missing_in_yahoo:
    print(f'   {s}')

# In Yahoo but not in NSE official list  
extra_in_yahoo = sorted(yahoo_symbols - nse_symbols)
print(f'\n➕ IN YAHOO BUT NOT IN NSE OFFICIAL ({len(extra_in_yahoo)} symbols):')
for s in extra_in_yahoo:
    print(f'   {s}')

# Common symbols
common = nse_symbols & yahoo_symbols
print(f'\n✅ Common symbols: {len(common)}')
