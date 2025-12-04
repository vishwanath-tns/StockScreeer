#!/usr/bin/env python3
"""
Crypto Database Schema Creation
===============================

Creates the crypto_marketdata database and all required tables.

Tables:
- crypto_symbols: Master list of cryptocurrencies
- crypto_daily_quotes: Daily OHLCV data (10 years)
- crypto_daily_ma: Moving averages (EMA21, SMA5/50/150/200)
- crypto_daily_rsi: RSI values
- crypto_advance_decline: Daily breadth data

Usage:
    python -m crypto.data.create_tables
"""

import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

load_dotenv()


def get_crypto_engine(database: str = None):
    """Get SQLAlchemy engine for crypto database."""
    url = URL.create(
        drivername="mysql+pymysql",
        username=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        database=database,
        query={"charset": "utf8mb4"}
    )
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600)


def create_database():
    """Create the crypto_marketdata database if it doesn't exist."""
    engine = get_crypto_engine(database=None)
    db_name = os.getenv("CRYPTO_DB", "crypto_marketdata")
    
    with engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
        conn.commit()
        print(f"✅ Database '{db_name}' created/verified")
    
    engine.dispose()


def create_tables():
    """Create all crypto tables."""
    db_name = os.getenv("CRYPTO_DB", "crypto_marketdata")
    engine = get_crypto_engine(database=db_name)
    
    # SQL statements for each table
    tables = {
        "crypto_symbols": """
            CREATE TABLE IF NOT EXISTS crypto_symbols (
                id INT AUTO_INCREMENT PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL COMMENT 'Base symbol (BTC, ETH)',
                yahoo_symbol VARCHAR(30) NOT NULL COMMENT 'Yahoo format (BTC-USD)',
                name VARCHAR(100) NOT NULL COMMENT 'Full name (Bitcoin)',
                category VARCHAR(50) DEFAULT 'other' COMMENT 'layer1, defi, meme, exchange, stablecoin, other',
                market_cap_rank INT COMMENT 'Rank by market cap',
                is_active BOOLEAN DEFAULT TRUE,
                added_date DATE DEFAULT (CURRENT_DATE),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_symbol (symbol),
                UNIQUE KEY uk_yahoo_symbol (yahoo_symbol),
                INDEX idx_category (category),
                INDEX idx_active (is_active),
                INDEX idx_rank (market_cap_rank)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            COMMENT='Master list of tracked cryptocurrencies'
        """,
        
        "crypto_daily_quotes": """
            CREATE TABLE IF NOT EXISTS crypto_daily_quotes (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL COMMENT 'Base symbol (BTC)',
                trade_date DATE NOT NULL,
                open_price DECIMAL(18,8) COMMENT 'Opening price (8 decimal precision for crypto)',
                high_price DECIMAL(18,8) COMMENT 'High price',
                low_price DECIMAL(18,8) COMMENT 'Low price',
                close_price DECIMAL(18,8) COMMENT 'Closing price',
                volume DECIMAL(24,2) COMMENT 'Trading volume in USD',
                pct_change DECIMAL(10,4) COMMENT 'Daily % change',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_symbol_date (symbol, trade_date),
                INDEX idx_date (trade_date),
                INDEX idx_symbol (symbol),
                INDEX idx_pct_change (pct_change)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            COMMENT='Daily OHLCV data for cryptocurrencies'
        """,
        
        "crypto_daily_ma": """
            CREATE TABLE IF NOT EXISTS crypto_daily_ma (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                trade_date DATE NOT NULL,
                ema_21 DECIMAL(18,8) COMMENT '21-day EMA',
                sma_5 DECIMAL(18,8) COMMENT '5-day SMA',
                sma_10 DECIMAL(18,8) COMMENT '10-day SMA',
                sma_20 DECIMAL(18,8) COMMENT '20-day SMA',
                sma_50 DECIMAL(18,8) COMMENT '50-day SMA',
                sma_150 DECIMAL(18,8) COMMENT '150-day SMA',
                sma_200 DECIMAL(18,8) COMMENT '200-day SMA',
                price_vs_sma50 DECIMAL(10,4) COMMENT '% above/below SMA50',
                price_vs_sma200 DECIMAL(10,4) COMMENT '% above/below SMA200',
                sma50_vs_sma200 DECIMAL(10,4) COMMENT 'SMA50 vs SMA200 (Golden/Death Cross)',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_symbol_date (symbol, trade_date),
                INDEX idx_date (trade_date),
                INDEX idx_symbol (symbol)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            COMMENT='Moving averages for cryptocurrencies'
        """,
        
        "crypto_daily_rsi": """
            CREATE TABLE IF NOT EXISTS crypto_daily_rsi (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                trade_date DATE NOT NULL,
                rsi_9 DECIMAL(10,4) COMMENT '9-period RSI',
                rsi_14 DECIMAL(10,4) COMMENT '14-period RSI',
                rsi_zone VARCHAR(20) COMMENT 'oversold/neutral/overbought',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_symbol_date (symbol, trade_date),
                INDEX idx_date (trade_date),
                INDEX idx_symbol (symbol),
                INDEX idx_rsi_zone (rsi_zone)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            COMMENT='RSI values for cryptocurrencies'
        """,
        
        "crypto_advance_decline": """
            CREATE TABLE IF NOT EXISTS crypto_advance_decline (
                id INT AUTO_INCREMENT PRIMARY KEY,
                trade_date DATE NOT NULL,
                advances INT NOT NULL DEFAULT 0 COMMENT 'Coins with positive change',
                declines INT NOT NULL DEFAULT 0 COMMENT 'Coins with negative change',
                unchanged INT NOT NULL DEFAULT 0 COMMENT 'Coins with ~0% change',
                total_coins INT NOT NULL DEFAULT 0,
                ad_ratio DECIMAL(10,4) COMMENT 'Advances / Declines ratio',
                ad_diff INT COMMENT 'Advances - Declines',
                ad_line DECIMAL(16,4) COMMENT 'Cumulative A/D line',
                
                -- Distribution buckets (% change ranges)
                gain_0_1 INT DEFAULT 0 COMMENT '0% to 1%',
                gain_1_2 INT DEFAULT 0 COMMENT '1% to 2%',
                gain_2_3 INT DEFAULT 0 COMMENT '2% to 3%',
                gain_3_5 INT DEFAULT 0 COMMENT '3% to 5%',
                gain_5_10 INT DEFAULT 0 COMMENT '5% to 10%',
                gain_10_plus INT DEFAULT 0 COMMENT '>10%',
                
                loss_0_1 INT DEFAULT 0 COMMENT '0% to -1%',
                loss_1_2 INT DEFAULT 0 COMMENT '-1% to -2%',
                loss_2_3 INT DEFAULT 0 COMMENT '-2% to -3%',
                loss_3_5 INT DEFAULT 0 COMMENT '-3% to -5%',
                loss_5_10 INT DEFAULT 0 COMMENT '-5% to -10%',
                loss_10_plus INT DEFAULT 0 COMMENT '<-10%',
                
                -- Market stats
                avg_change DECIMAL(10,4) COMMENT 'Average % change',
                median_change DECIMAL(10,4) COMMENT 'Median % change',
                total_volume DECIMAL(24,2) COMMENT 'Total market volume',
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_date (trade_date),
                INDEX idx_ad_ratio (ad_ratio),
                INDEX idx_advances (advances),
                INDEX idx_declines (declines)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            COMMENT='Daily advance/decline breadth data for crypto market'
        """
    }
    
    with engine.connect() as conn:
        for table_name, sql in tables.items():
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"✅ Table '{table_name}' created/verified")
            except Exception as e:
                print(f"❌ Error creating '{table_name}': {e}")
    
    engine.dispose()


def verify_tables():
    """Verify all tables exist and show row counts."""
    db_name = os.getenv("CRYPTO_DB", "crypto_marketdata")
    engine = get_crypto_engine(database=db_name)
    
    tables = [
        "crypto_symbols",
        "crypto_daily_quotes", 
        "crypto_daily_ma",
        "crypto_daily_rsi",
        "crypto_advance_decline"
    ]
    
    print(f"\n📊 Table Status in '{db_name}':")
    print("-" * 50)
    
    with engine.connect() as conn:
        for table in tables:
            try:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"  {table}: {count:,} rows")
            except Exception as e:
                print(f"  {table}: ❌ Error - {e}")
    
    engine.dispose()


def main():
    """Main entry point."""
    print("🪙 Crypto Database Setup")
    print("=" * 50)
    
    # Create database
    create_database()
    
    # Create tables
    print("\n📦 Creating tables...")
    create_tables()
    
    # Verify
    verify_tables()
    
    print("\n✅ Crypto database setup complete!")


if __name__ == "__main__":
    main()
