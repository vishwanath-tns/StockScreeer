"""Check which Nifty 50 symbols are in dhan_instruments database."""
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

load_dotenv()
pw = quote_plus(os.getenv('MYSQL_PASSWORD',''))
e = create_engine(f'mysql+pymysql://root:{pw}@localhost:3306/dhan_trading')

NIFTY50 = [
    'ADANIENT', 'ADANIPORTS', 'APOLLOHOSP', 'ASIANPAINT', 'AXISBANK',
    'BAJAJ-AUTO', 'BAJFINANCE', 'BAJAJFINSV', 'BEL', 'BPCL',
    'BHARTIARTL', 'BRITANNIA', 'CIPLA', 'COALINDIA', 'DRREDDY',
    'EICHERMOT', 'GRASIM', 'HCLTECH', 'HDFCBANK', 'HDFCLIFE',
    'HEROMOTOCO', 'HINDALCO', 'HINDUNILVR', 'ICICIBANK', 'ITC',
    'INDUSINDBK', 'INFY', 'JSWSTEEL', 'KOTAKBANK', 'LT',
    'M&M', 'MARUTI', 'NTPC', 'NESTLEIND', 'ONGC',
    'POWERGRID', 'RELIANCE', 'SBILIFE', 'SHRIRAMFIN', 'SBIN',
    'SUNPHARMA', 'TCS', 'TATACONSUM', 'TATAMOTORS', 'TATASTEEL',
    'TECHM', 'TITAN', 'TRENT', 'ULTRACEMCO', 'WIPRO'
]

with e.connect() as c:
    print("=== Checking Missing Nifty 50 Symbols ===\n")
    
    missing_stocks = ['HDFCLIFE', 'TATAMOTORS', 'ADANIENT']
    for stock in missing_stocks:
        r = c.execute(text(f"SELECT COUNT(*) FROM dhan_instruments WHERE underlying_symbol = '{stock}'"))
        count = r.scalar()
        print(f'{stock:15s} : {count} records')
    
    print("\n=== All Nifty 50 Symbols in Database ===")
    placeholders = ', '.join([f"'{s}'" for s in NIFTY50])
    
    r = c.execute(text(f"""
        SELECT underlying_symbol, COUNT(*) as cnt
        FROM dhan_instruments
        WHERE underlying_symbol IN ({placeholders})
        GROUP BY underlying_symbol
        ORDER BY underlying_symbol
    """))
    
    stocks = r.fetchall()
    print(f'\nFound {len(stocks)}/50 Nifty 50 symbols')
    
    missing = set(NIFTY50) - {row[0] for row in stocks}
    if missing:
        print(f'\n❌ Missing from database ({len(missing)}):\n  {", ".join(sorted(missing))}')
    else:
        print('\n✅ All Nifty 50 symbols present!')
