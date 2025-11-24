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

print("Index Mappings:")
result = conn.execute(text("""
    SELECT nse_symbol, yahoo_symbol, is_active 
    FROM nse_yahoo_symbol_map 
    WHERE nse_symbol IN ('NIFTY', 'BANKNIFTY', 'SENSEX', 'NIFTY BANK')
    ORDER BY nse_symbol
"""))

for row in result:
    print(f"  {row[0]:<15} -> {row[1]:<20} (active: {row[2]})")

print("\nCurrent TATAMOTORS/TMCV mappings:")
result = conn.execute(text("""
    SELECT nse_symbol, yahoo_symbol, is_active 
    FROM nse_yahoo_symbol_map 
    WHERE nse_symbol IN ('TATAMOTORS', 'TMCV') 
       OR yahoo_symbol IN ('TATAMOTORS.NS', 'TMCV.NS')
    ORDER BY nse_symbol
"""))

for row in result:
    print(f"  {row[0]:<15} -> {row[1]:<20} (active: {row[2]})")
