"""
Bollinger Bands Job Models

Data structures for parallel processing jobs.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import json
import uuid


class JobType(Enum):
    """Types of BB processing jobs."""
    CALCULATE_DAILY = "calculate_daily"
    CALCULATE_BACKFILL = "calculate_backfill"
    GENERATE_RATINGS = "generate_ratings"
    GENERATE_SIGNALS = "generate_signals"
    RUN_SCAN = "run_scan"


class JobStatus(Enum):
    """Job status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobPriority(Enum):
    """Job priority levels."""
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


@dataclass
class BBJob:
    """
    A Bollinger Bands processing job.
    
    Jobs are queued in Redis and processed by workers.
    """
    job_id: str
    job_type: JobType
    symbol: str
    priority: JobPriority = JobPriority.NORMAL
    status: JobStatus = JobStatus.PENDING
    
    # Job parameters
    params: Dict[str, Any] = field(default_factory=dict)
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Results
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    @classmethod
    def create(cls, job_type: JobType, symbol: str, 
               priority: JobPriority = JobPriority.NORMAL,
               **params) -> "BBJob":
        """Create a new job with auto-generated ID."""
        return cls(
            job_id=str(uuid.uuid4()),
            job_type=job_type,
            symbol=symbol,
            priority=priority,
            params=params
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for Redis storage."""
        return {
            "job_id": self.job_id,
            "job_type": self.job_type.value,
            "symbol": self.symbol,
            "priority": self.priority.value,
            "status": self.status.value,
            "params": self.params,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: dict) -> "BBJob":
        """Create from dictionary."""
        return cls(
            job_id=data["job_id"],
            job_type=JobType(data["job_type"]),
            symbol=data["symbol"],
            priority=JobPriority(data["priority"]),
            status=JobStatus(data["status"]),
            params=data.get("params", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            result=data.get("result"),
            error_message=data.get("error_message"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3)
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "BBJob":
        """Deserialize from JSON."""
        return cls.from_dict(json.loads(json_str))
    
    def mark_started(self):
        """Mark job as started."""
        self.status = JobStatus.IN_PROGRESS
        self.started_at = datetime.now()
    
    def mark_completed(self, result: Dict[str, Any] = None):
        """Mark job as completed."""
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.now()
        self.result = result
    
    def mark_failed(self, error: str):
        """Mark job as failed."""
        self.status = JobStatus.FAILED
        self.completed_at = datetime.now()
        self.error_message = error
        self.retry_count += 1
    
    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return self.retry_count < self.max_retries


@dataclass
class BatchJob:
    """A batch of jobs for bulk processing."""
    batch_id: str
    job_type: JobType
    symbols: List[str]
    priority: JobPriority = JobPriority.NORMAL
    
    # Progress tracking
    total_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Common parameters for all jobs in batch
    common_params: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(cls, job_type: JobType, symbols: List[str],
               priority: JobPriority = JobPriority.NORMAL,
               **common_params) -> "BatchJob":
        """Create a new batch job."""
        return cls(
            batch_id=str(uuid.uuid4()),
            job_type=job_type,
            symbols=symbols,
            priority=priority,
            total_jobs=len(symbols),
            common_params=common_params
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "batch_id": self.batch_id,
            "job_type": self.job_type.value,
            "symbols": self.symbols,
            "priority": self.priority.value,
            "total_jobs": self.total_jobs,
            "completed_jobs": self.completed_jobs,
            "failed_jobs": self.failed_jobs,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "common_params": self.common_params
        }
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: dict) -> "BatchJob":
        """Create from dictionary."""
        batch = cls(
            batch_id=data["batch_id"],
            job_type=JobType(data["job_type"]),
            symbols=data["symbols"],
            priority=JobPriority(data["priority"]),
            total_jobs=data.get("total_jobs", len(data["symbols"])),
            completed_jobs=data.get("completed_jobs", 0),
            failed_jobs=data.get("failed_jobs", 0),
            common_params=data.get("common_params", {})
        )
        batch.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("started_at"):
            batch.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            batch.completed_at = datetime.fromisoformat(data["completed_at"])
        return batch
    
    def generate_jobs(self) -> List[BBJob]:
        """Generate individual jobs for each symbol."""
        jobs = []
        for symbol in self.symbols:
            job = BBJob.create(
                job_type=self.job_type,
                symbol=symbol,
                priority=self.priority,
                batch_id=self.batch_id,
                **self.common_params
            )
            jobs.append(job)
        return jobs
    
    @property
    def progress_percent(self) -> float:
        """Get completion percentage."""
        if self.total_jobs == 0:
            return 0.0
        return ((self.completed_jobs + self.failed_jobs) / self.total_jobs) * 100
    
    @property
    def is_complete(self) -> bool:
        """Check if batch is complete."""
        return (self.completed_jobs + self.failed_jobs) >= self.total_jobs


@dataclass
class JobResult:
    """Result from a completed job."""
    job_id: str
    symbol: str
    success: bool
    duration_ms: float
    records_processed: int = 0
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
