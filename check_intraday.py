from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
from urllib.parse import quote_plus

load_dotenv()
pwd = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
eng = create_engine(f"mysql+pymysql://{os.getenv('MYSQL_USER','root')}:{pwd}@{os.getenv('MYSQL_HOST','localhost')}:{os.getenv('MYSQL_PORT','3306')}/{os.getenv('MYSQL_DB','marketdata')}")

with eng.connect() as conn:
    # Check all tables
    print("Tables in marketdata database:")
    print("="*80)
    r = conn.execute(text("SHOW TABLES"))
    for row in r:
        print(f"  {row[0]}")
    
    print("\n" + "="*80)
    print("Yahoo Finance Data by Timeframe (yfinance_daily_quotes):")
    print("="*80)
    r = conn.execute(text("SELECT timeframe, MIN(date) as min_date, MAX(date) as max_date, COUNT(DISTINCT DATE(date)) as unique_days, COUNT(DISTINCT symbol) as symbols, COUNT(*) as total FROM yfinance_daily_quotes GROUP BY timeframe ORDER BY timeframe"))
    for row in r:
        print(f"  {row[0]:10} | {row[1]} to {row[2]} | {row[3]} days | {row[4]} symbols | {row[5]:,} records")
