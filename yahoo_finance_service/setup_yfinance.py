#!/usr/bin/env python3
"""
Setup script for Yahoo Finance Service
Initializes database tables and validates configuration
"""

import sys
import os
import mysql.connector
from mysql.connector import Error

# Add service directory to path
service_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, service_dir)
parent_dir = os.path.dirname(service_dir)
sys.path.insert(0, parent_dir)

from yahoo_finance_service.config import YFinanceConfig
from yahoo_finance_service.db_service import YFinanceDBService
from yahoo_finance_service.yahoo_client import YahooFinanceClient

def test_database_connection():
    """Test database connection"""
    print("🔍 Testing database connection...")
    
    try:
        config = YFinanceConfig.get_db_config()
        conn = mysql.connector.connect(**config)
        
        if conn.is_connected():
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            print(f"✅ Connected to MySQL database: {version}")
            
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()[0]
            print(f"✅ Current database: {db_name}")
            
            cursor.close()
            conn.close()
            return True
            
    except Error as e:
        print(f"❌ Database connection failed: {e}")
        return False

def initialize_schema():
    """Initialize database schema"""
    print("\n🏗️  Initializing database schema...")
    
    try:
        db_service = YFinanceDBService()
        success = db_service.initialize_database()
        
        if success:
            print("✅ Database schema initialized successfully")
            return True
        else:
            print("⚠️  Schema initialization completed with warnings")
            return True
            
    except Exception as e:
        print(f"❌ Schema initialization failed: {e}")
        return False

def test_yahoo_finance_api():
    """Test Yahoo Finance API connection"""
    print("\n🌐 Testing Yahoo Finance API...")
    
    try:
        client = YahooFinanceClient()
        
        # Test symbol validation
        is_valid = client.validate_symbol('NIFTY')
        if is_valid:
            print("✅ NIFTY symbol validation successful")
        else:
            print("⚠️  NIFTY symbol validation failed")
        
        # Test getting symbol info
        info = client.get_symbol_info('NIFTY')
        print(f"✅ Symbol info retrieved: {info['name']} ({info['yahoo_symbol']})")
        
        return True
        
    except Exception as e:
        print(f"❌ Yahoo Finance API test failed: {e}")
        return False

def check_dependencies():
    """Check required dependencies"""
    print("\n📦 Checking dependencies...")
    
    required_packages = [
        'yfinance',
        'mysql-connector-python', 
        'pandas',
        'python-dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - Missing")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Install with: pip install " + " ".join(missing_packages))
        return False
    
    return True

def display_configuration():
    """Display current configuration"""
    print("\n⚙️  Configuration:")
    print(f"   MySQL Host: {YFinanceConfig.MYSQL_HOST}")
    print(f"   MySQL Port: {YFinanceConfig.MYSQL_PORT}")
    print(f"   MySQL Database: {YFinanceConfig.MYSQL_DATABASE}")
    print(f"   Default Symbol: {YFinanceConfig.DEFAULT_SYMBOL}")
    print(f"   Yahoo Symbol: {YFinanceConfig.DEFAULT_YAHOO_SYMBOL}")
    print(f"   Default Timeframe: {YFinanceConfig.DEFAULT_TIMEFRAME}")

def main():
    """Main setup function"""
    print("🚀 Yahoo Finance Service Setup")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Setup failed: Missing dependencies")
        return False
    
    # Display configuration
    display_configuration()
    
    # Test database connection
    if not test_database_connection():
        print("\n❌ Setup failed: Database connection failed")
        return False
    
    # Initialize schema
    if not initialize_schema():
        print("\n❌ Setup failed: Schema initialization failed")
        return False
    
    # Test Yahoo Finance API
    if not test_yahoo_finance_api():
        print("\n⚠️  Setup completed with warnings: Yahoo Finance API test failed")
        print("   This might be due to network issues or API limits")
    
    print("\n" + "=" * 50)
    print("✅ Setup completed successfully!")
    print("\nNext steps:")
    print("1. Run: python launch_downloader.py")
    print("2. Select date range and download NIFTY data")
    print("3. View data in the preview panel")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)