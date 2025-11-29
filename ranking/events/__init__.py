"""
Ranking Events Module

Event definitions for the ranking system's event-based architecture.
Uses Redis pub/sub for communication between services.
"""

from .ranking_events import (
    RankingEvent,
    RankingCalculationRequested,
    RankingScoreUpdated,
    RankingBatchCompleted,
    RankingCalculationFailed,
)

__all__ = [
    "RankingEvent",
    "RankingCalculationRequested",
    "RankingScoreUpdated",
    "RankingBatchCompleted",
    "RankingCalculationFailed",
]
