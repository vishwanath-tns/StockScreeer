"""
Job Dispatcher for Bollinger Bands Processing

Dispatches jobs to the Redis queue for parallel processing.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set
import time

from .bb_job_models import (
    BBJob, BatchJob, JobType, JobPriority, JobStatus
)
from .bb_redis_manager import BBRedisManager, RedisConfig


logger = logging.getLogger(__name__)


class BBDispatcher:
    """
    Dispatcher for BB processing jobs.
    
    Responsibilities:
    - Create and enqueue jobs/batches
    - Track job/batch progress
    - Manage job priorities
    - Handle retries and failures
    """
    
    def __init__(self, redis_config: RedisConfig = None):
        """
        Initialize dispatcher.
        
        Args:
            redis_config: Redis configuration
        """
        self.redis_manager = BBRedisManager(redis_config)
        self._progress_callbacks: List[Callable] = []
    
    def dispatch_daily_calculation(self, 
                                   symbol: str,
                                   trade_date: date = None,
                                   priority: JobPriority = JobPriority.NORMAL) -> str:
        """
        Dispatch a single daily BB calculation job.
        
        Args:
            symbol: Stock symbol
            trade_date: Date to calculate (defaults to today)
            priority: Job priority
            
        Returns:
            Job ID
        """
        trade_date = trade_date or date.today()
        
        job = BBJob.create(
            job_type=JobType.CALCULATE_DAILY,
            symbol=symbol,
            priority=priority,
            trade_date=str(trade_date)
        )
        
        self.redis_manager.enqueue_job(job)
        logger.info(f"Dispatched daily calculation for {symbol} on {trade_date}")
        
        return job.job_id
    
    def dispatch_daily_batch(self,
                             symbols: List[str],
                             trade_date: date = None,
                             priority: JobPriority = JobPriority.NORMAL) -> str:
        """
        Dispatch daily calculation for multiple symbols.
        
        Args:
            symbols: List of stock symbols
            trade_date: Date to calculate
            priority: Job priority
            
        Returns:
            Batch ID
        """
        trade_date = trade_date or date.today()
        
        batch = BatchJob.create(
            job_type=JobType.CALCULATE_DAILY,
            symbols=symbols,
            priority=priority,
            trade_date=str(trade_date)
        )
        
        count = self.redis_manager.enqueue_batch(batch)
        logger.info(f"Dispatched batch {batch.batch_id} with {count} daily calculation jobs")
        
        return batch.batch_id
    
    def dispatch_backfill(self,
                          symbol: str,
                          start_date: date,
                          end_date: date = None,
                          priority: JobPriority = JobPriority.LOW) -> str:
        """
        Dispatch backfill calculation for a symbol.
        
        Args:
            symbol: Stock symbol
            start_date: Start of backfill period
            end_date: End of backfill period (defaults to today)
            priority: Job priority (lower for backfill)
            
        Returns:
            Job ID
        """
        end_date = end_date or date.today()
        
        job = BBJob.create(
            job_type=JobType.CALCULATE_BACKFILL,
            symbol=symbol,
            priority=priority,
            start_date=str(start_date),
            end_date=str(end_date)
        )
        
        self.redis_manager.enqueue_job(job)
        logger.info(f"Dispatched backfill for {symbol}: {start_date} to {end_date}")
        
        return job.job_id
    
    def dispatch_backfill_batch(self,
                                symbols: List[str],
                                start_date: date,
                                end_date: date = None,
                                priority: JobPriority = JobPriority.LOW) -> str:
        """
        Dispatch backfill for multiple symbols.
        
        Args:
            symbols: List of stock symbols
            start_date: Start of backfill period
            end_date: End of backfill period
            priority: Job priority
            
        Returns:
            Batch ID
        """
        end_date = end_date or date.today()
        
        batch = BatchJob.create(
            job_type=JobType.CALCULATE_BACKFILL,
            symbols=symbols,
            priority=priority,
            start_date=str(start_date),
            end_date=str(end_date)
        )
        
        count = self.redis_manager.enqueue_batch(batch)
        logger.info(f"Dispatched backfill batch {batch.batch_id} with {count} jobs")
        
        return batch.batch_id
    
    def dispatch_rating_generation(self,
                                    symbol: str,
                                    trade_date: date = None,
                                    priority: JobPriority = JobPriority.NORMAL) -> str:
        """
        Dispatch rating generation job.
        
        Args:
            symbol: Stock symbol
            trade_date: Date for rating
            priority: Job priority
            
        Returns:
            Job ID
        """
        trade_date = trade_date or date.today()
        
        job = BBJob.create(
            job_type=JobType.GENERATE_RATINGS,
            symbol=symbol,
            priority=priority,
            trade_date=str(trade_date)
        )
        
        self.redis_manager.enqueue_job(job)
        return job.job_id
    
    def dispatch_rating_batch(self,
                               symbols: List[str],
                               trade_date: date = None,
                               priority: JobPriority = JobPriority.NORMAL) -> str:
        """
        Dispatch rating generation for multiple symbols.
        
        Returns:
            Batch ID
        """
        trade_date = trade_date or date.today()
        
        batch = BatchJob.create(
            job_type=JobType.GENERATE_RATINGS,
            symbols=symbols,
            priority=priority,
            trade_date=str(trade_date)
        )
        
        count = self.redis_manager.enqueue_batch(batch)
        logger.info(f"Dispatched rating batch {batch.batch_id} with {count} jobs")
        
        return batch.batch_id
    
    def dispatch_signal_generation(self,
                                    symbol: str,
                                    priority: JobPriority = JobPriority.NORMAL) -> str:
        """
        Dispatch signal generation job.
        
        Returns:
            Job ID
        """
        job = BBJob.create(
            job_type=JobType.GENERATE_SIGNALS,
            symbol=symbol,
            priority=priority
        )
        
        self.redis_manager.enqueue_job(job)
        return job.job_id
    
    def dispatch_scan(self,
                      scan_type: str,
                      priority: JobPriority = JobPriority.HIGH) -> str:
        """
        Dispatch a scan job.
        
        Args:
            scan_type: Type of scan (squeeze, bulge, trend, pullback, reversion)
            priority: Job priority (high for scans - user-triggered)
            
        Returns:
            Job ID
        """
        job = BBJob.create(
            job_type=JobType.RUN_SCAN,
            symbol="*",  # All symbols
            priority=priority,
            scan_type=scan_type
        )
        
        self.redis_manager.enqueue_job(job)
        logger.info(f"Dispatched {scan_type} scan")
        
        return job.job_id
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a job.
        
        Returns:
            Job status dict or None if not found
        """
        job = self.redis_manager.get_job(job_id)
        if job:
            return {
                "job_id": job.job_id,
                "status": job.status.value,
                "symbol": job.symbol,
                "job_type": job.job_type.value,
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "result": job.result,
                "error": job.error_message
            }
        return None
    
    def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a batch.
        
        Returns:
            Batch status dict or None if not found
        """
        batch_data = self.redis_manager.client.get(
            f"{self.redis_manager.BATCH_DATA}{batch_id}"
        )
        
        if batch_data:
            import json
            batch = BatchJob.from_dict(json.loads(batch_data))
            return {
                "batch_id": batch.batch_id,
                "job_type": batch.job_type.value,
                "total_jobs": batch.total_jobs,
                "completed_jobs": batch.completed_jobs,
                "failed_jobs": batch.failed_jobs,
                "progress_percent": batch.progress_percent,
                "is_complete": batch.is_complete,
                "created_at": batch.created_at.isoformat(),
                "completed_at": batch.completed_at.isoformat() if batch.completed_at else None
            }
        return None
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics.
        
        Returns:
            Queue stats dict
        """
        queue_length = self.redis_manager.get_queue_length()
        workers = self.redis_manager.get_active_workers()
        
        return {
            "queue_length": queue_length,
            "active_workers": len(workers),
            "workers": workers
        }
    
    def wait_for_batch(self, batch_id: str, 
                       timeout: float = None,
                       poll_interval: float = 1.0,
                       progress_callback: Callable[[float], None] = None) -> bool:
        """
        Wait for a batch to complete.
        
        Args:
            batch_id: Batch ID to wait for
            timeout: Maximum wait time in seconds
            poll_interval: Seconds between status checks
            progress_callback: Optional callback for progress updates
            
        Returns:
            True if batch completed successfully, False if timeout or failed
        """
        start_time = time.time()
        last_progress = 0
        
        while True:
            status = self.get_batch_status(batch_id)
            
            if status is None:
                logger.error(f"Batch {batch_id} not found")
                return False
            
            # Report progress
            current_progress = status["progress_percent"]
            if progress_callback and current_progress != last_progress:
                progress_callback(current_progress)
                last_progress = current_progress
            
            if status["is_complete"]:
                success_rate = status["completed_jobs"] / status["total_jobs"] if status["total_jobs"] > 0 else 0
                return success_rate >= 0.9  # Consider success if 90%+ completed
            
            # Check timeout
            if timeout and (time.time() - start_time) >= timeout:
                logger.warning(f"Batch {batch_id} timed out")
                return False
            
            time.sleep(poll_interval)
    
    def cancel_batch(self, batch_id: str) -> bool:
        """
        Cancel a batch (remove pending jobs).
        
        Args:
            batch_id: Batch ID to cancel
            
        Returns:
            True if cancelled successfully
        """
        # Note: This only prevents pending jobs from running
        # Already running jobs will complete
        logger.warning(f"Batch cancellation not fully implemented: {batch_id}")
        return False
    
    def on_progress(self, callback: Callable[[str, float], None]):
        """
        Register a progress callback.
        
        Args:
            callback: Function(batch_id, progress_percent)
        """
        self._progress_callbacks.append(callback)
    
    def subscribe_to_events(self, handler: Callable[[str, Dict], None]):
        """
        Subscribe to job events.
        
        Args:
            handler: Function(event_type, event_data)
        """
        self.redis_manager.subscribe(handler)
