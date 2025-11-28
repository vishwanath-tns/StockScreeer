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

# Find all symbol mapping tables
cursor.execute("SHOW TABLES LIKE '%symbol%'")
print('\n=== Symbol-related Tables ===')
for row in cursor.fetchall():
    print(f'  {row[0]}')

# Check both tables
print('\n=== nse_yahoo_symbol_map ===')
cursor.execute('SELECT COUNT(*) as total, SUM(is_verified) as verified FROM nse_yahoo_symbol_map WHERE is_active = 1')
row = cursor.fetchone()
print(f'  Active symbols: {row[0]}')
print(f'  Verified symbols: {int(row[1])}')

# Check if there's a verification_status column in another table format
cursor.execute("SHOW TABLES")
all_tables = [row[0] for row in cursor.fetchall()]

for table in all_tables:
    if 'symbol' in table.lower() or 'map' in table.lower():
        cursor.execute(f"DESCRIBE {table}")
        cols = [col[0] for col in cursor.fetchall()]
        if 'verification_status' in cols:
            print(f'\n=== Found verification_status in: {table} ===')
            cursor.execute(f'SELECT verification_status, COUNT(*) FROM {table} GROUP BY verification_status')
            for row in cursor.fetchall():
                print(f'  {row[0]}: {row[1]}')

conn.close()
