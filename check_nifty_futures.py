#!/usr/bin/env python
"""Check NIFTY futures in database."""

from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

load_dotenv()

pw = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
engine = create_engine(f'mysql+pymysql://root:{pw}@localhost:3306/dhan_trading')

with engine.connect() as conn:
    # Check all NIFTY instruments
    print("All NIFTY instruments (first 20):")
    result = conn.execute(text("""
        SELECT security_id, symbol, strike_price, option_type, expiry_date, instrument_type
        FROM dhan_instruments 
        WHERE underlying_symbol = 'NIFTY'
        ORDER BY expiry_date
        LIMIT 20
    """))
    for row in result:
        print(row)
    
    print("\n\nNIFTY futures candidates (instrument_type like FUT):")
    result = conn.execute(text("""
        SELECT security_id, symbol, strike_price, option_type, expiry_date, instrument_type
        FROM dhan_instruments 
        WHERE symbol LIKE 'NIFTY%FUT%'
           OR (underlying_symbol = 'NIFTY' AND instrument_type LIKE '%FUT%')
        LIMIT 20
    """))
    for row in result:
        print(row)
