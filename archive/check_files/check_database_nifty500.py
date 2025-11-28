#!/usr/bin/env python3
"""
Check database for Nifty 500 symbols and mappings
"""

import mysql.connector
import os
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

def check_database():
    """Check current state of database"""
    try:
        conn = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            database='marketdata'
        )
        
        cursor = conn.cursor()
        
        print("=" * 70)
        print("DATABASE STATUS CHECK")
        print("=" * 70)
        
        # Check nse_yahoo_symbol_map
        print("\n📊 NSE Yahoo Symbol Map:")
        cursor.execute("SELECT COUNT(*) FROM nse_yahoo_symbol_map")
        total = cursor.fetchone()[0]
        print(f"  Total mappings: {total}")
        
        cursor.execute("SELECT COUNT(*) FROM nse_yahoo_symbol_map WHERE is_active = 1")
        active = cursor.fetchone()[0]
        print(f"  Active mappings: {active}")
        
        cursor.execute("SELECT COUNT(*) FROM nse_yahoo_symbol_map WHERE is_verified = 1")
        verified = cursor.fetchone()[0]
        print(f"  Verified mappings: {verified}")
        
        # Check yfinance_daily_quotes
        print("\n📈 YFinance Daily Quotes:")
        cursor.execute("SELECT COUNT(*) FROM yfinance_daily_quotes")
        total_records = cursor.fetchone()[0]
        print(f"  Total records: {total_records:,}")
        
        cursor.execute("SELECT COUNT(DISTINCT symbol) FROM yfinance_daily_quotes")
        unique_symbols = cursor.fetchone()[0]
        print(f"  Unique symbols: {unique_symbols}")
        
        cursor.execute("SELECT MAX(date) FROM yfinance_daily_quotes")
        latest_date = cursor.fetchone()[0]
        print(f"  Latest date: {latest_date}")
        
        # Check for Nifty 500 coverage
        print("\n🎯 Nifty 500 Coverage Check:")
        
        # Sample active symbols
        print("\n📋 Sample Active Symbol Mappings (first 20):")
        cursor.execute("""
            SELECT nse_symbol, yahoo_symbol, is_verified 
            FROM nse_yahoo_symbol_map 
            WHERE is_active = 1 
            ORDER BY nse_symbol 
            LIMIT 20
        """)
        
        for row in cursor.fetchall():
            status = "✅" if row[2] else "❓"
            print(f"  {status} {row[0]:15} -> {row[1]}")
        
        # Check which symbols have data
        print("\n💾 Symbols with Downloaded Data:")
        cursor.execute("""
            SELECT m.nse_symbol, m.yahoo_symbol, COUNT(*) as records, MAX(q.date) as latest
            FROM nse_yahoo_symbol_map m
            LEFT JOIN yfinance_daily_quotes q ON m.yahoo_symbol = q.symbol
            WHERE m.is_active = 1
            GROUP BY m.nse_symbol, m.yahoo_symbol
            HAVING records > 0
            ORDER BY records DESC
            LIMIT 15
        """)
        
        results = cursor.fetchall()
        if results:
            for row in results:
                print(f"  {row[0]:15} -> {row[2]:5} records (latest: {row[3]})")
        else:
            print("  No data found")
        
        # Check for symbols without data
        cursor.execute("""
            SELECT COUNT(*) 
            FROM nse_yahoo_symbol_map m
            LEFT JOIN yfinance_daily_quotes q ON m.yahoo_symbol = q.symbol
            WHERE m.is_active = 1 AND q.symbol IS NULL
        """)
        missing = cursor.fetchone()[0]
        print(f"\n⚠️  Symbols without data: {missing}/{active}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_database()
