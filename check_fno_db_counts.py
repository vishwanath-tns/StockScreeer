"""Quick script to check FNO database record counts."""
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

load_dotenv()

# Build DB URL
password = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
db_url = (
    f"mysql+pymysql://{os.getenv('MYSQL_USER', 'root')}:"
    f"{password}@"
    f"{os.getenv('MYSQL_HOST', 'localhost')}:"
    f"{os.getenv('MYSQL_PORT', '3306')}/"
    f"dhan_trading?charset=utf8mb4"
)

engine = create_engine(db_url)

with engine.connect() as conn:
    print("=" * 60)
    print("FNO Database Record Counts")
    print("=" * 60)
    print()
    
    # dhan_fno_quotes
    print("=== dhan_fno_quotes (Futures & Commodities) ===")
    try:
        r1 = conn.execute(text("SELECT COUNT(*) as cnt FROM dhan_fno_quotes")).fetchone()
        print(f"Total rows: {r1[0]:,}")
        
        # Get date range
        r2 = conn.execute(text("""
            SELECT MIN(created_at) as min_dt, MAX(created_at) as max_dt 
            FROM dhan_fno_quotes
        """)).fetchone()
        print(f"Date range: {r2[0]} to {r2[1]}")
        
        # Count by segment
        r3 = conn.execute(text("""
            SELECT exchange_segment, COUNT(*) as cnt 
            FROM dhan_fno_quotes 
            GROUP BY exchange_segment
        """)).fetchall()
        print("By segment:")
        for row in r3:
            print(f"  {row[0]}: {row[1]:,}")
    except Exception as e:
        print(f"Error: {e}")
    
    print()
    
    # dhan_options_quotes
    print("=== dhan_options_quotes (Options) ===")
    try:
        r4 = conn.execute(text("SELECT COUNT(*) as cnt FROM dhan_options_quotes")).fetchone()
        print(f"Total rows: {r4[0]:,}")
        
        # Get date range
        r5 = conn.execute(text("""
            SELECT MIN(created_at) as min_dt, MAX(created_at) as max_dt 
            FROM dhan_options_quotes
        """)).fetchone()
        print(f"Date range: {r5[0]} to {r5[1]}")
        
        # Count by segment
        r6 = conn.execute(text("""
            SELECT exchange_segment, COUNT(*) as cnt 
            FROM dhan_options_quotes 
            GROUP BY exchange_segment
        """)).fetchall()
        print("By segment:")
        for row in r6:
            print(f"  {row[0]}: {row[1]:,}")
    except Exception as e:
        print(f"Error: {e}")
    
    print()
    print("=" * 60)
