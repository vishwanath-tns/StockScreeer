"""
Database Schema for Bollinger Bands System

Defines tables for storing BB calculations, ratings, and signals.
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()


def get_bb_engine():
    """Create SQLAlchemy engine for BB operations."""
    host = os.getenv("MYSQL_HOST", "localhost")
    port = os.getenv("MYSQL_PORT", "3306")
    db = os.getenv("MYSQL_DB", "stockdata")
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    
    # URL-encode the password to handle special characters like @
    encoded_password = quote_plus(password)
    
    url = f"mysql+pymysql://{user}:{encoded_password}@{host}:{port}/{db}?charset=utf8mb4"
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600)


def create_bb_tables(engine=None):
    """
    Create Bollinger Bands tables if they don't exist.
    
    Tables:
    - stock_bollinger_daily: Daily BB values
    - stock_bb_ratings_history: Historical BB ratings
    - stock_bb_signals: Generated buy/sell signals
    - stock_bb_scan_cache: Cached scanner results
    """
    if engine is None:
        engine = get_bb_engine()
    
    statements = _get_create_statements()
    results = {}
    
    with engine.begin() as conn:
        for stmt in statements:
            table_name = _extract_table_name(stmt)
            try:
                conn.execute(text(stmt))
                results[table_name] = "created"
            except Exception as e:
                if "already exists" in str(e).lower():
                    results[table_name] = "exists"
                else:
                    results[table_name] = f"error: {e}"
    
    return results


def _extract_table_name(sql: str) -> str:
    """Extract table name from CREATE TABLE statement."""
    import re
    match = re.search(r"CREATE TABLE\s+(?:IF NOT EXISTS\s+)?`?(\w+)`?", sql, re.IGNORECASE)
    return match.group(1) if match else "unknown"


def _get_create_statements() -> list:
    """Get CREATE TABLE statements for BB system."""
    return [
        # Daily Bollinger Bands values
        """
        CREATE TABLE IF NOT EXISTS stock_bollinger_daily (
            id INT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            date DATE NOT NULL,
            
            -- Price data
            close_price DECIMAL(12,2) NOT NULL,
            
            -- Bollinger Bands values
            bb_upper DECIMAL(12,2) NOT NULL,
            bb_middle DECIMAL(12,2) NOT NULL,
            bb_lower DECIMAL(12,2) NOT NULL,
            
            -- Indicators
            percent_b DECIMAL(8,4) NOT NULL,          -- %b indicator
            bandwidth DECIMAL(8,4) NOT NULL,          -- BandWidth (%)
            bandwidth_percentile DECIMAL(5,2) DEFAULT 50.0, -- Historical percentile
            
            -- Configuration used
            bb_period INT DEFAULT 20,
            bb_std_dev DECIMAL(3,1) DEFAULT 2.0,
            
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            
            -- Indexes
            UNIQUE KEY uk_symbol_date (symbol, date),
            INDEX idx_date (date),
            INDEX idx_percent_b (date, percent_b),
            INDEX idx_bandwidth (date, bandwidth_percentile)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        
        # Historical BB Ratings
        """
        CREATE TABLE IF NOT EXISTS stock_bb_ratings_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            rating_date DATE NOT NULL,
            
            -- Component scores (0-100)
            squeeze_score DECIMAL(5,2) DEFAULT 50.0,
            trend_score DECIMAL(5,2) DEFAULT 50.0,
            momentum_score DECIMAL(5,2) DEFAULT 50.0,
            pattern_score DECIMAL(5,2) DEFAULT 50.0,
            
            -- Composite score (0-100)
            composite_score DECIMAL(5,2) DEFAULT 50.0,
            
            -- Ranking
            bb_rank INT DEFAULT 0,
            bb_percentile DECIMAL(5,2) DEFAULT 50.0,
            total_stocks_ranked INT DEFAULT 0,
            
            -- Current state snapshot
            percent_b DECIMAL(8,4) DEFAULT 0.5,
            bandwidth DECIMAL(8,4) DEFAULT 0.0,
            bandwidth_percentile DECIMAL(5,2) DEFAULT 50.0,
            is_squeeze TINYINT(1) DEFAULT 0,
            is_bulge TINYINT(1) DEFAULT 0,
            trend_direction VARCHAR(20) DEFAULT 'neutral',
            
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            -- Indexes
            UNIQUE KEY uk_symbol_rating_date (symbol, rating_date),
            INDEX idx_rating_date (rating_date),
            INDEX idx_composite (rating_date, composite_score DESC),
            INDEX idx_squeeze (rating_date, is_squeeze),
            INDEX idx_trend (rating_date, trend_direction)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        
        # Trading Signals
        """
        CREATE TABLE IF NOT EXISTS stock_bb_signals (
            id INT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            signal_date DATE NOT NULL,
            signal_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            
            -- Signal details
            signal_type ENUM('BUY', 'SELL', 'HOLD') NOT NULL,
            pattern VARCHAR(50) NOT NULL,
            confidence DECIMAL(5,2) NOT NULL,
            
            -- Price at signal
            price_at_signal DECIMAL(12,2) NOT NULL,
            percent_b DECIMAL(8,4) NOT NULL,
            bandwidth DECIMAL(8,4) NOT NULL,
            
            -- Volume confirmation
            volume_confirmed TINYINT(1) DEFAULT 0,
            volume_ratio DECIMAL(5,2) DEFAULT 1.0,
            
            -- Trade management
            target_price DECIMAL(12,2) DEFAULT NULL,
            stop_loss DECIMAL(12,2) DEFAULT NULL,
            
            -- Description
            description TEXT DEFAULT NULL,
            
            -- Outcome tracking (updated later)
            outcome VARCHAR(20) DEFAULT NULL,  -- 'win', 'loss', 'open', NULL
            exit_price DECIMAL(12,2) DEFAULT NULL,
            exit_date DATE DEFAULT NULL,
            return_pct DECIMAL(8,4) DEFAULT NULL,
            
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            -- Indexes
            INDEX idx_symbol_date (symbol, signal_date),
            INDEX idx_signal_date (signal_date),
            INDEX idx_signal_type (signal_date, signal_type),
            INDEX idx_confidence (signal_date, confidence DESC),
            INDEX idx_pattern (pattern)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        
        # Scanner Cache
        """
        CREATE TABLE IF NOT EXISTS stock_bb_scan_cache (
            id INT AUTO_INCREMENT PRIMARY KEY,
            scan_type VARCHAR(50) NOT NULL,
            scan_date DATE NOT NULL,
            
            -- Results
            total_scanned INT DEFAULT 0,
            matches_found INT DEFAULT 0,
            results_json JSON,
            
            -- Execution info
            execution_time_ms DECIMAL(10,2) DEFAULT 0,
            
            -- Cache management
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP DEFAULT NULL,
            
            -- Indexes
            UNIQUE KEY uk_scan_type_date (scan_type, scan_date),
            INDEX idx_expires (expires_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    ]


def check_bb_tables_exist(engine=None) -> dict:
    """Check if BB tables exist."""
    if engine is None:
        engine = get_bb_engine()
    
    tables = [
        "stock_bollinger_daily",
        "stock_bb_ratings_history", 
        "stock_bb_signals",
        "stock_bb_scan_cache"
    ]
    results = {}
    
    with engine.connect() as conn:
        for table in tables:
            try:
                conn.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
                results[table] = True
            except:
                results[table] = False
    
    return results


def get_bb_table_stats(engine=None) -> dict:
    """Get row counts for BB tables."""
    if engine is None:
        engine = get_bb_engine()
    
    tables = [
        "stock_bollinger_daily",
        "stock_bb_ratings_history",
        "stock_bb_signals",
        "stock_bb_scan_cache"
    ]
    stats = {}
    
    with engine.connect() as conn:
        for table in tables:
            try:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                stats[table] = result.scalar()
            except:
                stats[table] = 0
    
    return stats


if __name__ == "__main__":
    print("Creating Bollinger Bands tables...")
    results = create_bb_tables()
    for table, status in results.items():
        print(f"  {table}: {status}")
    
    print("\nTable statistics:")
    stats = get_bb_table_stats()
    for table, count in stats.items():
        print(f"  {table}: {count:,} rows")
