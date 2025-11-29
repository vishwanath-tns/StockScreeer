"""
Ranking Services Module

Modular rating calculators for the ranking system.
Each service implements a consistent interface for testability.
"""

from .base_calculator import IRatingCalculator, CalculatorResult, BaseCalculator
from .rs_rating_service import RSRatingService, RSResult
from .momentum_score_service import MomentumScoreService, MomentumResult
from .trend_template_service import TrendTemplateService, TrendTemplateResult, TrendCondition
from .technical_score_service import TechnicalScoreService, TechnicalResult
from .composite_score_service import CompositeScoreService, CompositeResult
from .ranking_orchestrator import RankingOrchestrator, RankingResult

__all__ = [
    # Base
    "IRatingCalculator",
    "CalculatorResult",
    "BaseCalculator",
    # Services
    "RSRatingService",
    "RSResult",
    "MomentumScoreService",
    "MomentumResult",
    "TrendTemplateService",
    "TrendTemplateResult",
    "TrendCondition",
    "TechnicalScoreService",
    "TechnicalResult",
    "CompositeScoreService",
    "CompositeResult",
    "RankingOrchestrator",
    "RankingResult",
]
