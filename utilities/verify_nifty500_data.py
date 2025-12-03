"""
Verify Nifty 500 Yahoo Finance Data Coverage
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

from utilities.nifty500_stocks_list import NIFTY_500_STOCKS

# Create Yahoo symbols with .NS suffix
yahoo_symbols = [f'{s}.NS' for s in NIFTY_500_STOCKS]
yahoo_symbols_set = set(yahoo_symbols)

with engine.connect() as conn:
    # Get all symbols in database with their latest date
    result = conn.execute(text("""
        SELECT symbol, MAX(date) as latest_date, COUNT(*) as record_count
        FROM yfinance_daily_quotes 
        GROUP BY symbol
    """))
    db_data = {row[0]: {'latest': row[1], 'count': row[2]} for row in result.fetchall()}
    
    # Get symbols with Dec 2 data
    result = conn.execute(text("""
        SELECT DISTINCT symbol 
        FROM yfinance_daily_quotes 
        WHERE date = '2025-12-02'
    """))
    symbols_with_dec2 = set(row[0] for row in result.fetchall())

print('=' * 70)
print('NIFTY 500 YAHOO FINANCE DATA VERIFICATION')
print('=' * 70)
print(f'Total Nifty 500 symbols (with .NS): {len(yahoo_symbols)}')
print(f'Symbols in yfinance_daily_quotes table: {len(db_data)}')
print(f'Symbols with Dec 2, 2025 data: {len(symbols_with_dec2)}')

# Check coverage
symbols_in_db = set(db_data.keys())
nifty500_in_db = yahoo_symbols_set & symbols_in_db
nifty500_with_dec2 = yahoo_symbols_set & symbols_with_dec2

print(f'\nNifty 500 symbols in database: {len(nifty500_in_db)}')
print(f'Nifty 500 symbols with Dec 2 data: {len(nifty500_with_dec2)}')

# Missing symbols (not in database at all)
missing_symbols = yahoo_symbols_set - symbols_in_db
print(f'\n❌ MISSING FROM DATABASE ({len(missing_symbols)} symbols):')
for s in sorted(missing_symbols):
    print(f'   {s}')

# Symbols without Dec 2 data  
nifty500_without_dec2 = nifty500_in_db - symbols_with_dec2
if nifty500_without_dec2:
    print(f'\n⚠️ IN DB BUT NO DEC 2 DATA ({len(nifty500_without_dec2)} symbols):')
    for s in sorted(nifty500_without_dec2):
        info = db_data.get(s, {})
        latest = info.get('latest', 'N/A')
        count = info.get('count', 0)
        print(f'   {s} - latest: {latest}, records: {count}')

# Summary
print(f'\n' + '=' * 70)
print('SUMMARY')
print('=' * 70)
print(f'✅ Nifty 500 with Dec 2 data: {len(nifty500_with_dec2)}/500')
print(f'⚠️ Nifty 500 without Dec 2 data: {len(nifty500_without_dec2)}/500')
print(f'❌ Nifty 500 missing from DB: {len(missing_symbols)}/500')
