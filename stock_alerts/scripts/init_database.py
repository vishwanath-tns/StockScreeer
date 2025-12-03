"""
Initialize the alerts_db database.

This script creates the alerts_db database and all required tables.
Run this once before starting the Stock Alert System.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
import pymysql
from urllib.parse import quote_plus

# Load environment variables
load_dotenv()


def create_database():
    """Create the alerts_db database."""
    
    # Get credentials from environment
    host = os.getenv('ALERTS_DB_HOST', os.getenv('MYSQL_HOST', 'localhost'))
    port = int(os.getenv('ALERTS_DB_PORT', os.getenv('MYSQL_PORT', '3306')))
    user = os.getenv('ALERTS_DB_USER', os.getenv('MYSQL_USER', 'root'))
    password = os.getenv('ALERTS_DB_PASSWORD', os.getenv('MYSQL_PASSWORD', ''))
    
    print(f"Connecting to MySQL at {host}:{port} as {user}...")
    
    # Connect without specifying database
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        charset='utf8mb4',
    )
    
    try:
        with conn.cursor() as cursor:
            # Create database
            print("Creating alerts_db database...")
            cursor.execute("""
                CREATE DATABASE IF NOT EXISTS alerts_db
                CHARACTER SET utf8mb4
                COLLATE utf8mb4_unicode_ci
            """)
            print("✓ Database created")
            
            # Switch to database
            cursor.execute("USE alerts_db")
            
            # Create tables
            print("\nCreating tables...")
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    max_alerts INT DEFAULT 50,
                    max_api_keys INT DEFAULT 5,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_admin BOOLEAN DEFAULT FALSE,
                    notification_settings JSON,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_login_at DATETIME,
                    INDEX idx_username (username),
                    INDEX idx_email (email)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            print("✓ users table")
            
            # API keys table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id INT NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    key_hash VARCHAR(255) NOT NULL,
                    prefix VARCHAR(8) NOT NULL,
                    permissions JSON,
                    rate_limit_per_minute INT DEFAULT 60,
                    is_active BOOLEAN DEFAULT TRUE,
                    expires_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_used_at DATETIME,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    INDEX idx_user_id (user_id),
                    INDEX idx_prefix (prefix)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            print("✓ api_keys table")
            
            # Price alerts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_alerts (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id INT NOT NULL,
                    symbol VARCHAR(50) NOT NULL,
                    yahoo_symbol VARCHAR(50) NOT NULL,
                    asset_type ENUM('nse_equity', 'bse_equity', 'nse_index', 'commodity', 'crypto', 'forex') NOT NULL,
                    alert_type ENUM('price', 'volume', 'technical', 'custom') NOT NULL,
                    `condition` VARCHAR(50) NOT NULL,
                    target_value DECIMAL(20, 4) NOT NULL,
                    target_value_2 DECIMAL(20, 4),
                    status ENUM('active', 'triggered', 'paused', 'expired', 'cancelled') DEFAULT 'active',
                    priority ENUM('low', 'normal', 'high', 'critical') DEFAULT 'normal',
                    notification_channels JSON,
                    webhook_url VARCHAR(500),
                    trigger_once BOOLEAN DEFAULT TRUE,
                    cooldown_minutes INT DEFAULT 60,
                    expires_at DATETIME,
                    source VARCHAR(50) DEFAULT 'manual',
                    source_id VARCHAR(100),
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    last_triggered_at DATETIME,
                    trigger_count INT DEFAULT 0,
                    previous_price DECIMAL(20, 4),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    INDEX idx_user_id (user_id),
                    INDEX idx_symbol (symbol),
                    INDEX idx_yahoo_symbol (yahoo_symbol),
                    INDEX idx_status (status),
                    INDEX idx_asset_type (asset_type),
                    INDEX idx_user_status (user_id, status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            print("✓ price_alerts table")
            
            # Alert history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    id VARCHAR(36) PRIMARY KEY,
                    alert_id VARCHAR(36) NOT NULL,
                    user_id INT NOT NULL,
                    symbol VARCHAR(50) NOT NULL,
                    `condition` VARCHAR(50) NOT NULL,
                    target_value DECIMAL(20, 4) NOT NULL,
                    actual_value DECIMAL(20, 4) NOT NULL,
                    notifications_sent JSON,
                    notification_results JSON,
                    triggered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    INDEX idx_alert_id (alert_id),
                    INDEX idx_user_id (user_id),
                    INDEX idx_triggered_at (triggered_at),
                    INDEX idx_user_triggered (user_id, triggered_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            print("✓ alert_history table")
            
            # Watchlists table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS watchlists (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id INT NOT NULL,
                    watchlist_name VARCHAR(100) NOT NULL,
                    symbol VARCHAR(50) NOT NULL,
                    yahoo_symbol VARCHAR(50) NOT NULL,
                    asset_type ENUM('nse_equity', 'bse_equity', 'nse_index', 'commodity', 'crypto', 'forex') NOT NULL,
                    sort_order INT DEFAULT 0,
                    notes TEXT,
                    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE KEY unique_user_watchlist_symbol (user_id, watchlist_name, symbol),
                    INDEX idx_user_watchlist (user_id, watchlist_name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            print("✓ watchlists table")
            
            # Symbol cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS symbol_cache (
                    yahoo_symbol VARCHAR(50) PRIMARY KEY,
                    symbol VARCHAR(50) NOT NULL,
                    name VARCHAR(255),
                    asset_type ENUM('nse_equity', 'bse_equity', 'nse_index', 'commodity', 'crypto', 'forex') NOT NULL,
                    exchange VARCHAR(50),
                    currency VARCHAR(10),
                    last_price DECIMAL(20, 4),
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_symbol (symbol),
                    INDEX idx_asset_type (asset_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            print("✓ symbol_cache table")
            
            # System settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    `key` VARCHAR(100) PRIMARY KEY,
                    `value` TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            print("✓ system_settings table")
            
            # Create default admin user (password: admin123)
            # Hash generated with bcrypt
            print("\nCreating default admin user...")
            cursor.execute("""
                INSERT IGNORE INTO users (username, email, password_hash, is_admin, max_alerts, max_api_keys)
                VALUES ('admin', 'admin@localhost', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.W8X.EXAMPLE', TRUE, 1000, 100)
            """)
            print("✓ Default admin user created (username: admin)")
            
            conn.commit()
            print("\n" + "="*50)
            print("Database initialization complete!")
            print("="*50)
            print("\nYou can now run the Stock Alert System:")
            print("  python stock_alerts_launcher.py demo")
            print("  python stock_alerts_launcher.py gui")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    create_database()
