#!/usr/bin/env python3
"""
Check what options are actually available in the database
"""
import os
import sys
from datetime import date, timedelta
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dhan_trading.db_setup import get_engine, DHAN_DB_NAME

def main():
    engine = get_engine(DHAN_DB_NAME)
    
    print("\n" + "="*120)
    print("CHECKING AVAILABLE OPTIONS IN DATABASE")
    print("="*120 + "\n")
    
    # Check what underlying symbols have options
    with engine.connect() as conn:
        query = text("""
            SELECT DISTINCT underlying_symbol, expiry_date, COUNT(*) as count
            FROM dhan_instruments
            WHERE instrument = 'OPTIDX'
            GROUP BY underlying_symbol, expiry_date
            ORDER BY underlying_symbol, expiry_date
        """)
        
        result = conn.execute(query)
        rows = result.fetchall()
        
        if rows:
            print("OPTIONS AVAILABLE BY UNDERLYING AND EXPIRY:")
            print("-"*120)
            print(f"{'Underlying':<20} {'Expiry Date':<20} {'Total Contracts':<20}")
            print("-"*120)
            
            for underlying, expiry, count in rows:
                print(f"{underlying:<20} {str(expiry):<20} {count:<20}")
        else:
            print("NO OPTIONS FOUND IN DATABASE!")
        
        print("\n" + "="*120)
        print("CHECKING SPECIFIC UNDERLYINGS")
        print("="*120 + "\n")
        
        # Check NIFTY
        print("NIFTY Options:")
        query = text("""
            SELECT expiry_date, COUNT(*) as count
            FROM dhan_instruments
            WHERE underlying_symbol = 'NIFTY' AND instrument = 'OPTIDX'
            GROUP BY expiry_date
            ORDER BY expiry_date
        """)
        
        result = conn.execute(query)
        nifty_rows = result.fetchall()
        if nifty_rows:
            for expiry, count in nifty_rows:
                print(f"  {expiry}: {count} contracts")
        else:
            print("  NOT FOUND")
        
        # Check BANKNIFTY
        print("\nBANKNIFTY Options:")
        query = text("""
            SELECT expiry_date, COUNT(*) as count
            FROM dhan_instruments
            WHERE underlying_symbol = 'BANKNIFTY' AND instrument = 'OPTIDX'
            GROUP BY expiry_date
            ORDER BY expiry_date
        """)
        
        result = conn.execute(query)
        bnifty_rows = result.fetchall()
        if bnifty_rows:
            for expiry, count in bnifty_rows:
                print(f"  {expiry}: {count} contracts")
        else:
            print("  NOT FOUND")
        
        # Check FINNIFTY
        print("\nFINNIFTY Options:")
        query = text("""
            SELECT expiry_date, COUNT(*) as count
            FROM dhan_instruments
            WHERE underlying_symbol = 'FINNIFTY' AND instrument = 'OPTIDX'
            GROUP BY expiry_date
            ORDER BY expiry_date
        """)
        
        result = conn.execute(query)
        finnifty_rows = result.fetchall()
        if finnifty_rows:
            for expiry, count in finnifty_rows:
                print(f"  {expiry}: {count} contracts")
        else:
            print("  NOT FOUND")
        
        # Show sample of what's available
        print("\n" + "="*120)
        print("SAMPLE INSTRUMENTS WITH OPTIONS")
        print("="*120 + "\n")
        
        query = text("""
            SELECT underlying_symbol, MIN(expiry_date) as nearest_expiry, COUNT(*) as total
            FROM dhan_instruments
            WHERE instrument = 'OPTIDX'
            GROUP BY underlying_symbol
            ORDER BY underlying_symbol
        """)
        
        result = conn.execute(query)
        for underlying, nearest_expiry, total in result.fetchall():
            print(f"{underlying:<20} Nearest: {nearest_expiry}  Total contracts: {total}")

if __name__ == "__main__":
    main()
