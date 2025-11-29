"""
Ranking Orchestrator

Coordinates all ranking calculators and manages the ranking workflow.
Handles event-based communication and database operations.
"""

import os
from datetime import date, datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
import pandas as pd
from sqlalchemy import text
from dotenv import load_dotenv

from .rs_rating_service import RSRatingService
from .momentum_score_service import MomentumScoreService
from .trend_template_service import TrendTemplateService
from .technical_score_service import TechnicalScoreService
from .composite_score_service import CompositeScoreService
from ..db.schema import get_ranking_engine, create_ranking_tables
from ..db.ranking_repository import RankingRepository

load_dotenv()


@dataclass
class RankingResult:
    """Complete ranking result for a stock."""
    symbol: str
    calculation_date: date
    rs_rating: float = 0
    momentum_score: float = 0
    trend_template_score: int = 0
    technical_score: float = 0
    composite_score: float = 0
    rs_rank: int = 0
    momentum_rank: int = 0
    technical_rank: int = 0
    composite_rank: int = 0
    composite_percentile: float = 0
    success: bool = True
    errors: List[str] = field(default_factory=list)


class RankingOrchestrator:
    """
    Main orchestrator for the ranking system.
    
    Coordinates all calculators, loads data, and saves results.
    """
    
    def __init__(
        self,
        engine=None,
        event_callback: Optional[Callable[[str, Any], None]] = None,
    ):
        self.engine = engine or get_ranking_engine()
        self.repository = RankingRepository(self.engine)
        self.event_callback = event_callback
        
        # Initialize calculators
        self.rs_calculator = RSRatingService()
        self.momentum_calculator = MomentumScoreService()
        self.trend_calculator = TrendTemplateService()
        self.technical_calculator = TechnicalScoreService()
        self.composite_calculator = CompositeScoreService()
        
        # Ensure tables exist
        create_ranking_tables(self.engine)
    
    def _emit_event(self, channel: str, message: Any):
        if self.event_callback:
            self.event_callback(channel, message)
    
    def load_price_data(
        self,
        symbols: Optional[List[str]] = None,
        min_days: int = 300,
    ) -> Dict[str, pd.DataFrame]:
        """Load price data from yfinance_daily_quotes."""
        if symbols:
            placeholders = ",".join([f":s{i}" for i in range(len(symbols))])
            sql = f"""
            SELECT symbol, date, open, high, low, close, volume
            FROM yfinance_daily_quotes
            WHERE symbol IN ({placeholders})
            ORDER BY symbol, date
            """
            params = {f"s{i}": s for i, s in enumerate(symbols)}
        else:
            sql = """
            SELECT symbol, date, open, high, low, close, volume
            FROM yfinance_daily_quotes
            ORDER BY symbol, date
            """
            params = {}
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params=params)
        
        if df.empty:
            return {}
        
        data = {}
        for symbol, group in df.groupby("symbol"):
            if len(group) >= min_days:
                data[symbol] = group.reset_index(drop=True)
        
        return data
    
    def calculate_rankings(
        self,
        symbols: Optional[List[str]] = None,
        calculation_date: Optional[date] = None,
        save_to_db: bool = True,
        save_history: bool = True,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> Dict[str, RankingResult]:
        """Calculate rankings for all stocks."""
        calc_date = calculation_date or date.today()
        start_time = datetime.now()
        
        self._emit_event("ranking:status", {
            "status": "started",
            "calculation_date": str(calc_date),
            "timestamp": start_time.isoformat(),
        })
        
        if progress_callback:
            progress_callback("Loading data", 0, 100)
        
        price_data = self.load_price_data(symbols)
        
        if not price_data:
            self._emit_event("ranking:error", {"error": "No price data available"})
            return {}
        
        all_symbols = list(price_data.keys())
        total = len(all_symbols)
        
        if progress_callback:
            progress_callback("Loading data", 100, 100)
        
        # Run all calculators
        if progress_callback:
            progress_callback("RS Rating", 0, total)
        rs_results = self.rs_calculator.calculate_batch(price_data, calc_date)
        if progress_callback:
            progress_callback("RS Rating", total, total)
        
        if progress_callback:
            progress_callback("Momentum", 0, total)
        momentum_results = self.momentum_calculator.calculate_batch(price_data, calc_date)
        if progress_callback:
            progress_callback("Momentum", total, total)
        
        if progress_callback:
            progress_callback("Trend Template", 0, total)
        trend_results = self.trend_calculator.calculate_batch(price_data, calc_date)
        if progress_callback:
            progress_callback("Trend Template", total, total)
        
        if progress_callback:
            progress_callback("Technical", 0, total)
        technical_results = self.technical_calculator.calculate_batch(price_data, calc_date)
        if progress_callback:
            progress_callback("Technical", total, total)
        
        # Combine into composite
        if progress_callback:
            progress_callback("Composite", 0, total)
        
        scores_data = {}
        for symbol in all_symbols:
            rs = rs_results.get(symbol)
            mom = momentum_results.get(symbol)
            trend = trend_results.get(symbol)
            tech = technical_results.get(symbol)
            
            scores_data[symbol] = {
                "rs_rating": rs.rs_rating if rs else 0,
                "momentum_score": mom.momentum_score if mom else 0,
                "trend_template_score": trend.score if trend else 0,
                "technical_score": tech.technical_score if tech else 0,
            }
        
        composite_results = self.composite_calculator.calculate_batch(scores_data)
        
        if progress_callback:
            progress_callback("Composite", total, total)
        
        # Build final results
        results = {}
        for symbol in all_symbols:
            rs = rs_results.get(symbol)
            mom = momentum_results.get(symbol)
            trend = trend_results.get(symbol)
            tech = technical_results.get(symbol)
            comp = composite_results.get(symbol)
            
            errors = []
            if rs and not rs.success:
                errors.append(f"RS: {rs.error}")
            if mom and not mom.success:
                errors.append(f"Momentum: {mom.error}")
            if trend and not trend.success:
                errors.append(f"Trend: {trend.error}")
            if tech and not tech.success:
                errors.append(f"Technical: {tech.error}")
            
            results[symbol] = RankingResult(
                symbol=symbol,
                calculation_date=calc_date,
                rs_rating=rs.rs_rating if rs else 0,
                momentum_score=mom.momentum_score if mom else 0,
                trend_template_score=trend.score if trend else 0,
                technical_score=tech.technical_score if tech else 0,
                composite_score=comp.composite_score if comp else 0,
                rs_rank=rs.rank if rs else 0,
                momentum_rank=mom.rank if mom else 0,
                technical_rank=tech.rank if tech else 0,
                composite_rank=comp.rank if comp else 0,
                composite_percentile=comp.percentile if comp else 0,
                success=len(errors) == 0,
                errors=errors,
            )
        
        # Save to database
        if save_to_db:
            if progress_callback:
                progress_callback("Saving", 0, total)
            
            db_records = []
            for symbol, r in results.items():
                db_records.append({
                    "symbol": symbol,
                    "calculation_date": calc_date,
                    "rs_rating": r.rs_rating,
                    "momentum_score": r.momentum_score,
                    "trend_template_score": r.trend_template_score,
                    "technical_score": r.technical_score,
                    "composite_score": r.composite_score,
                    "rs_rank": r.rs_rank,
                    "momentum_rank": r.momentum_rank,
                    "technical_rank": r.technical_rank,
                    "composite_rank": r.composite_rank,
                    "composite_percentile": r.composite_percentile,
                    "total_stocks_ranked": total,
                })
            
            self.repository.save_rankings_batch(db_records, calc_date)
            
            if save_history:
                self.repository.save_history_snapshot(db_records, calc_date)
            
            if progress_callback:
                progress_callback("Saving", total, total)
        
        # Emit completion event
        duration = (datetime.now() - start_time).total_seconds()
        successful = sum(1 for r in results.values() if r.success)
        
        self._emit_event("ranking:completed", {
            "status": "completed",
            "calculation_date": str(calc_date),
            "total_stocks": total,
            "successful": successful,
            "failed": total - successful,
            "duration_seconds": round(duration, 2),
        })
        
        return results
    
    def get_top_stocks(
        self,
        n: int = 50,
        min_percentile: float = 80,
        calculation_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """Get top ranked stocks."""
        return self.repository.get_top_stocks_by_score(
            score_type="composite_score",
            limit=n,
            calculation_date=calculation_date,
        )
    
    def get_leaders(self, calculation_date: Optional[date] = None) -> pd.DataFrame:
        """Get market leaders (top 10 percentile + trend template 6+)."""
        df = self.repository.get_latest_rankings(limit=500, min_composite_percentile=90)
        if df.empty:
            return df
        return df[df["trend_template_score"] >= 6].head(50)
