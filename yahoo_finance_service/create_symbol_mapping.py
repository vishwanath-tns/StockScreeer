#!/usr/bin/env python3
"""
NSE to Yahoo Finance Symbol Mapping System
Creates tables to map NSE symbols to Yahoo Finance symbols
"""

import sys
import os
import mysql.connector
from mysql.connector import Error
import pandas as pd
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

def get_db_connection():
    """Get database connection"""
    try:
        return mysql.connector.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            database='marketdata',
            charset='utf8mb4'
        )
    except Error as e:
        print(f"❌ Database connection failed: {e}")
        raise

def check_existing_tables():
    """Check existing NSE tables structure"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check NSE index constituents table
        print("🔍 Checking NSE index constituents table...")
        try:
            cursor.execute("DESCRIBE nse_index_constituents")
            columns = cursor.fetchall()
            print("✅ NSE Index Constituents table structure:")
            for col in columns:
                print(f"   {col[0]} - {col[1]}")
        except Error as e:
            print(f"❌ NSE index constituents table not found: {e}")
        
        print()
        
        # Check NSE indices table
        print("🔍 Checking NSE indices table...")
        try:
            cursor.execute("DESCRIBE nse_indices")
            columns = cursor.fetchall()
            print("✅ NSE Indices table structure:")
            for col in columns:
                print(f"   {col[0]} - {col[1]}")
        except Error as e:
            print(f"❌ NSE indices table not found: {e}")
        
        print()
        
        # Sample data from NSE tables
        print("📋 Sample data from NSE index constituents:")
        try:
            cursor.execute("SELECT * FROM nse_index_constituents LIMIT 5")
            rows = cursor.fetchall()
            if rows:
                cursor.execute("SHOW COLUMNS FROM nse_index_constituents")
                columns = [col[0] for col in cursor.fetchall()]
                for row in rows:
                    print(f"   {dict(zip(columns, row))}")
            else:
                print("   No data found")
        except Error as e:
            print(f"   Error reading data: {e}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking tables: {e}")

def create_symbol_mapping_tables():
    """Create symbol mapping tables"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("🏗️  Creating symbol mapping tables...")
        
        # Table 1: NSE to Yahoo Finance symbol mapping
        symbol_mapping_sql = """
        CREATE TABLE IF NOT EXISTS nse_yahoo_symbol_map (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nse_symbol VARCHAR(50) NOT NULL,
            yahoo_symbol VARCHAR(50) NOT NULL,
            company_name VARCHAR(255) NULL,
            sector VARCHAR(100) NULL,
            market_cap_category ENUM('LARGE_CAP', 'MID_CAP', 'SMALL_CAP') NULL,
            is_active BOOLEAN DEFAULT TRUE,
            is_verified BOOLEAN DEFAULT FALSE,
            last_verified DATE NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            
            -- Constraints
            UNIQUE KEY uk_nse_symbol (nse_symbol),
            UNIQUE KEY uk_yahoo_symbol (yahoo_symbol),
            
            -- Indexes for performance
            INDEX idx_nse_symbol (nse_symbol),
            INDEX idx_yahoo_symbol (yahoo_symbol),
            INDEX idx_sector (sector),
            INDEX idx_is_active (is_active),
            INDEX idx_is_verified (is_verified),
            INDEX idx_market_cap (market_cap_category)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        COMMENT='Maps NSE symbols to Yahoo Finance symbols for data download';
        """
        
        cursor.execute(symbol_mapping_sql)
        print("✅ Created nse_yahoo_symbol_map table")
        
        # Table 2: Symbol mapping validation log
        validation_log_sql = """
        CREATE TABLE IF NOT EXISTS symbol_mapping_validation_log (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            nse_symbol VARCHAR(50) NOT NULL,
            yahoo_symbol VARCHAR(50) NOT NULL,
            validation_status ENUM('SUCCESS', 'FAILED', 'NOT_FOUND', 'DATA_MISMATCH') NOT NULL,
            validation_method ENUM('API_TEST', 'DATA_DOWNLOAD', 'MANUAL_CHECK') NOT NULL,
            error_message TEXT NULL,
            sample_data_matches BOOLEAN NULL,
            last_trading_date DATE NULL,
            validation_notes TEXT NULL,
            validated_by VARCHAR(100) DEFAULT 'SYSTEM',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            -- Indexes
            INDEX idx_nse_symbol (nse_symbol),
            INDEX idx_yahoo_symbol (yahoo_symbol),
            INDEX idx_status (validation_status),
            INDEX idx_method (validation_method),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        COMMENT='Tracks validation attempts for symbol mappings';
        """
        
        cursor.execute(validation_log_sql)
        print("✅ Created symbol_mapping_validation_log table")
        
        # Table 3: Symbol mapping statistics and metadata
        mapping_stats_sql = """
        CREATE TABLE IF NOT EXISTS symbol_mapping_stats (
            id INT AUTO_INCREMENT PRIMARY KEY,
            total_nse_symbols INT DEFAULT 0,
            mapped_symbols INT DEFAULT 0,
            verified_symbols INT DEFAULT 0,
            failed_mappings INT DEFAULT 0,
            coverage_percentage DECIMAL(6,3) DEFAULT 0.000,
            last_validation_run TIMESTAMP NULL,
            last_validation_run TIMESTAMP NULL,
            notes TEXT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        COMMENT='Statistics and metadata for symbol mapping coverage';
        """
        
        cursor.execute(mapping_stats_sql)
        print("✅ Created symbol_mapping_stats table")
        
        # Insert initial statistics record
        cursor.execute("""
            INSERT INTO symbol_mapping_stats 
            (total_nse_symbols, mapped_symbols, verified_symbols, failed_mappings, coverage_percentage, notes)
            VALUES (0, 0, 0, 0, 0.00, 'Initial setup - no mappings created yet')
        """)
        
        conn.commit()
        print("✅ Initialized symbol mapping statistics")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 Symbol mapping tables created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        if 'conn' in locals():
            conn.rollback()

def create_initial_symbol_mappings():
    """Create initial symbol mappings for common stocks"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("📋 Creating initial symbol mappings...")
        
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
            ('TATAMOTORS', 'TATAMOTORS.NS', 'Tata Motors Limited', 'Automobile', 'LARGE_CAP'),
            ('M&M', 'M&M.NS', 'Mahindra & Mahindra Limited', 'Automobile', 'LARGE_CAP'),
            ('BAJAJ-AUTO', 'BAJAJ-AUTO.NS', 'Bajaj Auto Limited', 'Automobile', 'LARGE_CAP'),
            
            # FMCG stocks  
            ('HINDUUNILVR', 'HINDUNILVR.NS', 'Hindustan Unilever Limited', 'FMCG', 'LARGE_CAP'),
            ('ITC', 'ITC.NS', 'ITC Limited', 'FMCG', 'LARGE_CAP'),
            ('NESTLEIND', 'NESTLEIND.NS', 'Nestle India Limited', 'FMCG', 'LARGE_CAP'),
            ('BRITANNIA', 'BRITANNIA.NS', 'Britannia Industries Limited', 'FMCG', 'LARGE_CAP'),
            
            # Pharma stocks
            ('SUNPHARMA', 'SUNPHARMA.NS', 'Sun Pharmaceutical Industries Limited', 'Pharma', 'LARGE_CAP'),
            ('DRREDDY', 'DRREDDY.NS', 'Dr. Reddys Laboratories Limited', 'Pharma', 'LARGE_CAP'),
            ('CIPLA', 'CIPLA.NS', 'Cipla Limited', 'Pharma', 'LARGE_CAP'),
            ('APOLLOHOSP', 'APOLLOHOSP.NS', 'Apollo Hospitals Enterprise Limited', 'Healthcare', 'LARGE_CAP'),
            
            # Metal & Mining
            ('TATASTEEL', 'TATASTEEL.NS', 'Tata Steel Limited', 'Metals', 'LARGE_CAP'),
            ('JSWSTEEL', 'JSWSTEEL.NS', 'JSW Steel Limited', 'Metals', 'LARGE_CAP'),
            ('HINDALCO', 'HINDALCO.NS', 'Hindalco Industries Limited', 'Metals', 'LARGE_CAP'),
            ('VEDL', 'VEDL.NS', 'Vedanta Limited', 'Metals', 'LARGE_CAP'),
            
            # Energy & Oil
            ('RELIANCE', 'RELIANCE.NS', 'Reliance Industries Limited', 'Energy', 'LARGE_CAP'),
            ('ONGC', 'ONGC.NS', 'Oil and Natural Gas Corporation Limited', 'Energy', 'LARGE_CAP'),
            ('IOC', 'IOC.NS', 'Indian Oil Corporation Limited', 'Energy', 'LARGE_CAP'),
            ('BPCL', 'BPCL.NS', 'Bharat Petroleum Corporation Limited', 'Energy', 'LARGE_CAP'),
            
            # Telecom
            ('BHARTIARTL', 'BHARTIARTL.NS', 'Bharti Airtel Limited', 'Telecom', 'LARGE_CAP'),
            ('JIOFC', 'JIOFC.NS', 'Jio Financial Services Limited', 'Financial Services', 'LARGE_CAP'),
            
            # Indices (already existing)
            ('NIFTY', '^NSEI', 'NIFTY 50', 'Index', 'LARGE_CAP'),
            ('BANKNIFTY', '^NSEBANK', 'Bank Nifty', 'Index', 'LARGE_CAP'),
            ('SENSEX', '^BSESN', 'BSE Sensex', 'Index', 'LARGE_CAP')
        ]
        
        # Insert mappings
        insert_sql = """
            INSERT INTO nse_yahoo_symbol_map 
            (nse_symbol, yahoo_symbol, company_name, sector, market_cap_category, is_verified)
            VALUES (%s, %s, %s, %s, %s, FALSE)
            ON DUPLICATE KEY UPDATE 
            yahoo_symbol = VALUES(yahoo_symbol),
            company_name = VALUES(company_name),
            sector = VALUES(sector),
            market_cap_category = VALUES(market_cap_category),
            updated_at = CURRENT_TIMESTAMP
        """
        
        cursor.executemany(insert_sql, initial_mappings)
        
        # Update statistics
        cursor.execute("SELECT COUNT(*) FROM nse_yahoo_symbol_map")
        total_mapped = cursor.fetchone()[0]
        
        cursor.execute("""
            UPDATE symbol_mapping_stats 
            SET mapped_symbols = %s, 
                coverage_percentage = (mapped_symbols / GREATEST(total_nse_symbols, 1)) * 100,
                last_validation_run = CURRENT_TIMESTAMP,
                notes = 'Initial mappings created for major stocks'
            ORDER BY id DESC LIMIT 1
        """, (total_mapped,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Created {len(initial_mappings)} initial symbol mappings")
        
    except Exception as e:
        print(f"❌ Error creating initial mappings: {e}")

def create_symbol_discovery_procedures():
    """Create stored procedures for symbol mapping operations"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("⚙️  Creating symbol mapping procedures...")
        
        # Procedure to populate mappings from NSE constituents
        procedure_sql = """
        CREATE PROCEDURE IF NOT EXISTS PopulateSymbolMappingsFromNSE()
        BEGIN
            DECLARE done INT DEFAULT FALSE;
            DECLARE v_symbol VARCHAR(50);
            DECLARE v_company_name VARCHAR(255);
            DECLARE v_sector VARCHAR(100);
            DECLARE cur CURSOR FOR 
                SELECT DISTINCT symbol, company_name, industry 
                FROM nse_index_constituents 
                WHERE symbol IS NOT NULL AND symbol != '';
            DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
            
            OPEN cur;
            
            read_loop: LOOP
                FETCH cur INTO v_symbol, v_company_name, v_sector;
                IF done THEN
                    LEAVE read_loop;
                END IF;
                
                -- Insert mapping with .NS suffix for Yahoo Finance
                INSERT INTO nse_yahoo_symbol_map 
                (nse_symbol, yahoo_symbol, company_name, sector, is_verified)
                VALUES 
                (v_symbol, CONCAT(v_symbol, '.NS'), v_company_name, v_sector, FALSE)
                ON DUPLICATE KEY UPDATE 
                company_name = COALESCE(VALUES(company_name), company_name),
                sector = COALESCE(VALUES(sector), sector);
                
            END LOOP;
            
            CLOSE cur;
            
            -- Update statistics
            UPDATE symbol_mapping_stats 
            SET total_nse_symbols = (SELECT COUNT(DISTINCT symbol) FROM nse_index_constituents),
                mapped_symbols = (SELECT COUNT(*) FROM nse_yahoo_symbol_map),
                last_validation_run = CURRENT_TIMESTAMP,
                notes = 'Auto-populated from NSE index constituents'
            ORDER BY id DESC LIMIT 1;
            
        END
        """
        
        # Drop procedure if exists and recreate
        cursor.execute("DROP PROCEDURE IF EXISTS PopulateSymbolMappingsFromNSE")
        cursor.execute(procedure_sql)
        print("✅ Created PopulateSymbolMappingsFromNSE procedure")
        
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error creating procedures: {e}")

def show_mapping_summary():
    """Show summary of symbol mappings"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        print("\n📊 Symbol Mapping Summary")
        print("=" * 50)
        
        # Get mapping statistics
        cursor.execute("SELECT * FROM symbol_mapping_stats ORDER BY id DESC LIMIT 1")
        stats = cursor.fetchone()
        
        if stats:
            print(f"Total NSE Symbols: {stats['total_nse_symbols']}")
            print(f"Mapped Symbols: {stats['mapped_symbols']}")
            print(f"Verified Symbols: {stats['verified_symbols']}")
            print(f"Failed Mappings: {stats['failed_mappings']}")
            print(f"Coverage: {stats['coverage_percentage']:.2f}%")
            print(f"Last Update: {stats.get('last_validation_run', 'None')}")
        
        # Sample mappings
        print("\n📋 Sample Symbol Mappings:")
        cursor.execute("""
            SELECT nse_symbol, yahoo_symbol, company_name, sector, is_verified 
            FROM nse_yahoo_symbol_map 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        
        mappings = cursor.fetchall()
        for mapping in mappings:
            verified = "✅" if mapping['is_verified'] else "❓"
            print(f"{verified} {mapping['nse_symbol']} → {mapping['yahoo_symbol']} ({mapping['sector']})")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error showing summary: {e}")

def main():
    """Main function"""
    print("🚀 NSE to Yahoo Finance Symbol Mapping Setup")
    print("=" * 60)
    
    try:
        # Step 1: Check existing NSE tables
        check_existing_tables()
        
        # Step 2: Create symbol mapping tables
        create_symbol_mapping_tables()
        
        # Step 3: Create initial mappings
        create_initial_symbol_mappings()
        
        # Step 4: Create stored procedures
        create_symbol_discovery_procedures()
        
        # Step 5: Show summary
        show_mapping_summary()
        
        print("\n" + "=" * 60)
        print("✅ Symbol mapping setup completed successfully!")
        print("\n📋 Next steps:")
        print("1. Run: CALL PopulateSymbolMappingsFromNSE(); -- To auto-populate from NSE data")
        print("2. Verify mappings with Yahoo Finance API")
        print("3. Use mappings for bulk stock data download")
        print("\n🔧 Tables created:")
        print("• nse_yahoo_symbol_map - Main mapping table")
        print("• symbol_mapping_validation_log - Validation tracking")
        print("• symbol_mapping_stats - Coverage statistics")
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)