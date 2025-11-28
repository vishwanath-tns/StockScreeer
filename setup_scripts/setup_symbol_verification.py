"""
Setup verification tables for NSE symbol mapping
Creates necessary database tables if they don't exist
"""

import os
import mysql.connector
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_connection():
    """Get database connection"""
    return mysql.connector.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', '3306')),
        database=os.getenv('MYSQL_DB', 'MarketData'),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', 'admin')
    )

def create_verification_tables():
    """Create verification tables if they don't exist"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create nse_yahoo_symbol_map table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nse_yahoo_symbol_map (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nse_symbol VARCHAR(50) NOT NULL,
                yahoo_symbol VARCHAR(50) NOT NULL,
                sector VARCHAR(100),
                is_verified BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_nse_symbol (nse_symbol),
                INDEX idx_yahoo_symbol (yahoo_symbol),
                INDEX idx_sector (sector),
                INDEX idx_verified (is_verified),
                INDEX idx_active (is_active)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Create symbol_mapping_validation_log table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS symbol_mapping_validation_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nse_symbol VARCHAR(50) NOT NULL,
                yahoo_symbol_tested VARCHAR(50) NOT NULL,
                is_valid BOOLEAN DEFAULT FALSE,
                error_message TEXT,
                tested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_nse_symbol (nse_symbol),
                INDEX idx_yahoo_symbol (yahoo_symbol_tested),
                INDEX idx_valid (is_valid),
                INDEX idx_tested_at (tested_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Create symbol_mapping_stats table if not exists  
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS symbol_mapping_stats (
                id INT AUTO_INCREMENT PRIMARY KEY,
                verification_date DATE NOT NULL,
                total_symbols INT DEFAULT 0,
                verified_count INT DEFAULT 0,
                failed_count INT DEFAULT 0,
                success_rate DECIMAL(5,2) DEFAULT 0.00,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_date (verification_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✓ Verification tables created/verified successfully")
        return True
        
    except Exception as e:
        print(f"Error creating verification tables: {e}")
        return False

def check_existing_data():
    """Check what data already exists"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check nse_index_constituents
        cursor.execute("SELECT COUNT(*) FROM nse_index_constituents")
        nse_count = cursor.fetchone()[0]
        
        # Check existing mappings
        cursor.execute("SELECT COUNT(*) FROM nse_yahoo_symbol_map WHERE is_active = 1")
        mapping_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        print(f"NSE symbols in database: {nse_count}")
        print(f"Existing mappings: {mapping_count}")
        
        if nse_count == 0:
            print("WARNING: No NSE symbols found in nse_index_constituents table!")
            return False
            
        return True
        
    except Exception as e:
        print(f"Error checking existing data: {e}")
        return False

def main():
    print("Setting up NSE Symbol Verification Tables")
    print("="*45)
    
    # Create tables
    if not create_verification_tables():
        return
    
    # Check existing data
    if not check_existing_data():
        print("\nPlease ensure NSE symbols are loaded in nse_index_constituents table first")
        return
    
    print("\n✓ Setup complete! You can now run:")
    print("  python quick_symbol_check.py    # Quick status check")
    print("  python verify_all_nse_symbols.py # Full verification")

if __name__ == "__main__":
    main()