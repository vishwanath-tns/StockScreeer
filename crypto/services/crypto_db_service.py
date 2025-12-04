#!/usr/bin/env python3
"""
Crypto Database Service
=======================

Database connection and CRUD operations for crypto module.

Usage:
    from crypto.services.crypto_db_service import CryptoDBService
    
    db = CryptoDBService()
    db.ensure_tables()
    db.upsert_daily_quotes(df)
"""

import os
import sys
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional, Any
import logging

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine
from dotenv import load_dotenv

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CryptoDBService:
    """Database service for crypto data operations."""
    
    def __init__(self):
        """Initialize database service."""
        self._engine: Optional[Engine] = None
        self.db_name = os.getenv("CRYPTO_DB", "crypto_marketdata")
    
    @property
    def engine(self) -> Engine:
        """Get or create database engine."""
        if self._engine is None:
            url = URL.create(
                drivername="mysql+pymysql",
                username=os.getenv("MYSQL_USER", "root"),
                password=os.getenv("MYSQL_PASSWORD", ""),
                host=os.getenv("MYSQL_HOST", "localhost"),
                port=int(os.getenv("MYSQL_PORT", 3306)),
                database=self.db_name,
                query={"charset": "utf8mb4"}
            )
            self._engine = create_engine(url, pool_pre_ping=True, pool_recycle=3600)
        return self._engine
    
    def ensure_database(self):
        """Create database if it doesn't exist."""
        url = URL.create(
            drivername="mysql+pymysql",
            username=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            host=os.getenv("MYSQL_HOST", "localhost"),
            port=int(os.getenv("MYSQL_PORT", 3306)),
            database=None,
            query={"charset": "utf8mb4"}
        )
        engine = create_engine(url)
        
        with engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{self.db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            conn.commit()
        
        engine.dispose()
        logger.info(f"Database '{self.db_name}' verified")
    
    def ensure_tables(self):
        """Create all required tables."""
        from crypto.data.create_tables import create_database, create_tables
        create_database()
        create_tables()
    
    # ==================== Symbol Operations ====================
    
    def insert_symbols(self, symbols: List[tuple]):
        """Insert symbols into crypto_symbols table.
        
        Args:
            symbols: List of (symbol, yahoo_symbol, name, category, rank) tuples
        """
        sql = """
            INSERT INTO crypto_symbols (symbol, yahoo_symbol, name, category, market_cap_rank)
            VALUES (:symbol, :yahoo_symbol, :name, :category, :rank)
            ON DUPLICATE KEY UPDATE
                yahoo_symbol = VALUES(yahoo_symbol),
                name = VALUES(name),
                category = VALUES(category),
                market_cap_rank = VALUES(market_cap_rank),
                updated_at = CURRENT_TIMESTAMP
        """
        
        with self.engine.connect() as conn:
            for sym in symbols:
                conn.execute(text(sql), {
                    "symbol": sym[0],
                    "yahoo_symbol": sym[1],
                    "name": sym[2],
                    "category": sym[3],
                    "rank": sym[4]
                })
            conn.commit()
        
        logger.info(f"Inserted/updated {len(symbols)} symbols")
    
    def get_active_symbols(self) -> List[Dict]:
        """Get all active crypto symbols."""
        sql = "SELECT * FROM crypto_symbols WHERE is_active = 1 ORDER BY market_cap_rank"
        
        with self.engine.connect() as conn:
            result = conn.execute(text(sql))
            return [dict(row._mapping) for row in result]
    
    def get_yahoo_symbols(self) -> List[str]:
        """Get list of Yahoo symbols for active cryptos."""
        sql = "SELECT yahoo_symbol FROM crypto_symbols WHERE is_active = 1 ORDER BY market_cap_rank"
        
        with self.engine.connect() as conn:
            result = conn.execute(text(sql))
            return [row[0] for row in result]
    
    # ==================== Daily Quotes Operations ====================
    
    def upsert_daily_quotes(self, df: pd.DataFrame):
        """Upsert daily quotes dataframe.
        
        Args:
            df: DataFrame with columns: symbol, trade_date, open_price, high_price, 
                low_price, close_price, volume, pct_change
        """
        if df.empty:
            return
        
        # Create temp table and upsert
        with self.engine.connect() as conn:
            # Write to temp table
            df.to_sql("tmp_crypto_quotes", con=conn, if_exists="replace", index=False, method="multi", chunksize=5000)
            
            # Upsert to main table
            upsert_sql = """
                INSERT INTO crypto_daily_quotes (symbol, trade_date, open_price, high_price, low_price, close_price, volume, pct_change)
                SELECT symbol, trade_date, open_price, high_price, low_price, close_price, volume, pct_change
                FROM tmp_crypto_quotes
                ON DUPLICATE KEY UPDATE
                    open_price = VALUES(open_price),
                    high_price = VALUES(high_price),
                    low_price = VALUES(low_price),
                    close_price = VALUES(close_price),
                    volume = VALUES(volume),
                    pct_change = VALUES(pct_change),
                    updated_at = CURRENT_TIMESTAMP
            """
            conn.execute(text(upsert_sql))
            conn.execute(text("DROP TABLE IF EXISTS tmp_crypto_quotes"))
            conn.commit()
        
        logger.info(f"Upserted {len(df)} daily quote records")
    
    def get_daily_quotes(self, symbol: str, start_date: date = None, end_date: date = None) -> pd.DataFrame:
        """Get daily quotes for a symbol.
        
        Args:
            symbol: Base symbol (BTC) or Yahoo symbol (BTC-USD)
            start_date: Start date (optional)
            end_date: End date (optional)
        """
        # Normalize symbol
        symbol = symbol.replace("-USD", "").upper()
        
        sql = "SELECT * FROM crypto_daily_quotes WHERE symbol = :symbol"
        params = {"symbol": symbol}
        
        if start_date:
            sql += " AND trade_date >= :start_date"
            params["start_date"] = start_date
        
        if end_date:
            sql += " AND trade_date <= :end_date"
            params["end_date"] = end_date
        
        sql += " ORDER BY trade_date"
        
        with self.engine.connect() as conn:
            return pd.read_sql(text(sql), conn, params=params)
    
    def get_latest_date(self, symbol: str = None) -> Optional[date]:
        """Get the latest date with data.
        
        Args:
            symbol: Optional symbol to check (if None, returns max across all)
        """
        if symbol:
            symbol = symbol.replace("-USD", "").upper()
            sql = "SELECT MAX(trade_date) FROM crypto_daily_quotes WHERE symbol = :symbol"
            params = {"symbol": symbol}
        else:
            sql = "SELECT MAX(trade_date) FROM crypto_daily_quotes"
            params = {}
        
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), params)
            row = result.fetchone()
            return row[0] if row and row[0] else None
    
    def get_quotes_for_date(self, trade_date: date) -> pd.DataFrame:
        """Get all quotes for a specific date."""
        sql = """
            SELECT q.*, s.name, s.category
            FROM crypto_daily_quotes q
            JOIN crypto_symbols s ON q.symbol = s.symbol
            WHERE q.trade_date = :trade_date
            ORDER BY s.market_cap_rank
        """
        
        with self.engine.connect() as conn:
            return pd.read_sql(text(sql), conn, params={"trade_date": trade_date})
    
    # ==================== Moving Averages Operations ====================
    
    def upsert_moving_averages(self, df: pd.DataFrame):
        """Upsert moving averages dataframe.
        
        Args:
            df: DataFrame with columns: symbol, trade_date, ema_21, sma_5, sma_10, 
                sma_20, sma_50, sma_150, sma_200, price_vs_sma50, price_vs_sma200, sma50_vs_sma200
        """
        if df.empty:
            return
        
        with self.engine.connect() as conn:
            df.to_sql("tmp_crypto_ma", con=conn, if_exists="replace", index=False, method="multi", chunksize=5000)
            
            upsert_sql = """
                INSERT INTO crypto_daily_ma (symbol, trade_date, ema_21, sma_5, sma_10, sma_20, sma_50, sma_150, sma_200, 
                                             price_vs_sma50, price_vs_sma200, sma50_vs_sma200)
                SELECT symbol, trade_date, ema_21, sma_5, sma_10, sma_20, sma_50, sma_150, sma_200,
                       price_vs_sma50, price_vs_sma200, sma50_vs_sma200
                FROM tmp_crypto_ma
                ON DUPLICATE KEY UPDATE
                    ema_21 = VALUES(ema_21),
                    sma_5 = VALUES(sma_5),
                    sma_10 = VALUES(sma_10),
                    sma_20 = VALUES(sma_20),
                    sma_50 = VALUES(sma_50),
                    sma_150 = VALUES(sma_150),
                    sma_200 = VALUES(sma_200),
                    price_vs_sma50 = VALUES(price_vs_sma50),
                    price_vs_sma200 = VALUES(price_vs_sma200),
                    sma50_vs_sma200 = VALUES(sma50_vs_sma200),
                    updated_at = CURRENT_TIMESTAMP
            """
            conn.execute(text(upsert_sql))
            conn.execute(text("DROP TABLE IF EXISTS tmp_crypto_ma"))
            conn.commit()
        
        logger.info(f"Upserted {len(df)} MA records")
    
    # ==================== RSI Operations ====================
    
    def upsert_rsi(self, df: pd.DataFrame):
        """Upsert RSI dataframe.
        
        Args:
            df: DataFrame with columns: symbol, trade_date, rsi_9, rsi_14, rsi_zone
        """
        if df.empty:
            return
        
        with self.engine.connect() as conn:
            df.to_sql("tmp_crypto_rsi", con=conn, if_exists="replace", index=False, method="multi", chunksize=5000)
            
            upsert_sql = """
                INSERT INTO crypto_daily_rsi (symbol, trade_date, rsi_9, rsi_14, rsi_zone)
                SELECT symbol, trade_date, rsi_9, rsi_14, rsi_zone
                FROM tmp_crypto_rsi
                ON DUPLICATE KEY UPDATE
                    rsi_9 = VALUES(rsi_9),
                    rsi_14 = VALUES(rsi_14),
                    rsi_zone = VALUES(rsi_zone),
                    updated_at = CURRENT_TIMESTAMP
            """
            conn.execute(text(upsert_sql))
            conn.execute(text("DROP TABLE IF EXISTS tmp_crypto_rsi"))
            conn.commit()
        
        logger.info(f"Upserted {len(df)} RSI records")
    
    # ==================== Advance/Decline Operations ====================
    
    def upsert_advance_decline(self, data: Dict):
        """Upsert a single day's advance/decline data.
        
        Args:
            data: Dictionary with all advance/decline fields
        """
        sql = """
            INSERT INTO crypto_advance_decline (
                trade_date, advances, declines, unchanged, total_coins, ad_ratio, ad_diff, ad_line,
                gain_0_1, gain_1_2, gain_2_3, gain_3_5, gain_5_10, gain_10_plus,
                loss_0_1, loss_1_2, loss_2_3, loss_3_5, loss_5_10, loss_10_plus,
                avg_change, median_change, total_volume
            ) VALUES (
                :trade_date, :advances, :declines, :unchanged, :total_coins, :ad_ratio, :ad_diff, :ad_line,
                :gain_0_1, :gain_1_2, :gain_2_3, :gain_3_5, :gain_5_10, :gain_10_plus,
                :loss_0_1, :loss_1_2, :loss_2_3, :loss_3_5, :loss_5_10, :loss_10_plus,
                :avg_change, :median_change, :total_volume
            )
            ON DUPLICATE KEY UPDATE
                advances = VALUES(advances),
                declines = VALUES(declines),
                unchanged = VALUES(unchanged),
                total_coins = VALUES(total_coins),
                ad_ratio = VALUES(ad_ratio),
                ad_diff = VALUES(ad_diff),
                ad_line = VALUES(ad_line),
                gain_0_1 = VALUES(gain_0_1),
                gain_1_2 = VALUES(gain_1_2),
                gain_2_3 = VALUES(gain_2_3),
                gain_3_5 = VALUES(gain_3_5),
                gain_5_10 = VALUES(gain_5_10),
                gain_10_plus = VALUES(gain_10_plus),
                loss_0_1 = VALUES(loss_0_1),
                loss_1_2 = VALUES(loss_1_2),
                loss_2_3 = VALUES(loss_2_3),
                loss_3_5 = VALUES(loss_3_5),
                loss_5_10 = VALUES(loss_5_10),
                loss_10_plus = VALUES(loss_10_plus),
                avg_change = VALUES(avg_change),
                median_change = VALUES(median_change),
                total_volume = VALUES(total_volume),
                updated_at = CURRENT_TIMESTAMP
        """
        
        with self.engine.connect() as conn:
            conn.execute(text(sql), data)
            conn.commit()
    
    def get_advance_decline(self, start_date: date = None, end_date: date = None) -> pd.DataFrame:
        """Get advance/decline data for date range."""
        sql = "SELECT * FROM crypto_advance_decline WHERE 1=1"
        params = {}
        
        if start_date:
            sql += " AND trade_date >= :start_date"
            params["start_date"] = start_date
        
        if end_date:
            sql += " AND trade_date <= :end_date"
            params["end_date"] = end_date
        
        sql += " ORDER BY trade_date"
        
        with self.engine.connect() as conn:
            return pd.read_sql(text(sql), conn, params=params)
    
    def get_latest_ad_line(self) -> float:
        """Get the latest cumulative A/D line value."""
        sql = "SELECT ad_line FROM crypto_advance_decline ORDER BY trade_date DESC LIMIT 1"
        
        with self.engine.connect() as conn:
            result = conn.execute(text(sql))
            row = result.fetchone()
            return row[0] if row and row[0] else 0.0
    
    # ==================== Stats Operations ====================
    
    def get_table_stats(self) -> Dict[str, int]:
        """Get row counts for all tables."""
        tables = ["crypto_symbols", "crypto_daily_quotes", "crypto_daily_ma", "crypto_daily_rsi", "crypto_advance_decline"]
        stats = {}
        
        with self.engine.connect() as conn:
            for table in tables:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    stats[table] = result.scalar()
                except Exception:
                    stats[table] = 0
        
        return stats
    
    def dispose(self):
        """Close database connections."""
        if self._engine:
            self._engine.dispose()
            self._engine = None


# Singleton instance
_db_service: Optional[CryptoDBService] = None


def get_db_service() -> CryptoDBService:
    """Get singleton database service instance."""
    global _db_service
    if _db_service is None:
        _db_service = CryptoDBService()
    return _db_service


if __name__ == "__main__":
    # Test database service
    print("🪙 Testing Crypto Database Service")
    print("=" * 50)
    
    db = CryptoDBService()
    
    # Ensure tables exist
    db.ensure_database()
    db.ensure_tables()
    
    # Insert symbols
    from crypto.data.crypto_symbols import TOP_100_CRYPTOS
    db.insert_symbols(TOP_100_CRYPTOS)
    
    # Show stats
    stats = db.get_table_stats()
    print("\n📊 Table Stats:")
    for table, count in stats.items():
        print(f"  {table}: {count:,} rows")
    
    # Show active symbols
    symbols = db.get_active_symbols()
    print(f"\n✅ Active symbols: {len(symbols)}")
    print(f"   Top 5: {[s['symbol'] for s in symbols[:5]]}")
