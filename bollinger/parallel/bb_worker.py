"""
Bollinger Bands Worker

Worker process for parallel BB calculations.
"""

import logging
import signal
import threading
import time
import traceback
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
import uuid

from .bb_job_models import BBJob, JobType, JobStatus, JobResult
from .bb_redis_manager import BBRedisManager, RedisConfig
from ..services.bb_calculator import BBCalculator
from ..services.squeeze_detector import SqueezeDetector
from ..services.trend_analyzer import TrendAnalyzer
from ..services.bb_rating_service import BBRatingService
from ..db.bb_repository import BBRepository


logger = logging.getLogger(__name__)


class BBWorker:
    """
    Worker for processing Bollinger Bands jobs.
    
    Runs in a loop, fetching and processing jobs from Redis queue.
    """
    
    def __init__(self,
                 redis_config: RedisConfig = None,
                 worker_id: str = None,
                 poll_interval: float = 0.5):
        """
        Initialize worker.
        
        Args:
            redis_config: Redis configuration
            worker_id: Unique worker ID (auto-generated if None)
            poll_interval: Seconds between queue polls
        """
        self.worker_id = worker_id or f"bb-worker-{uuid.uuid4().hex[:8]}"
        self.poll_interval = poll_interval
        
        self.redis_manager = BBRedisManager(redis_config)
        self.repository = BBRepository()
        
        # Services
        self.calculator = BBCalculator()
        self.squeeze_detector = SqueezeDetector()
        self.trend_analyzer = TrendAnalyzer()
        self.rating_service = BBRatingService()
        
        # Worker state
        self._running = False
        self._current_job: Optional[BBJob] = None
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        # Statistics
        self.stats = {
            "jobs_processed": 0,
            "jobs_failed": 0,
            "total_processing_time_ms": 0,
            "started_at": None
        }
        
        # Job handlers
        self._handlers: Dict[JobType, Callable] = {
            JobType.CALCULATE_DAILY: self._handle_calculate_daily,
            JobType.CALCULATE_BACKFILL: self._handle_calculate_backfill,
            JobType.GENERATE_RATINGS: self._handle_generate_ratings,
            JobType.GENERATE_SIGNALS: self._handle_generate_signals,
            JobType.RUN_SCAN: self._handle_run_scan
        }
    
    def start(self):
        """Start the worker."""
        if self._running:
            logger.warning(f"Worker {self.worker_id} already running")
            return
        
        logger.info(f"Starting worker {self.worker_id}")
        self._running = True
        self.stats["started_at"] = datetime.now()
        
        # Register with Redis
        self.redis_manager.register_worker(self.worker_id, {
            "handlers": [jt.value for jt in self._handlers.keys()]
        })
        
        # Start heartbeat thread
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Main processing loop
        try:
            self._process_loop()
        except Exception as e:
            logger.error(f"Worker error: {e}")
            traceback.print_exc()
        finally:
            self.stop()
    
    def stop(self):
        """Stop the worker."""
        logger.info(f"Stopping worker {self.worker_id}")
        self._running = False
        self._shutdown_event.set()
        
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)
        
        self.redis_manager.close()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def _heartbeat_loop(self):
        """Send periodic heartbeats to Redis."""
        while self._running and not self._shutdown_event.is_set():
            try:
                status = "processing" if self._current_job else "idle"
                self.redis_manager.worker_heartbeat(self.worker_id, status)
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")
            
            self._shutdown_event.wait(30)  # Heartbeat every 30 seconds
    
    def _process_loop(self):
        """Main job processing loop."""
        logger.info(f"Worker {self.worker_id} entering processing loop")
        
        while self._running:
            try:
                # Fetch next job
                job = self.redis_manager.dequeue_job()
                
                if job is None:
                    # No jobs available, wait
                    time.sleep(self.poll_interval)
                    continue
                
                # Process the job
                self._current_job = job
                result = self._process_job(job)
                self._current_job = None
                
                # Update statistics
                self.stats["jobs_processed"] += 1
                if result:
                    self.stats["total_processing_time_ms"] += result.duration_ms
                
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                traceback.print_exc()
                time.sleep(1)  # Avoid tight loop on errors
    
    def _process_job(self, job: BBJob) -> Optional[JobResult]:
        """
        Process a single job.
        
        Returns:
            JobResult with processing details
        """
        start_time = time.time()
        logger.info(f"Processing job {job.job_id}: {job.job_type.value} for {job.symbol}")
        
        try:
            # Get handler for job type
            handler = self._handlers.get(job.job_type)
            
            if handler is None:
                raise ValueError(f"No handler for job type: {job.job_type}")
            
            # Execute handler
            result_data = handler(job)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Mark job complete
            self.redis_manager.complete_job(job, result_data)
            
            logger.info(f"Completed job {job.job_id} in {duration_ms:.0f}ms")
            
            return JobResult(
                job_id=job.job_id,
                symbol=job.symbol,
                success=True,
                duration_ms=duration_ms,
                records_processed=result_data.get("records_processed", 0) if result_data else 0,
                data=result_data
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            
            logger.error(f"Job {job.job_id} failed: {error_msg}")
            traceback.print_exc()
            
            # Mark job failed
            self.redis_manager.fail_job(job, error_msg)
            self.stats["jobs_failed"] += 1
            
            return JobResult(
                job_id=job.job_id,
                symbol=job.symbol,
                success=False,
                duration_ms=duration_ms,
                error=error_msg
            )
    
    def _handle_calculate_daily(self, job: BBJob) -> Dict[str, Any]:
        """Handle daily BB calculation job."""
        symbol = job.symbol
        trade_date = job.params.get("trade_date")
        
        if isinstance(trade_date, str):
            trade_date = date.fromisoformat(trade_date)
        
        # Get price data (would come from database)
        # For now, return placeholder
        # In real implementation: fetch from price database, calculate BB, save
        
        return {
            "symbol": symbol,
            "trade_date": str(trade_date) if trade_date else None,
            "records_processed": 1,
            "status": "calculated"
        }
    
    def _handle_calculate_backfill(self, job: BBJob) -> Dict[str, Any]:
        """Handle backfill calculation job."""
        symbol = job.symbol
        start_date = job.params.get("start_date")
        end_date = job.params.get("end_date")
        
        if isinstance(start_date, str):
            start_date = date.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)
        
        # In real implementation:
        # 1. Fetch historical price data
        # 2. Calculate BB for each day
        # 3. Save to database
        
        records = 0
        # ... processing logic ...
        
        return {
            "symbol": symbol,
            "start_date": str(start_date) if start_date else None,
            "end_date": str(end_date) if end_date else None,
            "records_processed": records
        }
    
    def _handle_generate_ratings(self, job: BBJob) -> Dict[str, Any]:
        """Handle rating generation job."""
        symbol = job.symbol
        trade_date = job.params.get("trade_date")
        
        # In real implementation:
        # 1. Fetch BB data for symbol
        # 2. Calculate rating using rating service
        # 3. Save rating to database
        
        return {
            "symbol": symbol,
            "trade_date": str(trade_date) if trade_date else None,
            "rating_calculated": True
        }
    
    def _handle_generate_signals(self, job: BBJob) -> Dict[str, Any]:
        """Handle signal generation job."""
        symbol = job.symbol
        
        # In real implementation:
        # 1. Fetch BB history
        # 2. Run signal generators
        # 3. Save signals to database
        
        return {
            "symbol": symbol,
            "signals_generated": 0
        }
    
    def _handle_run_scan(self, job: BBJob) -> Dict[str, Any]:
        """Handle scan job."""
        scan_type = job.params.get("scan_type")
        
        # In real implementation:
        # 1. Run appropriate scanner
        # 2. Cache results
        
        return {
            "scan_type": scan_type,
            "results_count": 0
        }


class WorkerPool:
    """Pool of workers for parallel processing."""
    
    def __init__(self,
                 num_workers: int = 5,
                 redis_config: RedisConfig = None):
        """
        Initialize worker pool.
        
        Args:
            num_workers: Number of workers to spawn
            redis_config: Redis configuration
        """
        self.num_workers = num_workers
        self.redis_config = redis_config or RedisConfig()
        self.workers: List[BBWorker] = []
        self.threads: List[threading.Thread] = []
    
    def start(self):
        """Start all workers in threads."""
        logger.info(f"Starting worker pool with {self.num_workers} workers")
        
        for i in range(self.num_workers):
            worker = BBWorker(
                redis_config=self.redis_config,
                worker_id=f"bb-worker-{i+1}"
            )
            self.workers.append(worker)
            
            thread = threading.Thread(target=worker.start, daemon=True)
            self.threads.append(thread)
            thread.start()
        
        logger.info(f"Started {len(self.workers)} workers")
    
    def stop(self):
        """Stop all workers."""
        logger.info("Stopping worker pool")
        
        for worker in self.workers:
            worker.stop()
        
        for thread in self.threads:
            thread.join(timeout=5)
        
        self.workers.clear()
        self.threads.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get combined stats from all workers."""
        total_processed = sum(w.stats["jobs_processed"] for w in self.workers)
        total_failed = sum(w.stats["jobs_failed"] for w in self.workers)
        total_time = sum(w.stats["total_processing_time_ms"] for w in self.workers)
        
        return {
            "workers": len(self.workers),
            "total_processed": total_processed,
            "total_failed": total_failed,
            "avg_processing_time_ms": total_time / total_processed if total_processed > 0 else 0
        }
