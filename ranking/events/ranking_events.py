"""
Ranking Event Definitions

All events used by the ranking system for pub/sub communication.
Events are serializable to JSON for Redis transport.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Any
from enum import Enum
import json
import uuid


class EventType(str, Enum):
    """Types of ranking events."""
    CALCULATION_REQUESTED = "ranking.calculation.requested"
    SCORE_UPDATED = "ranking.score.updated"
    BATCH_COMPLETED = "ranking.batch.completed"
    CALCULATION_FAILED = "ranking.calculation.failed"


@dataclass
class RankingEvent:
    """Base class for all ranking events."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    event_type: str = ""
    
    def to_json(self) -> str:
        """Serialize event to JSON string."""
        data = asdict(self)
        # Convert datetime to ISO format
        data["timestamp"] = self.timestamp.isoformat()
        return json.dumps(data)
    
    def to_bytes(self) -> bytes:
        """Serialize event to bytes for Redis."""
        return self.to_json().encode("utf-8")
    
    @classmethod
    def from_json(cls, json_str: str) -> "RankingEvent":
        """Deserialize event from JSON string."""
        data = json.loads(json_str)
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> "RankingEvent":
        """Deserialize event from bytes."""
        return cls.from_json(data.decode("utf-8"))


@dataclass
class RankingCalculationRequested(RankingEvent):
    """
    Event fired when ranking calculation is requested.
    
    Attributes:
        symbols: List of symbols to calculate rankings for.
                 If empty, calculates for all available stocks.
        calculation_date: Date to calculate rankings for.
        force_recalculate: If True, recalculate even if rankings exist.
    """
    event_type: str = field(default=EventType.CALCULATION_REQUESTED.value)
    symbols: list[str] = field(default_factory=list)
    calculation_date: Optional[str] = None  # ISO format date string
    force_recalculate: bool = False
    
    def to_json(self) -> str:
        """Serialize event to JSON string."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return json.dumps(data)


@dataclass
class RankingScoreUpdated(RankingEvent):
    """
    Event fired when a stock's ranking score is updated.
    
    Attributes:
        symbol: Stock symbol.
        score_type: Type of score (rs_rating, momentum_score, etc.).
        score_value: Calculated score value.
        rank: Rank among all stocks (1 = best).
        percentile: Percentile rank (99 = top 1%).
    """
    event_type: str = field(default=EventType.SCORE_UPDATED.value)
    symbol: str = ""
    score_type: str = ""
    score_value: float = 0.0
    rank: int = 0
    percentile: float = 0.0
    calculation_date: str = ""
    
    def to_json(self) -> str:
        """Serialize event to JSON string."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return json.dumps(data)


@dataclass
class RankingBatchCompleted(RankingEvent):
    """
    Event fired when a batch of rankings is completed.
    
    Attributes:
        total_symbols: Total symbols processed.
        successful: Number of successful calculations.
        failed: Number of failed calculations.
        duration_seconds: Time taken to complete batch.
    """
    event_type: str = field(default=EventType.BATCH_COMPLETED.value)
    total_symbols: int = 0
    successful: int = 0
    failed: int = 0
    duration_seconds: float = 0.0
    calculation_date: str = ""
    
    def to_json(self) -> str:
        """Serialize event to JSON string."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return json.dumps(data)


@dataclass
class RankingCalculationFailed(RankingEvent):
    """
    Event fired when ranking calculation fails for a symbol.
    
    Attributes:
        symbol: Stock symbol that failed.
        error_message: Description of the error.
        error_type: Type of exception that occurred.
    """
    event_type: str = field(default=EventType.CALCULATION_FAILED.value)
    symbol: str = ""
    error_message: str = ""
    error_type: str = ""
    
    def to_json(self) -> str:
        """Serialize event to JSON string."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return json.dumps(data)


# Channel names for Redis pub/sub
class RankingChannels:
    """Channel names used by the ranking system."""
    CALCULATION_REQUESTS = "ranking:requests"
    SCORE_UPDATES = "ranking:scores"
    BATCH_STATUS = "ranking:batch"
    ERRORS = "ranking:errors"
