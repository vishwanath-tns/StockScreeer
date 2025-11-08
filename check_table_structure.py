#!/usr/bin/env python3
"""Check the table structure to understand column names."""

import reporting_adv_decl as rad
from sqlalchemy import text

def check_table_structure():
    engine = rad.engine()
    
    print("Checking nse_equity_bhavcopy_full table structure...")
    
    with engine.connect() as conn:
        # Check table structure
        result = conn.execute(text('DESCRIBE nse_equity_bhavcopy_full'))
        print("Column definitions:")
        for row in result:
            print(f"  {row[0]}: {row[1]}")
        
        print("\nChecking actual data to see column names...")
        result = conn.execute(text('SELECT * FROM nse_equity_bhavcopy_full LIMIT 1'))
        columns = result.keys()
        print("Actual column names:")
        for col in columns:
            print(f"  {col}")

if __name__ == "__main__":
    check_table_structure()