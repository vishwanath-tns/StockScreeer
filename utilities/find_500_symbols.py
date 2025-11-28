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

# Check yfinance_daily_quotes for distinct symbols
cursor.execute('SELECT COUNT(DISTINCT symbol) FROM yfinance_daily_quotes')
total_quotes = cursor.fetchone()[0]
print(f'\n=== yfinance_daily_quotes ===')
print(f'Distinct symbols with data: {total_quotes}')

# Sample some symbols
cursor.execute('SELECT DISTINCT symbol FROM yfinance_daily_quotes ORDER BY symbol LIMIT 20')
print('\nSample symbols (first 20):')
for row in cursor.fetchall():
    print(f'  {row[0]}')

# Check if there's a nifty 500 list table
cursor.execute("SHOW TABLES")
all_tables = [row[0] for row in cursor.fetchall()]
print(f'\n=== Looking for Nifty 500 tables ===')
nifty_tables = [t for t in all_tables if 'nifty' in t.lower() or '500' in t]
for table in nifty_tables:
    cursor.execute(f'SELECT COUNT(*) FROM {table}')
    count = cursor.fetchone()[0]
    print(f'  {table}: {count} records')

# Check if we can get 500 symbols from yfinance_daily_quotes
cursor.execute('''
    SELECT symbol, COUNT(*) as record_count, MAX(date) as latest_date
    FROM yfinance_daily_quotes 
    GROUP BY symbol 
    HAVING record_count > 100
    ORDER BY symbol
    LIMIT 510
''')
symbols_with_data = cursor.fetchall()
print(f'\n=== Symbols with >100 records in yfinance_daily_quotes ===')
print(f'Total: {len(symbols_with_data)} symbols')
print('\nFirst 10:')
for row in symbols_with_data[:10]:
    print(f'  {row[0]}: {row[1]} records, latest: {row[2]}')

conn.close()
