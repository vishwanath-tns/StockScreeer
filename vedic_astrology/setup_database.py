"""
Database Setup Script for Planetary Position System

This script helps set up the MySQL database and table for the planetary position system.
Run this if you encounter database connection errors.

Author: AI Assistant
Date: November 20, 2025
"""

import mysql.connector
import os
from dotenv import load_dotenv

def setup_database():
    """Set up the database and table for planetary positions."""
    
    # Load environment variables
    load_dotenv()
    
    print("🔧 Setting up Planetary Position Database...")
    print("=" * 60)
    
    # Get configuration
    host = os.getenv('MYSQL_HOST', 'localhost')
    port = int(os.getenv('MYSQL_PORT', 3306))
    user = os.getenv('MYSQL_USER', 'root')
    password = os.getenv('MYSQL_PASSWORD', '')
    database_name = os.getenv('MYSQL_DATABASE', 'vedic_astrology_test')
    
    print(f"📍 Host: {host}:{port}")
    print(f"👤 User: {user}")
    print(f"🗄️ Database: {database_name}")
    print()
    
    try:
        # Connect to MySQL server (without specifying database)
        print("🔗 Connecting to MySQL server...")
        
        connection = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        print("✅ Connected to MySQL server successfully!")
        
        # Create database
        print(f"\n📝 Creating database '{database_name}'...")
        
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"✅ Database '{database_name}' created/verified!")
        
        # Use the database
        cursor.execute(f"USE `{database_name}`")
        print(f"✅ Using database '{database_name}'")
        
        # Create the planetary_positions table
        print(f"\n🛠️ Creating planetary_positions table...")
        
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS planetary_positions (
            timestamp DATETIME PRIMARY KEY,
            sun_position DECIMAL(8,4) NOT NULL,
            moon_position DECIMAL(8,4) NOT NULL,
            mercury_position DECIMAL(8,4) NOT NULL,
            venus_position DECIMAL(8,4) NOT NULL,
            mars_position DECIMAL(8,4) NOT NULL,
            jupiter_position DECIMAL(8,4) NOT NULL,
            saturn_position DECIMAL(8,4) NOT NULL,
            rahu_position DECIMAL(8,4) NOT NULL,
            ketu_position DECIMAL(8,4) NOT NULL,
            sun_speed DECIMAL(8,4) DEFAULT 0,
            moon_speed DECIMAL(8,4) DEFAULT 0,
            mercury_speed DECIMAL(8,4) DEFAULT 0,
            venus_speed DECIMAL(8,4) DEFAULT 0,
            mars_speed DECIMAL(8,4) DEFAULT 0,
            jupiter_speed DECIMAL(8,4) DEFAULT 0,
            saturn_speed DECIMAL(8,4) DEFAULT 0,
            rahu_speed DECIMAL(8,4) DEFAULT 0,
            ketu_speed DECIMAL(8,4) DEFAULT 0,
            sun_house DECIMAL(8,4) DEFAULT 0,
            moon_house DECIMAL(8,4) DEFAULT 0,
            mercury_house DECIMAL(8,4) DEFAULT 0,
            venus_house DECIMAL(8,4) DEFAULT 0,
            mars_house DECIMAL(8,4) DEFAULT 0,
            jupiter_house DECIMAL(8,4) DEFAULT 0,
            saturn_house DECIMAL(8,4) DEFAULT 0,
            rahu_house DECIMAL(8,4) DEFAULT 0,
            ketu_house DECIMAL(8,4) DEFAULT 0,
            sun_nakshatra DECIMAL(8,4) DEFAULT 0,
            moon_nakshatra DECIMAL(8,4) DEFAULT 0,
            mercury_nakshatra DECIMAL(8,4) DEFAULT 0,
            venus_nakshatra DECIMAL(8,4) DEFAULT 0,
            mars_nakshatra DECIMAL(8,4) DEFAULT 0,
            jupiter_nakshatra DECIMAL(8,4) DEFAULT 0,
            saturn_nakshatra DECIMAL(8,4) DEFAULT 0,
            rahu_nakshatra DECIMAL(8,4) DEFAULT 0,
            ketu_nakshatra DECIMAL(8,4) DEFAULT 0
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        cursor.execute(create_table_sql)
        print("✅ Table 'planetary_positions' created/verified!")
        
        # Check if table has data
        cursor.execute("SELECT COUNT(*) FROM planetary_positions")
        record_count = cursor.fetchone()[0]
        
        if record_count > 0:
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM planetary_positions")
            date_range = cursor.fetchone()
            print(f"\n📊 Existing data found:")
            print(f"   Records: {record_count:,}")
            print(f"   Range: {date_range[0]} to {date_range[1]}")
        else:
            print(f"\n📊 Table is empty - ready for data generation")
        
        # Create index for performance
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON planetary_positions(timestamp)")
            print("✅ Performance index created!")
        except:
            pass  # Index might already exist
        
        # Commit changes
        connection.commit()
        cursor.close()
        connection.close()
        
        print("\n" + "=" * 60)
        print("🎉 DATABASE SETUP COMPLETE!")
        print("✅ Your planetary position system is ready to use!")
        print("\n🚀 You can now:")
        print("   1. Run the Planetary Position Generator GUI")
        print("   2. Run the Planetary Position Viewer")
        print("   3. Generate accurate planetary data")
        print("=" * 60)
        
        return True
        
    except mysql.connector.Error as mysql_error:
        error_code = mysql_error.errno
        error_msg = str(mysql_error)
        
        print(f"\n❌ MySQL Error ({error_code}): {error_msg}")
        
        if error_code == 1045:  # Access denied
            print("\n💡 Solutions for Access Denied:")
            print("   1. Check your MySQL username and password")
            print("   2. Make sure user has CREATE and INSERT permissions")
            print("   3. Try: GRANT ALL PRIVILEGES ON *.* TO 'your_user'@'localhost';")
            
        elif error_code == 2003:  # Connection refused
            print("\n💡 Solutions for Connection Refused:")
            print("   1. Make sure MySQL server is running")
            print("   2. Check if MySQL is running on the correct port")
            print("   3. Try: net start mysql (Windows) or sudo systemctl start mysql (Linux)")
            
        elif error_code == 1049:  # Unknown database
            print("\n💡 This error should not occur with this setup script")
            print("   The script creates the database automatically")
            
        else:
            print("\n💡 General troubleshooting:")
            print("   1. Verify MySQL server is installed and running")
            print("   2. Check your .env file configuration")
            print("   3. Test connection with MySQL client")
        
        return False
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        print("\n💡 Please check:")
        print("   1. MySQL server installation")
        print("   2. Network connectivity")
        print("   3. Firewall settings")
        
        return False

def show_current_config():
    """Show current database configuration."""
    load_dotenv()
    
    print("📋 Current Database Configuration:")
    print("=" * 40)
    print(f"MYSQL_HOST: {os.getenv('MYSQL_HOST', 'localhost')}")
    print(f"MYSQL_PORT: {os.getenv('MYSQL_PORT', '3306')}")
    print(f"MYSQL_USER: {os.getenv('MYSQL_USER', 'root')}")
    print(f"MYSQL_PASSWORD: {'*' * len(os.getenv('MYSQL_PASSWORD', ''))}")
    print(f"MYSQL_DATABASE: {os.getenv('MYSQL_DATABASE', 'vedic_astrology_test')}")
    print("=" * 40)

if __name__ == "__main__":
    print("🌟 Planetary Position Database Setup")
    print("Professional Swiss Ephemeris System")
    print()
    
    show_current_config()
    print()
    
    setup_success = setup_database()
    
    if setup_success:
        print("\n✨ Setup completed successfully!")
        print("You can now use the Planetary Position Generator GUI without database errors.")
    else:
        print("\n❌ Setup failed!")
        print("Please resolve the errors above and try again.")