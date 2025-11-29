"""
Parallel Ranking Module

Provides scalable, event-driven parallel processing for historical rankings
using Redis for job distribution.

Components:
- RedisManager: Connection pooling and queue operations
- RankingWorker: Worker process that calculates rankings
- ParallelRankingsDispatcher: Job creation and progress monitoring

Architecture:
    [Dispatcher] --creates jobs--> [Redis Queue] <--pulls jobs-- [Worker 1]
                                                <--pulls jobs-- [Worker 2]
                                                <--pulls jobs-- [Worker N]

Usage:
    # Start workers (in separate terminals)
    python -m ranking.parallel.worker --id worker-1
    python -m ranking.parallel.worker --id worker-2
    
    # Dispatch jobs
    from ranking.parallel import ParallelRankingsDispatcher
    dispatcher = ParallelRankingsDispatcher()
    result = dispatcher.build_historical_rankings(years=3)
"""

from .redis_manager import RedisManager, RedisConfig, check_redis_available
from .job_models import RankingJob, JobType, JobStatus, BatchProgress, WorkerInfo
from .worker import RankingWorker
from .dispatcher import ParallelRankingsDispatcher

__all__ = [
    # Redis
    "RedisManager",
    "RedisConfig",
    "check_redis_available",
    # Models
    "RankingJob",
    "JobType",
    "JobStatus",
    "BatchProgress",
    "WorkerInfo",
    # Worker
    "RankingWorker",
    # Dispatcher
    "ParallelRankingsDispatcher",
]
