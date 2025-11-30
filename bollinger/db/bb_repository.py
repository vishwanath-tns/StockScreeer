"""
Repository for Bollinger Bands Database Operations

Handles CRUD operations for BB data, ratings, and signals.
"""

from datetime import date, datetime, timedelta
from typing import List, Dict, Optional, Any
import pandas as pd
from sqlalchemy import text

from .bb_schema import get_bb_engine


class BBRepository:
    """
    Repository for Bollinger Bands database operations.
    
    Handles:
    - Saving/loading daily BB values
    - Saving/loading BB ratings
    - Saving/loading signals
    - Cache management for scans
    """
    
    def __init__(self, engine=None):
        """Initialize with optional engine."""
        self.engine = engine or get_bb_engine()
    
    # =========================================================================
    # Daily BB Values
    # =========================================================================
    
    def save_bb_daily(self, data: Dict[str, Any]) -> bool:
        """
        Save or update daily BB values for a symbol.
        
        Args:
            data: Dict with symbol, date, bb values, etc.
        """
        sql = """
        INSERT INTO stock_bollinger_daily 
            (symbol, date, close_price, bb_upper, bb_middle, bb_lower,
             percent_b, bandwidth, bandwidth_percentile, bb_period, bb_std_dev)
        VALUES 
            (:symbol, :date, :close_price, :bb_upper, :bb_middle, :bb_lower,
             :percent_b, :bandwidth, :bandwidth_percentile, :bb_period, :bb_std_dev)
        ON DUPLICATE KEY UPDATE
            close_price = VALUES(close_price),
            bb_upper = VALUES(bb_upper),
            bb_middle = VALUES(bb_middle),
            bb_lower = VALUES(bb_lower),
            percent_b = VALUES(percent_b),
            bandwidth = VALUES(bandwidth),
            bandwidth_percentile = VALUES(bandwidth_percentile),
            bb_period = VALUES(bb_period),
            bb_std_dev = VALUES(bb_std_dev)
        """
        
        with self.engine.begin() as conn:
            conn.execute(text(sql), data)
        return True
    
    def save_bb_daily_batch(self, records: List[Dict[str, Any]]) -> int:
        """
        Save multiple daily BB records using batch upsert.
        
        Returns number of records saved.
        """
        if not records:
            return 0
        
        df = pd.DataFrame(records)
        
        with self.engine.begin() as conn:
            # Create temp table
            conn.execute(text("DROP TEMPORARY TABLE IF EXISTS tmp_bb_daily"))
            conn.execute(text("""
                CREATE TEMPORARY TABLE tmp_bb_daily (
                    symbol VARCHAR(20),
                    date DATE,
                    close_price DECIMAL(12,2),
                    bb_upper DECIMAL(12,2),
                    bb_middle DECIMAL(12,2),
                    bb_lower DECIMAL(12,2),
                    percent_b DECIMAL(8,4),
                    bandwidth DECIMAL(8,4),
                    bandwidth_percentile DECIMAL(5,2),
                    bb_period INT,
                    bb_std_dev DECIMAL(3,1)
                )
            """))
            
            # Bulk insert to temp
            df.to_sql("tmp_bb_daily", conn, if_exists="append", 
                      index=False, method="multi", chunksize=500)
            
            # Upsert from temp
            conn.execute(text("""
                INSERT INTO stock_bollinger_daily 
                    (symbol, date, close_price, bb_upper, bb_middle, bb_lower,
                     percent_b, bandwidth, bandwidth_percentile, bb_period, bb_std_dev)
                SELECT 
                    symbol, date, close_price, bb_upper, bb_middle, bb_lower,
                    percent_b, bandwidth, bandwidth_percentile, bb_period, bb_std_dev
                FROM tmp_bb_daily
                ON DUPLICATE KEY UPDATE
                    close_price = VALUES(close_price),
                    bb_upper = VALUES(bb_upper),
                    bb_middle = VALUES(bb_middle),
                    bb_lower = VALUES(bb_lower),
                    percent_b = VALUES(percent_b),
                    bandwidth = VALUES(bandwidth),
                    bandwidth_percentile = VALUES(bandwidth_percentile)
            """))
        
        return len(records)
    
    def get_bb_daily(self, symbol: str, start_date: date = None, 
                     end_date: date = None, limit: int = 500) -> pd.DataFrame:
        """Get daily BB values for a symbol."""
        sql = "SELECT * FROM stock_bollinger_daily WHERE symbol = :symbol"
        params = {"symbol": symbol}
        
        if start_date:
            sql += " AND date >= :start_date"
            params["start_date"] = start_date
        if end_date:
            sql += " AND date <= :end_date"
            params["end_date"] = end_date
        
        sql += " ORDER BY date DESC LIMIT :limit"
        params["limit"] = limit
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params=params)
        return df
    
    def get_latest_bb(self, symbol: str) -> Optional[Dict]:
        """Get the most recent BB values for a symbol."""
        sql = """
        SELECT * FROM stock_bollinger_daily 
        WHERE symbol = :symbol 
        ORDER BY date DESC LIMIT 1
        """
        
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), {"symbol": symbol}).fetchone()
        
        return dict(result._mapping) if result else None
    
    def get_all_latest_bb(self, target_date: date = None) -> pd.DataFrame:
        """Get latest BB values for all symbols."""
        if target_date is None:
            target_date = date.today()
        
        sql = """
        SELECT * FROM stock_bollinger_daily 
        WHERE date = (
            SELECT MAX(date) FROM stock_bollinger_daily WHERE date <= :target_date
        )
        ORDER BY percent_b DESC
        """
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params={"target_date": target_date})
        return df
    
    # =========================================================================
    # BB Ratings
    # =========================================================================
    
    def save_bb_rating(self, rating: Dict[str, Any]) -> bool:
        """Save or update a BB rating."""
        sql = """
        INSERT INTO stock_bb_ratings_history 
            (symbol, rating_date, squeeze_score, trend_score, momentum_score,
             pattern_score, composite_score, bb_rank, bb_percentile,
             total_stocks_ranked, percent_b, bandwidth, bandwidth_percentile,
             is_squeeze, is_bulge, trend_direction)
        VALUES 
            (:symbol, :rating_date, :squeeze_score, :trend_score, :momentum_score,
             :pattern_score, :composite_score, :bb_rank, :bb_percentile,
             :total_stocks_ranked, :percent_b, :bandwidth, :bandwidth_percentile,
             :is_squeeze, :is_bulge, :trend_direction)
        ON DUPLICATE KEY UPDATE
            squeeze_score = VALUES(squeeze_score),
            trend_score = VALUES(trend_score),
            momentum_score = VALUES(momentum_score),
            pattern_score = VALUES(pattern_score),
            composite_score = VALUES(composite_score),
            bb_rank = VALUES(bb_rank),
            bb_percentile = VALUES(bb_percentile),
            total_stocks_ranked = VALUES(total_stocks_ranked),
            percent_b = VALUES(percent_b),
            bandwidth = VALUES(bandwidth),
            bandwidth_percentile = VALUES(bandwidth_percentile),
            is_squeeze = VALUES(is_squeeze),
            is_bulge = VALUES(is_bulge),
            trend_direction = VALUES(trend_direction)
        """
        
        with self.engine.begin() as conn:
            conn.execute(text(sql), rating)
        return True
    
    def save_bb_ratings_batch(self, ratings: List[Dict[str, Any]], 
                               rating_date: date) -> int:
        """Save multiple BB ratings in batch."""
        if not ratings:
            return 0
        
        df = pd.DataFrame(ratings)
        df["rating_date"] = rating_date
        
        with self.engine.begin() as conn:
            conn.execute(text("DROP TEMPORARY TABLE IF EXISTS tmp_bb_ratings"))
            conn.execute(text("""
                CREATE TEMPORARY TABLE tmp_bb_ratings LIKE stock_bb_ratings_history
            """))
            
            df.to_sql("tmp_bb_ratings", conn, if_exists="append", 
                      index=False, method="multi", chunksize=500)
            
            conn.execute(text("""
                INSERT INTO stock_bb_ratings_history 
                    (symbol, rating_date, squeeze_score, trend_score, momentum_score,
                     pattern_score, composite_score, bb_rank, bb_percentile,
                     total_stocks_ranked, percent_b, bandwidth, bandwidth_percentile,
                     is_squeeze, is_bulge, trend_direction)
                SELECT 
                    symbol, rating_date, squeeze_score, trend_score, momentum_score,
                    pattern_score, composite_score, bb_rank, bb_percentile,
                    total_stocks_ranked, percent_b, bandwidth, bandwidth_percentile,
                    is_squeeze, is_bulge, trend_direction
                FROM tmp_bb_ratings
                ON DUPLICATE KEY UPDATE
                    squeeze_score = VALUES(squeeze_score),
                    trend_score = VALUES(trend_score),
                    momentum_score = VALUES(momentum_score),
                    pattern_score = VALUES(pattern_score),
                    composite_score = VALUES(composite_score),
                    bb_rank = VALUES(bb_rank),
                    bb_percentile = VALUES(bb_percentile)
            """))
        
        return len(ratings)
    
    def get_latest_ratings(self, limit: int = 100, 
                           min_composite: float = 0) -> pd.DataFrame:
        """Get latest BB ratings sorted by composite score."""
        sql = """
        SELECT * FROM stock_bb_ratings_history
        WHERE rating_date = (SELECT MAX(rating_date) FROM stock_bb_ratings_history)
          AND composite_score >= :min_composite
        ORDER BY composite_score DESC
        LIMIT :limit
        """
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params={
                "min_composite": min_composite,
                "limit": limit
            })
        return df
    
    def get_rating_history(self, symbol: str, 
                           start_date: date = None,
                           end_date: date = None) -> pd.DataFrame:
        """Get rating history for a symbol."""
        sql = "SELECT * FROM stock_bb_ratings_history WHERE symbol = :symbol"
        params = {"symbol": symbol}
        
        if start_date:
            sql += " AND rating_date >= :start_date"
            params["start_date"] = start_date
        if end_date:
            sql += " AND rating_date <= :end_date"
            params["end_date"] = end_date
        
        sql += " ORDER BY rating_date ASC"
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params=params)
        return df
    
    def get_squeeze_stocks(self, target_date: date = None) -> pd.DataFrame:
        """Get stocks currently in squeeze."""
        if target_date is None:
            target_date = date.today()
        
        sql = """
        SELECT * FROM stock_bb_ratings_history
        WHERE rating_date = (
            SELECT MAX(rating_date) FROM stock_bb_ratings_history 
            WHERE rating_date <= :target_date
        )
        AND is_squeeze = 1
        ORDER BY bandwidth_percentile ASC
        """
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params={"target_date": target_date})
        return df
    
    def get_trending_stocks(self, direction: str, 
                            target_date: date = None) -> pd.DataFrame:
        """Get stocks in specified trend direction."""
        if target_date is None:
            target_date = date.today()
        
        sql = """
        SELECT * FROM stock_bb_ratings_history
        WHERE rating_date = (
            SELECT MAX(rating_date) FROM stock_bb_ratings_history 
            WHERE rating_date <= :target_date
        )
        AND trend_direction = :direction
        ORDER BY trend_score DESC
        """
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params={
                "target_date": target_date,
                "direction": direction
            })
        return df
    
    # =========================================================================
    # Signals
    # =========================================================================
    
    def save_signal(self, signal: Dict[str, Any]) -> int:
        """Save a new signal. Returns signal ID."""
        sql = """
        INSERT INTO stock_bb_signals 
            (symbol, signal_date, signal_type, pattern, confidence,
             price_at_signal, percent_b, bandwidth, volume_confirmed,
             volume_ratio, target_price, stop_loss, description)
        VALUES 
            (:symbol, :signal_date, :signal_type, :pattern, :confidence,
             :price_at_signal, :percent_b, :bandwidth, :volume_confirmed,
             :volume_ratio, :target_price, :stop_loss, :description)
        """
        
        with self.engine.begin() as conn:
            result = conn.execute(text(sql), signal)
            return result.lastrowid
    
    def get_recent_signals(self, days: int = 7, 
                           signal_type: str = None,
                           min_confidence: float = 0) -> pd.DataFrame:
        """Get recent signals."""
        start_date = date.today() - timedelta(days=days)
        
        sql = """
        SELECT * FROM stock_bb_signals
        WHERE signal_date >= :start_date
          AND confidence >= :min_confidence
        """
        params = {"start_date": start_date, "min_confidence": min_confidence}
        
        if signal_type:
            sql += " AND signal_type = :signal_type"
            params["signal_type"] = signal_type
        
        sql += " ORDER BY signal_date DESC, confidence DESC"
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params=params)
        return df
    
    def get_signals_for_symbol(self, symbol: str, 
                                limit: int = 50) -> pd.DataFrame:
        """Get signals for a specific symbol."""
        sql = """
        SELECT * FROM stock_bb_signals
        WHERE symbol = :symbol
        ORDER BY signal_date DESC
        LIMIT :limit
        """
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params={
                "symbol": symbol, "limit": limit
            })
        return df
    
    def update_signal_outcome(self, signal_id: int, outcome: str,
                               exit_price: float, exit_date: date,
                               return_pct: float) -> bool:
        """Update signal with its outcome."""
        sql = """
        UPDATE stock_bb_signals
        SET outcome = :outcome,
            exit_price = :exit_price,
            exit_date = :exit_date,
            return_pct = :return_pct
        WHERE id = :signal_id
        """
        
        with self.engine.begin() as conn:
            conn.execute(text(sql), {
                "signal_id": signal_id,
                "outcome": outcome,
                "exit_price": exit_price,
                "exit_date": exit_date,
                "return_pct": return_pct
            })
        return True
    
    # =========================================================================
    # Scan Cache
    # =========================================================================
    
    def cache_scan_result(self, scan_type: str, scan_date: date,
                          result: Dict[str, Any], 
                          ttl_hours: int = 4) -> bool:
        """Cache a scan result."""
        import json
        
        expires_at = datetime.now() + timedelta(hours=ttl_hours)
        
        sql = """
        INSERT INTO stock_bb_scan_cache 
            (scan_type, scan_date, total_scanned, matches_found, 
             results_json, execution_time_ms, expires_at)
        VALUES 
            (:scan_type, :scan_date, :total_scanned, :matches_found,
             :results_json, :execution_time_ms, :expires_at)
        ON DUPLICATE KEY UPDATE
            total_scanned = VALUES(total_scanned),
            matches_found = VALUES(matches_found),
            results_json = VALUES(results_json),
            execution_time_ms = VALUES(execution_time_ms),
            expires_at = VALUES(expires_at),
            created_at = CURRENT_TIMESTAMP
        """
        
        with self.engine.begin() as conn:
            conn.execute(text(sql), {
                "scan_type": scan_type,
                "scan_date": scan_date,
                "total_scanned": result.get("total_scanned", 0),
                "matches_found": result.get("matches_found", 0),
                "results_json": json.dumps(result.get("results", [])),
                "execution_time_ms": result.get("execution_time_ms", 0),
                "expires_at": expires_at
            })
        return True
    
    def get_cached_scan(self, scan_type: str, 
                        scan_date: date) -> Optional[Dict]:
        """Get cached scan result if not expired."""
        sql = """
        SELECT * FROM stock_bb_scan_cache
        WHERE scan_type = :scan_type 
          AND scan_date = :scan_date
          AND expires_at > NOW()
        """
        
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), {
                "scan_type": scan_type,
                "scan_date": scan_date
            }).fetchone()
        
        if result:
            import json
            row = dict(result._mapping)
            row["results"] = json.loads(row["results_json"]) if row.get("results_json") else []
            return row
        return None
    
    def clear_expired_cache(self) -> int:
        """Clear expired cache entries. Returns count deleted."""
        sql = "DELETE FROM stock_bb_scan_cache WHERE expires_at < NOW()"
        
        with self.engine.begin() as conn:
            result = conn.execute(text(sql))
            return result.rowcount
    
    # =========================================================================
    # Utilities
    # =========================================================================
    
    def get_available_dates(self, table: str = "stock_bollinger_daily") -> List[date]:
        """Get list of dates with data."""
        sql = f"SELECT DISTINCT date FROM {table} ORDER BY date DESC"
        
        with self.engine.connect() as conn:
            result = conn.execute(text(sql))
            return [row[0] for row in result]
    
    def get_symbols_with_data(self, min_records: int = 252) -> List[str]:
        """Get symbols with sufficient data."""
        sql = """
        SELECT symbol, COUNT(*) as cnt
        FROM stock_bollinger_daily
        GROUP BY symbol
        HAVING COUNT(*) >= :min_records
        ORDER BY symbol
        """
        
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), {"min_records": min_records})
            return [row[0] for row in result]
    
    def get_date_range(self) -> Dict[str, date]:
        """Get min and max dates in BB data."""
        sql = """
        SELECT MIN(date) as min_date, MAX(date) as max_date
        FROM stock_bollinger_daily
        """
        
        with self.engine.connect() as conn:
            result = conn.execute(text(sql)).fetchone()
        
        return {
            "min_date": result[0] if result else None,
            "max_date": result[1] if result else None
        }
