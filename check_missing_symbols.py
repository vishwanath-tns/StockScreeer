"""Check ADANIENT and HDFCLIFE details."""
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

load_dotenv()
pw = quote_plus(os.getenv('MYSQL_PASSWORD',''))
e = create_engine(f'mysql+pymysql://root:{pw}@localhost:3306/dhan_trading')

with e.connect() as c:
    print("=== ADANIENT Details ===")
    r = c.execute(text("""
        SELECT exchange_segment, series, underlying_symbol, symbol, display_name, security_id
        FROM dhan_instruments 
        WHERE underlying_symbol = 'ADANIENT'
        LIMIT 5
    """))
    for row in r.fetchall():
        print(f"  {row[0]:12s} | Series: {row[1]:3s} | {row[2]:12s} | {row[3]:20s} | {row[4]}")
    
    print("\n=== HDFCLIFE Details ===")
    r = c.execute(text("""
        SELECT exchange_segment, series, underlying_symbol, symbol, display_name, security_id
        FROM dhan_instruments 
        WHERE underlying_symbol = 'HDFCLIFE'
        LIMIT 5
    """))
    for row in r.fetchall():
        print(f"  {row[0]:12s} | Series: {row[1]:3s} | {row[2]:12s} | {row[3]:20s} | {row[4]}")
    
    print("\n=== Available Segments/Series ===")
    r = c.execute(text("""
        SELECT DISTINCT exchange_segment, series
        FROM dhan_instruments
        WHERE underlying_symbol IN ('ADANIENT', 'HDFCLIFE')
        ORDER BY exchange_segment, series
    """))
    for row in r.fetchall():
        print(f"  {row[0]:15s} | {row[1]:3s}")
