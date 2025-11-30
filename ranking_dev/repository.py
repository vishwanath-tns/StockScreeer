"""
Ranking Repository

Database CRUD operations for stock rankings.
Handles saving, loading, and querying rankings.
"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any
import pandas as pd
from sqlalchemy import text
from .schema import get_ranking_engine


class RankingRepository:
    """
    Repository for stock ranking database operations.
    
    Handles:
    - Saving current rankings (upsert)
    - Saving historical snapshots
    - Loading rankings for display/analysis
    - Querying top stocks by various criteria
    """
    
    def __init__(self, engine=None):
        """Initialize with optional engine."""
        self.engine = engine or get_ranking_engine()
    
    # -------------------------------------------------------------------------
    # Save Operations
    # -------------------------------------------------------------------------
    
    def save_ranking(self, ranking: Dict[str, Any]) -> bool:
        """
        Save or update a single stock ranking.
        
        Args:
            ranking: Dict with symbol, calculation_date, scores, ranks.
            
        Returns:
            True if successful.
        """
        sql = """
        INSERT INTO stock_rankings 
            (symbol, calculation_date, rs_rating, momentum_score, 
             trend_template_score, technical_score, composite_score,
             rs_rank, momentum_rank, technical_rank, composite_rank,
             composite_percentile, total_stocks_ranked)
        VALUES 
            (:symbol, :calculation_date, :rs_rating, :momentum_score,
             :trend_template_score, :technical_score, :composite_score,
             :rs_rank, :momentum_rank, :technical_rank, :composite_rank,
             :composite_percentile, :total_stocks_ranked)
        ON DUPLICATE KEY UPDATE
            rs_rating = VALUES(rs_rating),
            momentum_score = VALUES(momentum_score),
            trend_template_score = VALUES(trend_template_score),
            technical_score = VALUES(technical_score),
            composite_score = VALUES(composite_score),
            rs_rank = VALUES(rs_rank),
            momentum_rank = VALUES(momentum_rank),
            technical_rank = VALUES(technical_rank),
            composite_rank = VALUES(composite_rank),
            composite_percentile = VALUES(composite_percentile),
            total_stocks_ranked = VALUES(total_stocks_ranked)
        """
        
        with self.engine.begin() as conn:
            conn.execute(text(sql), ranking)
        return True
    
    def save_rankings_batch(
        self,
        rankings: List[Dict[str, Any]],
        calculation_date: date,
    ) -> int:
        """
        Save multiple rankings in a batch.
        
        Args:
            rankings: List of ranking dicts.
            calculation_date: Date of calculation.
            
        Returns:
            Number of rankings saved.
        """
        if not rankings:
            return 0
        
        # Create DataFrame for bulk insert
        df = pd.DataFrame(rankings)
        df["calculation_date"] = calculation_date
        
        # Use temp table + upsert pattern
        with self.engine.begin() as conn:
            # Create temp table
            conn.execute(text("DROP TEMPORARY TABLE IF EXISTS tmp_rankings"))
            conn.execute(text("""
                CREATE TEMPORARY TABLE tmp_rankings (
                    symbol VARCHAR(20),
                    calculation_date DATE,
                    rs_rating DECIMAL(5,2),
                    momentum_score DECIMAL(5,2),
                    trend_template_score TINYINT,
                    technical_score DECIMAL(5,2),
                    composite_score DECIMAL(5,2),
                    rs_rank INT,
                    momentum_rank INT,
                    technical_rank INT,
                    composite_rank INT,
                    composite_percentile DECIMAL(5,2),
                    total_stocks_ranked INT
                )
            """))
            
            # Bulk insert to temp
            df.to_sql("tmp_rankings", conn, if_exists="append", index=False, method="multi", chunksize=500)
            
            # Upsert from temp
            conn.execute(text("""
                INSERT INTO stock_rankings 
                    (symbol, calculation_date, rs_rating, momentum_score,
                     trend_template_score, technical_score, composite_score,
                     rs_rank, momentum_rank, technical_rank, composite_rank,
                     composite_percentile, total_stocks_ranked)
                SELECT 
                    symbol, calculation_date, rs_rating, momentum_score,
                    trend_template_score, technical_score, composite_score,
                    rs_rank, momentum_rank, technical_rank, composite_rank,
                    composite_percentile, total_stocks_ranked
                FROM tmp_rankings
                ON DUPLICATE KEY UPDATE
                    rs_rating = VALUES(rs_rating),
                    momentum_score = VALUES(momentum_score),
                    trend_template_score = VALUES(trend_template_score),
                    technical_score = VALUES(technical_score),
                    composite_score = VALUES(composite_score),
                    rs_rank = VALUES(rs_rank),
                    momentum_rank = VALUES(momentum_rank),
                    technical_rank = VALUES(technical_rank),
                    composite_rank = VALUES(composite_rank),
                    composite_percentile = VALUES(composite_percentile),
                    total_stocks_ranked = VALUES(total_stocks_ranked)
            """))
        
        return len(rankings)
    
    def save_history_snapshot(
        self,
        rankings: List[Dict[str, Any]],
        ranking_date: date,
    ) -> int:
        """
        Save daily snapshot to history table.
        
        Args:
            rankings: List of ranking dicts.
            ranking_date: Date of snapshot.
            
        Returns:
            Number of history records saved.
        """
        if not rankings:
            return 0
        
        df = pd.DataFrame(rankings)
        df["ranking_date"] = ranking_date
        
        # Select only history columns
        history_cols = [
            "symbol", "ranking_date", "rs_rating", "momentum_score",
            "trend_template_score", "technical_score", "composite_score",
            "composite_rank", "composite_percentile", "total_stocks_ranked"
        ]
        df_history = df[[c for c in history_cols if c in df.columns]]
        
        with self.engine.begin() as conn:
            # Use INSERT IGNORE to skip duplicates
            conn.execute(text("DROP TEMPORARY TABLE IF EXISTS tmp_history"))
            conn.execute(text("""
                CREATE TEMPORARY TABLE tmp_history LIKE stock_rankings_history
            """))
            
            df_history.to_sql("tmp_history", conn, if_exists="append", index=False, method="multi")
            
            conn.execute(text("""
                INSERT IGNORE INTO stock_rankings_history 
                    (symbol, ranking_date, rs_rating, momentum_score,
                     trend_template_score, technical_score, composite_score,
                     composite_rank, composite_percentile, total_stocks_ranked)
                SELECT 
                    symbol, ranking_date, rs_rating, momentum_score,
                    trend_template_score, technical_score, composite_score,
                    composite_rank, composite_percentile, total_stocks_ranked
                FROM tmp_history
            """))
        
        return len(rankings)
    
    # -------------------------------------------------------------------------
    # Load Operations
    # -------------------------------------------------------------------------
    
    def get_latest_rankings(
        self,
        limit: int = 100,
        min_composite_percentile: float = 0,
    ) -> pd.DataFrame:
        """
        Get latest rankings sorted by composite rank.
        
        Args:
            limit: Max records to return.
            min_composite_percentile: Filter by min percentile.
            
        Returns:
            DataFrame with rankings.
        """
        sql = """
        SELECT * FROM stock_rankings
        WHERE calculation_date = (SELECT MAX(calculation_date) FROM stock_rankings)
          AND composite_percentile >= :min_percentile
        ORDER BY composite_rank ASC
        LIMIT :limit
        """
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params={
                "min_percentile": min_composite_percentile,
                "limit": limit
            })
        return df
    
    def get_rankings_for_date(
        self,
        calculation_date: date,
        symbols: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Get rankings for a specific date.
        
        Args:
            calculation_date: Date to get rankings for.
            symbols: Optional filter by symbols.
            
        Returns:
            DataFrame with rankings.
        """
        if symbols:
            placeholders = ",".join([f":s{i}" for i in range(len(symbols))])
            sql = f"""
            SELECT * FROM stock_rankings
            WHERE calculation_date = :calc_date
              AND symbol IN ({placeholders})
            ORDER BY composite_rank ASC
            """
            params = {"calc_date": calculation_date}
            params.update({f"s{i}": s for i, s in enumerate(symbols)})
        else:
            sql = """
            SELECT * FROM stock_rankings
            WHERE calculation_date = :calc_date
            ORDER BY composite_rank ASC
            """
            params = {"calc_date": calculation_date}
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params=params)
        return df
    
    def get_ranking_history(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """
        Get ranking history for a symbol.
        
        Args:
            symbol: Stock symbol.
            start_date: Optional start date filter.
            end_date: Optional end date filter.
            
        Returns:
            DataFrame with historical rankings.
        """
        sql = "SELECT * FROM stock_rankings_history WHERE symbol = :symbol"
        params = {"symbol": symbol}
        
        if start_date:
            sql += " AND ranking_date >= :start_date"
            params["start_date"] = start_date
        if end_date:
            sql += " AND ranking_date <= :end_date"
            params["end_date"] = end_date
        
        sql += " ORDER BY ranking_date ASC"
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params=params)
        return df
    
    def get_top_stocks_by_score(
        self,
        score_type: str = "composite_score",
        limit: int = 50,
        calculation_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """
        Get top stocks by a specific score type.
        
        Args:
            score_type: Score column name.
            limit: Number of top stocks.
            calculation_date: Date to query. If None, uses latest.
            
        Returns:
            DataFrame with top stocks.
        """
        valid_scores = [
            "rs_rating", "momentum_score", "trend_template_score",
            "technical_score", "composite_score"
        ]
        if score_type not in valid_scores:
            raise ValueError(f"Invalid score_type. Must be one of {valid_scores}")
        
        if calculation_date:
            sql = f"""
            SELECT * FROM stock_rankings
            WHERE calculation_date = :calc_date
            ORDER BY {score_type} DESC
            LIMIT :limit
            """
            params = {"calc_date": calculation_date, "limit": limit}
        else:
            sql = f"""
            SELECT * FROM stock_rankings
            WHERE calculation_date = (SELECT MAX(calculation_date) FROM stock_rankings)
            ORDER BY {score_type} DESC
            LIMIT :limit
            """
            params = {"limit": limit}
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params=params)
        return df
    
    # -------------------------------------------------------------------------
    # Utility Operations
    # -------------------------------------------------------------------------
    
    def get_available_dates(self) -> List[date]:
        """Get list of dates with rankings."""
        sql = "SELECT DISTINCT calculation_date FROM stock_rankings ORDER BY calculation_date DESC"
        with self.engine.connect() as conn:
            result = conn.execute(text(sql))
            return [row[0] for row in result]
    
    def get_stocks_count_for_date(self, calculation_date: date) -> int:
        """Get count of stocks ranked for a date."""
        sql = "SELECT COUNT(*) FROM stock_rankings WHERE calculation_date = :calc_date"
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), {"calc_date": calculation_date})
            return result.scalar() or 0


if __name__ == "__main__":
    # Test repository
    repo = RankingRepository()
    
    print("Available dates:", repo.get_available_dates())
    
    df = repo.get_latest_rankings(limit=10)
    if not df.empty:
        print(f"\nTop 10 stocks:\n{df[['symbol', 'composite_score', 'composite_rank']]}")
    else:
        print("\nNo rankings found. Run ranking calculation first.")
