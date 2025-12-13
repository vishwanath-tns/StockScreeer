#!/usr/bin/env python
"""Check Dec 12 quotes in Redis vs Database."""

from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

load_dotenv()

pw = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
engine = create_engine(f'mysql+pymysql://root:{pw}@localhost:3306/dhan_trading')

with engine.connect() as conn:
    # Check quotes from Dec 12 9:30 AM onwards
    result = conn.execute(text("SELECT COUNT(*) FROM dhan_quotes WHERE received_at >= '2025-12-12 09:30:00'"))
    print(f"Quotes from Dec 12 9:30 AM onwards in DB: {result.fetchone()[0]:,}")
    
    # Check last quote timestamp
    result = conn.execute(text("SELECT MAX(received_at) FROM dhan_quotes"))
    print(f"Last quote in DB: {result.fetchone()[0]}")
    
    # Check quotes by date
    result = conn.execute(text("""
        SELECT DATE(received_at) as date, COUNT(*) as cnt 
        FROM dhan_quotes 
        GROUP BY DATE(received_at) 
        ORDER BY date DESC 
        LIMIT 5
    """))
    print("\nQuotes by date:")
    for row in result:
        print(f"  {row[0]}: {row[1]:,} quotes")
