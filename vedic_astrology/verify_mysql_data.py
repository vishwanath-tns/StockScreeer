#!/usr/bin/env python3
"""
MySQL Database Verification for Planetary Positions
Quick verification of the 6-month collection
"""

import pymysql
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def verify_mysql_data():
    """Verify the MySQL planetary data"""
    
    # MySQL connection
    mysql_config = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', 3306)),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', ''),
        'database': os.getenv('MYSQL_DB', 'stock_screener'),
        'charset': 'utf8mb4'
    }
    
    print("""
╔══════════════════════════════════════════════════════════════════╗
║              📊 MySQL Planetary Data Verification               ║
║                      6 Months Collection                        ║
╚══════════════════════════════════════════════════════════════════╝
""")
    
    try:
        conn = pymysql.connect(**mysql_config)
        cursor = conn.cursor()
        
        # Basic stats
        print(f"🔗 Connected to MySQL: {mysql_config['host']}:{mysql_config['port']}")
        print(f"📋 Database: {mysql_config['database']}")
        
        # Record count
        cursor.execute("SELECT COUNT(*) FROM planetary_positions")
        total_count = cursor.fetchone()[0]
        print(f"📊 Total records: {total_count:,}")
        
        # Date range
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM planetary_positions")
        min_date, max_date = cursor.fetchone()
        print(f"📅 Date range: {min_date} to {max_date}")
        
        # Check for gaps
        cursor.execute("""
        SELECT COUNT(*) as expected_count
        FROM (
            SELECT DATE_ADD('2024-01-01', INTERVAL (a.a + 10*b.a + 100*c.a + 1000*d.a) MINUTE) as minute_time
            FROM (SELECT 0 AS a UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9) AS a
            CROSS JOIN (SELECT 0 AS a UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9) AS b
            CROSS JOIN (SELECT 0 AS a UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9) AS c
            CROSS JOIN (SELECT 0 AS a UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9) AS d
            WHERE DATE_ADD('2024-01-01', INTERVAL (a.a + 10*b.a + 100*c.a + 1000*d.a) MINUTE) < '2024-07-01'
        ) AS minutes
        """)
        expected_count = cursor.fetchone()[0]
        
        coverage = (total_count / expected_count) * 100
        print(f"📈 Expected: {expected_count:,} minutes")
        print(f"🎯 Coverage: {coverage:.2f}%")
        
        if coverage >= 99.9:
            print(f"✅ EXCELLENT: Nearly perfect coverage!")
        elif coverage >= 95:
            print(f"✅ GOOD: High coverage")
        else:
            print(f"⚠️  Coverage needs improvement")
        
        # Sample data
        print(f"\n🔍 Sample Records (Latest 5):")
        cursor.execute("""
        SELECT timestamp, sun_longitude, sun_sign, moon_longitude, moon_sign, 
               mars_longitude, jupiter_longitude, saturn_longitude
        FROM planetary_positions 
        ORDER BY timestamp DESC LIMIT 5
        """)
        
        samples = cursor.fetchall()
        for i, sample in enumerate(samples, 1):
            timestamp, sun_lon, sun_sign, moon_lon, moon_sign, mars_lon, jupiter_lon, saturn_lon = sample
            print(f"   {i}. {timestamp}")
            print(f"      Sun: {sun_lon:.2f}° in {sun_sign}")
            print(f"      Moon: {moon_lon:.2f}° in {moon_sign}")
            print(f"      Mars: {mars_lon:.2f}°, Jupiter: {jupiter_lon:.2f}°, Saturn: {saturn_lon:.2f}°")
        
        # Data quality check
        print(f"\n🔍 Data Quality Check:")
        cursor.execute("SELECT COUNT(*) FROM planetary_positions WHERE sun_longitude IS NULL OR sun_longitude = 0")
        null_sun = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM planetary_positions WHERE moon_longitude IS NULL OR moon_longitude = 0")
        null_moon = cursor.fetchone()[0]
        
        print(f"   Null/Zero Sun positions: {null_sun}")
        print(f"   Null/Zero Moon positions: {null_moon}")
        
        if null_sun == 0 and null_moon == 0:
            print(f"✅ Data quality: EXCELLENT")
        else:
            print(f"⚠️  Some data quality issues detected")
        
        # Table structure
        print(f"\n🏗️  Table Structure:")
        cursor.execute("DESCRIBE planetary_positions")
        columns = cursor.fetchall()
        
        for col in columns:
            field, col_type, null, key, default, extra = col
            key_text = f" ({key})" if key else ""
            print(f"   {field:<20} {col_type:<20}{key_text}")
        
        conn.close()
        
        print(f"\n🎉 MySQL verification complete!")
        print(f"💡 Ready for trading analysis and longer duration collections!")
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")

if __name__ == "__main__":
    verify_mysql_data()