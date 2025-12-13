#!/usr/bin/env python
"""Check NIFTY strikes in database."""

from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

load_dotenv()

pw = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
engine = create_engine(f'mysql+pymysql://root:{pw}@localhost:3306/dhan_trading')

with engine.connect() as conn:
    # Get all distinct strikes for NIFTY nearest expiry
    result = conn.execute(text("""
        SELECT DISTINCT strike_price 
        FROM dhan_instruments 
        WHERE underlying_symbol = 'NIFTY' 
          AND strike_price IS NOT NULL
          AND expiry_date = (
              SELECT MIN(expiry_date) FROM dhan_instruments 
              WHERE underlying_symbol = 'NIFTY' 
                AND strike_price IS NOT NULL
                AND expiry_date >= CURDATE()
          )
        ORDER BY strike_price
    """))
    
    strikes = [int(row[0]) for row in result]
    print(f"Total strikes for nearest expiry: {len(strikes)}")
    print(f"Min: {min(strikes)}, Max: {max(strikes)}")
    print(f"\nStrikes above 25000: {[s for s in strikes if s > 25000]}")
    print(f"\nStrikes between 24000-26000: {[s for s in strikes if 24000 <= s <= 26000]}")
