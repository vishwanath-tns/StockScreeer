#!/usr/bin/env python3
"""
Insert initial NSE to Yahoo Finance symbol mappings
"""

import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def insert_initial_mappings():
    """Insert initial symbol mappings"""
    
    # Initial mappings for major stocks (NSE symbol -> Yahoo Finance symbol)
    initial_mappings = [
        # Major IT stocks
        ('TCS', 'TCS.NS', 'Tata Consultancy Services', 'IT', 'LARGE_CAP'),
        ('INFY', 'INFY.NS', 'Infosys Limited', 'IT', 'LARGE_CAP'),
        ('WIPRO', 'WIPRO.NS', 'Wipro Limited', 'IT', 'LARGE_CAP'),
        ('HCLTECH', 'HCLTECH.NS', 'HCL Technologies Limited', 'IT', 'LARGE_CAP'),
        ('TECHM', 'TECHM.NS', 'Tech Mahindra Limited', 'IT', 'LARGE_CAP'),
        
        # Banking stocks
        ('HDFCBANK', 'HDFCBANK.NS', 'HDFC Bank Limited', 'Banking', 'LARGE_CAP'),
        ('ICICIBANK', 'ICICIBANK.NS', 'ICICI Bank Limited', 'Banking', 'LARGE_CAP'),
        ('AXISBANK', 'AXISBANK.NS', 'Axis Bank Limited', 'Banking', 'LARGE_CAP'),
        ('SBIN', 'SBIN.NS', 'State Bank of India', 'Banking', 'LARGE_CAP'),
        ('KOTAKBANK', 'KOTAKBANK.NS', 'Kotak Mahindra Bank Limited', 'Banking', 'LARGE_CAP'),
        
        # Auto stocks
        ('MARUTI', 'MARUTI.NS', 'Maruti Suzuki India Limited', 'Automobile', 'LARGE_CAP'),
        ('M&M', 'M&M.NS', 'Mahindra & Mahindra Limited', 'Automobile', 'LARGE_CAP'),
        ('TATAMOTORS', 'TATAMOTORS.NS', 'Tata Motors Limited', 'Automobile', 'LARGE_CAP'),
        ('BAJAJ-AUTO', 'BAJAJ-AUTO.NS', 'Bajaj Auto Limited', 'Automobile', 'LARGE_CAP'),
        ('HEROMOTOCO', 'HEROMOTOCO.NS', 'Hero MotoCorp Limited', 'Automobile', 'LARGE_CAP'),
        
        # Pharma stocks
        ('SUNPHARMA', 'SUNPHARMA.NS', 'Sun Pharmaceutical Industries Limited', 'Pharmaceuticals', 'LARGE_CAP'),
        ('DRREDDY', 'DRREDDY.NS', 'Dr. Reddys Laboratories Limited', 'Pharmaceuticals', 'LARGE_CAP'),
        ('CIPLA', 'CIPLA.NS', 'Cipla Limited', 'Pharmaceuticals', 'LARGE_CAP'),
        ('DIVISLAB', 'DIVISLAB.NS', 'Divis Laboratories Limited', 'Pharmaceuticals', 'LARGE_CAP'),
        ('APOLLOHOSP', 'APOLLOHOSP.NS', 'Apollo Hospitals Enterprise Limited', 'Healthcare', 'LARGE_CAP'),
        
        # FMCG stocks
        ('HINDUNILVR', 'HINDUNILVR.NS', 'Hindustan Unilever Limited', 'FMCG', 'LARGE_CAP'),
        ('NESTLEIND', 'NESTLEIND.NS', 'Nestle India Limited', 'FMCG', 'LARGE_CAP'),
        ('BRITANNIA', 'BRITANNIA.NS', 'Britannia Industries Limited', 'FMCG', 'LARGE_CAP'),
        ('ITC', 'ITC.NS', 'ITC Limited', 'FMCG', 'LARGE_CAP'),
        ('DABUR', 'DABUR.NS', 'Dabur India Limited', 'FMCG', 'MID_CAP'),
        
        # Telecom & Energy
        ('BHARTIARTL', 'BHARTIARTL.NS', 'Bharti Airtel Limited', 'Telecom', 'LARGE_CAP'),
        ('RELIANCE', 'RELIANCE.NS', 'Reliance Industries Limited', 'Oil & Gas', 'LARGE_CAP'),
        ('ONGC', 'ONGC.NS', 'Oil and Natural Gas Corporation Limited', 'Oil & Gas', 'LARGE_CAP'),
        ('IOCL', 'IOC.NS', 'Indian Oil Corporation Limited', 'Oil & Gas', 'LARGE_CAP'),
        ('BPCL', 'BPCL.NS', 'Bharat Petroleum Corporation Limited', 'Oil & Gas', 'LARGE_CAP'),
        
        # Metals & Mining
        ('TATASTEEL', 'TATASTEEL.NS', 'Tata Steel Limited', 'Metals', 'LARGE_CAP'),
        ('HINDALCO', 'HINDALCO.NS', 'Hindalco Industries Limited', 'Metals', 'LARGE_CAP'),
        ('JSWSTEEL', 'JSWSTEEL.NS', 'JSW Steel Limited', 'Metals', 'LARGE_CAP'),
        ('COALINDIA', 'COALINDIA.NS', 'Coal India Limited', 'Mining', 'LARGE_CAP'),
        ('SAIL', 'SAIL.NS', 'Steel Authority of India Limited', 'Metals', 'LARGE_CAP'),
    ]
    
    try:
        conn = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            database='marketdata'
        )
        
        cursor = conn.cursor()
        
        print(f"📋 Inserting {len(initial_mappings)} initial symbol mappings...")
        
        insert_sql = """
        INSERT INTO nse_yahoo_symbol_map 
        (nse_symbol, yahoo_symbol, company_name, sector, market_cap_category, is_active)
        VALUES (%s, %s, %s, %s, %s, TRUE)
        ON DUPLICATE KEY UPDATE
            yahoo_symbol = VALUES(yahoo_symbol),
            company_name = VALUES(company_name),
            sector = VALUES(sector),
            market_cap_category = VALUES(market_cap_category),
            is_active = VALUES(is_active),
            updated_at = CURRENT_TIMESTAMP
        """
        
        success_count = 0
        for mapping in initial_mappings:
            try:
                cursor.execute(insert_sql, mapping)
                success_count += 1
                print(f"  ✅ {mapping[0]} → {mapping[1]}")
            except Exception as e:
                print(f"  ❌ Failed to insert {mapping[0]}: {e}")
        
        # Update statistics
        cursor.execute("SELECT COUNT(*) FROM nse_yahoo_symbol_map")
        total_mapped = cursor.fetchone()[0]
        
        cursor.execute("""
            UPDATE symbol_mapping_stats 
            SET mapped_symbols = %s, 
                coverage_percentage = 100.000,
                last_validation_run = CURRENT_TIMESTAMP,
                notes = 'Initial mappings created for major stocks'
            ORDER BY id DESC LIMIT 1
        """, (total_mapped,))
        
        conn.commit()
        
        print(f"\n✅ Successfully inserted {success_count}/{len(initial_mappings)} mappings")
        print(f"📊 Total mappings in database: {total_mapped}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error inserting mappings: {e}")
        return False

if __name__ == "__main__":
    print("🚀 NSE to Yahoo Finance Initial Symbol Mappings")
    print("=" * 60)
    
    if insert_initial_mappings():
        print("\n✅ Initial mappings setup completed!")
        print("\n📋 Next steps:")
        print("1. Run validate_symbol_mapping.py to test the mappings")
        print("2. Use the validated mappings for bulk data download")
    else:
        print("\n❌ Setup failed!")