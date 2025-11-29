"""
Job Models for Parallel Ranking

Defines job types and data structures for the ranking job queue.
"""

from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import json


class JobType(Enum):
    """Types of ranking jobs."""
    CALCULATE_DATE = "calculate_date"      # Calculate rankings for a specific date
    CALCULATE_SYMBOLS = "calculate_symbols"  # Calculate rankings for specific symbols on a date
    BATCH_DATES = "batch_dates"            # Process multiple dates


class JobStatus(Enum):
    """Job status states."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class RankingJob:
    """
    A job for ranking calculation.
    
    Can be for a single date with all symbols, or specific symbols on a date.
    """
    job_type: JobType
    calculation_date: date
    symbols: List[str] = field(default_factory=list)  # Empty = all symbols
    batch_id: str = ""  # For grouping related jobs
    priority: int = 0   # Higher = more urgent
    
    # Metadata (set by queue)
    job_id: str = ""
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: JobStatus = JobStatus.PENDING
    worker_id: str = ""
    
    # Result
    result: Optional[Dict[str, Any]] = None
    error: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage."""
        return {
            "job_type": self.job_type.value,
            "calculation_date": self.calculation_date.isoformat(),
            "symbols": self.symbols,
            "batch_id": self.batch_id,
            "priority": self.priority,
            "job_id": self.job_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status.value,
            "worker_id": self.worker_id,
            "result": self.result,
            "error": self.error,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RankingJob':
        """Create from dictionary."""
        return cls(
            job_type=JobType(data.get("job_type", "calculate_date")),
            calculation_date=date.fromisoformat(data["calculation_date"]) if isinstance(data.get("calculation_date"), str) else data.get("calculation_date"),
            symbols=data.get("symbols", []),
            batch_id=data.get("batch_id", ""),
            priority=int(data.get("priority", 0)),
            job_id=data.get("job_id", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            status=JobStatus(data.get("status", "pending")),
            worker_id=data.get("worker_id", ""),
            result=data.get("result"),
            error=data.get("error", ""),
        )


@dataclass
class BatchProgress:
    """Track progress of a batch of jobs."""
    batch_id: str
    total_jobs: int = 0
    pending_jobs: int = 0
    processing_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    total_symbols_processed: int = 0
    start_time: Optional[datetime] = None
    
    @property
    def progress_pct(self) -> float:
        if self.total_jobs == 0:
            return 0
        return (self.completed_jobs + self.failed_jobs) / self.total_jobs * 100
    
    @property
    def elapsed_seconds(self) -> float:
        if not self.start_time:
            return 0
        return (datetime.now() - self.start_time).total_seconds()
    
    @property
    def jobs_per_second(self) -> float:
        if self.elapsed_seconds == 0:
            return 0
        return self.completed_jobs / self.elapsed_seconds
    
    @property
    def eta_seconds(self) -> float:
        if self.jobs_per_second == 0:
            return 0
        remaining = self.pending_jobs + self.processing_jobs
        return remaining / self.jobs_per_second
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "total_jobs": self.total_jobs,
            "pending_jobs": self.pending_jobs,
            "processing_jobs": self.processing_jobs,
            "completed_jobs": self.completed_jobs,
            "failed_jobs": self.failed_jobs,
            "total_symbols_processed": self.total_symbols_processed,
            "progress_pct": self.progress_pct,
            "elapsed_seconds": self.elapsed_seconds,
            "jobs_per_second": self.jobs_per_second,
            "eta_seconds": self.eta_seconds,
            "start_time": self.start_time.isoformat() if self.start_time else None,
        }


@dataclass  
class WorkerInfo:
    """Information about a worker process."""
    worker_id: str
    hostname: str = ""
    pid: int = 0
    started_at: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    jobs_completed: int = 0
    jobs_failed: int = 0
    current_job: str = ""
    status: str = "active"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "hostname": self.hostname,
            "pid": self.pid,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "jobs_completed": self.jobs_completed,
            "jobs_failed": self.jobs_failed,
            "current_job": self.current_job,
            "status": self.status,
        }
