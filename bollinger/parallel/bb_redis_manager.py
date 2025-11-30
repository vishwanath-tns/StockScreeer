"""
Redis Manager for Bollinger Bands Processing

Handles Redis connections and pub/sub for event-driven processing.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set
from contextlib import contextmanager

try:
    import redis
    from redis.exceptions import ConnectionError, TimeoutError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from .bb_job_models import BBJob, BatchJob, JobStatus, JobType, JobPriority


logger = logging.getLogger(__name__)


class RedisConfig:
    """Redis connection configuration."""
    
    def __init__(self,
                 host: str = "localhost",
                 port: int = 6379,
                 db: int = 0,
                 password: Optional[str] = None,
                 socket_timeout: int = 5,
                 decode_responses: bool = True):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.socket_timeout = socket_timeout
        self.decode_responses = decode_responses


class BBRedisManager:
    """
    Redis manager for BB processing system.
    
    Handles:
    - Job queue management (priority queue)
    - Pub/sub for real-time events
    - Job status tracking
    - Result caching
    """
    
    # Redis key prefixes
    JOB_QUEUE = "bb:queue:jobs"
    JOB_DATA = "bb:jobs:"
    BATCH_DATA = "bb:batches:"
    WORKER_STATUS = "bb:workers:"
    RESULTS_CACHE = "bb:results:"
    EVENTS_CHANNEL = "bb:events"
    
    # Event types
    EVENT_JOB_CREATED = "job_created"
    EVENT_JOB_STARTED = "job_started"
    EVENT_JOB_COMPLETED = "job_completed"
    EVENT_JOB_FAILED = "job_failed"
    EVENT_BATCH_PROGRESS = "batch_progress"
    EVENT_BATCH_COMPLETED = "batch_completed"
    
    def __init__(self, config: RedisConfig = None):
        """
        Initialize Redis manager.
        
        Args:
            config: Redis configuration (uses defaults if None)
        """
        if not REDIS_AVAILABLE:
            raise ImportError("redis package not installed. Install with: pip install redis")
        
        self.config = config or RedisConfig()
        self._client: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        self._event_handlers: Dict[str, List[Callable]] = {}
    
    @property
    def client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                socket_timeout=self.config.socket_timeout,
                decode_responses=self.config.decode_responses
            )
        return self._client
    
    def ping(self) -> bool:
        """Check Redis connection."""
        try:
            return self.client.ping()
        except (ConnectionError, TimeoutError):
            return False
    
    def close(self):
        """Close Redis connection."""
        if self._pubsub:
            self._pubsub.close()
            self._pubsub = None
        if self._client:
            self._client.close()
            self._client = None
    
    # ========== Queue Operations ==========
    
    def enqueue_job(self, job: BBJob) -> bool:
        """
        Add a job to the queue.
        
        Jobs are stored with priority (higher = processed first).
        """
        try:
            # Store job data
            self.client.set(
                f"{self.JOB_DATA}{job.job_id}",
                job.to_json(),
                ex=86400 * 7  # Expire after 7 days
            )
            
            # Add to priority queue (sorted set with priority as score)
            self.client.zadd(
                self.JOB_QUEUE,
                {job.job_id: job.priority.value}
            )
            
            # Publish event
            self.publish_event(self.EVENT_JOB_CREATED, {
                "job_id": job.job_id,
                "symbol": job.symbol,
                "job_type": job.job_type.value
            })
            
            return True
        except Exception as e:
            logger.error(f"Failed to enqueue job: {e}")
            return False
    
    def enqueue_batch(self, batch: BatchJob) -> int:
        """
        Enqueue all jobs from a batch.
        
        Returns:
            Number of jobs enqueued
        """
        # Store batch data
        self.client.set(
            f"{self.BATCH_DATA}{batch.batch_id}",
            batch.to_json(),
            ex=86400 * 7
        )
        
        # Generate and enqueue individual jobs
        jobs = batch.generate_jobs()
        count = 0
        
        # Use pipeline for efficiency
        pipe = self.client.pipeline()
        
        for job in jobs:
            pipe.set(
                f"{self.JOB_DATA}{job.job_id}",
                job.to_json(),
                ex=86400 * 7
            )
            pipe.zadd(self.JOB_QUEUE, {job.job_id: job.priority.value})
            count += 1
        
        pipe.execute()
        
        return count
    
    def dequeue_job(self) -> Optional[BBJob]:
        """
        Get the highest priority job from queue.
        
        Returns:
            BBJob or None if queue is empty
        """
        try:
            # Pop highest priority job (highest score)
            result = self.client.zpopmax(self.JOB_QUEUE, 1)
            
            if not result:
                return None
            
            job_id = result[0][0]
            
            # Get job data
            job_data = self.client.get(f"{self.JOB_DATA}{job_id}")
            
            if not job_data:
                return None
            
            job = BBJob.from_json(job_data)
            job.mark_started()
            
            # Update job data
            self.client.set(
                f"{self.JOB_DATA}{job_id}",
                job.to_json(),
                ex=86400 * 7
            )
            
            # Publish event
            self.publish_event(self.EVENT_JOB_STARTED, {
                "job_id": job.job_id,
                "symbol": job.symbol
            })
            
            return job
            
        except Exception as e:
            logger.error(f"Failed to dequeue job: {e}")
            return None
    
    def get_queue_length(self) -> int:
        """Get number of jobs in queue."""
        return self.client.zcard(self.JOB_QUEUE)
    
    def get_job(self, job_id: str) -> Optional[BBJob]:
        """Get job by ID."""
        job_data = self.client.get(f"{self.JOB_DATA}{job_id}")
        if job_data:
            return BBJob.from_json(job_data)
        return None
    
    def update_job(self, job: BBJob):
        """Update job data."""
        self.client.set(
            f"{self.JOB_DATA}{job.job_id}",
            job.to_json(),
            ex=86400 * 7
        )
    
    def complete_job(self, job: BBJob, result: Dict[str, Any] = None):
        """Mark job as completed."""
        job.mark_completed(result)
        self.update_job(job)
        
        # Publish event
        self.publish_event(self.EVENT_JOB_COMPLETED, {
            "job_id": job.job_id,
            "symbol": job.symbol,
            "duration_ms": (job.completed_at - job.started_at).total_seconds() * 1000 if job.started_at else 0
        })
        
        # Update batch if applicable
        batch_id = job.params.get("batch_id")
        if batch_id:
            self._update_batch_progress(batch_id, completed=True)
    
    def fail_job(self, job: BBJob, error: str):
        """Mark job as failed."""
        job.mark_failed(error)
        
        if job.can_retry():
            # Re-queue for retry
            job.status = JobStatus.PENDING
            self.enqueue_job(job)
        else:
            self.update_job(job)
            
            # Publish failure event
            self.publish_event(self.EVENT_JOB_FAILED, {
                "job_id": job.job_id,
                "symbol": job.symbol,
                "error": error
            })
            
            # Update batch if applicable
            batch_id = job.params.get("batch_id")
            if batch_id:
                self._update_batch_progress(batch_id, failed=True)
    
    def _update_batch_progress(self, batch_id: str, completed: bool = False, failed: bool = False):
        """Update batch progress."""
        batch_data = self.client.get(f"{self.BATCH_DATA}{batch_id}")
        if not batch_data:
            return
        
        batch = BatchJob.from_dict(json.loads(batch_data))
        
        if completed:
            batch.completed_jobs += 1
        if failed:
            batch.failed_jobs += 1
        
        # Check if batch is complete
        if batch.is_complete:
            batch.completed_at = datetime.now()
            self.publish_event(self.EVENT_BATCH_COMPLETED, {
                "batch_id": batch_id,
                "total": batch.total_jobs,
                "completed": batch.completed_jobs,
                "failed": batch.failed_jobs
            })
        else:
            self.publish_event(self.EVENT_BATCH_PROGRESS, {
                "batch_id": batch_id,
                "progress": batch.progress_percent,
                "completed": batch.completed_jobs,
                "failed": batch.failed_jobs,
                "total": batch.total_jobs
            })
        
        self.client.set(
            f"{self.BATCH_DATA}{batch_id}",
            batch.to_json(),
            ex=86400 * 7
        )
    
    # ========== Pub/Sub Operations ==========
    
    def publish_event(self, event_type: str, data: Dict[str, Any]):
        """Publish an event to the events channel."""
        message = json.dumps({
            "event": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
        self.client.publish(self.EVENTS_CHANNEL, message)
    
    def subscribe(self, handler: Callable[[str, Dict], None]):
        """
        Subscribe to events.
        
        Args:
            handler: Callback function (event_type, data)
        """
        if self._pubsub is None:
            self._pubsub = self.client.pubsub()
            self._pubsub.subscribe(self.EVENTS_CHANNEL)
        
        def message_handler(message):
            if message["type"] == "message":
                event_data = json.loads(message["data"])
                handler(event_data["event"], event_data["data"])
        
        # Start listening in a thread
        self._pubsub.run_in_thread(sleep_time=0.1)
    
    # ========== Cache Operations ==========
    
    def cache_result(self, symbol: str, date_str: str, data: Dict[str, Any],
                     ttl: int = 3600):
        """Cache BB calculation result."""
        key = f"{self.RESULTS_CACHE}{symbol}:{date_str}"
        self.client.set(key, json.dumps(data), ex=ttl)
    
    def get_cached_result(self, symbol: str, date_str: str) -> Optional[Dict[str, Any]]:
        """Get cached result."""
        key = f"{self.RESULTS_CACHE}{symbol}:{date_str}"
        data = self.client.get(key)
        if data:
            return json.loads(data)
        return None
    
    # ========== Worker Management ==========
    
    def register_worker(self, worker_id: str, capabilities: Dict[str, Any] = None):
        """Register a worker."""
        worker_data = {
            "worker_id": worker_id,
            "status": "idle",
            "registered_at": datetime.now().isoformat(),
            "last_heartbeat": datetime.now().isoformat(),
            "capabilities": capabilities or {}
        }
        self.client.set(
            f"{self.WORKER_STATUS}{worker_id}",
            json.dumps(worker_data),
            ex=300  # Expire after 5 minutes without heartbeat
        )
    
    def worker_heartbeat(self, worker_id: str, status: str = "idle"):
        """Update worker heartbeat."""
        key = f"{self.WORKER_STATUS}{worker_id}"
        worker_data = self.client.get(key)
        
        if worker_data:
            data = json.loads(worker_data)
            data["last_heartbeat"] = datetime.now().isoformat()
            data["status"] = status
            self.client.set(key, json.dumps(data), ex=300)
    
    def get_active_workers(self) -> List[Dict[str, Any]]:
        """Get list of active workers."""
        workers = []
        for key in self.client.scan_iter(f"{self.WORKER_STATUS}*"):
            data = self.client.get(key)
            if data:
                workers.append(json.loads(data))
        return workers
    
    def clear_queue(self):
        """Clear all pending jobs (use with caution)."""
        self.client.delete(self.JOB_QUEUE)
