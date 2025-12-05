#!/usr/bin/env python3
"""
Volume-Price Pattern Analyzer
=============================
Correlates volume events with price patterns to find high-probability setups.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class VolumePattern:
    """A volume-price pattern with statistics."""
    pattern_name: str
    description: str
    criteria: Dict
    event_count: int
    avg_return_1d: float
    avg_return_1w: float
    avg_return_1m: float
    win_rate_1d: float
    win_rate_1w: float
    win_rate_1m: float
    best_stocks: List[str]  # Stocks where this pattern works best


@dataclass
class PatternMatch:
    """A specific pattern match for a stock."""
    symbol: str
    event_date: datetime
    pattern_name: str
    volume: int
    relative_volume: float
    day_return: float
    close_price: float
    
    # Technical context
    rsi_14: Optional[float] = None
    above_sma_20: Optional[bool] = None
    above_sma_50: Optional[bool] = None
    distance_from_52w_high: Optional[float] = None
    
    # Forward returns (populated if historical)
    return_1d: Optional[float] = None
    return_1w: Optional[float] = None
    return_1m: Optional[float] = None


class VolumePatternAnalyzer:
    """
    Analyzes volume-price patterns and their predictive power.
    
    Patterns Analyzed:
    1. Breakout on Volume - High volume + price > 3% + new high
    2. Breakdown on Volume - High volume + price < -3% + new low  
    3. Accumulation Day - High volume + up day + closes in upper half
    4. Distribution Day - High volume + down day + closes in lower half
    5. Pocket Pivot - Volume > any down day volume in last 10 days + up day
    6. Climax Top - Very high volume + large range + closes in lower half
    7. Capitulation - Very high volume + large down day + oversold
    8. Gap Up on Volume - Gap > 2% + high volume
    9. Gap Down on Volume - Gap < -2% + high volume
    10. Follow Through Day - After correction, up 1%+ on higher volume
    """
    
    PATTERNS = {
        'breakout': {
            'name': 'Breakout on Volume',
            'description': 'High volume day with price up >3%, often near highs',
            'volume_min': 2.0,
            'return_min': 3.0,
        },
        'breakdown': {
            'name': 'Breakdown on Volume',
            'description': 'High volume day with price down >3%, often near lows',
            'volume_min': 2.0,
            'return_max': -3.0,
        },
        'accumulation': {
            'name': 'Accumulation Day',
            'description': 'High volume up day closing in upper half of range',
            'volume_min': 1.5,
            'return_min': 0.5,
            'close_position': 'upper',  # Closes in upper half of range
        },
        'distribution': {
            'name': 'Distribution Day',
            'description': 'High volume down day closing in lower half of range',
            'volume_min': 1.5,
            'return_max': -0.5,
            'close_position': 'lower',
        },
        'pocket_pivot': {
            'name': 'Pocket Pivot',
            'description': 'Up day with volume > max down-day volume in 10 days',
            'return_min': 0,
        },
        'climax_top': {
            'name': 'Climax Top',
            'description': 'Very high volume, wide range, closes weak - potential top',
            'volume_min': 3.0,
            'range_min': 4.0,  # High-Low as % of close
            'close_position': 'lower',
        },
        'capitulation': {
            'name': 'Capitulation',
            'description': 'Very high volume, large down day - potential bottom',
            'volume_min': 3.0,
            'return_max': -4.0,
        },
        'gap_up_volume': {
            'name': 'Gap Up on Volume',
            'description': 'Gap up >2% with high volume',
            'volume_min': 2.0,
            'gap_min': 2.0,
        },
        'gap_down_volume': {
            'name': 'Gap Down on Volume', 
            'description': 'Gap down >2% with high volume',
            'volume_min': 2.0,
            'gap_max': -2.0,
        },
    }
    
    def __init__(self):
        self.engine = self._create_engine()
    
    def _create_engine(self):
        """Create database engine."""
        password = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
        host = os.getenv('MYSQL_HOST', 'localhost')
        port = os.getenv('MYSQL_PORT', '3306')
        db = os.getenv('MYSQL_DB', 'marketdata')
        user = os.getenv('MYSQL_USER', 'root')
        return create_engine(f'mysql+pymysql://{user}:{password}@{host}:{port}/{db}', pool_pre_ping=True)
    
    def analyze_pattern_performance(self, pattern_name: str = None) -> pd.DataFrame:
        """Analyze performance of volume-price patterns."""
        
        if pattern_name and pattern_name not in self.PATTERNS:
            raise ValueError(f"Unknown pattern: {pattern_name}")
        
        # Build pattern classification query
        query = """
            SELECT 
                symbol,
                event_date,
                volume,
                relative_volume,
                day_return,
                close_price,
                prev_close,
                return_1d,
                return_1w,
                return_2w,
                return_1m,
                volume_quintile
            FROM volume_cluster_events
            WHERE return_1m IS NOT NULL
            ORDER BY symbol, event_date
        """
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(query), conn)
        
        if df.empty:
            return pd.DataFrame()
        
        # Classify each event into patterns
        df['pattern'] = df.apply(self._classify_event, axis=1)
        
        # Calculate statistics by pattern
        pattern_stats = []
        
        patterns_to_analyze = [pattern_name] if pattern_name else list(self.PATTERNS.keys())
        
        for pname in patterns_to_analyze:
            pdata = df[df['pattern'] == pname]
            if len(pdata) < 10:  # Need minimum events
                continue
            
            stats = {
                'pattern': self.PATTERNS[pname]['name'],
                'events': len(pdata),
                'avg_day_return': round(pdata['day_return'].mean(), 2),
                'avg_1d': round(pdata['return_1d'].mean(), 2),
                'avg_1w': round(pdata['return_1w'].mean(), 2),
                'avg_2w': round(pdata['return_2w'].mean(), 2),
                'avg_1m': round(pdata['return_1m'].mean(), 2),
                'win_1d': round((pdata['return_1d'] > 0).mean() * 100, 1),
                'win_1w': round((pdata['return_1w'] > 0).mean() * 100, 1),
                'win_1m': round((pdata['return_1m'] > 0).mean() * 100, 1),
                'max_1m': round(pdata['return_1m'].max(), 1),
                'min_1m': round(pdata['return_1m'].min(), 1),
            }
            pattern_stats.append(stats)
        
        return pd.DataFrame(pattern_stats)
    
    def _classify_event(self, row) -> str:
        """Classify a volume event into a pattern."""
        
        rel_vol = row['relative_volume'] if pd.notna(row['relative_volume']) else 0
        day_ret = row['day_return'] if pd.notna(row['day_return']) else 0
        
        # Check patterns in order of specificity
        
        # Breakout: High volume + strong up day
        if rel_vol >= 2.0 and day_ret >= 3.0:
            return 'breakout'
        
        # Breakdown: High volume + strong down day
        if rel_vol >= 2.0 and day_ret <= -3.0:
            return 'breakdown'
        
        # Capitulation: Very high volume + large down
        if rel_vol >= 3.0 and day_ret <= -4.0:
            return 'capitulation'
        
        # Climax Top: Very high volume + closes weak (approximated by small/negative return despite volume)
        if rel_vol >= 3.0 and -1.0 <= day_ret <= 1.0:
            return 'climax_top'
        
        # Gap patterns (using day_return as proxy for gap)
        if rel_vol >= 2.0 and day_ret >= 2.0 and day_ret < 3.0:
            return 'gap_up_volume'
        
        if rel_vol >= 2.0 and day_ret <= -2.0 and day_ret > -3.0:
            return 'gap_down_volume'
        
        # Accumulation: High volume + moderate up
        if rel_vol >= 1.5 and day_ret >= 0.5 and day_ret < 3.0:
            return 'accumulation'
        
        # Distribution: High volume + moderate down
        if rel_vol >= 1.5 and day_ret <= -0.5 and day_ret > -3.0:
            return 'distribution'
        
        return 'neutral'
    
    def find_recent_patterns(self, days: int = 5, pattern_filter: str = None) -> List[PatternMatch]:
        """Find recent pattern matches."""
        
        cutoff = datetime.now() - timedelta(days=days)
        
        query = """
            SELECT 
                symbol, event_date, volume, relative_volume, day_return, close_price,
                return_1d, return_1w, return_1m
            FROM volume_cluster_events
            WHERE event_date >= :cutoff
            AND volume_quintile IN ('High', 'Very High')
            ORDER BY event_date DESC, relative_volume DESC
        """
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(query), conn, params={'cutoff': cutoff.strftime('%Y-%m-%d')})
        
        matches = []
        for _, row in df.iterrows():
            pattern = self._classify_event(row)
            
            if pattern == 'neutral':
                continue
            
            if pattern_filter and pattern != pattern_filter:
                continue
            
            match = PatternMatch(
                symbol=row['symbol'],
                event_date=row['event_date'],
                pattern_name=self.PATTERNS.get(pattern, {}).get('name', pattern),
                volume=int(row['volume']),
                relative_volume=float(row['relative_volume']) if pd.notna(row['relative_volume']) else 0,
                day_return=float(row['day_return']) if pd.notna(row['day_return']) else 0,
                close_price=float(row['close_price']) if pd.notna(row['close_price']) else 0,
                return_1d=float(row['return_1d']) if pd.notna(row['return_1d']) else None,
                return_1w=float(row['return_1w']) if pd.notna(row['return_1w']) else None,
                return_1m=float(row['return_1m']) if pd.notna(row['return_1m']) else None,
            )
            matches.append(match)
        
        return matches
    
    def get_best_patterns_by_return(self) -> pd.DataFrame:
        """Rank patterns by forward return performance."""
        stats = self.analyze_pattern_performance()
        if stats.empty:
            return stats
        return stats.sort_values('avg_1m', ascending=False)
    
    def get_best_patterns_by_win_rate(self) -> pd.DataFrame:
        """Rank patterns by win rate."""
        stats = self.analyze_pattern_performance()
        if stats.empty:
            return stats
        return stats.sort_values('win_1m', ascending=False)
    
    def get_pattern_by_stock(self, symbol: str) -> pd.DataFrame:
        """Get pattern statistics for a specific stock."""
        
        query = """
            SELECT 
                symbol, event_date, volume, relative_volume, day_return, close_price,
                return_1d, return_1w, return_2w, return_1m
            FROM volume_cluster_events
            WHERE symbol = :symbol
            AND return_1m IS NOT NULL
            ORDER BY event_date
        """
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(query), conn, params={'symbol': symbol})
        
        if df.empty:
            return pd.DataFrame()
        
        df['pattern'] = df.apply(self._classify_event, axis=1)
        
        # Group by pattern
        stats = df.groupby('pattern').agg({
            'event_date': 'count',
            'day_return': 'mean',
            'return_1d': 'mean',
            'return_1w': 'mean',
            'return_1m': ['mean', lambda x: (x > 0).mean() * 100]
        }).round(2)
        
        stats.columns = ['events', 'avg_day', 'avg_1d', 'avg_1w', 'avg_1m', 'win_1m']
        stats = stats[stats['events'] >= 3]  # Minimum events
        
        return stats.sort_values('avg_1m', ascending=False)
    
    def generate_pattern_report(self) -> str:
        """Generate a comprehensive pattern analysis report."""
        
        lines = []
        lines.append("="*80)
        lines.append(" VOLUME-PRICE PATTERN ANALYSIS REPORT")
        lines.append("="*80)
        lines.append("")
        
        # Overall statistics
        stats = self.get_best_patterns_by_return()
        
        if stats.empty:
            return "No pattern data available."
        
        lines.append("PATTERN PERFORMANCE RANKING (by 1-Month Return)")
        lines.append("-"*80)
        lines.append(f"{'Pattern':<25} {'Events':>8} {'Avg 1M':>8} {'Win% 1M':>8} {'Avg 1W':>8}")
        lines.append("-"*80)
        
        for _, row in stats.iterrows():
            lines.append(
                f"{row['pattern']:<25} {row['events']:>8} {row['avg_1m']:>+7.1f}% "
                f"{row['win_1m']:>7.1f}% {row['avg_1w']:>+7.1f}%"
            )
        
        lines.append("")
        lines.append("="*80)
        lines.append(" KEY INSIGHTS")
        lines.append("="*80)
        
        # Best pattern
        best = stats.iloc[0]
        lines.append(f"✅ Best Pattern: {best['pattern']}")
        lines.append(f"   Average 1-Month Return: {best['avg_1m']:+.1f}%")
        lines.append(f"   Win Rate: {best['win_1m']:.1f}%")
        lines.append("")
        
        # Patterns with >60% win rate
        high_win = stats[stats['win_1m'] >= 60]
        if not high_win.empty:
            lines.append("🎯 High Win Rate Patterns (>60%):")
            for _, row in high_win.iterrows():
                lines.append(f"   - {row['pattern']}: {row['win_1m']:.1f}% win rate")
        
        return "\n".join(lines)


def print_pattern_matches(matches: List[PatternMatch], title: str = "Pattern Matches"):
    """Print pattern matches."""
    print(f"\n{'='*80}")
    print(f" {title}")
    print(f"{'='*80}")
    
    if not matches:
        print("No matches found.")
        return
    
    print(f"{'Symbol':<15} {'Date':<12} {'Pattern':<20} {'Day%':>8} {'RelVol':>8}")
    print("-"*80)
    
    for m in matches:
        print(f"{m.symbol:<15} {str(m.event_date)[:10]:<12} {m.pattern_name:<20} "
              f"{m.day_return:>+7.1f}% {m.relative_volume:>7.1f}x")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Volume-Price Pattern Analyzer')
    parser.add_argument('--report', action='store_true', help='Generate full report')
    parser.add_argument('--recent', type=int, default=5, help='Find patterns in last N days')
    parser.add_argument('--pattern', type=str, help='Filter by pattern name')
    parser.add_argument('--stock', type=str, help='Analyze specific stock')
    parser.add_argument('--best-return', action='store_true', help='Show patterns by return')
    parser.add_argument('--best-win', action='store_true', help='Show patterns by win rate')
    args = parser.parse_args()
    
    analyzer = VolumePatternAnalyzer()
    
    if args.report:
        print(analyzer.generate_pattern_report())
    
    elif args.stock:
        print(f"\nPattern Analysis for {args.stock}:")
        stats = analyzer.get_pattern_by_stock(args.stock)
        if not stats.empty:
            print(stats.to_string())
        else:
            print("No data found.")
    
    elif args.best_return:
        print("\nPatterns Ranked by 1-Month Return:")
        stats = analyzer.get_best_patterns_by_return()
        print(stats.to_string(index=False))
    
    elif args.best_win:
        print("\nPatterns Ranked by Win Rate:")
        stats = analyzer.get_best_patterns_by_win_rate()
        print(stats.to_string(index=False))
    
    else:
        matches = analyzer.find_recent_patterns(days=args.recent, pattern_filter=args.pattern)
        print_pattern_matches(matches, f"Recent Patterns (Last {args.recent} Days)")
