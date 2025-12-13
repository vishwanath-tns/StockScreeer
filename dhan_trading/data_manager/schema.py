"""
Database schema for indices and historical data management.
Creates tables: dhan_indices, dhan_index_constituents, dhan_daily_ohlcv, dhan_minute_ohlcv
"""
import os
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

def get_db_engine():
    """Create database engine."""
    pw = quote_plus(os.getenv("MYSQL_PASSWORD", ""))
    user = os.getenv("MYSQL_USER", "root")
    host = os.getenv("MYSQL_HOST", "localhost")
    port = os.getenv("MYSQL_PORT", "3306")
    db = os.getenv("MYSQL_DB", "dhan_trading")
    return create_engine(f"mysql+pymysql://{user}:{pw}@{host}:{port}/{db}")

# SQL statements to create tables
CREATE_INDICES_TABLE = """
CREATE TABLE IF NOT EXISTS dhan_indices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    index_name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200),
    description TEXT,
    num_constituents INT DEFAULT 0,
    source_file VARCHAR(255),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_index_name (index_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

CREATE_INDEX_CONSTITUENTS_TABLE = """
CREATE TABLE IF NOT EXISTS dhan_index_constituents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    index_id INT NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    security_id BIGINT,
    weight DECIMAL(10,4),
    open_price DECIMAL(15,4),
    high_price DECIMAL(15,4),
    low_price DECIMAL(15,4),
    prev_close DECIMAL(15,4),
    ltp DECIMAL(15,4),
    change_val DECIMAL(15,4),
    change_pct DECIMAL(10,4),
    volume BIGINT,
    value_cr DECIMAL(15,4),
    week52_high DECIMAL(15,4),
    week52_low DECIMAL(15,4),
    day30_change_pct DECIMAL(10,4),
    day365_change_pct DECIMAL(10,4),
    data_date DATE,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (index_id) REFERENCES dhan_indices(id) ON DELETE CASCADE,
    UNIQUE KEY idx_index_symbol_date (index_id, symbol, data_date),
    INDEX idx_symbol (symbol),
    INDEX idx_security_id (security_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

CREATE_UNIQUE_STOCKS_TABLE = """
CREATE TABLE IF NOT EXISTS dhan_stocks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL UNIQUE,
    security_id BIGINT,
    exchange VARCHAR(10) DEFAULT 'NSE',
    isin VARCHAR(20),
    company_name VARCHAR(255),
    sector VARCHAR(100),
    industry VARCHAR(100),
    is_active TINYINT(1) DEFAULT 1,
    indices_count INT DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol (symbol),
    INDEX idx_security_id (security_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

CREATE_DAILY_OHLCV_TABLE = """
CREATE TABLE IF NOT EXISTS dhan_daily_ohlcv (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    security_id BIGINT,
    trade_date DATE NOT NULL,
    open_price DECIMAL(15,4),
    high_price DECIMAL(15,4),
    low_price DECIMAL(15,4),
    close_price DECIMAL(15,4),
    volume BIGINT,
    value DECIMAL(20,4),
    oi BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY idx_symbol_date (symbol, trade_date),
    INDEX idx_security_id_date (security_id, trade_date),
    INDEX idx_trade_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

CREATE_MINUTE_OHLCV_TABLE = """
CREATE TABLE IF NOT EXISTS dhan_minute_ohlcv (
    symbol VARCHAR(50) NOT NULL,
    security_id BIGINT,
    trade_datetime DATETIME NOT NULL,
    open_price DECIMAL(15,4),
    high_price DECIMAL(15,4),
    low_price DECIMAL(15,4),
    close_price DECIMAL(15,4),
    volume BIGINT,
    oi BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, trade_datetime),
    INDEX idx_security_id_datetime (security_id, trade_datetime),
    INDEX idx_trade_datetime (trade_datetime)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
PARTITION BY RANGE (YEAR(trade_datetime)) (
    PARTITION p2015 VALUES LESS THAN (2016),
    PARTITION p2016 VALUES LESS THAN (2017),
    PARTITION p2017 VALUES LESS THAN (2018),
    PARTITION p2018 VALUES LESS THAN (2019),
    PARTITION p2019 VALUES LESS THAN (2020),
    PARTITION p2020 VALUES LESS THAN (2021),
    PARTITION p2021 VALUES LESS THAN (2022),
    PARTITION p2022 VALUES LESS THAN (2023),
    PARTITION p2023 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026),
    PARTITION pmax VALUES LESS THAN MAXVALUE
);
"""

# Link table for stocks to indices (many-to-many)
CREATE_STOCK_INDEX_LINK_TABLE = """
CREATE TABLE IF NOT EXISTS dhan_stock_index_link (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_id INT NOT NULL,
    index_id INT NOT NULL,
    weight DECIMAL(10,4),
    added_date DATE,
    FOREIGN KEY (stock_id) REFERENCES dhan_stocks(id) ON DELETE CASCADE,
    FOREIGN KEY (index_id) REFERENCES dhan_indices(id) ON DELETE CASCADE,
    UNIQUE KEY idx_stock_index (stock_id, index_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# Track download progress
CREATE_DOWNLOAD_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS dhan_download_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    security_id BIGINT,
    data_type ENUM('daily', 'minute') NOT NULL,
    from_date DATE,
    to_date DATE,
    rows_downloaded INT DEFAULT 0,
    status ENUM('pending', 'in_progress', 'completed', 'failed') DEFAULT 'pending',
    error_message TEXT,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol_type (symbol, data_type),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


def create_all_tables():
    """Create all required tables."""
    engine = get_db_engine()
    
    tables = [
        ("dhan_indices", CREATE_INDICES_TABLE),
        ("dhan_index_constituents", CREATE_INDEX_CONSTITUENTS_TABLE),
        ("dhan_stocks", CREATE_UNIQUE_STOCKS_TABLE),
        ("dhan_stock_index_link", CREATE_STOCK_INDEX_LINK_TABLE),
        ("dhan_daily_ohlcv", CREATE_DAILY_OHLCV_TABLE),
        ("dhan_minute_ohlcv", CREATE_MINUTE_OHLCV_TABLE),
        ("dhan_download_log", CREATE_DOWNLOAD_LOG_TABLE),
    ]
    
    with engine.begin() as conn:
        for table_name, sql in tables:
            try:
                conn.execute(text(sql))
                print(f"✓ Created/verified table: {table_name}")
            except Exception as e:
                print(f"✗ Error creating {table_name}: {e}")
    
    print("\nAll tables created successfully!")
    return True


def drop_all_tables():
    """Drop all tables (use with caution!)."""
    engine = get_db_engine()
    
    tables = [
        "dhan_download_log",
        "dhan_minute_ohlcv", 
        "dhan_daily_ohlcv",
        "dhan_stock_index_link",
        "dhan_index_constituents",
        "dhan_stocks",
        "dhan_indices",
    ]
    
    with engine.begin() as conn:
        for table_name in tables:
            try:
                conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
                print(f"✓ Dropped table: {table_name}")
            except Exception as e:
                print(f"✗ Error dropping {table_name}: {e}")


def show_table_status():
    """Show status of all tables."""
    engine = get_db_engine()
    
    with engine.connect() as conn:
        print("\n=== Table Status ===\n")
        
        tables = [
            "dhan_indices",
            "dhan_index_constituents", 
            "dhan_stocks",
            "dhan_stock_index_link",
            "dhan_daily_ohlcv",
            "dhan_minute_ohlcv",
            "dhan_download_log",
        ]
        
        for table in tables:
            try:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"{table:30} : {count:>10,} rows")
            except Exception as e:
                print(f"{table:30} : NOT FOUND")


if __name__ == "__main__":
    print("Creating database tables...")
    create_all_tables()
    show_table_status()
