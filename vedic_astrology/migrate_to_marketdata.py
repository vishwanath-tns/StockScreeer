#!/usr/bin/env python3
"""Move planetary position data from vedic_astrology_test to marketdata database"""

import mysql.connector
import os
from dotenv import load_dotenv

def check_databases():
    """Check current state of both databases"""
    load_dotenv()
    
    conn = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', '')
    )
    
    cursor = conn.cursor()
    
    print("📊 Database Status Check:")
    print("=" * 50)
    
    # Check vedic_astrology_test database
    print("\n🔍 vedic_astrology_test database:")
    try:
        cursor.execute("USE vedic_astrology_test")
        cursor.execute("SELECT COUNT(*) FROM planetary_positions")
        test_records = cursor.fetchone()[0]
        print(f"   Records: {test_records:,}")
        
        if test_records > 0:
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM planetary_positions")
            test_range = cursor.fetchone()
            print(f"   Range: {test_range[0]} to {test_range[1]}")
            
            # Check 2025 data specifically
            cursor.execute("SELECT COUNT(*) FROM planetary_positions WHERE YEAR(timestamp) = 2025")
            records_2025 = cursor.fetchone()[0]
            print(f"   2025 Records: {records_2025:,}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Check marketdata database
    print("\n🔍 marketdata database:")
    try:
        cursor.execute("USE marketdata")
        cursor.execute("SHOW TABLES LIKE 'planetary_positions'")
        table_exists = cursor.fetchone()
        
        if table_exists:
            cursor.execute("SELECT COUNT(*) FROM planetary_positions")
            market_records = cursor.fetchone()[0]
            print(f"   Records: {market_records:,}")
            
            if market_records > 0:
                cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM planetary_positions")
                market_range = cursor.fetchone()
                print(f"   Range: {market_range[0]} to {market_range[1]}")
                
                # Check 2025 data specifically
                cursor.execute("SELECT COUNT(*) FROM planetary_positions WHERE YEAR(timestamp) = 2025")
                market_2025 = cursor.fetchone()[0]
                print(f"   2025 Records: {market_2025:,}")
        else:
            print("   planetary_positions table does not exist")
    except Exception as e:
        print(f"   Error: {e}")
    
    cursor.close()
    conn.close()

def create_table_in_marketdata():
    """Create planetary_positions table in marketdata if it doesn't exist"""
    load_dotenv()
    
    conn = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', '')
    )
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("USE marketdata")
        
        # Check if table exists
        cursor.execute("SHOW TABLES LIKE 'planetary_positions'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("🔧 Creating planetary_positions table in marketdata...")
            
            # Get the table structure from vedic_astrology_test
            cursor.execute("USE vedic_astrology_test")
            cursor.execute("SHOW CREATE TABLE planetary_positions")
            create_statement = cursor.fetchone()[1]
            
            # Create table in marketdata
            cursor.execute("USE marketdata")
            cursor.execute(create_statement)
            print("   ✅ Table created successfully")
        else:
            print("✅ planetary_positions table already exists in marketdata")
            
    except Exception as e:
        print(f"❌ Error creating table: {e}")
    
    cursor.close()
    conn.close()

def move_data():
    """Move all data from vedic_astrology_test to marketdata"""
    load_dotenv()
    
    conn = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', '')
    )
    
    cursor = conn.cursor()
    
    try:
        print("\n🚀 Moving data from vedic_astrology_test to marketdata...")
        
        # Clear existing data in marketdata (if any)
        cursor.execute("USE marketdata")
        cursor.execute("DELETE FROM planetary_positions")
        print("   🧹 Cleared existing data in marketdata")
        
        # Copy all data from vedic_astrology_test to marketdata
        copy_query = """
        INSERT INTO marketdata.planetary_positions 
        SELECT * FROM vedic_astrology_test.planetary_positions
        """
        
        cursor.execute(copy_query)
        conn.commit()
        
        # Verify the copy
        cursor.execute("SELECT COUNT(*) FROM marketdata.planetary_positions")
        copied_records = cursor.fetchone()[0]
        print(f"   ✅ Successfully copied {copied_records:,} records")
        
        # Check 2025 data specifically
        cursor.execute("SELECT COUNT(*) FROM marketdata.planetary_positions WHERE YEAR(timestamp) = 2025")
        copied_2025 = cursor.fetchone()[0]
        print(f"   📅 2025 records copied: {copied_2025:,}")
        
        # Show date range
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM marketdata.planetary_positions")
        date_range = cursor.fetchone()
        print(f"   📊 Date range: {date_range[0]} to {date_range[1]}")
        
    except Exception as e:
        print(f"❌ Error moving data: {e}")
        conn.rollback()
    
    cursor.close()
    conn.close()

def cleanup_test_database():
    """Optionally remove data from vedic_astrology_test after successful move"""
    load_dotenv()
    
    response = input("\n❓ Do you want to clear the data from vedic_astrology_test database? (y/n): ")
    if response.lower() == 'y':
        conn = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', '')
        )
        
        cursor = conn.cursor()
        
        try:
            cursor.execute("USE vedic_astrology_test")
            cursor.execute("DELETE FROM planetary_positions")
            conn.commit()
            print("   ✅ Cleared data from vedic_astrology_test")
        except Exception as e:
            print(f"   ❌ Error clearing test database: {e}")
        
        cursor.close()
        conn.close()
    else:
        print("   ℹ️  Keeping data in vedic_astrology_test as backup")

if __name__ == "__main__":
    print("🔄 PLANETARY DATA MIGRATION TOOL")
    print("=" * 60)
    
    # Step 1: Check current state
    check_databases()
    
    # Step 2: Create table if needed
    create_table_in_marketdata()
    
    # Step 3: Move the data
    move_data()
    
    # Step 4: Final verification
    print("\n" + "=" * 60)
    print("📋 FINAL VERIFICATION:")
    check_databases()
    
    # Step 5: Optional cleanup
    cleanup_test_database()
    
    print("\n🎉 Migration Complete! Your GUI should now see all the 2025 data.")