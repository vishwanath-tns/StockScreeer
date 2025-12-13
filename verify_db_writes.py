#!/usr/bin/env python
"""
Verify that quotes are being written to the database
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database imports
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

def get_db_engine():
    """Create database engine"""
    host = os.getenv('MYSQL_HOST', 'localhost')
    port = os.getenv('MYSQL_PORT', '3306')
    user = os.getenv('MYSQL_USER', 'root')
    password = os.getenv('MYSQL_PASSWORD', '')
    db = os.getenv('MYSQL_DB', 'dhan_trading')
    
    # URL-encode password to handle special characters like @
    password_encoded = quote_plus(password)
    connection_string = f"mysql+pymysql://{user}:{password_encoded}@{host}:{port}/{db}"
    return create_engine(connection_string)

def verify_quotes_in_db():
    """Check quotes in database"""
    try:
        engine = get_db_engine()
        
        with engine.connect() as conn:
            # Get total count
            result = conn.execute(text("SELECT COUNT(*) as count FROM dhan_fno_quotes"))
            total_count = result.fetchone()[0]
            print(f"\n{'='*80}")
            print(f"TOTAL QUOTES IN DATABASE: {total_count:,}")
            print(f"{'='*80}\n")
            
            # Get count from last 5 minutes
            five_min_ago = datetime.now() - timedelta(minutes=5)
            result = conn.execute(text("""
                SELECT COUNT(*) as count 
                FROM dhan_fno_quotes 
                WHERE received_at > :time
            """), {"time": five_min_ago})
            recent_count = result.fetchone()[0]
            print(f"Quotes written in last 5 minutes: {recent_count:,}")
            print(f"Quotes written in last 1 minute: ", end="")
            
            one_min_ago = datetime.now() - timedelta(minutes=1)
            result = conn.execute(text("""
                SELECT COUNT(*) as count 
                FROM dhan_fno_quotes 
                WHERE received_at > :time
            """), {"time": one_min_ago})
            one_min_count = result.fetchone()[0]
            print(f"{one_min_count:,}\n")
            
            # Get latest 10 quotes
            print(f"{'='*80}")
            print("LATEST 10 QUOTES IN DATABASE")
            print(f"{'='*80}\n")
            
            result = conn.execute(text("""
                SELECT 
                    security_id, 
                    ltp, 
                    volume, 
                    bid_price,
                    ask_price,
                    received_at 
                FROM dhan_fno_quotes 
                ORDER BY received_at DESC 
                LIMIT 10
            """))
            
            for row in result:
                sec_id, ltp, vol, bid, ask, created = row
                print(f"ID: {sec_id:5} | LTP: {ltp:10.2f} | Vol: {vol:12,d} | Bid: {bid:8.2f} | Ask: {ask:8.2f} | {created}")
            
            print(f"\n{'='*80}")
            print("✓ Database write verification SUCCESSFUL!")
            print(f"{'='*80}\n")
            
            return True
            
    except Exception as e:
        print(f"\n{'='*80}")
        print(f"ERROR: {e}")
        print(f"{'='*80}\n")
        return False

if __name__ == '__main__':
    verify_quotes_in_db()
