from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
from urllib.parse import quote_plus

load_dotenv()
pwd = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
user = os.getenv('MYSQL_USER', 'root')
host = os.getenv('MYSQL_HOST', 'localhost')
port = os.getenv('MYSQL_PORT', '3306')
db = os.getenv('MYSQL_DB', 'marketdata')
eng = create_engine(f'mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}')

with eng.connect() as conn:
    print('yfinance_intraday_quotes Summary:')
    print('='*80)
    r = conn.execute(text('''
        SELECT 
            timeframe,
            MIN(datetime) as min_date,
            MAX(datetime) as max_date,
            COUNT(DISTINCT DATE(datetime)) as unique_days,
            COUNT(DISTINCT symbol) as symbols,
            COUNT(*) as total
        FROM yfinance_intraday_quotes 
        GROUP BY timeframe 
        ORDER BY timeframe
    '''))
    rows = list(r)
    if rows:
        for row in rows:
            print(f'  {row[0]:6} | {row[1]} to {row[2]} | {row[3]} days | {row[4]} symbols | {row[5]:,} records')
    else:
        print('  No intraday data found in yfinance_intraday_quotes table')
    
    print('\n' + '='*80)
    print('Other Intraday Tables:')
    print('='*80)
    
    # Check intraday_1min_candles
    r = conn.execute(text('SELECT COUNT(*) FROM intraday_1min_candles'))
    count = r.fetchone()[0]
    if count > 0:
        r = conn.execute(text('SELECT MIN(datetime), MAX(datetime), COUNT(DISTINCT DATE(datetime)), COUNT(DISTINCT symbol) FROM intraday_1min_candles'))
        row = r.fetchone()
        print(f'  intraday_1min_candles: {row[0]} to {row[1]} | {row[2]} days | {row[3]} symbols | {count:,} records')
    else:
        print(f'  intraday_1min_candles: empty')
    
    # Check intraday_stock_prices
    r = conn.execute(text('SELECT COUNT(*) FROM intraday_stock_prices'))
    count = r.fetchone()[0]
    if count > 0:
        r = conn.execute(text('SELECT MIN(datetime), MAX(datetime), COUNT(DISTINCT DATE(datetime)), COUNT(DISTINCT symbol) FROM intraday_stock_prices'))
        row = r.fetchone()
        print(f'  intraday_stock_prices: {row[0]} to {row[1]} | {row[2]} days | {row[3]} symbols | {count:,} records')
    else:
        print(f'  intraday_stock_prices: empty')
