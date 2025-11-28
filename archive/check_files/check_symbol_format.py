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

print("Sample symbols from intraday_1min_candles:")
print("-" * 60)
result = conn.execute(text('SELECT DISTINCT symbol FROM intraday_1min_candles ORDER BY symbol LIMIT 30'))
for row in result:
    print(f"  {row[0]}")

print("\n\nChecking for Nifty 50 stocks...")
nifty50_base = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK',
                'HINDUNILVR', 'ITC', 'SBIN', 'BHARTIARTL', 'KOTAKBANK']

for symbol in nifty50_base:
    result = conn.execute(text('SELECT COUNT(*) FROM intraday_1min_candles WHERE symbol = :sym'), {'sym': symbol})
    count = result.scalar()
    print(f"  {symbol}: {count:,} candles")

conn.close()
