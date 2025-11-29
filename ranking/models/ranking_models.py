"""
Ranking Data Models

Core data structures for the ranking system.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, Dict, Any
from enum import Enum


class ScoreType(str, Enum):
    """Types of ranking scores."""
    RS_RATING = "rs_rating"
    MOMENTUM_SCORE = "momentum_score"
    TREND_TEMPLATE = "trend_template"
    TECHNICAL_SCORE = "technical_score"
    COMPOSITE_SCORE = "composite_score"


@dataclass
class RankingScore:
    """
    Individual score component.
    
    Attributes:
        score_type: Type of score (rs_rating, momentum_score, etc.).
        value: Raw score value.
        rank: Rank among all stocks for this score type.
        percentile: Percentile rank (99 = top 1%).
        details: Additional details about the score calculation.
    """
    score_type: ScoreType
    value: float
    rank: int = 0
    percentile: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Ensure score_type is an enum."""
        if isinstance(self.score_type, str):
            self.score_type = ScoreType(self.score_type)


@dataclass
class TrendTemplateCondition:
    """
    Single condition for Trend Template scoring.
    
    Attributes:
        name: Condition name.
        passed: Whether the condition passed.
        description: Human-readable description.
        actual_value: Actual value being checked.
        threshold: Threshold for the condition.
    """
    name: str
    passed: bool
    description: str
    actual_value: Optional[float] = None
    threshold: Optional[float] = None


@dataclass
class StockRanking:
    """
    Complete ranking for a single stock.
    
    Attributes:
        symbol: Stock symbol.
        calculation_date: Date of calculation.
        rs_rating: Relative Strength rating (1-99).
        momentum_score: Multi-timeframe momentum score (0-100).
        trend_template_score: Trend Template conditions passed (0-8).
        technical_score: Technical position score (0-100).
        composite_score: Weighted combination score (0-100).
        composite_rank: Overall rank among all stocks.
        composite_percentile: Overall percentile (99 = top 1%).
        trend_template_conditions: Individual condition results.
        updated_at: Timestamp of last update.
    """
    symbol: str
    calculation_date: date
    rs_rating: float = 0.0
    momentum_score: float = 0.0
    trend_template_score: int = 0
    technical_score: float = 0.0
    composite_score: float = 0.0
    composite_rank: int = 0
    composite_percentile: float = 0.0
    trend_template_conditions: list[TrendTemplateCondition] = field(default_factory=list)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Individual component ranks
    rs_rank: int = 0
    momentum_rank: int = 0
    technical_rank: int = 0
    
    @property
    def is_leader(self) -> bool:
        """Check if stock qualifies as a market leader."""
        return (
            self.composite_percentile >= 90 and
            self.trend_template_score >= 6 and
            self.rs_rating >= 80
        )
    
    @property
    def trend_template_passed(self) -> bool:
        """Check if stock passes Trend Template (all 8 conditions)."""
        return self.trend_template_score == 8
    
    def get_scores_dict(self) -> Dict[str, float]:
        """Get all scores as a dictionary."""
        return {
            "rs_rating": self.rs_rating,
            "momentum_score": self.momentum_score,
            "trend_template_score": self.trend_template_score,
            "technical_score": self.technical_score,
            "composite_score": self.composite_score,
        }
    
    def get_ranks_dict(self) -> Dict[str, int]:
        """Get all ranks as a dictionary."""
        return {
            "rs_rank": self.rs_rank,
            "momentum_rank": self.momentum_rank,
            "technical_rank": self.technical_rank,
            "composite_rank": self.composite_rank,
        }


@dataclass
class RankingHistory:
    """
    Historical snapshot of a stock's ranking.
    
    Used for backtesting and tracking rank changes over time.
    """
    id: Optional[int] = None
    symbol: str = ""
    ranking_date: date = field(default_factory=date.today)
    rs_rating: float = 0.0
    momentum_score: float = 0.0
    trend_template_score: int = 0
    technical_score: float = 0.0
    composite_score: float = 0.0
    composite_rank: int = 0
    composite_percentile: float = 0.0
    total_stocks_ranked: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def from_stock_ranking(cls, ranking: StockRanking, total_stocks: int) -> "RankingHistory":
        """Create history record from current ranking."""
        return cls(
            symbol=ranking.symbol,
            ranking_date=ranking.calculation_date,
            rs_rating=ranking.rs_rating,
            momentum_score=ranking.momentum_score,
            trend_template_score=ranking.trend_template_score,
            technical_score=ranking.technical_score,
            composite_score=ranking.composite_score,
            composite_rank=ranking.composite_rank,
            composite_percentile=ranking.composite_percentile,
            total_stocks_ranked=total_stocks,
        )
