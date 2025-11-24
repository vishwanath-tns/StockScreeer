"""
Create NSE Block & Bulk Deals tables directly
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

def get_engine():
    """Create database engine"""
    password = quote_plus(os.getenv('MYSQL_PASSWORD', 'rajat123'))
    return create_engine(
        f"mysql+pymysql://{os.getenv('MYSQL_USER', 'root')}:"
        f"{password}@"
        f"{os.getenv('MYSQL_HOST', 'localhost')}:"
        f"{os.getenv('MYSQL_PORT', '3306')}/"
        f"{os.getenv('MYSQL_DB', 'marketdata')}?charset=utf8mb4",
        pool_pre_ping=True
    )

print("=" * 80)
print("Creating NSE Block & Bulk Deals Tables")
print("=" * 80)

engine = get_engine()

with engine.begin() as conn:
    # Create nse_block_deals table
    print("\n✅ Creating nse_block_deals...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS nse_block_deals (
            id INT AUTO_INCREMENT PRIMARY KEY,
            trade_date DATE NOT NULL,
            symbol VARCHAR(50) NOT NULL,
            security_name VARCHAR(255),
            client_name VARCHAR(255),
            deal_type VARCHAR(10),
            quantity BIGINT,
            trade_price DECIMAL(15,4),
            remarks VARCHAR(500),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_trade_date (trade_date),
            INDEX idx_symbol (symbol),
            INDEX idx_symbol_date (symbol, trade_date),
            INDEX idx_client (client_name(100)),
            INDEX idx_deal_type (deal_type),
            UNIQUE KEY uk_block_deal (trade_date, symbol, client_name(200), deal_type, quantity, trade_price)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """))
    
    # Create nse_bulk_deals table
    print("✅ Creating nse_bulk_deals...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS nse_bulk_deals (
            id INT AUTO_INCREMENT PRIMARY KEY,
            trade_date DATE NOT NULL,
            symbol VARCHAR(50) NOT NULL,
            security_name VARCHAR(255),
            client_name VARCHAR(255),
            deal_type VARCHAR(10),
            quantity BIGINT,
            trade_price DECIMAL(15,4),
            remarks VARCHAR(500),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_trade_date (trade_date),
            INDEX idx_symbol (symbol),
            INDEX idx_symbol_date (symbol, trade_date),
            INDEX idx_client (client_name(100)),
            INDEX idx_deal_type (deal_type),
            UNIQUE KEY uk_bulk_deal (trade_date, symbol, client_name(200), deal_type, quantity, trade_price)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """))
    
    # Create import log table
    print("✅ Creating block_bulk_deals_import_log...")
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS block_bulk_deals_import_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            trade_date DATE NOT NULL,
            deal_category VARCHAR(20) NOT NULL,
            records_imported INT DEFAULT 0,
            import_status VARCHAR(20) DEFAULT 'SUCCESS',
            error_message TEXT,
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_trade_date (trade_date),
            INDEX idx_category (deal_category),
            UNIQUE KEY uk_import_log (trade_date, deal_category)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """))

# Verify
print("\n" + "=" * 80)
print("Verifying tables...")
print("=" * 80)

with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM nse_block_deals"))
    print(f"✅ nse_block_deals: {result.scalar():,} records")
    
    result = conn.execute(text("SELECT COUNT(*) FROM nse_bulk_deals"))
    print(f"✅ nse_bulk_deals: {result.scalar():,} records")
    
    result = conn.execute(text("SELECT COUNT(*) FROM block_bulk_deals_import_log"))
    print(f"✅ block_bulk_deals_import_log: {result.scalar():,} records")

print("\n" + "=" * 80)
print("✅ Tables created successfully!")
print("=" * 80)
print("\nNext: python block_bulk_deals/sync_deals_gui.py")
print("=" * 80)
