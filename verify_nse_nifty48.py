"""Verify all 48 NSE Nifty symbols are in database."""
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

load_dotenv()
pw = quote_plus(os.getenv('MYSQL_PASSWORD',''))
e = create_engine(f'mysql+pymysql://root:{pw}@localhost:3306/dhan_trading')

nifty48 = [
    'ADANIPORTS', 'APOLLOHOSP', 'ASIANPAINT', 'AXISBANK',
    'BAJAJ-AUTO', 'BAJFINANCE', 'BAJAJFINSV', 'BEL', 'BPCL',
    'BHARTIARTL', 'BRITANNIA', 'CIPLA', 'COALINDIA', 'DRREDDY',
    'EICHERMOT', 'GRASIM', 'HCLTECH', 'HDFCBANK',
    'HEROMOTOCO', 'HINDALCO', 'HINDUNILVR', 'ICICIBANK', 'ITC',
    'INDUSINDBK', 'INFY', 'JSWSTEEL', 'KOTAKBANK', 'LT',
    'M&M', 'MARUTI', 'NTPC', 'NESTLEIND', 'ONGC',
    'POWERGRID', 'RELIANCE', 'SBILIFE', 'SHRIRAMFIN', 'SBIN',
    'SUNPHARMA', 'TCS', 'TATACONSUM', 'TMPV', 'TATASTEEL',
    'TECHM', 'TITAN', 'TRENT', 'ULTRACEMCO', 'WIPRO'
]

with e.connect() as c:
    placeholders = ', '.join([f"'{s}'" for s in nifty48])
    r = c.execute(text(f"""
        SELECT COUNT(DISTINCT underlying_symbol) as cnt
        FROM dhan_instruments
        WHERE underlying_symbol IN ({placeholders})
          AND exchange_segment='NSE_EQ'
    """))
    
    found = r.scalar()
    print(f"✅ NSE Nifty 48 Stocks: {found}/48 found in database")
    
    if found == 48:
        print("✅ All 48 NSE symbols are available!")
    else:
        r = c.execute(text(f"""
            SELECT DISTINCT underlying_symbol
            FROM dhan_instruments
            WHERE underlying_symbol IN ({placeholders})
              AND exchange_segment='NSE_EQ'
        """))
        found_symbols = {row[0] for row in r.fetchall()}
        missing = set(nifty48) - found_symbols
        print(f"❌ Missing ({len(missing)}): {', '.join(sorted(missing))}")
