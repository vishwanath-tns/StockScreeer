#!/usr/bin/env python3
"""
Create Planetary Positions Table in MySQL
This creates the table in your existing MySQL database
"""

import mysql.connector
import os
from datetime import datetime

def create_mysql_planetary_table():
    """Create planetary positions table in MySQL database"""
    
    # MySQL connection details from your .env
    config = {
        'host': 'localhost',
        'port': 3306,
        'database': 'marketdata',
        'user': 'root',
        'password': 'Ganesh@@2283@@'
    }
    
    print("🔗 Connecting to MySQL database...")
    
    try:
        # Connect to MySQL
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        
        print(f"✅ Connected to MySQL: {config['database']}")
        
        # Create planetary_positions table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS planetary_positions (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            timestamp DATETIME UNIQUE NOT NULL,
            year INT NOT NULL,
            month INT NOT NULL,
            day INT NOT NULL,
            hour INT NOT NULL,
            minute INT NOT NULL,
            
            -- Sun data
            sun_longitude DECIMAL(10,6),
            sun_sign VARCHAR(20),
            sun_degree DECIMAL(8,6),
            
            -- Moon data  
            moon_longitude DECIMAL(10,6),
            moon_sign VARCHAR(20),
            moon_degree DECIMAL(8,6),
            
            -- Mercury data
            mercury_longitude DECIMAL(10,6),
            mercury_sign VARCHAR(20),
            mercury_degree DECIMAL(8,6),
            
            -- Venus data
            venus_longitude DECIMAL(10,6),
            venus_sign VARCHAR(20),
            venus_degree DECIMAL(8,6),
            
            -- Mars data
            mars_longitude DECIMAL(10,6),
            mars_sign VARCHAR(20),
            mars_degree DECIMAL(8,6),
            
            -- Jupiter data
            jupiter_longitude DECIMAL(10,6),
            jupiter_sign VARCHAR(20),
            jupiter_degree DECIMAL(8,6),
            
            -- Saturn data
            saturn_longitude DECIMAL(10,6),
            saturn_sign VARCHAR(20),
            saturn_degree DECIMAL(8,6),
            
            -- Rahu data (North node)
            rahu_longitude DECIMAL(10,6),
            rahu_sign VARCHAR(20),
            rahu_degree DECIMAL(8,6),
            
            -- Ketu data (South node)
            ketu_longitude DECIMAL(10,6),
            ketu_sign VARCHAR(20),
            ketu_degree DECIMAL(8,6),
            
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;
        """
        
        print("🏗️  Creating planetary_positions table...")
        cursor.execute(create_table_sql)
        
        # Add indexes for faster queries
        indexes = [
            "CREATE INDEX idx_timestamp ON planetary_positions (timestamp);",
            "CREATE INDEX idx_date ON planetary_positions (year, month, day);", 
            "CREATE INDEX idx_hour_minute ON planetary_positions (hour, minute);",
            "CREATE INDEX idx_created_at ON planetary_positions (created_at);"
        ]
        
        for i, index_sql in enumerate(indexes):
            try:
                print(f"🔍 Creating index {i+1}/{len(indexes)}...")
                cursor.execute(index_sql)
            except mysql.connector.Error as e:
                if "Duplicate key name" in str(e):
                    print(f"   Index already exists, skipping...")
                else:
                    print(f"   Warning: {e}")
        
        # Create progress tracking table
        progress_table_sql = """
        CREATE TABLE IF NOT EXISTS planetary_collection_progress (
            id INT PRIMARY KEY AUTO_INCREMENT,
            last_timestamp DATETIME,
            processed_count BIGINT DEFAULT 0,
            last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            collection_status ENUM('active', 'paused', 'completed') DEFAULT 'active'
        ) ENGINE=InnoDB;
        """
        
        print("📊 Creating progress tracking table...")
        cursor.execute(progress_table_sql)
        
        connection.commit()
        
        # Show table structure
        print("\n✅ MYSQL TABLE CREATED SUCCESSFULLY!")
        print("=" * 60)
        
        cursor.execute("DESCRIBE planetary_positions")
        columns = cursor.fetchall()
        
        print("🏗️  TABLE STRUCTURE: planetary_positions")
        for column in columns:
            field, type_info, null, key, default, extra = column
            key_info = f" ({key})" if key else ""
            print(f"   - {field:<25} {type_info:<20}{key_info}")
        
        # Check if data exists
        cursor.execute("SELECT COUNT(*) FROM planetary_positions")
        count = cursor.fetchone()[0]
        
        print(f"\n📊 Current Records: {count:,}")
        
        if count > 0:
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM planetary_positions")
            result = cursor.fetchone()
            if result[0]:
                print(f"📅 Date Range: {result[0]} to {result[1]}")
        
        print(f"\n🎯 DATABASE LOCATION:")
        print(f"   Host: {config['host']}")
        print(f"   Database: {config['database']}")
        print(f"   Table: planetary_positions")
        
        connection.close()
        
        return True
        
    except mysql.connector.Error as e:
        print(f"❌ MySQL Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def show_table_info():
    """Show existing MySQL tables"""
    config = {
        'host': 'localhost',
        'port': 3306,
        'database': 'marketdata', 
        'user': 'root',
        'password': 'Ganesh@@2283@@'
    }
    
    try:
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        
        print("\n🗄️  EXISTING MYSQL TABLES:")
        print("=" * 60)
        
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"   📋 {table_name:<30} ({count:,} records)")
        
        connection.close()
        
    except mysql.connector.Error as e:
        print(f"❌ MySQL Connection Error: {e}")

def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║           🌟 MySQL Planetary Positions Table Creator            ║
║                    Creates table in your MySQL DB               ║
╚══════════════════════════════════════════════════════════════════╝
""")
    
    # Show existing tables first
    show_table_info()
    
    # Create the planetary table
    if create_mysql_planetary_table():
        print(f"\n🎉 SUCCESS! Planetary positions table created in MySQL")
        print(f"📍 You can now view it in your MySQL database 'marketdata'")
    else:
        print(f"\n❌ Failed to create table. Check your MySQL connection.")

if __name__ == "__main__":
    main()