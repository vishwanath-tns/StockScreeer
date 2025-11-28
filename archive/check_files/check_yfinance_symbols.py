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

# Check yfinance_symbols structure
cursor.execute('DESCRIBE yfinance_symbols')
print('\n=== yfinance_symbols Table Structure ===')
for col in cursor.fetchall():
    print(f'  {col[0]}: {col[1]}')

# Check counts
cursor.execute('SELECT COUNT(*) FROM yfinance_symbols')
total = cursor.fetchone()[0]
print(f'\nTotal records: {total}')

# Check if there's verification_status
cursor.execute('SELECT verification_status, COUNT(*) FROM yfinance_symbols GROUP BY verification_status')
print('\nBreakdown by verification_status:')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]}')

# Sample records
cursor.execute('SELECT symbol, verification_status, is_active LIMIT 10')
print('\nSample records:')
for row in cursor.fetchall():
    print(f'  {row[0]}: status={row[1]}, active={row[2]}')

conn.close()
