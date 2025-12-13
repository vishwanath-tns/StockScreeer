#!/usr/bin/env python3
"""Check hourly quote statistics for Dec 12, 2025."""
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

load_dotenv()
pw = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
engine = create_engine(f'mysql+pymysql://root:{pw}@localhost:3306/dhan_trading')
conn = engine.connect()

print('=== Dec 12, 2025 - Time Range ===')
result = conn.execute(text("SELECT MIN(received_at), MAX(received_at) FROM dhan_quotes WHERE DATE(received_at) = '2025-12-12'"))
row = result.fetchone()
print(f'First quote: {row[0]}')
print(f'Last quote:  {row[1]}')

print('\n=== Dec 12, 2025 Quotes - Hourly Breakdown ===\n')

result = conn.execute(text("""
    SELECT HOUR(received_at) as hr, 
           COUNT(*) as cnt, 
           COUNT(DISTINCT security_id) as instruments
    FROM dhan_quotes 
    WHERE DATE(received_at) = '2025-12-12'
    GROUP BY HOUR(received_at) 
    ORDER BY hr
"""))
rows = list(result)

print(f'  Hour |     Quotes | Instruments')
print('-' * 35)
for r in rows:
    print(f'  {r[0]:>4} | {r[1]:>10,} | {r[2]:>10,}')

print()
result = conn.execute(text("SELECT COUNT(*), COUNT(DISTINCT security_id) FROM dhan_quotes WHERE DATE(received_at) = '2025-12-12'"))
row = result.fetchone()
print(f'Total Dec 12: {row[0]:,} quotes across {row[1]:,} instruments')

print('\n=== Dec 11 (for comparison) ===\n')
result = conn.execute(text("""
    SELECT HOUR(received_at) as hr, COUNT(*) as cnt
    FROM dhan_quotes 
    WHERE DATE(received_at) = '2025-12-11'
    GROUP BY HOUR(received_at) 
    ORDER BY hr
"""))
print(f'  Hour |     Quotes')
print('-' * 20)
for r in result:
    print(f'  {r[0]:>4} | {r[1]:>10,}')
