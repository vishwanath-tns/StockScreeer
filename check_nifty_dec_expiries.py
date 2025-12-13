#!/usr/bin/env python3
"""
Check NIFTY expiries available in December 2025
"""
import os
import sys
from datetime import date
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dhan_trading.db_setup import get_engine, DHAN_DB_NAME

def main():
    engine = get_engine(DHAN_DB_NAME)
    
    print("\n" + "="*100)
    print("NIFTY EXPIRIES IN DECEMBER 2025")
    print("="*100 + "\n")
    
    with engine.connect() as conn:
        # Get all NIFTY options in December
        query = text("""
            SELECT DISTINCT 
                expiry_date,
                DAYNAME(expiry_date) as day_name,
                COUNT(*) as total_contracts
            FROM dhan_instruments
            WHERE underlying_symbol = 'NIFTY'
              AND instrument = 'OPTIDX'
              AND MONTH(expiry_date) = 12
              AND YEAR(expiry_date) = 2025
            GROUP BY expiry_date, day_name
            ORDER BY expiry_date
        """)
        
        result = conn.execute(query)
        rows = result.fetchall()
        
        if rows:
            print(f"{'Expiry Date':<20} {'Day of Week':<20} {'Total Contracts':<20}")
            print("-"*100)
            
            for expiry_date, day_name, count in rows:
                print(f"{str(expiry_date):<20} {day_name:<20} {count:<20}")
            
            print("\n" + "="*100)
            print("DETAILS BY EXPIRY:")
            print("="*100 + "\n")
            
            # For each expiry, show strike range
            for expiry_date, day_name, count in rows:
                strike_query = text("""
                    SELECT 
                        MIN(strike_price) as min_strike,
                        MAX(strike_price) as max_strike,
                        COUNT(DISTINCT strike_price) as total_strikes,
                        SUM(CASE WHEN option_type = 'CE' THEN 1 ELSE 0 END) as ce_count,
                        SUM(CASE WHEN option_type = 'PE' THEN 1 ELSE 0 END) as pe_count
                    FROM dhan_instruments
                    WHERE underlying_symbol = 'NIFTY'
                      AND instrument = 'OPTIDX'
                      AND expiry_date = :expiry
                """)
                
                strike_result = conn.execute(strike_query, {'expiry': expiry_date})
                strike_row = strike_result.fetchone()
                
                min_strike, max_strike, total_strikes, ce_count, pe_count = strike_row
                
                print(f"{expiry_date.strftime('%A, %B %d, %Y')}")
                print(f"  Strike Range: {min_strike} to {max_strike}")
                print(f"  Total Unique Strikes: {total_strikes}")
                print(f"  Call Options (CE): {ce_count}")
                print(f"  Put Options (PE): {pe_count}")
                print(f"  Total Contracts: {count}")
                print()
        else:
            print("No NIFTY options found in December 2025")

if __name__ == "__main__":
    main()
