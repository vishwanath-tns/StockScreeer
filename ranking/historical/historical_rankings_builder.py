#!/usr/bin/env python3
"""
Historical Rankings Builder

Builds historical stock rankings for backtesting and analysis.
Uses the existing ranking module calculators to generate rankings
for each trading day over a specified period.

This is a one-time operation, separate from the daily wizard.

Features:
- Calculate rankings for any historical date range
- Resume capability (skip already calculated dates)
- Progress tracking with ETA
- Configurable batch size and parallel processing
- Save to stock_rankings_history table

Usage:
    from ranking.historical import HistoricalRankingsBuilder
    
    builder = HistoricalRankingsBuilder()
    builder.build(years=3)  # Build 3 years of history
    
    # Or with specific date range
    builder.build(start_date="2022-01-01", end_date="2024-12-31")
"""

import os
import sys
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Callable, Dict, Any
import time
from dataclasses import dataclass

import pandas as pd
from sqlalchemy import text, create_engine
from tqdm import tqdm

# Add project root for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ranking.db.schema import get_ranking_engine
from ranking.services.rs_rating_service import RSRatingService
from ranking.services.momentum_score_service import MomentumScoreService
from ranking.services.trend_template_service import TrendTemplateService
from ranking.services.technical_score_service import TechnicalScoreService
from ranking.services.composite_score_service import CompositeScoreService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class BuildProgress:
    """Track build progress."""
    total_dates: int = 0
    completed_dates: int = 0
    skipped_dates: int = 0
    failed_dates: int = 0
    current_date: Optional[date] = None
    start_time: Optional[datetime] = None
    
    @property
    def elapsed_seconds(self) -> float:
        if not self.start_time:
            return 0
        return (datetime.now() - self.start_time).total_seconds()
    
    @property
    def dates_per_second(self) -> float:
        if self.elapsed_seconds == 0:
            return 0
        return self.completed_dates / self.elapsed_seconds
    
    @property
    def eta_seconds(self) -> float:
        if self.dates_per_second == 0:
            return 0
        remaining = self.total_dates - self.completed_dates - self.skipped_dates
        return remaining / self.dates_per_second
    
    @property
    def eta_str(self) -> str:
        secs = int(self.eta_seconds)
        if secs < 60:
            return f"{secs}s"
        elif secs < 3600:
            return f"{secs // 60}m {secs % 60}s"
        else:
            return f"{secs // 3600}h {(secs % 3600) // 60}m"


class HistoricalRankingsBuilder:
    """
    Builds historical stock rankings for backtesting.
    
    Uses the existing ranking calculators to generate rankings
    for each trading day in the specified date range.
    """
    
    def __init__(self, engine=None):
        """
        Initialize the builder.
        
        Args:
            engine: SQLAlchemy engine. Creates from env if not provided.
        """
        self.engine = engine or get_ranking_engine()
        
        # Initialize calculators (they work with DataFrames, not DB)
        self.rs_service = RSRatingService()
        self.momentum_service = MomentumScoreService()
        self.trend_service = TrendTemplateService()
        self.technical_service = TechnicalScoreService()
        self.composite_service = CompositeScoreService()
        
        # Progress tracking
        self.progress = BuildProgress()
        self.stop_requested = False
    
    def get_available_trading_dates(
        self,
        start_date: date,
        end_date: date
    ) -> List[date]:
        """
        Get list of trading dates with data available.
        
        Args:
            start_date: Start of range.
            end_date: End of range.
            
        Returns:
            List of dates with trading data.
        """
        sql = """
        SELECT DISTINCT date 
        FROM yfinance_daily_quotes 
        WHERE date BETWEEN :start AND :end
        ORDER BY date
        """
        
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), {
                "start": start_date,
                "end": end_date
            })
            return [row[0] for row in result]
    
    def get_already_calculated_dates(
        self,
        start_date: date,
        end_date: date
    ) -> set:
        """
        Get dates that already have rankings in history.
        
        Args:
            start_date: Start of range.
            end_date: End of range.
            
        Returns:
            Set of dates already calculated.
        """
        sql = """
        SELECT DISTINCT ranking_date 
        FROM stock_rankings_history 
        WHERE ranking_date BETWEEN :start AND :end
        """
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql), {
                    "start": start_date,
                    "end": end_date
                })
                return {row[0] for row in result}
        except Exception as e:
            logger.warning(f"Could not get existing dates: {e}")
            return set()
    
    def calculate_rankings_for_date(
        self,
        calc_date: date,
        min_stocks: int = 50
    ) -> Dict[str, Any]:
        """
        Calculate rankings for a specific historical date.
        
        Args:
            calc_date: Date to calculate rankings for.
            min_stocks: Minimum stocks required for valid calculation.
            
        Returns:
            Dict with rankings data and stats.
        """
        try:
            # Get price data as of calc_date
            # We need 252 trading days before calc_date for 12M calculations
            lookback_start = calc_date - timedelta(days=400)  # ~1.5 years to be safe
            
            price_data = self._get_historical_price_data(lookback_start, calc_date)
            
            if price_data.empty:
                return {"success": False, "error": "No price data", "count": 0}
            
            # Get unique symbols with data on calc_date
            symbols_on_date = price_data[price_data["date"] == calc_date]["symbol"].unique().tolist()
            
            if len(symbols_on_date) < min_stocks:
                return {
                    "success": False, 
                    "error": f"Only {len(symbols_on_date)} stocks on date",
                    "count": len(symbols_on_date)
                }
            
            # Pivot to get price series per symbol
            price_pivot = price_data.pivot(index="date", columns="symbol", values="close")
            
            # Calculate each score
            rankings = []
            
            for symbol in symbols_on_date:
                if symbol not in price_pivot.columns:
                    continue
                
                symbol_prices = price_pivot[symbol].dropna()
                
                if len(symbol_prices) < 50:  # Need minimum history
                    continue
                
                # Get the price series ending at calc_date
                symbol_prices = symbol_prices[symbol_prices.index <= calc_date]
                
                if len(symbol_prices) < 50:
                    continue
                
                try:
                    # Calculate individual scores
                    rs_rating = self._calculate_rs_rating_for_symbol(
                        symbol, symbol_prices, price_pivot, calc_date
                    )
                    momentum = self._calculate_momentum_for_symbol(symbol_prices)
                    trend = self._calculate_trend_for_symbol(symbol_prices)
                    technical = self._calculate_technical_for_symbol(symbol_prices)
                    
                    rankings.append({
                        "symbol": symbol,
                        "rs_rating": rs_rating,
                        "momentum_score": momentum,
                        "trend_template_score": trend,
                        "technical_score": technical,
                    })
                except Exception as e:
                    # Skip symbols with calculation errors
                    continue
            
            if not rankings:
                return {"success": False, "error": "No valid rankings", "count": 0}
            
            # Create DataFrame for composite calculation
            df = pd.DataFrame(rankings)
            
            # Calculate composite score
            df = self.composite_service.calculate(df)
            
            # Calculate ranks
            total = len(df)
            df["composite_rank"] = df["composite_score"].rank(ascending=False, method="min").astype(int)
            df["composite_percentile"] = (df["composite_rank"] / total * 100).round(2)
            df["total_stocks_ranked"] = total
            df["ranking_date"] = calc_date
            
            return {
                "success": True,
                "rankings": df,
                "count": len(df)
            }
            
        except Exception as e:
            logger.error(f"Error calculating rankings for {calc_date}: {e}")
            return {"success": False, "error": str(e), "count": 0}
    
    def _get_historical_price_data(
        self,
        start_date: date,
        end_date: date
    ) -> pd.DataFrame:
        """Get historical price data for date range."""
        sql = """
        SELECT symbol, date, open, high, low, close, volume
        FROM yfinance_daily_quotes
        WHERE date BETWEEN :start AND :end
        ORDER BY symbol, date
        """
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params={
                "start": start_date,
                "end": end_date
            })
        
        return df
    
    def _calculate_rs_rating_for_symbol(
        self,
        symbol: str,
        symbol_prices: pd.Series,
        all_prices: pd.DataFrame,
        calc_date: date
    ) -> float:
        """Calculate RS Rating for a symbol relative to all stocks."""
        # Get 12M return for this symbol
        if len(symbol_prices) < 252:
            # Use available data
            lookback = len(symbol_prices) - 1
        else:
            lookback = 252
        
        if lookback < 20:
            return 50.0  # Default
        
        current_price = symbol_prices.iloc[-1]
        past_price = symbol_prices.iloc[-lookback-1] if lookback < len(symbol_prices) else symbol_prices.iloc[0]
        
        if past_price <= 0:
            return 50.0
        
        symbol_return = (current_price / past_price - 1) * 100
        
        # Get returns for all stocks
        all_returns = []
        for col in all_prices.columns:
            try:
                col_prices = all_prices[col].dropna()
                col_prices = col_prices[col_prices.index <= calc_date]
                
                if len(col_prices) >= lookback:
                    curr = col_prices.iloc[-1]
                    past = col_prices.iloc[-lookback-1] if lookback < len(col_prices) else col_prices.iloc[0]
                    if past > 0:
                        all_returns.append((curr / past - 1) * 100)
            except:
                continue
        
        if not all_returns:
            return 50.0
        
        # Calculate percentile
        all_returns = sorted(all_returns)
        rank = sum(1 for r in all_returns if r < symbol_return)
        percentile = (rank / len(all_returns)) * 99 + 1
        
        return round(min(99, max(1, percentile)), 0)
    
    def _calculate_momentum_for_symbol(self, prices: pd.Series) -> float:
        """Calculate momentum score for a symbol."""
        if len(prices) < 5:
            return 0.0
        
        # Weighted returns
        weights = {
            5: 0.05,    # 1W
            21: 0.15,   # 1M
            63: 0.30,   # 3M
            126: 0.30,  # 6M
            252: 0.20,  # 12M
        }
        
        total_score = 0
        total_weight = 0
        
        current = prices.iloc[-1]
        
        for days, weight in weights.items():
            if len(prices) > days:
                past = prices.iloc[-days-1]
                if past > 0:
                    ret = (current / past - 1) * 100
                    # Normalize: -50% to +100% -> 0 to 100
                    normalized = min(100, max(0, (ret + 50) * (100 / 150)))
                    total_score += normalized * weight
                    total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return round(total_score / total_weight * (1 / 0.05) * 0.05, 1)  # Normalize
    
    def _calculate_trend_for_symbol(self, prices: pd.Series) -> int:
        """Calculate trend template score (0-8)."""
        if len(prices) < 200:
            return 0
        
        current = prices.iloc[-1]
        sma_50 = prices.iloc[-50:].mean()
        sma_150 = prices.iloc[-150:].mean()
        sma_200 = prices.iloc[-200:].mean()
        
        # Check 200 SMA trend (compare to 20 days ago)
        sma_200_20d_ago = prices.iloc[-220:-20].mean() if len(prices) >= 220 else sma_200
        sma_200_trending = sma_200 > sma_200_20d_ago
        
        # 52W high (252 trading days)
        high_52w = prices.iloc[-252:].max() if len(prices) >= 252 else prices.max()
        pct_from_high = ((current / high_52w) - 1) * 100
        
        # Count conditions
        conditions = 0
        if current > sma_150:
            conditions += 1
        if current > sma_200:
            conditions += 1
        if sma_150 > sma_200:
            conditions += 1
        if sma_200_trending:
            conditions += 1
        if sma_50 > sma_150:
            conditions += 1
        if sma_50 > sma_200:
            conditions += 1
        if current > sma_50:
            conditions += 1
        if pct_from_high >= -25:  # Within 25% of 52W high
            conditions += 1
        
        return conditions
    
    def _calculate_technical_for_symbol(self, prices: pd.Series) -> float:
        """Calculate technical score (0-100)."""
        if len(prices) < 200:
            return 0.0
        
        current = prices.iloc[-1]
        sma_50 = prices.iloc[-50:].mean()
        sma_150 = prices.iloc[-150:].mean()
        sma_200 = prices.iloc[-200:].mean()
        
        score = 0.0
        
        # Price vs SMAs (each worth 25 points)
        if current > sma_50:
            score += 25 + min(25, ((current / sma_50 - 1) * 100))
        if current > sma_150:
            score += 20
        if current > sma_200:
            score += 15
        
        # SMA alignment
        if sma_50 > sma_150 > sma_200:
            score += 15
        
        return round(min(100, max(0, score)), 1)
    
    def save_rankings_to_history(
        self,
        rankings_df: pd.DataFrame,
        ranking_date: date
    ) -> int:
        """
        Save rankings to history table.
        
        Args:
            rankings_df: DataFrame with rankings.
            ranking_date: Date of rankings.
            
        Returns:
            Number of records saved.
        """
        if rankings_df.empty:
            return 0
        
        # Prepare data
        df = rankings_df.copy()
        df["ranking_date"] = ranking_date
        
        # Select columns for history table
        history_cols = [
            "symbol", "ranking_date", "rs_rating", "momentum_score",
            "trend_template_score", "technical_score", "composite_score",
            "composite_rank", "composite_percentile", "total_stocks_ranked"
        ]
        df = df[[c for c in history_cols if c in df.columns]]
        
        # Use INSERT IGNORE to skip duplicates
        with self.engine.begin() as conn:
            conn.execute(text("DROP TEMPORARY TABLE IF EXISTS tmp_hist"))
            conn.execute(text("""
                CREATE TEMPORARY TABLE tmp_hist (
                    symbol VARCHAR(20),
                    ranking_date DATE,
                    rs_rating DECIMAL(5,2),
                    momentum_score DECIMAL(5,2),
                    trend_template_score TINYINT,
                    technical_score DECIMAL(5,2),
                    composite_score DECIMAL(5,2),
                    composite_rank INT,
                    composite_percentile DECIMAL(5,2),
                    total_stocks_ranked INT
                )
            """))
            
            df.to_sql("tmp_hist", conn, if_exists="append", index=False, method="multi")
            
            conn.execute(text("""
                INSERT IGNORE INTO stock_rankings_history 
                    (symbol, ranking_date, rs_rating, momentum_score,
                     trend_template_score, technical_score, composite_score,
                     composite_rank, composite_percentile, total_stocks_ranked)
                SELECT 
                    symbol, ranking_date, rs_rating, momentum_score,
                    trend_template_score, technical_score, composite_score,
                    composite_rank, composite_percentile, total_stocks_ranked
                FROM tmp_hist
            """))
        
        return len(df)
    
    def build(
        self,
        years: int = 3,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        skip_existing: bool = True,
        progress_callback: Optional[Callable] = None,
        min_stocks: int = 50
    ) -> Dict[str, Any]:
        """
        Build historical rankings.
        
        Args:
            years: Number of years to build (from today going back).
            start_date: Override start date (YYYY-MM-DD).
            end_date: Override end date (YYYY-MM-DD).
            skip_existing: Skip dates already in history.
            progress_callback: Optional callback(progress: BuildProgress).
            min_stocks: Minimum stocks required for valid ranking.
            
        Returns:
            Dict with build statistics.
        """
        self.stop_requested = False
        self.progress = BuildProgress()
        self.progress.start_time = datetime.now()
        
        # Determine date range
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            end_dt = date.today() - timedelta(days=1)  # Yesterday
        
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        else:
            start_dt = end_dt - timedelta(days=years * 365)
        
        logger.info(f"Building historical rankings from {start_dt} to {end_dt}")
        
        # Get trading dates
        trading_dates = self.get_available_trading_dates(start_dt, end_dt)
        logger.info(f"Found {len(trading_dates)} trading dates")
        
        if not trading_dates:
            return {"success": False, "error": "No trading dates found"}
        
        # Get already calculated dates
        existing_dates = set()
        if skip_existing:
            existing_dates = self.get_already_calculated_dates(start_dt, end_dt)
            logger.info(f"Found {len(existing_dates)} dates already calculated")
        
        # Filter out existing dates
        dates_to_process = [d for d in trading_dates if d not in existing_dates]
        
        self.progress.total_dates = len(dates_to_process)
        self.progress.skipped_dates = len(existing_dates)
        
        logger.info(f"Processing {len(dates_to_process)} dates (skipping {len(existing_dates)} existing)")
        
        if not dates_to_process:
            return {
                "success": True,
                "total_dates": len(trading_dates),
                "skipped": len(existing_dates),
                "processed": 0,
                "failed": 0
            }
        
        # Process each date
        failed_dates = []
        
        for calc_date in tqdm(dates_to_process, desc="Building rankings"):
            if self.stop_requested:
                logger.info("Build stopped by user")
                break
            
            self.progress.current_date = calc_date
            
            # Calculate rankings
            result = self.calculate_rankings_for_date(calc_date, min_stocks)
            
            if result["success"]:
                # Save to history
                saved = self.save_rankings_to_history(result["rankings"], calc_date)
                self.progress.completed_dates += 1
            else:
                failed_dates.append((calc_date, result.get("error", "Unknown")))
                self.progress.failed_dates += 1
            
            # Callback
            if progress_callback:
                progress_callback(self.progress)
        
        # Summary
        summary = {
            "success": True,
            "total_dates": len(trading_dates),
            "skipped": len(existing_dates),
            "processed": self.progress.completed_dates,
            "failed": self.progress.failed_dates,
            "elapsed_seconds": self.progress.elapsed_seconds,
            "failed_dates": failed_dates[:10],  # First 10 failures
        }
        
        logger.info(f"Build complete: {summary}")
        
        return summary
    
    def stop(self):
        """Request stop of build process."""
        self.stop_requested = True


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Build historical stock rankings")
    parser.add_argument("--years", type=int, default=3, help="Years of history to build")
    parser.add_argument("--start", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--no-skip", action="store_true", help="Don't skip existing dates")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Historical Rankings Builder")
    print("=" * 60)
    
    builder = HistoricalRankingsBuilder()
    
    def progress_cb(p: BuildProgress):
        if p.completed_dates % 10 == 0:
            print(f"Progress: {p.completed_dates}/{p.total_dates} | "
                  f"ETA: {p.eta_str} | Current: {p.current_date}")
    
    result = builder.build(
        years=args.years,
        start_date=args.start,
        end_date=args.end,
        skip_existing=not args.no_skip,
        progress_callback=progress_cb
    )
    
    print("\n" + "=" * 60)
    print("Build Summary:")
    print(f"  Total dates: {result['total_dates']}")
    print(f"  Skipped (existing): {result['skipped']}")
    print(f"  Processed: {result['processed']}")
    print(f"  Failed: {result['failed']}")
    print(f"  Elapsed: {result['elapsed_seconds']:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
