"""
Redis Connection Manager

Provides Redis connection pooling and configuration for the ranking system.
Uses environment variables for configuration.
"""

import os
import json
import logging
from typing import Optional, Any, Dict, List
from datetime import datetime, timedelta
import redis
from redis import ConnectionPool
from dotenv import load_dotenv

# Load environment
load_dotenv()

logger = logging.getLogger(__name__)


class RedisConfig:
    """Redis configuration from environment."""
    
    def __init__(self):
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", "6379"))
        self.db = int(os.getenv("REDIS_DB", "0"))
        self.password = os.getenv("REDIS_PASSWORD", None)
        self.max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))
        
        # Key prefixes for namespacing
        self.prefix = "ranking:"
        self.job_queue_key = f"{self.prefix}jobs:pending"
        self.processing_key = f"{self.prefix}jobs:processing"
        self.results_key = f"{self.prefix}jobs:results"
        self.failed_key = f"{self.prefix}jobs:failed"
        self.progress_key = f"{self.prefix}progress"
        self.workers_key = f"{self.prefix}workers"
        self.events_channel = f"{self.prefix}events"


class RedisManager:
    """
    Manages Redis connections with connection pooling.
    
    Thread-safe and can be shared across multiple workers.
    """
    
    _instance: Optional['RedisManager'] = None
    _pool: Optional[ConnectionPool] = None
    
    def __new__(cls):
        """Singleton pattern for connection pool reuse."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.config = RedisConfig()
        self._create_pool()
        self._initialized = True
        logger.info(f"Redis manager initialized: {self.config.host}:{self.config.port}")
    
    def _create_pool(self):
        """Create connection pool."""
        RedisManager._pool = ConnectionPool(
            host=self.config.host,
            port=self.config.port,
            db=self.config.db,
            password=self.config.password,
            max_connections=self.config.max_connections,
            decode_responses=True,  # Return strings instead of bytes
        )
    
    def get_client(self) -> redis.Redis:
        """Get a Redis client from the pool."""
        return redis.Redis(connection_pool=self._pool)
    
    def ping(self) -> bool:
        """Test Redis connection."""
        try:
            client = self.get_client()
            return client.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False
    
    # -------------------------------------------------------------------------
    # Job Queue Operations
    # -------------------------------------------------------------------------
    
    def enqueue_job(self, job_data: Dict[str, Any]) -> str:
        """
        Add a job to the queue.
        
        Args:
            job_data: Job parameters (symbols, date, etc.)
            
        Returns:
            Job ID.
        """
        client = self.get_client()
        
        job_id = f"job:{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        job_data["job_id"] = job_id
        job_data["created_at"] = datetime.now().isoformat()
        job_data["status"] = "pending"
        
        # Store job data
        client.hset(f"{self.config.prefix}{job_id}", mapping={
            k: json.dumps(v) if isinstance(v, (list, dict)) else str(v)
            for k, v in job_data.items()
        })
        
        # Add to queue
        client.lpush(self.config.job_queue_key, job_id)
        
        return job_id
    
    def enqueue_jobs_batch(self, jobs: List[Dict[str, Any]]) -> List[str]:
        """Enqueue multiple jobs efficiently."""
        client = self.get_client()
        job_ids = []
        
        pipe = client.pipeline()
        
        for job_data in jobs:
            job_id = f"job:{datetime.now().strftime('%Y%m%d%H%M%S%f')}:{len(job_ids)}"
            job_data["job_id"] = job_id
            job_data["created_at"] = datetime.now().isoformat()
            job_data["status"] = "pending"
            
            # Store job data
            pipe.hset(f"{self.config.prefix}{job_id}", mapping={
                k: json.dumps(v) if isinstance(v, (list, dict)) else str(v)
                for k, v in job_data.items()
            })
            
            # Add to queue
            pipe.lpush(self.config.job_queue_key, job_id)
            job_ids.append(job_id)
        
        pipe.execute()
        return job_ids
    
    def dequeue_job(self, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """
        Get next job from queue (blocking).
        
        Args:
            timeout: Seconds to wait for a job.
            
        Returns:
            Job data or None if timeout.
        """
        client = self.get_client()
        
        # Blocking pop from queue
        result = client.brpoplpush(
            self.config.job_queue_key,
            self.config.processing_key,
            timeout=timeout
        )
        
        if result is None:
            return None
        
        job_id = result
        
        # Get job data
        job_data = client.hgetall(f"{self.config.prefix}{job_id}")
        
        if not job_data:
            return None
        
        # Parse JSON fields
        parsed = {}
        for k, v in job_data.items():
            try:
                parsed[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                parsed[k] = v
        
        # Update status
        client.hset(f"{self.config.prefix}{job_id}", "status", "processing")
        
        return parsed
    
    def complete_job(self, job_id: str, result: Dict[str, Any]):
        """Mark job as complete with result."""
        client = self.get_client()
        
        # Remove from processing
        client.lrem(self.config.processing_key, 0, job_id)
        
        # Store result
        client.hset(f"{self.config.prefix}{job_id}", mapping={
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "result": json.dumps(result)
        })
        
        # Add to results list
        client.lpush(self.config.results_key, job_id)
        
        # Publish event
        self.publish_event("job_completed", {"job_id": job_id, **result})
    
    def fail_job(self, job_id: str, error: str):
        """Mark job as failed."""
        client = self.get_client()
        
        # Remove from processing
        client.lrem(self.config.processing_key, 0, job_id)
        
        # Store error
        client.hset(f"{self.config.prefix}{job_id}", mapping={
            "status": "failed",
            "failed_at": datetime.now().isoformat(),
            "error": error
        })
        
        # Add to failed list
        client.lpush(self.config.failed_key, job_id)
        
        # Publish event
        self.publish_event("job_failed", {"job_id": job_id, "error": error})
    
    def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics."""
        client = self.get_client()
        
        return {
            "pending": client.llen(self.config.job_queue_key),
            "processing": client.llen(self.config.processing_key),
            "completed": client.llen(self.config.results_key),
            "failed": client.llen(self.config.failed_key),
        }
    
    def clear_queue(self):
        """Clear all queues (for reset)."""
        client = self.get_client()
        
        # Get all job keys
        keys = client.keys(f"{self.config.prefix}job:*")
        
        pipe = client.pipeline()
        for key in keys:
            pipe.delete(key)
        
        pipe.delete(self.config.job_queue_key)
        pipe.delete(self.config.processing_key)
        pipe.delete(self.config.results_key)
        pipe.delete(self.config.failed_key)
        pipe.execute()
    
    # -------------------------------------------------------------------------
    # Progress Tracking
    # -------------------------------------------------------------------------
    
    def update_progress(self, progress_data: Dict[str, Any]):
        """Update overall progress."""
        client = self.get_client()
        
        progress_data["updated_at"] = datetime.now().isoformat()
        client.hset(self.config.progress_key, mapping={
            k: json.dumps(v) if isinstance(v, (list, dict)) else str(v)
            for k, v in progress_data.items()
        })
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current progress."""
        client = self.get_client()
        
        data = client.hgetall(self.config.progress_key)
        
        parsed = {}
        for k, v in data.items():
            try:
                parsed[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                parsed[k] = v
        
        return parsed
    
    # -------------------------------------------------------------------------
    # Worker Management
    # -------------------------------------------------------------------------
    
    def register_worker(self, worker_id: str, info: Dict[str, Any]):
        """Register a worker."""
        client = self.get_client()
        
        info["registered_at"] = datetime.now().isoformat()
        info["last_heartbeat"] = datetime.now().isoformat()
        info["status"] = "active"
        
        client.hset(f"{self.config.workers_key}:{worker_id}", mapping={
            k: str(v) for k, v in info.items()
        })
        
        # Set expiry for auto-cleanup of dead workers
        client.expire(f"{self.config.workers_key}:{worker_id}", 60)
    
    def worker_heartbeat(self, worker_id: str):
        """Update worker heartbeat."""
        client = self.get_client()
        
        client.hset(
            f"{self.config.workers_key}:{worker_id}",
            "last_heartbeat",
            datetime.now().isoformat()
        )
        client.expire(f"{self.config.workers_key}:{worker_id}", 60)
    
    def get_active_workers(self) -> List[Dict[str, Any]]:
        """Get list of active workers."""
        client = self.get_client()
        
        worker_keys = client.keys(f"{self.config.workers_key}:*")
        workers = []
        
        for key in worker_keys:
            worker_data = client.hgetall(key)
            if worker_data:
                worker_data["worker_id"] = key.split(":")[-1]
                workers.append(worker_data)
        
        return workers
    
    # -------------------------------------------------------------------------
    # Pub/Sub for Events
    # -------------------------------------------------------------------------
    
    def publish_event(self, event_type: str, data: Dict[str, Any]):
        """Publish an event to the events channel."""
        client = self.get_client()
        
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        client.publish(self.config.events_channel, json.dumps(message))
    
    def subscribe_events(self):
        """Subscribe to events channel. Returns a pubsub object."""
        client = self.get_client()
        pubsub = client.pubsub()
        pubsub.subscribe(self.config.events_channel)
        return pubsub


def check_redis_available() -> bool:
    """Check if Redis is available."""
    try:
        manager = RedisManager()
        return manager.ping()
    except Exception as e:
        logger.warning(f"Redis not available: {e}")
        return False


if __name__ == "__main__":
    # Test Redis connection
    print("Testing Redis connection...")
    
    if check_redis_available():
        print("✓ Redis is available")
        
        manager = RedisManager()
        
        # Test queue operations
        print("\nTesting queue operations...")
        
        job_id = manager.enqueue_job({
            "type": "test",
            "symbols": ["RELIANCE", "TCS", "INFY"],
            "date": "2024-01-15"
        })
        print(f"  Enqueued job: {job_id}")
        
        stats = manager.get_queue_stats()
        print(f"  Queue stats: {stats}")
        
        # Dequeue
        job = manager.dequeue_job(timeout=1)
        print(f"  Dequeued job: {job}")
        
        if job:
            manager.complete_job(job["job_id"], {"success": True, "count": 3})
            print("  Job completed")
        
        stats = manager.get_queue_stats()
        print(f"  Final stats: {stats}")
        
        # Cleanup
        manager.clear_queue()
        print("  Queue cleared")
        
        print("\n✓ All tests passed")
    else:
        print("✗ Redis is not available")
        print("  Make sure Redis is running on localhost:6379")
        print("  Or set REDIS_HOST, REDIS_PORT in .env")
