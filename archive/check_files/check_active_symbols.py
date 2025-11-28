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

# First check table structure
cursor.execute('DESCRIBE nse_yahoo_symbol_map')
print('\n=== Table Structure: nse_yahoo_symbol_map ===')
for col in cursor.fetchall():
    print(f'  {col[0]}: {col[1]}')

# Check is_active = 1 count
cursor.execute('SELECT COUNT(*) FROM nse_yahoo_symbol_map WHERE is_active = 1')
active_all = cursor.fetchone()[0]

# Check is_active = 1 AND is_verified = 1
cursor.execute('SELECT COUNT(*) FROM nse_yahoo_symbol_map WHERE is_active = 1 AND is_verified = 1')
active_verified = cursor.fetchone()[0]

# Check all records
cursor.execute('SELECT COUNT(*) FROM nse_yahoo_symbol_map')
total_all = cursor.fetchone()[0]

# Full breakdown by is_active and is_verified
cursor.execute('SELECT is_active, is_verified, COUNT(*) FROM nse_yahoo_symbol_map GROUP BY is_active, is_verified ORDER BY is_active, is_verified')

print('\n=== nse_yahoo_symbol_map Symbol Counts ===')
print(f'Total symbols: {total_all}')
print(f'is_active = 1 (ALL): {active_all}')
print(f'is_active = 1 AND is_verified = 1: {active_verified}')
print(f'\nFull breakdown by is_active and is_verified:')
for row in cursor.fetchall():
    active_label = 'Active' if row[0] == 1 else 'Inactive'
    verified_label = 'Verified' if row[1] == 1 else 'Unverified'
    print(f'  {active_label} + {verified_label}: {row[2]} symbols')

conn.close()
