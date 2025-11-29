"""
Stock Ranking Module

A modular, event-based stock ranking system that calculates multiple scores
to identify strong stocks for trading.

Architecture:
- events/: Event definitions for pub/sub communication
- models/: Data classes for type safety
- services/: Modular rating calculators
- db/: Database operations and repository

Usage:
    from ranking import RankingOrchestrator
    
    orchestrator = RankingOrchestrator()
    results = orchestrator.calculate_rankings()
    top_stocks = orchestrator.get_top_stocks(n=50)
"""

from .services import (
    RankingOrchestrator,
    RankingResult,
    RSRatingService,
    MomentumScoreService,
    TrendTemplateService,
    TechnicalScoreService,
    CompositeScoreService,
)
from .db import RankingRepository, create_ranking_tables
from .gui import RankingsViewer
from .exports import RankingsExporter
from .historical import HistoricalRankingsBuilder

__all__ = [
    # Main orchestrator
    "RankingOrchestrator",
    "RankingResult",
    # Individual services
    "RSRatingService",
    "MomentumScoreService",
    "TrendTemplateService",
    "TechnicalScoreService",
    "CompositeScoreService",
    # Database
    "RankingRepository",
    "create_ranking_tables",
    # GUI
    "RankingsViewer",
    # Export
    "RankingsExporter",
    # Historical
    "HistoricalRankingsBuilder",
]
