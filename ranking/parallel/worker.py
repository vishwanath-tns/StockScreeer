#!/usr/bin/env python3
"""
Ranking Worker

A worker process that pulls jobs from Redis queue and calculates rankings.
Multiple workers can run in parallel for scalability.

Usage:
    # Start a single worker
    python -m ranking.parallel.worker
    
    # Start with custom worker ID
    python -m ranking.parallel.worker --id worker-1
    
    # Start multiple workers (use different terminals or process manager)
    python -m ranking.parallel.worker --id worker-1
    python -m ranking.parallel.worker --id worker-2
    python -m ranking.parallel.worker --id worker-3
"""

import os
import sys
import time
import signal
import socket
import logging
import argparse
import threading
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
import uuid

import pandas as pd
from sqlalchemy import text

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ranking.parallel.redis_manager import RedisManager, check_redis_available
from ranking.parallel.job_models import RankingJob, JobType, JobStatus, WorkerInfo
from ranking.db.schema import get_ranking_engine
from ranking.services.rs_rating_service import RSRatingService
from ranking.services.momentum_score_service import MomentumScoreService
from ranking.services.trend_template_service import TrendTemplateService
from ranking.services.technical_score_service import TechnicalScoreService
from ranking.services.composite_score_service import CompositeScoreService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RankingWorker:
    """
    Worker that processes ranking jobs from Redis queue.
    
    Each worker:
    - Pulls jobs from the queue
    - Calculates rankings for the specified date/symbols
    - Saves results to database
    - Reports completion back to queue
    """
    
    def __init__(self, worker_id: str = None):
        """
        Initialize worker.
        
        Args:
            worker_id: Unique worker identifier. Auto-generated if not provided.
        """
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.hostname = socket.gethostname()
        self.pid = os.getpid()
        
        # Redis connection
        self.redis = RedisManager()
        
        # Database connection
        self.engine = get_ranking_engine()
        
        # Ranking calculators
        self.rs_service = RSRatingService()
        self.momentum_service = MomentumScoreService()
        self.trend_service = TrendTemplateService()
        self.technical_service = TechnicalScoreService()
        self.composite_service = CompositeScoreService()
        
        # Worker state
        self.running = False
        self.current_job: Optional[RankingJob] = None
        self.jobs_completed = 0
        self.jobs_failed = 0
        
        # Heartbeat thread
        self.heartbeat_thread: Optional[threading.Thread] = None
        
        logger.info(f"Worker {self.worker_id} initialized on {self.hostname}:{self.pid}")
    
    def start(self):
        """Start the worker."""
        self.running = True
        
        # Register with Redis
        self._register()
        
        # Start heartbeat
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        
        logger.info(f"Worker {self.worker_id} started")
        
        # Main processing loop
        self._process_loop()
    
    def stop(self):
        """Stop the worker gracefully."""
        logger.info(f"Worker {self.worker_id} stopping...")
        self.running = False
    
    def _register(self):
        """Register worker with Redis."""
        info = WorkerInfo(
            worker_id=self.worker_id,
            hostname=self.hostname,
            pid=self.pid,
            started_at=datetime.now(),
            last_heartbeat=datetime.now(),
            status="active"
        )
        self.redis.register_worker(self.worker_id, info.to_dict())
    
    def _heartbeat_loop(self):
        """Send heartbeats to Redis."""
        while self.running:
            try:
                self.redis.worker_heartbeat(self.worker_id)
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")
            time.sleep(10)  # Heartbeat every 10 seconds
    
    def _process_loop(self):
        """Main job processing loop."""
        while self.running:
            try:
                # Get next job (blocks for up to 5 seconds)
                job_data = self.redis.dequeue_job(timeout=5)
                
                if job_data is None:
                    continue
                
                # Parse job
                try:
                    job = RankingJob.from_dict(job_data)
                except Exception as e:
                    logger.error(f"Failed to parse job: {e}")
                    self.redis.fail_job(job_data.get("job_id", "unknown"), str(e))
                    self.jobs_failed += 1
                    continue
                
                self.current_job = job
                logger.info(f"Processing job {job.job_id}: {job.calculation_date} ({len(job.symbols) or 'all'} symbols)")
                
                # Process the job
                try:
                    result = self._process_job(job)
                    
                    # Complete job
                    self.redis.complete_job(job.job_id, result)
                    self.jobs_completed += 1
                    logger.info(f"Job {job.job_id} completed: {result.get('symbols_ranked', 0)} symbols ranked")
                    
                except Exception as e:
                    logger.exception(f"Job {job.job_id} failed")
                    self.redis.fail_job(job.job_id, str(e))
                    self.jobs_failed += 1
                
                self.current_job = None
                
            except Exception as e:
                logger.exception(f"Error in process loop: {e}")
                time.sleep(1)  # Avoid tight loop on persistent errors
    
    def _process_job(self, job: RankingJob) -> Dict[str, Any]:
        """
        Process a ranking job.
        
        Args:
            job: The job to process.
            
        Returns:
            Result dictionary.
        """
        calc_date = job.calculation_date
        symbols = job.symbols or None  # None means all symbols
        
        # Get price data
        price_data = self._get_price_data(calc_date, symbols)
        
        if price_data.empty:
            return {
                "success": False,
                "error": "No price data",
                "symbols_ranked": 0,
                "calculation_date": str(calc_date)
            }
        
        # Get unique symbols with data on this date
        symbols_on_date = price_data[price_data["date"] == calc_date]["symbol"].unique().tolist()
        
        if len(symbols_on_date) < 10:
            return {
                "success": False,
                "error": f"Only {len(symbols_on_date)} symbols on date",
                "symbols_ranked": len(symbols_on_date),
                "calculation_date": str(calc_date)
            }
        
        # Pivot for price series
        price_pivot = price_data.pivot_table(
            index="date", 
            columns="symbol", 
            values="close",
            aggfunc="last"
        )
        
        # Calculate rankings
        rankings = []
        
        for symbol in symbols_on_date:
            if symbol not in price_pivot.columns:
                continue
            
            symbol_prices = price_pivot[symbol].dropna()
            symbol_prices = symbol_prices[symbol_prices.index <= calc_date]
            
            if len(symbol_prices) < 50:
                continue
            
            try:
                ranking = self._calculate_symbol_ranking(
                    symbol, symbol_prices, price_pivot, calc_date
                )
                if ranking:
                    rankings.append(ranking)
            except Exception as e:
                logger.debug(f"Error calculating ranking for {symbol}: {e}")
                continue
        
        if not rankings:
            return {
                "success": False,
                "error": "No valid rankings calculated",
                "symbols_ranked": 0,
                "calculation_date": str(calc_date)
            }
        
        # Create DataFrame and calculate composite scores
        df = pd.DataFrame(rankings)
        
        # Calculate composite for each row using the service
        composite_scores = []
        for _, row in df.iterrows():
            result = self.composite_service.calculate_single(
                symbol=row["symbol"],
                rs_rating=row["rs_rating"],
                momentum_score=row["momentum_score"],
                trend_template_score=row["trend_template_score"],
                technical_score=row["technical_score"]
            )
            composite_scores.append(result.composite_score)
        
        df["composite_score"] = composite_scores
        
        # Calculate ranks
        total = len(df)
        df["composite_rank"] = df["composite_score"].rank(ascending=False, method="min").astype(int)
        df["composite_percentile"] = (df["composite_rank"] / total * 100).round(2)
        df["total_stocks_ranked"] = total
        df["ranking_date"] = calc_date
        
        # Save to history table
        saved = self._save_rankings(df, calc_date)
        
        return {
            "success": True,
            "symbols_ranked": len(df),
            "symbols_saved": saved,
            "calculation_date": str(calc_date),
            "top_5": df.nsmallest(5, "composite_rank")["symbol"].tolist()
        }
    
    def _get_price_data(
        self, 
        calc_date: date, 
        symbols: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """Get historical price data for calculations."""
        # Need 400 days of history for 12M calculations
        start_date = calc_date - timedelta(days=400)
        
        if symbols:
            placeholders = ",".join([f":s{i}" for i in range(len(symbols))])
            sql = f"""
            SELECT symbol, date, open, high, low, close, volume
            FROM yfinance_daily_quotes
            WHERE date BETWEEN :start AND :end
              AND symbol IN ({placeholders})
            ORDER BY symbol, date
            """
            params = {"start": start_date, "end": calc_date}
            params.update({f"s{i}": s for i, s in enumerate(symbols)})
        else:
            sql = """
            SELECT symbol, date, open, high, low, close, volume
            FROM yfinance_daily_quotes
            WHERE date BETWEEN :start AND :end
            ORDER BY symbol, date
            """
            params = {"start": start_date, "end": calc_date}
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params=params)
        
        return df
    
    def _calculate_symbol_ranking(
        self,
        symbol: str,
        symbol_prices: pd.Series,
        all_prices: pd.DataFrame,
        calc_date: date
    ) -> Optional[Dict[str, Any]]:
        """Calculate all ranking scores for a symbol."""
        if len(symbol_prices) < 50:
            return None
        
        current_price = symbol_prices.iloc[-1]
        
        # RS Rating (relative to all stocks)
        rs_rating = self._calculate_rs_rating(symbol, symbol_prices, all_prices, calc_date)
        
        # Momentum Score
        momentum = self._calculate_momentum(symbol_prices)
        
        # Trend Template (0-8)
        trend = self._calculate_trend_template(symbol_prices)
        
        # Technical Score
        technical = self._calculate_technical(symbol_prices)
        
        return {
            "symbol": symbol,
            "rs_rating": rs_rating,
            "momentum_score": momentum,
            "trend_template_score": trend,
            "technical_score": technical,
        }
    
    def _calculate_rs_rating(
        self,
        symbol: str,
        symbol_prices: pd.Series,
        all_prices: pd.DataFrame,
        calc_date: date
    ) -> float:
        """Calculate RS Rating (1-99 percentile)."""
        lookback = min(252, len(symbol_prices) - 1)
        if lookback < 20:
            return 50.0
        
        current = symbol_prices.iloc[-1]
        past = symbol_prices.iloc[-lookback-1] if lookback < len(symbol_prices) else symbol_prices.iloc[0]
        
        if past <= 0:
            return 50.0
        
        symbol_return = (current / past - 1) * 100
        
        # Get all returns
        all_returns = []
        for col in all_prices.columns:
            try:
                col_prices = all_prices[col].dropna()
                col_prices = col_prices[col_prices.index <= calc_date]
                
                if len(col_prices) > lookback:
                    curr = col_prices.iloc[-1]
                    past = col_prices.iloc[-lookback-1]
                    if past > 0:
                        all_returns.append((curr / past - 1) * 100)
            except:
                continue
        
        if not all_returns:
            return 50.0
        
        # Percentile
        rank = sum(1 for r in all_returns if r < symbol_return)
        percentile = (rank / len(all_returns)) * 99 + 1
        
        return round(min(99, max(1, percentile)), 0)
    
    def _calculate_momentum(self, prices: pd.Series) -> float:
        """Calculate momentum score (0-100)."""
        if len(prices) < 5:
            return 0.0
        
        weights = {5: 0.05, 21: 0.15, 63: 0.30, 126: 0.30, 252: 0.20}
        
        total_score = 0
        total_weight = 0
        current = prices.iloc[-1]
        
        for days, weight in weights.items():
            if len(prices) > days:
                past = prices.iloc[-days-1]
                if past > 0:
                    ret = (current / past - 1) * 100
                    normalized = min(100, max(0, (ret + 50) * (100 / 150)))
                    total_score += normalized * weight
                    total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return round(total_score / total_weight, 1)
    
    def _calculate_trend_template(self, prices: pd.Series) -> int:
        """Calculate trend template score (0-8)."""
        if len(prices) < 200:
            return 0
        
        current = prices.iloc[-1]
        sma_50 = prices.iloc[-50:].mean()
        sma_150 = prices.iloc[-150:].mean()
        sma_200 = prices.iloc[-200:].mean()
        
        sma_200_20d_ago = prices.iloc[-220:-20].mean() if len(prices) >= 220 else sma_200
        high_52w = prices.iloc[-252:].max() if len(prices) >= 252 else prices.max()
        pct_from_high = ((current / high_52w) - 1) * 100
        
        conditions = 0
        if current > sma_150: conditions += 1
        if current > sma_200: conditions += 1
        if sma_150 > sma_200: conditions += 1
        if sma_200 > sma_200_20d_ago: conditions += 1
        if sma_50 > sma_150: conditions += 1
        if sma_50 > sma_200: conditions += 1
        if current > sma_50: conditions += 1
        if pct_from_high >= -25: conditions += 1
        
        return conditions
    
    def _calculate_technical(self, prices: pd.Series) -> float:
        """Calculate technical score (0-100)."""
        if len(prices) < 200:
            return 0.0
        
        current = prices.iloc[-1]
        sma_50 = prices.iloc[-50:].mean()
        sma_150 = prices.iloc[-150:].mean()
        sma_200 = prices.iloc[-200:].mean()
        
        score = 0.0
        
        if current > sma_50:
            score += 25 + min(25, ((current / sma_50 - 1) * 100))
        if current > sma_150:
            score += 20
        if current > sma_200:
            score += 15
        if sma_50 > sma_150 > sma_200:
            score += 15
        
        return round(min(100, max(0, score)), 1)
    
    def _save_rankings(self, df: pd.DataFrame, ranking_date: date) -> int:
        """Save rankings to history table."""
        if df.empty:
            return 0
        
        history_cols = [
            "symbol", "ranking_date", "rs_rating", "momentum_score",
            "trend_template_score", "technical_score", "composite_score",
            "composite_rank", "composite_percentile", "total_stocks_ranked"
        ]
        df_save = df[[c for c in history_cols if c in df.columns]].copy()
        
        with self.engine.begin() as conn:
            conn.execute(text("DROP TEMPORARY TABLE IF EXISTS tmp_worker_hist"))
            conn.execute(text("""
                CREATE TEMPORARY TABLE tmp_worker_hist (
                    symbol VARCHAR(20),
                    ranking_date DATE,
                    rs_rating DECIMAL(5,2),
                    momentum_score DECIMAL(5,2),
                    trend_template_score TINYINT,
                    technical_score DECIMAL(5,2),
                    composite_score DECIMAL(5,2),
                    composite_rank INT,
                    composite_percentile DECIMAL(5,2),
                    total_stocks_ranked INT
                )
            """))
            
            df_save.to_sql("tmp_worker_hist", conn, if_exists="append", index=False, method="multi")
            
            conn.execute(text("""
                INSERT IGNORE INTO stock_rankings_history 
                    (symbol, ranking_date, rs_rating, momentum_score,
                     trend_template_score, technical_score, composite_score,
                     composite_rank, composite_percentile, total_stocks_ranked)
                SELECT 
                    symbol, ranking_date, rs_rating, momentum_score,
                    trend_template_score, technical_score, composite_score,
                    composite_rank, composite_percentile, total_stocks_ranked
                FROM tmp_worker_hist
            """))
        
        return len(df_save)


def main():
    """Main entry point for worker."""
    parser = argparse.ArgumentParser(description="Ranking Worker")
    parser.add_argument("--id", type=str, default=None, help="Worker ID")
    args = parser.parse_args()
    
    # Check Redis
    if not check_redis_available():
        print("ERROR: Redis is not available. Please start Redis first.")
        print("  Install: https://redis.io/download")
        print("  Or use Docker: docker run -d -p 6379:6379 redis")
        sys.exit(1)
    
    # Create and start worker
    worker = RankingWorker(worker_id=args.id)
    
    # Handle shutdown signals
    def signal_handler(signum, frame):
        print("\nReceived shutdown signal...")
        worker.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start worker
    try:
        worker.start()
    except KeyboardInterrupt:
        worker.stop()
    
    print(f"Worker {worker.worker_id} stopped. Completed: {worker.jobs_completed}, Failed: {worker.jobs_failed}")


if __name__ == "__main__":
    main()
