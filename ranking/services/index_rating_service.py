#!/usr/bin/env python3
"""
Index/Sector Rating Service

Calculates ratings for indices similar to stocks to help with:
- Sector rotation analysis
- Finding leading/lagging sectors
- Relative strength comparison between sectors

Ratings calculated:
- RS Rating: Relative strength vs Nifty 50
- Momentum Score: Based on price momentum
- Trend Score: MA alignment and price position
- Composite Score: Weighted combination
"""

import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from sqlalchemy import text

from ranking.db.schema import get_ranking_engine


@dataclass
class IndexRating:
    """Rating result for an index."""
    symbol: str
    name: str
    date: date
    close: float
    rs_rating: float  # 1-99, relative to Nifty
    momentum_score: float  # 0-100
    trend_score: float  # 0-100
    composite_score: float  # 0-100
    
    # Additional metrics
    return_1w: float
    return_1m: float
    return_3m: float
    return_6m: float
    return_1y: float
    
    # Trend indicators
    above_20dma: bool
    above_50dma: bool
    above_200dma: bool
    ma_aligned: bool  # 20 > 50 > 200


# Index name mapping for display
INDEX_NAMES = {
    "^NSEI": "Nifty 50",
    "^NSEBANK": "Bank Nifty",
    "^CNXIT": "Nifty IT",
    "^CNXPHARMA": "Nifty Pharma",
    "^CNXAUTO": "Nifty Auto",
    "^CNXFMCG": "Nifty FMCG",
    "^CNXMETAL": "Nifty Metal",
    "^CNXREALTY": "Nifty Realty",
    "^CNXENERGY": "Nifty Energy",
    "^CNXINFRA": "Nifty Infra",
    "^CNXPSUBANK": "Nifty PSU Bank",
    "^NSMIDCP": "Nifty Midcap 100",
    "NIFTY_FIN_SERVICE.NS": "Nifty Financial",
    "NIFTY_PVT_BANK.NS": "Nifty Pvt Bank",
}


class IndexRatingService:
    """Service for calculating index/sector ratings."""
    
    def __init__(self):
        self.engine = get_ranking_engine()
    
    def get_available_indices(self) -> List[Tuple[str, str, int]]:
        """Get list of indices with sufficient data."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT symbol, COUNT(*) as cnt
                FROM yfinance_indices_daily_quotes
                GROUP BY symbol
                HAVING COUNT(*) >= 252
                ORDER BY symbol
            """)).fetchall()
            
            indices = []
            for r in result:
                name = INDEX_NAMES.get(r[0], r[0])
                indices.append((r[0], name, r[1]))
            return indices
    
    def calculate_ratings(self, target_date: Optional[date] = None) -> List[IndexRating]:
        """Calculate ratings for all indices on a given date."""
        if target_date is None:
            target_date = date.today()
        
        # Get Nifty 50 data for relative strength calculation
        nifty_data = self._get_index_data("^NSEI", target_date)
        if nifty_data is None or len(nifty_data) < 252:
            raise ValueError("Insufficient Nifty 50 data")
        
        # Calculate Nifty returns for RS comparison
        nifty_returns = self._calculate_returns(nifty_data)
        
        # Get all indices
        indices = self.get_available_indices()
        
        ratings = []
        for symbol, name, _ in indices:
            if symbol == "^NSEI":  # Skip Nifty itself for RS calculation
                continue
                
            try:
                rating = self._calculate_single_rating(symbol, name, target_date, nifty_returns)
                if rating:
                    ratings.append(rating)
            except Exception as e:
                print(f"Error calculating rating for {symbol}: {e}")
        
        # Sort by composite score
        ratings.sort(key=lambda x: x.composite_score, reverse=True)
        
        # Assign ranks
        return ratings
    
    def _get_index_data(self, symbol: str, target_date: date, days: int = 400) -> Optional[pd.DataFrame]:
        """Get historical data for an index."""
        with self.engine.connect() as conn:
            df = pd.read_sql(text("""
                SELECT date, open, high, low, close, volume
                FROM yfinance_indices_daily_quotes
                WHERE symbol = :symbol AND date <= :target_date
                ORDER BY date DESC
                LIMIT :days
            """), conn, params={"symbol": symbol, "target_date": target_date, "days": days})
        
        if df.empty:
            return None
        
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        return df
    
    def _calculate_returns(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate various period returns."""
        if len(df) < 252:
            return {}
        
        current = df['close'].iloc[-1]
        
        returns = {}
        periods = [
            ("1w", 5),
            ("1m", 21),
            ("3m", 63),
            ("6m", 126),
            ("1y", 252),
        ]
        
        for name, days in periods:
            if len(df) > days:
                past = df['close'].iloc[-days-1]
                returns[name] = (current / past - 1) * 100
            else:
                returns[name] = 0
        
        return returns
    
    def _calculate_single_rating(self, symbol: str, name: str, 
                                  target_date: date, nifty_returns: Dict[str, float]) -> Optional[IndexRating]:
        """Calculate rating for a single index."""
        df = self._get_index_data(symbol, target_date)
        if df is None or len(df) < 252:
            return None
        
        current_price = df['close'].iloc[-1]
        current_date = df['date'].iloc[-1].date()
        
        # Calculate returns
        returns = self._calculate_returns(df)
        if not returns:
            return None
        
        # Calculate RS Rating (relative to Nifty)
        rs_rating = self._calculate_rs_rating(returns, nifty_returns)
        
        # Calculate Momentum Score
        momentum_score = self._calculate_momentum_score(df, returns)
        
        # Calculate Trend Score
        trend_score, above_20, above_50, above_200, ma_aligned = self._calculate_trend_score(df)
        
        # Calculate Composite Score
        composite_score = (
            rs_rating * 0.35 +  # RS weight
            momentum_score * 0.35 +  # Momentum weight
            trend_score * 0.30  # Trend weight
        )
        
        return IndexRating(
            symbol=symbol,
            name=name,
            date=current_date,
            close=current_price,
            rs_rating=rs_rating,
            momentum_score=momentum_score,
            trend_score=trend_score,
            composite_score=composite_score,
            return_1w=returns.get("1w", 0),
            return_1m=returns.get("1m", 0),
            return_3m=returns.get("3m", 0),
            return_6m=returns.get("6m", 0),
            return_1y=returns.get("1y", 0),
            above_20dma=above_20,
            above_50dma=above_50,
            above_200dma=above_200,
            ma_aligned=ma_aligned,
        )
    
    def _calculate_rs_rating(self, index_returns: Dict[str, float], 
                             nifty_returns: Dict[str, float]) -> float:
        """Calculate relative strength rating vs Nifty."""
        # Weighted relative performance
        weights = {"1m": 0.15, "3m": 0.25, "6m": 0.30, "1y": 0.30}
        
        rs_score = 0
        total_weight = 0
        
        for period, weight in weights.items():
            idx_ret = index_returns.get(period, 0)
            nif_ret = nifty_returns.get(period, 0)
            
            # Relative outperformance
            outperformance = idx_ret - nif_ret
            
            # Convert to score (outperformance of 10% = 70 base + adjustments)
            period_score = 50 + (outperformance * 2.5)  # Scale factor
            period_score = max(1, min(99, period_score))  # Clamp to 1-99
            
            rs_score += period_score * weight
            total_weight += weight
        
        return rs_score / total_weight if total_weight > 0 else 50
    
    def _calculate_momentum_score(self, df: pd.DataFrame, returns: Dict[str, float]) -> float:
        """Calculate momentum score based on price momentum."""
        # ROC-based momentum
        roc_scores = []
        
        # Short-term momentum (higher weight for recency)
        if returns.get("1w", 0) > 0:
            roc_scores.append(60 + min(returns["1w"] * 5, 30))
        else:
            roc_scores.append(40 + max(returns.get("1w", 0) * 5, -30))
        
        if returns.get("1m", 0) > 0:
            roc_scores.append(60 + min(returns["1m"] * 2, 30))
        else:
            roc_scores.append(40 + max(returns.get("1m", 0) * 2, -30))
        
        if returns.get("3m", 0) > 0:
            roc_scores.append(60 + min(returns["3m"] * 1, 30))
        else:
            roc_scores.append(40 + max(returns.get("3m", 0) * 1, -30))
        
        # Weighted average with recency bias
        weights = [0.4, 0.35, 0.25]
        momentum = sum(s * w for s, w in zip(roc_scores, weights))
        
        return max(0, min(100, momentum))
    
    def _calculate_trend_score(self, df: pd.DataFrame) -> Tuple[float, bool, bool, bool, bool]:
        """Calculate trend score based on MA alignment."""
        if len(df) < 200:
            return 50, False, False, False, False
        
        current_price = df['close'].iloc[-1]
        
        # Calculate MAs
        ma20 = df['close'].rolling(20).mean().iloc[-1]
        ma50 = df['close'].rolling(50).mean().iloc[-1]
        ma200 = df['close'].rolling(200).mean().iloc[-1]
        
        above_20 = current_price > ma20
        above_50 = current_price > ma50
        above_200 = current_price > ma200
        ma_aligned = ma20 > ma50 > ma200
        
        # Build trend score
        score = 50  # Base
        
        # Price position
        if above_200:
            score += 15
        if above_50:
            score += 10
        if above_20:
            score += 5
        
        # MA alignment
        if ma_aligned:
            score += 15
        elif ma20 > ma50:
            score += 5
        
        # Price distance from 200 DMA
        dist_200 = (current_price / ma200 - 1) * 100
        if dist_200 > 10:
            score += 5
        elif dist_200 < -10:
            score -= 10
        
        return max(0, min(100, score)), above_20, above_50, above_200, ma_aligned
    
    def get_sector_rotation_analysis(self, target_date: Optional[date] = None) -> Dict:
        """Get comprehensive sector rotation analysis."""
        ratings = self.calculate_ratings(target_date)
        
        if not ratings:
            return {}
        
        # Categorize sectors
        leading = [r for r in ratings if r.composite_score >= 70]
        improving = [r for r in ratings if 50 <= r.composite_score < 70 and r.return_1m > r.return_3m / 3]
        weakening = [r for r in ratings if 50 <= r.composite_score < 70 and r.return_1m < r.return_3m / 3]
        lagging = [r for r in ratings if r.composite_score < 50]
        
        return {
            "date": ratings[0].date if ratings else target_date,
            "all_ratings": ratings,
            "leading_sectors": leading,
            "improving_sectors": improving,
            "weakening_sectors": weakening,
            "lagging_sectors": lagging,
            "top_sector": ratings[0] if ratings else None,
            "bottom_sector": ratings[-1] if ratings else None,
        }


def get_letter_rating(score: float) -> str:
    """Convert score to letter rating."""
    if score >= 90:
        return "A+ ⭐"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B+"
    elif score >= 60:
        return "B"
    elif score >= 50:
        return "C+"
    elif score >= 40:
        return "C"
    elif score >= 30:
        return "D"
    else:
        return "F"


if __name__ == "__main__":
    # Test the service
    service = IndexRatingService()
    
    print("Available indices:")
    for symbol, name, count in service.get_available_indices():
        print(f"  {symbol}: {name} ({count} records)")
    
    print("\n" + "="*80)
    print("Sector Ratings (as of latest data):")
    print("="*80)
    
    try:
        ratings = service.calculate_ratings()
        
        print(f"\n{'Rank':<5} {'Sector':<20} {'RS':<6} {'Mom':<6} {'Trend':<6} {'Comp':<6} {'1W%':<8} {'1M%':<8} {'3M%':<8} {'Rating'}")
        print("-" * 95)
        
        for i, r in enumerate(ratings, 1):
            letter = get_letter_rating(r.composite_score)
            print(f"{i:<5} {r.name:<20} {r.rs_rating:>5.1f} {r.momentum_score:>5.1f} "
                  f"{r.trend_score:>5.1f} {r.composite_score:>5.1f} {r.return_1w:>7.2f}% {r.return_1m:>7.2f}% "
                  f"{r.return_3m:>7.2f}% {letter}")
        
        print("\n" + "="*80)
        analysis = service.get_sector_rotation_analysis()
        
        if analysis.get("leading_sectors"):
            print("\n🚀 LEADING SECTORS (Score >= 70):")
            for r in analysis["leading_sectors"]:
                print(f"  • {r.name}: {r.composite_score:.1f} (RS: {r.rs_rating:.0f}, 1M: {r.return_1m:+.1f}%)")
        
        if analysis.get("improving_sectors"):
            print("\n📈 IMPROVING SECTORS:")
            for r in analysis["improving_sectors"]:
                print(f"  • {r.name}: {r.composite_score:.1f} (RS: {r.rs_rating:.0f}, 1M: {r.return_1m:+.1f}%)")
        
        if analysis.get("lagging_sectors"):
            print("\n📉 LAGGING SECTORS (Score < 50):")
            for r in analysis["lagging_sectors"]:
                print(f"  • {r.name}: {r.composite_score:.1f} (RS: {r.rs_rating:.0f}, 1M: {r.return_1m:+.1f}%)")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
