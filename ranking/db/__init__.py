"""
Ranking Database Module

Database operations for the ranking system.
"""

from .schema import create_ranking_tables, get_ranking_engine, check_tables_exist
from .ranking_repository import RankingRepository

__all__ = [
    "RankingRepository",
    "create_ranking_tables",
    "get_ranking_engine",
    "check_tables_exist",
]
