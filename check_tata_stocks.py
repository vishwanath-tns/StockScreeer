"""Check TATA stocks in database."""
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

load_dotenv()
pw = quote_plus(os.getenv('MYSQL_PASSWORD',''))
e = create_engine(f'mysql+pymysql://root:{pw}@localhost:3306/dhan_trading')

with e.connect() as c:
    print("=== TATA Stocks in NSE_EQ Segment ===")
    r = c.execute(text("""
        SELECT underlying_symbol, symbol, display_name, security_id 
        FROM dhan_instruments 
        WHERE underlying_symbol LIKE '%TATA%' 
          AND exchange_segment='NSE_EQ'
        ORDER BY underlying_symbol
    """))
    
    for row in r.fetchall():
        print(f'{row[0]:15s} | {row[1]:15s} | {row[2]:30s} | ID: {row[3]}')
    
    print("\n=== Search for TATAMOTORS (Case-Insensitive) ===")
    r = c.execute(text("""
        SELECT underlying_symbol, symbol, display_name, security_id 
        FROM dhan_instruments 
        WHERE UPPER(underlying_symbol) = 'TATAMOTORS'
        LIMIT 5
    """))
    
    result = r.fetchall()
    if result:
        for row in result:
            print(f'{row[0]:15s} | {row[1]:15s} | {row[2]:30s} | ID: {row[3]}')
    else:
        print("TATAMOTORS not found!")
    
    print("\n=== Database Stats ===")
    r = c.execute(text("SELECT COUNT(DISTINCT underlying_symbol) FROM dhan_instruments WHERE exchange_segment='NSE_EQ'"))
    total = r.scalar()
    print(f"Total unique symbols in NSE_EQ: {total}")
