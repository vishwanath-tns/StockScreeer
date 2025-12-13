#!/usr/bin/env python
"""Check database for quotes written by FNO Database Writer"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import text, create_engine
from urllib.parse import quote_plus

# Load environment
load_dotenv()

# Get connection details
user = os.getenv('MYSQL_USER', 'root')
password = os.getenv('MYSQL_PASSWORD', '')
host = os.getenv('MYSQL_HOST', 'localhost')
port = os.getenv('MYSQL_PORT', '3306')
db = os.getenv('MYSQL_DB', 'marketdata')

print("\n" + "=" * 70)
print("DATABASE QUOTE STATISTICS".center(70))
print("=" * 70)
print(f"\n🔌 Connecting to MySQL:")
print(f"   Host: {host}:{port}")
print(f"   Database: {db}")
print(f"   User: {user}")

try:
    # Build connection string with urllib.parse to handle special chars in password
    password_encoded = quote_plus(password)
    conn_str = f"mysql+pymysql://{user}:{password_encoded}@{host}:{port}/{db}"
    engine = create_engine(conn_str, echo=False)
    
    with engine.connect() as conn:
        # Count records
        result = conn.execute(text('SELECT COUNT(*) as count FROM dhan_fno_quotes'))
        fno_count = result.fetchone()[0]
        
        result = conn.execute(text('SELECT COUNT(*) as count FROM dhan_options_quotes'))
        opt_count = result.fetchone()[0]
        
        # Get latest timestamps
        result = conn.execute(text('SELECT MAX(created_at) as latest FROM dhan_fno_quotes'))
        latest_fno = result.fetchone()[0]
        
        result = conn.execute(text('SELECT MAX(created_at) as latest FROM dhan_options_quotes'))
        latest_opt = result.fetchone()[0]
        
        # Get sample records
        result = conn.execute(text('SELECT instrument_id, ltp, volume, created_at FROM dhan_fno_quotes ORDER BY created_at DESC LIMIT 5'))
        fno_samples = result.fetchall()
        
        result = conn.execute(text('SELECT instrument_id, ltp, volume, created_at FROM dhan_options_quotes ORDER BY created_at DESC LIMIT 5'))
        opt_samples = result.fetchall()
    
    print("\n✅ Connected to database successfully!")
    
    print(f"\n📊 Quote Counts:")
    print(f"   FNO Quotes (Futures & Commodities): {fno_count:>10,}")
    print(f"   Options Quotes (Index & Stock):     {opt_count:>10,}")
    print(f"   {'─' * 45}")
    print(f"   Total Quotes Written:               {fno_count + opt_count:>10,}")
    
    print(f"\n⏰ Latest Timestamps:")
    print(f"   FNO Latest:                         {latest_fno}")
    print(f"   Options Latest:                     {latest_opt}")
    
    if fno_samples:
        print(f"\n📈 Sample FNO Quotes (Most Recent):")
        print(f"   {'ID':<8} {'LTP':<12} {'Volume':<15} {'Timestamp':<20}")
        print(f"   {'-' * 55}")
        for row in fno_samples:
            print(f"   {row[0]:<8} {row[1]:<12.2f} {row[2]:<15,} {str(row[3]):<20}")
    
    if opt_samples:
        print(f"\n📈 Sample Options Quotes (Most Recent):")
        print(f"   {'ID':<8} {'LTP':<12} {'Volume':<15} {'Timestamp':<20}")
        print(f"   {'-' * 55}")
        for row in opt_samples:
            print(f"   {row[0]:<8} {row[1]:<12.2f} {row[2]:<15,} {str(row[3]):<20}")
    
    print("\n" + "=" * 70)
    
    if fno_count + opt_count == 0:
        print("⚠️  NO QUOTES IN DATABASE - Database writer may not be running")
    elif fno_count == 0:
        print("⚠️  No FNO quotes written yet")
    elif opt_count == 0:
        print("⚠️  No Options quotes written yet")
    else:
        print(f"✅ Database is receiving quotes! Total: {fno_count + opt_count:,} records")
    
    print("=" * 70 + "\n")

except Exception as e:
    print(f"\n❌ Connection Error: {e}")
    print("\n⚠️  Make sure MySQL Server is running!")
    sys.exit(1)
