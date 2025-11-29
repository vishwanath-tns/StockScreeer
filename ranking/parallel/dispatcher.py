#!/usr/bin/env python3
"""
Parallel Rankings Dispatcher

Orchestrates the parallel calculation of historical rankings.
Creates jobs, distributes to workers via Redis, monitors progress.

Usage:
    from ranking.parallel import ParallelRankingsDispatcher
    
    dispatcher = ParallelRankingsDispatcher()
    result = dispatcher.build_historical_rankings(years=3)
"""

import os
import sys
import time
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Callable, Dict, Any
import threading

from sqlalchemy import text

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ranking.parallel.redis_manager import RedisManager, check_redis_available
from ranking.parallel.job_models import RankingJob, JobType, BatchProgress
from ranking.db.schema import get_ranking_engine

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ParallelRankingsDispatcher:
    """
    Dispatches ranking jobs to parallel workers.
    
    Responsibilities:
    - Create jobs for each date to process
    - Enqueue jobs to Redis
    - Monitor progress
    - Aggregate results
    """
    
    def __init__(self, engine=None):
        """
        Initialize dispatcher.
        
        Args:
            engine: SQLAlchemy engine. Creates from env if not provided.
        """
        self.engine = engine or get_ranking_engine()
        self.redis = RedisManager()
        
        self.batch_id: str = ""
        self.progress = BatchProgress(batch_id="")
        self.stop_requested = False
        
        self._monitor_thread: Optional[threading.Thread] = None
        self._progress_callback: Optional[Callable] = None
    
    def get_trading_dates(
        self,
        start_date: date,
        end_date: date
    ) -> List[date]:
        """Get list of trading dates with data."""
        sql = """
        SELECT DISTINCT date 
        FROM yfinance_daily_quotes 
        WHERE date BETWEEN :start AND :end
        ORDER BY date
        """
        
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), {
                "start": start_date,
                "end": end_date
            })
            return [row[0] for row in result]
    
    def get_already_calculated_dates(
        self,
        start_date: date,
        end_date: date
    ) -> set:
        """Get dates already in history table."""
        sql = """
        SELECT DISTINCT ranking_date 
        FROM stock_rankings_history 
        WHERE ranking_date BETWEEN :start AND :end
        """
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql), {
                    "start": start_date,
                    "end": end_date
                })
                return {row[0] for row in result}
        except Exception as e:
            logger.warning(f"Could not get existing dates: {e}")
            return set()
    
    def create_jobs(
        self,
        dates: List[date],
        batch_id: str
    ) -> List[str]:
        """
        Create and enqueue jobs for dates.
        
        Args:
            dates: List of dates to process.
            batch_id: Batch identifier.
            
        Returns:
            List of job IDs.
        """
        jobs = []
        
        for calc_date in dates:
            job = RankingJob(
                job_type=JobType.CALCULATE_DATE,
                calculation_date=calc_date,
                symbols=[],  # All symbols
                batch_id=batch_id,
            )
            jobs.append(job.to_dict())
        
        # Enqueue all jobs in batch
        job_ids = self.redis.enqueue_jobs_batch(jobs)
        
        logger.info(f"Created {len(job_ids)} jobs for batch {batch_id}")
        
        return job_ids
    
    def build_historical_rankings(
        self,
        years: int = 3,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        skip_existing: bool = True,
        progress_callback: Optional[Callable] = None,
        wait_for_completion: bool = True,
        poll_interval: float = 2.0
    ) -> Dict[str, Any]:
        """
        Build historical rankings using parallel workers.
        
        Args:
            years: Number of years to build.
            start_date: Override start date (YYYY-MM-DD).
            end_date: Override end date (YYYY-MM-DD).
            skip_existing: Skip dates already calculated.
            progress_callback: Optional callback(BatchProgress).
            wait_for_completion: Wait for all jobs to complete.
            poll_interval: Seconds between progress checks.
            
        Returns:
            Result summary.
        """
        self.stop_requested = False
        self._progress_callback = progress_callback
        
        # Generate batch ID
        self.batch_id = f"batch-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Determine date range
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            end_dt = date.today() - timedelta(days=1)
        
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        else:
            start_dt = end_dt - timedelta(days=years * 365)
        
        logger.info(f"Building rankings from {start_dt} to {end_dt}")
        
        # Get trading dates
        trading_dates = self.get_trading_dates(start_dt, end_dt)
        logger.info(f"Found {len(trading_dates)} trading dates")
        
        if not trading_dates:
            return {
                "success": False,
                "error": "No trading dates found",
                "batch_id": self.batch_id
            }
        
        # Filter out existing dates
        existing_dates = set()
        if skip_existing:
            existing_dates = self.get_already_calculated_dates(start_dt, end_dt)
            logger.info(f"Skipping {len(existing_dates)} already calculated dates")
        
        dates_to_process = [d for d in trading_dates if d not in existing_dates]
        
        if not dates_to_process:
            return {
                "success": True,
                "batch_id": self.batch_id,
                "total_dates": len(trading_dates),
                "skipped": len(existing_dates),
                "processed": 0,
                "message": "All dates already calculated"
            }
        
        logger.info(f"Processing {len(dates_to_process)} dates")
        
        # Initialize progress
        self.progress = BatchProgress(
            batch_id=self.batch_id,
            total_jobs=len(dates_to_process),
            pending_jobs=len(dates_to_process),
            start_time=datetime.now()
        )
        
        # Clear any old jobs
        self.redis.clear_queue()
        
        # Create jobs
        job_ids = self.create_jobs(dates_to_process, self.batch_id)
        
        # Update Redis progress
        self.redis.update_progress(self.progress.to_dict())
        
        if not wait_for_completion:
            return {
                "success": True,
                "batch_id": self.batch_id,
                "jobs_created": len(job_ids),
                "message": "Jobs created. Workers will process them."
            }
        
        # Wait for completion with progress monitoring
        result = self._wait_for_completion(poll_interval)
        
        return result
    
    def _wait_for_completion(self, poll_interval: float) -> Dict[str, Any]:
        """Wait for all jobs to complete."""
        logger.info("Waiting for workers to complete jobs...")
        
        last_completed = 0
        stall_count = 0
        max_stall = 30  # 30 * poll_interval seconds without progress = stall
        
        while not self.stop_requested:
            stats = self.redis.get_queue_stats()
            
            self.progress.pending_jobs = stats["pending"]
            self.progress.processing_jobs = stats["processing"]
            self.progress.completed_jobs = stats["completed"]
            self.progress.failed_jobs = stats["failed"]
            
            # Check for progress stall (no workers?)
            if self.progress.completed_jobs == last_completed and self.progress.pending_jobs > 0:
                stall_count += 1
                if stall_count > max_stall:
                    logger.warning("No progress detected. Are workers running?")
                    workers = self.redis.get_active_workers()
                    if not workers:
                        logger.error("No active workers found!")
            else:
                stall_count = 0
                last_completed = self.progress.completed_jobs
            
            # Callback
            if self._progress_callback:
                self._progress_callback(self.progress)
            
            # Check completion
            if self.progress.pending_jobs == 0 and self.progress.processing_jobs == 0:
                logger.info("All jobs completed")
                break
            
            time.sleep(poll_interval)
        
        # Final stats
        return {
            "success": True,
            "batch_id": self.batch_id,
            "total_jobs": self.progress.total_jobs,
            "completed": self.progress.completed_jobs,
            "failed": self.progress.failed_jobs,
            "elapsed_seconds": self.progress.elapsed_seconds,
            "jobs_per_second": self.progress.jobs_per_second,
            "stopped": self.stop_requested
        }
    
    def get_active_workers(self) -> List[Dict[str, Any]]:
        """Get list of active workers."""
        return self.redis.get_active_workers()
    
    def get_progress(self) -> BatchProgress:
        """Get current progress."""
        stats = self.redis.get_queue_stats()
        
        self.progress.pending_jobs = stats["pending"]
        self.progress.processing_jobs = stats["processing"]
        self.progress.completed_jobs = stats["completed"]
        self.progress.failed_jobs = stats["failed"]
        
        return self.progress
    
    def stop(self):
        """Stop waiting for completion."""
        self.stop_requested = True
    
    def cancel_pending_jobs(self):
        """Cancel all pending jobs (clears queue)."""
        self.redis.clear_queue()
        logger.info("Pending jobs cancelled")


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Parallel Rankings Dispatcher")
    parser.add_argument("--years", type=int, default=3, help="Years of history")
    parser.add_argument("--start", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--no-skip", action="store_true", help="Don't skip existing")
    parser.add_argument("--no-wait", action="store_true", help="Don't wait for completion")
    
    args = parser.parse_args()
    
    # Check Redis
    if not check_redis_available():
        print("ERROR: Redis is not available. Please start Redis first.")
        sys.exit(1)
    
    print("=" * 60)
    print("Parallel Rankings Dispatcher")
    print("=" * 60)
    
    dispatcher = ParallelRankingsDispatcher()
    
    # Check for workers
    workers = dispatcher.get_active_workers()
    print(f"Active workers: {len(workers)}")
    
    if not workers and not args.no_wait:
        print("\nWARNING: No workers detected!")
        print("Start workers in separate terminals:")
        print("  python -m ranking.parallel.worker --id worker-1")
        print("  python -m ranking.parallel.worker --id worker-2")
        print("")
        
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(0)
    
    def progress_cb(p: BatchProgress):
        print(f"\rProgress: {p.completed_jobs}/{p.total_jobs} "
              f"({p.progress_pct:.1f}%) | "
              f"Rate: {p.jobs_per_second:.2f}/s | "
              f"ETA: {p.eta_seconds:.0f}s     ", end="")
    
    result = dispatcher.build_historical_rankings(
        years=args.years,
        start_date=args.start,
        end_date=args.end,
        skip_existing=not args.no_skip,
        progress_callback=progress_cb,
        wait_for_completion=not args.no_wait
    )
    
    print("\n" + "=" * 60)
    print("Result:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    print("=" * 60)


if __name__ == "__main__":
    main()
