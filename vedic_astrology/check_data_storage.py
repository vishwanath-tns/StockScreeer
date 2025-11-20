#!/usr/bin/env python3
"""Check where planetary position data is stored - MySQL vs SQLite"""

import sqlite3
import mysql.connector
import os
from dotenv import load_dotenv

def check_sqlite_databases():
    """Check SQLite databases for data"""
    print("=" * 60)
    print("CHECKING SQLITE DATABASES")
    print("=" * 60)
    
    db_files = ['planetary_positions.db', 'historical_planetary_data.db']
    
    for db_file in db_files:
        if os.path.exists(db_file):
            print(f"\n🗃️  Checking {db_file}:")
            try:
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                
                # Get table names
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                table_names = [table[0] for table in tables]
                print(f"   Tables: {table_names}")
                
                # Check planetary_positions table if it exists
                if 'planetary_positions' in table_names:
                    cursor.execute('SELECT COUNT(*) FROM planetary_positions')
                    total_records = cursor.fetchone()[0]
                    print(f"   📊 Total Records: {total_records:,}")
                    
                    if total_records > 0:
                        cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM planetary_positions')
                        date_range = cursor.fetchone()
                        print(f"   📅 Date Range: {date_range[0]} to {date_range[1]}")
                        
                        # Check for 2025 data
                        cursor.execute("SELECT COUNT(*) FROM planetary_positions WHERE timestamp LIKE '2025%'")
                        records_2025 = cursor.fetchone()[0]
                        print(f"   🎯 2025 Records: {records_2025:,}")
                        
                        # Show recent entries
                        cursor.execute('SELECT timestamp, sun_position, moon_position FROM planetary_positions ORDER BY timestamp DESC LIMIT 3')
                        recent = cursor.fetchall()
                        print(f"   🕐 Recent Records:")
                        for record in recent:
                            print(f"      {record[0]} - Sun: {record[1]}°, Moon: {record[2]}°")
                else:
                    print("   ❌ No planetary_positions table found")
                
                conn.close()
                
            except Exception as e:
                print(f"   ❌ Error reading {db_file}: {e}")
        else:
            print(f"🚫 {db_file} does not exist")

def check_mysql_database():
    """Check MySQL database for data"""
    print("\n" + "=" * 60)
    print("CHECKING MYSQL DATABASE")
    print("=" * 60)
    
    load_dotenv()
    
    try:
        conn = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            database=os.getenv('MYSQL_DATABASE', 'vedic_astrology_test')
        )
        
        cursor = conn.cursor()
        print(f"✅ Connected to MySQL database: {os.getenv('MYSQL_DATABASE', 'vedic_astrology_test')}")
        
        # Check if table exists
        cursor.execute("SHOW TABLES LIKE 'planetary_positions'")
        table_exists = cursor.fetchone()
        
        if table_exists:
            print("✅ planetary_positions table exists")
            
            # Check total records
            cursor.execute('SELECT COUNT(*) FROM planetary_positions')
            total_records = cursor.fetchone()[0]
            print(f"📊 Total Records: {total_records:,}")
            
            if total_records > 0:
                # Check date range
                cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM planetary_positions')
                date_range = cursor.fetchone()
                print(f"📅 Date Range: {date_range[0]} to {date_range[1]}")
                
                # Check 2025 specific data
                cursor.execute('SELECT COUNT(*) FROM planetary_positions WHERE YEAR(timestamp) = 2025')
                records_2025 = cursor.fetchone()[0]
                print(f"🎯 2025 Records: {records_2025:,}")
                
                # Check most recent records
                cursor.execute('SELECT timestamp, sun_position, moon_position FROM planetary_positions ORDER BY timestamp DESC LIMIT 3')
                recent = cursor.fetchall()
                print(f"🕐 Most Recent Records:")
                for record in recent:
                    print(f"   {record[0]} - Sun: {record[1]}°, Moon: {record[2]}°")
            else:
                print("⚠️  Table exists but contains no data")
        else:
            print("❌ planetary_positions table does not exist")
        
        cursor.close()
        conn.close()
        
    except mysql.connector.Error as e:
        print(f"❌ MySQL Connection Error: {e}")
        print("   Make sure MySQL is running and credentials are correct")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")

def check_environment():
    """Check environment configuration"""
    print("\n" + "=" * 60)
    print("CHECKING ENVIRONMENT CONFIGURATION")
    print("=" * 60)
    
    load_dotenv()
    
    print(f"MYSQL_HOST: {os.getenv('MYSQL_HOST', 'localhost')}")
    print(f"MYSQL_PORT: {os.getenv('MYSQL_PORT', 3306)}")
    print(f"MYSQL_DATABASE: {os.getenv('MYSQL_DATABASE', 'vedic_astrology_test')}")
    print(f"MYSQL_USER: {os.getenv('MYSQL_USER', 'root')}")
    print(f"MYSQL_PASSWORD: {'*' * len(os.getenv('MYSQL_PASSWORD', '')) if os.getenv('MYSQL_PASSWORD') else 'Not set'}")

if __name__ == "__main__":
    check_environment()
    check_sqlite_databases()
    check_mysql_database()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("Data can be stored in either:")
    print("1. SQLite databases (planetary_positions.db, historical_planetary_data.db)")
    print("2. MySQL database (vedic_astrology_test.planetary_positions)")
    print("Check the output above to see where your 2025 data is located.")