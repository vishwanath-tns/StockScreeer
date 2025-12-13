#!/usr/bin/env python
"""Check NIFTY options in database."""
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

load_dotenv()
pw = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
engine = create_engine(f'mysql+pymysql://root:{pw}@localhost:3306/dhan_trading')

with engine.connect() as conn:
    # Check exchange segments
    print("=== Exchange Segments ===")
    result = conn.execute(text("SELECT DISTINCT exchange_segment FROM dhan_instruments"))
    for row in result:
        print(row[0])
    
    print("\n=== NIFTY Options Sample ===")
    result = conn.execute(text("""
        SELECT security_id, symbol, strike_price, option_type, expiry_date, exchange_segment 
        FROM dhan_instruments 
        WHERE symbol LIKE 'NIFTY%' 
        AND option_type IS NOT NULL
        LIMIT 20
    """))
    for row in result:
        print(row)
