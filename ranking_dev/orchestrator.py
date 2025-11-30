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

# Import calculators
from .rs_rating import RSRatingCalculator
from .momentum import MomentumScoreCalculator
from .trend_template import TrendTemplateCalculator
from .technical import TechnicalScoreCalculator
from .composite import CompositeScoreCalculator
from .schema import get_ranking_engine, create_ranking_tables
from .repository import RankingRepository

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
    
    Responsibilities:
    - Load price data from database
    - Run all calculators
    - Combine results
    - Save to database
    - Emit events for subscribers
    """
    
    def __init__(
        self,
        engine=None,
        event_callback: Optional[Callable[[str, Any], None]] = None,
    ):
        """
        Initialize orchestrator.
        
        Args:
            engine: SQLAlchemy engine. If None, creates from env.
            event_callback: Optional callback for events (channel, message).
        """
        self.engine = engine or get_ranking_engine()
        self.repository = RankingRepository(self.engine)
        self.event_callback = event_callback
        
        # Initialize calculators
        self.rs_calculator = RSRatingCalculator()
        self.momentum_calculator = MomentumScoreCalculator()
        self.trend_calculator = TrendTemplateCalculator()
        self.technical_calculator = TechnicalScoreCalculator()
        self.composite_calculator = CompositeScoreCalculator()
        
        # Ensure tables exist
        create_ranking_tables(self.engine)
    
    def _emit_event(self, channel: str, message: Any):
        """Emit event if callback is set."""
        if self.event_callback:
            self.event_callback(channel, message)
    
    def load_price_data(
        self,
        symbols: Optional[List[str]] = None,
        min_days: int = 300,
    ) -> Dict[str, pd.DataFrame]:
        """
        Load price data from yfinance_daily_quotes.
        
        Args:
            symbols: Optional list of symbols. If None, loads all.
            min_days: Minimum days of data required.
            
        Returns:
            Dict mapping symbol to price DataFrame.
        """
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
        
        # Split by symbol
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
        """
        Calculate rankings for all stocks.
        
        Args:
            symbols: Optional list of symbols. If None, uses all.
            calculation_date: Date to calculate for. Defaults to today.
            save_to_db: Whether to save results to database.
            save_history: Whether to save historical snapshot.
            progress_callback: Optional callback(stage, current, total).
            
        Returns:
            Dict mapping symbol to RankingResult.
        """
        calc_date = calculation_date or date.today()
        start_time = datetime.now()
        
        # Emit start event
        self._emit_event("ranking:status", {
            "status": "started",
            "calculation_date": str(calc_date),
            "timestamp": start_time.isoformat(),
        })
        
        # Load data
        if progress_callback:
            progress_callback("Loading data", 0, 100)
        
        price_data = self.load_price_data(symbols)
        
        if not price_data:
            self._emit_event("ranking:error", {
                "error": "No price data available",
            })
            return {}
        
        all_symbols = list(price_data.keys())
        total = len(all_symbols)
        
        if progress_callback:
            progress_callback("Loading data", 100, 100)
        
        # Run calculators
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
            
            saved = self.repository.save_rankings_batch(db_records, calc_date)
            
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
        """
        Get top ranked stocks.
        
        Args:
            n: Number of stocks to return.
            min_percentile: Minimum composite percentile.
            calculation_date: Date to query. Defaults to latest.
            
        Returns:
            DataFrame with top stocks.
        """
        return self.repository.get_top_stocks_by_score(
            score_type="composite_score",
            limit=n,
            calculation_date=calculation_date,
        )
    
    def get_leaders(
        self,
        calculation_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """
        Get market leaders (top 10 percentile + trend template 6+).
        """
        df = self.repository.get_latest_rankings(
            limit=500,
            min_composite_percentile=90,
        )
        
        if df.empty:
            return df
        
        # Filter for trend template >= 6
        return df[df["trend_template_score"] >= 6].head(50)


# Standalone test
if __name__ == "__main__":
    print("Testing Ranking Orchestrator...")
    print("-" * 60)
    
    def progress(stage, current, total):
        print(f"  {stage}: {current}/{total}")
    
    def event_handler(channel, message):
        print(f"  EVENT [{channel}]: {message}")
    
    try:
        orchestrator = RankingOrchestrator(event_callback=event_handler)
        
        # Run for all stocks
        results = orchestrator.calculate_rankings(
            save_to_db=True,
            save_history=True,
            progress_callback=progress,
        )
        
        print(f"\nCalculated rankings for {len(results)} stocks")
        
        # Show top 10
        top = orchestrator.get_top_stocks(n=10)
        if not top.empty:
            print("\nTop 10 Stocks:")
            print(top[["symbol", "composite_score", "composite_rank", "rs_rating", "trend_template_score"]])
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
