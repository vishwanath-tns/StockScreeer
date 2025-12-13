#!/usr/bin/env python3
"""
Query database for NIFTY and BANKNIFTY weekly options
"""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

# Create database connection
engine = create_engine(
    f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}"
    f"@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT', '3306')}/{os.getenv('MYSQL_DB')}"
)

with engine.connect() as conn:
    # Query for NIFTY and BANKNIFTY options
    query = text("""
        SELECT 
            symbol,
            name,
            expiry_date,
            strike_price,
            option_type,
            instrument_id,
            segment
        FROM nse_security_master
        WHERE (symbol LIKE 'NIFTY%' OR symbol LIKE 'BANKNIFTY%')
        AND segment = 'OPT'
        AND expiry_date >= CURDATE()
        ORDER BY expiry_date, symbol, strike_price
    """)
    
    result = conn.execute(query)
    rows = result.fetchall()
    
    if not rows:
        print("No NIFTY/BANKNIFTY options found in database")
        print("\nLet's check what symbols are available:")
        
        query2 = text("""
            SELECT DISTINCT symbol, segment, expiry_date
            FROM nse_security_master
            WHERE (symbol LIKE 'NIFTY%' OR symbol LIKE 'BANKNIFTY%' OR symbol LIKE 'FINNIFTY%')
            ORDER BY symbol, expiry_date
        """)
        result2 = conn.execute(query2)
        for row in result2:
            print(f"{row[0]:<20} {row[1]:<10} {str(row[2]):<15}")
    else:
        print("\n" + "="*120)
        print("NIFTY AND BANKNIFTY OPTIONS - ALL AVAILABLE")
        print("="*120)
        print(f"{'Symbol':<25} {'Expiry Date':<15} {'Strike':<10} {'Type':<6} {'Inst ID':<12}")
        print("-"*120)
        
        # Group by expiry date
        current_expiry = None
        for row in rows:
            symbol, name, expiry_date, strike_price, option_type, instrument_id, segment = row
            if current_expiry != expiry_date:
                if current_expiry is not None:
                    print()
                current_expiry = expiry_date
                days_left = (expiry_date - datetime.now().date()).days
                print(f"\n--- Expiring {expiry_date} ({days_left} days) ---")
            
            print(f"{symbol:<25} {str(expiry_date):<15} {str(strike_price):<10} {option_type:<6} {str(instrument_id):<12}")
        
        # Summary
        print("\n" + "="*120)
        today = datetime.now().date()
        next_week_start = today + timedelta(days=1)
        next_week_end = next_week_start + timedelta(days=6)
        
        print(f"\nTODAY: {today} ({datetime.now().strftime('%A')})")
        print(f"NEXT WEEK: {next_week_start} to {next_week_end}")
        
        # Filter for next week
        nifty_weekly = [r for r in rows if next_week_start <= r[2] <= next_week_end and 'NIFTY' in r[0] and 'BANKNIFTY' not in r[0]]
        banknifty_weekly = [r for r in rows if next_week_start <= r[2] <= next_week_end and 'BANKNIFTY' in r[0]]
        
        print(f"\nNIFTY options expiring next week: {len(nifty_weekly)}")
        print(f"BANKNIFTY options expiring next week: {len(banknifty_weekly)}")
        
        if nifty_weekly:
            print(f"\nNIFTY Weekly Expiry Options:")
            for r in nifty_weekly[:10]:  # Show first 10
                print(f"  {r[0]:<25} Strike={str(r[3]):<8} {r[4]:<4} ID={r[5]}")
            if len(nifty_weekly) > 10:
                print(f"  ... and {len(nifty_weekly) - 10} more")
        
        if banknifty_weekly:
            print(f"\nBANKNIFTY Weekly Expiry Options:")
            for r in banknifty_weekly[:10]:  # Show first 10
                print(f"  {r[0]:<25} Strike={str(r[3]):<8} {r[4]:<4} ID={r[5]}")
            if len(banknifty_weekly) > 10:
                print(f"  ... and {len(banknifty_weekly) - 10} more")
