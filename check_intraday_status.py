"""Quick check of intraday data status."""
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

load_dotenv()

user = os.getenv('MYSQL_USER')
pwd = os.getenv('MYSQL_PASSWORD')
host = os.getenv('MYSQL_HOST')
port = os.getenv('MYSQL_PORT')

eng = create_engine(f'mysql+pymysql://{user}:{quote_plus(pwd)}@{host}:{port}/dhan_trading')
conn = eng.connect()

# Fast estimate using table statistics (instant)
r = conn.execute(text("""
    SELECT TABLE_ROWS 
    FROM information_schema.TABLES 
    WHERE TABLE_SCHEMA = 'dhan_trading' AND TABLE_NAME = 'dhan_minute_ohlcv'
""")).fetchone()
print(f'Estimated Records: ~{r[0]:,}' if r else 'Table not found')

# Fast symbol count using index
r2 = conn.execute(text('SELECT COUNT(DISTINCT symbol) FROM dhan_minute_ohlcv USE INDEX (PRIMARY)')).fetchone()
print(f'Symbols: {r2[0]}')
