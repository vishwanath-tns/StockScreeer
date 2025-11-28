"""Check table structure"""
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
import os

load_dotenv()

url = URL.create(
    drivername="mysql+pymysql",
    username=os.getenv('MYSQL_USER', 'root'),
    password=os.getenv('MYSQL_PASSWORD', ''),
    host=os.getenv('MYSQL_HOST', 'localhost'),
    port=int(os.getenv('MYSQL_PORT', 3306)),
    database=os.getenv('MYSQL_DB', 'marketdata'),
    query={"charset": "utf8mb4"}
)

engine = create_engine(url)
conn = engine.connect()

print("nse_yahoo_symbol_map table structure:")
print("-" * 60)
result = conn.execute(text('DESCRIBE nse_yahoo_symbol_map'))
for row in result:
    print(f"{row[0]:<30} {row[1]:<20} {row[2]}")

print("\nSample data:")
result = conn.execute(text('SELECT * FROM nse_yahoo_symbol_map LIMIT 5'))
for row in result:
    print(row)

conn.close()
