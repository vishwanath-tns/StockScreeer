#!/usr/bin/env python3
"""Check the trend_analysis table structure."""

import reporting_adv_decl as rad
from sqlalchemy import text

def check_trend_table_structure():
    engine = rad.engine()
    
    print("Checking trend_analysis table structure...")
    
    with engine.connect() as conn:
        # Check table structure
        result = conn.execute(text('DESCRIBE trend_analysis'))
        print("Column definitions:")
        for row in result:
            print(f"  {row[0]}: {row[1]}")

if __name__ == "__main__":
    check_trend_table_structure()