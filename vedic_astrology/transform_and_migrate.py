#!/usr/bin/env python3
"""
Transform and migrate planetary position data from vedic_astrology_test to marketdata database
Handles schema differences between the two tables
"""

import mysql.connector
import os
from dotenv import load_dotenv
from datetime import datetime

def transform_and_migrate():
    """Transform data format and migrate from vedic_astrology_test to marketdata"""
    load_dotenv()
    
    conn = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', '')
    )
    
    cursor = conn.cursor()
    
    try:
        print("🔄 Transforming and migrating data...")
        print("   📊 Reading data from vedic_astrology_test...")
        
        # Read data from source
        cursor.execute("USE vedic_astrology_test")
        cursor.execute("""
            SELECT timestamp, sun_position, moon_position, mercury_position, 
                   venus_position, mars_position, jupiter_position, saturn_position, 
                   rahu_position, ketu_position 
            FROM planetary_positions 
            ORDER BY timestamp
        """)
        
        source_data = cursor.fetchall()
        print(f"   📝 Found {len(source_data):,} records to transform")
        
        # Clear existing data in marketdata
        cursor.execute("USE marketdata")
        cursor.execute("DELETE FROM planetary_positions")
        print("   🧹 Cleared existing data in marketdata")
        
        # Transform and insert data in batches
        batch_size = 1000
        total_inserted = 0
        
        for i in range(0, len(source_data), batch_size):
            batch = source_data[i:i + batch_size]
            
            # Prepare batch insert
            insert_query = """
                INSERT INTO planetary_positions 
                (timestamp, year, month, day, hour, minute,
                 sun_longitude, sun_sign, sun_degree,
                 moon_longitude, moon_sign, moon_degree,
                 mercury_longitude, mercury_sign, mercury_degree,
                 venus_longitude, venus_sign, venus_degree,
                 mars_longitude, mars_sign, mars_degree,
                 jupiter_longitude, jupiter_sign, jupiter_degree,
                 saturn_longitude, saturn_sign, saturn_degree,
                 rahu_longitude, rahu_sign, rahu_degree,
                 ketu_longitude, ketu_sign, ketu_degree,
                 created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                        %s, %s, %s, %s, %s, %s)
            """
            
            batch_values = []
            for row in batch:
                timestamp = row[0]
                positions = row[1:10]  # sun through ketu positions
                
                # Extract date/time components
                year = timestamp.year
                month = timestamp.month
                day = timestamp.day
                hour = timestamp.hour
                minute = timestamp.minute
                
                # Transform positions to longitude/sign/degree format
                transformed_row = [
                    timestamp, year, month, day, hour, minute
                ]
                
                # Convert each planetary position
                signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
                        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
                
                for pos in positions:
                    longitude = float(pos) if pos else 0.0
                    sign_index = int(longitude / 30) % 12
                    sign = signs[sign_index]
                    degree = longitude % 30
                    
                    transformed_row.extend([longitude, sign, degree])
                
                # Add timestamps
                now = datetime.now()
                transformed_row.extend([now, now])
                
                batch_values.append(transformed_row)
            
            # Execute batch insert
            cursor.executemany(insert_query, batch_values)
            total_inserted += len(batch_values)
            
            print(f"   ✅ Inserted batch {i//batch_size + 1}/{(len(source_data) + batch_size - 1)//batch_size} "
                  f"({total_inserted:,}/{len(source_data):,} records)")
        
        # Commit all changes
        conn.commit()
        
        # Verify the migration
        cursor.execute("SELECT COUNT(*) FROM marketdata.planetary_positions")
        final_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM marketdata.planetary_positions WHERE YEAR(timestamp) = 2025")
        count_2025 = cursor.fetchone()[0]
        
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM marketdata.planetary_positions")
        date_range = cursor.fetchone()
        
        print(f"\n🎉 Migration Complete!")
        print(f"   📊 Total records in marketdata: {final_count:,}")
        print(f"   📅 2025 records: {count_2025:,}")
        print(f"   🕐 Date range: {date_range[0]} to {date_range[1]}")
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        conn.rollback()
        raise
    
    finally:
        cursor.close()
        conn.close()

def verify_migration():
    """Verify the migration was successful"""
    load_dotenv()
    
    conn = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', '')
    )
    
    cursor = conn.cursor()
    
    print("\n📋 VERIFICATION:")
    print("=" * 40)
    
    try:
        cursor.execute("USE marketdata")
        
        # Check total records
        cursor.execute("SELECT COUNT(*) FROM planetary_positions")
        total = cursor.fetchone()[0]
        print(f"Total records: {total:,}")
        
        # Check 2025 data
        cursor.execute("SELECT COUNT(*) FROM planetary_positions WHERE YEAR(timestamp) = 2025")
        count_2025 = cursor.fetchone()[0]
        print(f"2025 records: {count_2025:,}")
        
        # Show sample data
        cursor.execute("""
            SELECT timestamp, sun_longitude, sun_sign, moon_longitude, moon_sign 
            FROM planetary_positions 
            WHERE YEAR(timestamp) = 2025 
            ORDER BY timestamp 
            LIMIT 3
        """)
        samples = cursor.fetchall()
        
        print("Sample 2025 data:")
        for sample in samples:
            print(f"  {sample[0]} - Sun: {sample[1]}° in {sample[2]}, Moon: {sample[3]}° in {sample[4]}")
            
    except Exception as e:
        print(f"Error during verification: {e}")
    
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("🔄 PLANETARY DATA TRANSFORMATION & MIGRATION")
    print("=" * 60)
    print("Transforming data from vedic_astrology_test format to marketdata format...")
    
    transform_and_migrate()
    verify_migration()
    
    print("\n✅ Your GUI should now see all 2025 planetary position data!")
    print("   The data has been properly transformed to match the marketdata schema.")