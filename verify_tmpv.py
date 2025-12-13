"""Verify TMPV is in database."""
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

load_dotenv()
pw = quote_plus(os.getenv('MYSQL_PASSWORD',''))
e = create_engine(f'mysql+pymysql://root:{pw}@localhost:3306/dhan_trading')

with e.connect() as c:
    r = c.execute(text("""
        SELECT underlying_symbol, symbol, display_name, security_id 
        FROM dhan_instruments 
        WHERE underlying_symbol = 'TMPV' 
          AND exchange_segment='NSE_EQ'
    """))
    rows = r.fetchall()
    if rows:
        for row in rows:
            print(f'✅ Found: {row[0]:10s} | {row[1]:20s} | {row[2]:30s} | ID: {row[3]}')
    else:
        print('❌ TMPV not found in database')
    
    # Now check all 50 Nifty symbols
    print("\n=== Verifying All 50 Nifty Symbols ===")
    nifty50 = [
        'ADANIENT', 'ADANIPORTS', 'APOLLOHOSP', 'ASIANPAINT', 'AXISBANK',
        'BAJAJ-AUTO', 'BAJFINANCE', 'BAJAJFINSV', 'BEL', 'BPCL',
        'BHARTIARTL', 'BRITANNIA', 'CIPLA', 'COALINDIA', 'DRREDDY',
        'EICHERMOT', 'GRASIM', 'HCLTECH', 'HDFCBANK', 'HDFCLIFE',
        'HEROMOTOCO', 'HINDALCO', 'HINDUNILVR', 'ICICIBANK', 'ITC',
        'INDUSINDBK', 'INFY', 'JSWSTEEL', 'KOTAKBANK', 'LT',
        'M&M', 'MARUTI', 'NTPC', 'NESTLEIND', 'ONGC',
        'POWERGRID', 'RELIANCE', 'SBILIFE', 'SHRIRAMFIN', 'SBIN',
        'SUNPHARMA', 'TCS', 'TATACONSUM', 'TMPV', 'TATASTEEL',
        'TECHM', 'TITAN', 'TRENT', 'ULTRACEMCO', 'WIPRO'
    ]
    
    placeholders = ', '.join([f"'{s}'" for s in nifty50])
    r = c.execute(text(f"""
        SELECT COUNT(DISTINCT underlying_symbol) as cnt
        FROM dhan_instruments
        WHERE underlying_symbol IN ({placeholders})
          AND exchange_segment='NSE_EQ'
    """))
    
    found = r.scalar()
    print(f"\n✅ Found {found}/50 Nifty 50 symbols in database")
    
    # List which ones are missing
    r = c.execute(text(f"""
        SELECT DISTINCT underlying_symbol
        FROM dhan_instruments
        WHERE underlying_symbol IN ({placeholders})
          AND exchange_segment='NSE_EQ'
    """))
    
    found_symbols = {row[0] for row in r.fetchall()}
    missing = set(nifty50) - found_symbols
    
    if missing:
        print(f"❌ Missing ({len(missing)}): {', '.join(sorted(missing))}")
    else:
        print("✅ All 50 Nifty symbols present!")
