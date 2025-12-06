#!/usr/bin/env python3
"""
Volume Event Scanner
====================
Scans for stocks with recent high volume events and analyzes patterns.
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
class RecentVolumeEvent:
    """Recent high volume event with context."""
    symbol: str
    event_date: datetime
    volume: int
    volume_quintile: str
    relative_volume: float
    day_return: float
    close_price: float
    
    # Pattern indicators
    pattern: str  # 'gap_up', 'gap_down', 'breakout', 'breakdown', 'neutral'
    gap_percent: Optional[float] = None
    is_52w_high: bool = False
    is_52w_low: bool = False
    days_since_event: int = 0
    
    # Current status (for tracking)
    current_price: Optional[float] = None
    return_since_event: Optional[float] = None


@dataclass 
class VolumeAlert:
    """Alert for a high volume event."""
    symbol: str
    event_date: datetime
    alert_type: str  # 'ultra_high_volume', 'very_high_volume', 'high_volume', 'breakout', 'breakdown'
    volume: int
    relative_volume: float
    day_return: float
    message: str
    priority: str  # 'critical', 'high', 'medium', 'low'


class VolumeEventScanner:
    """Scans for recent high volume events and patterns."""
    
    PATTERN_THRESHOLDS = {
        'gap_up': 2.0,      # Gap up > 2%
        'gap_down': -2.0,   # Gap down < -2%
        'breakout': 3.0,    # Day return > 3%
        'breakdown': -3.0,  # Day return < -3%
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
    
    def scan_recent_events(self, days: int = 5, quintile: str = 'Very High') -> List[RecentVolumeEvent]:
        """Scan for recent high volume events in the last N days."""
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = """
            SELECT 
                e.symbol, e.event_date, e.volume, e.volume_quintile,
                e.relative_volume, e.day_return, e.close_price,
                e.prev_close
            FROM volume_cluster_events e
            WHERE e.event_date >= :cutoff_date
            AND e.volume_quintile = :quintile
            ORDER BY e.event_date DESC, e.relative_volume DESC
        """
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(query), conn, params={
                'cutoff_date': cutoff_date.strftime('%Y-%m-%d'),
                'quintile': quintile
            })
        
        events = []
        for _, row in df.iterrows():
            # Determine pattern
            pattern = self._classify_pattern(row['day_return'], row['close_price'], row['prev_close'])
            gap_pct = ((row['close_price'] / row['prev_close']) - 1) * 100 if row['prev_close'] else None
            
            event = RecentVolumeEvent(
                symbol=row['symbol'],
                event_date=row['event_date'],
                volume=int(row['volume']),
                volume_quintile=row['volume_quintile'],
                relative_volume=float(row['relative_volume']) if pd.notna(row['relative_volume']) else 0,
                day_return=float(row['day_return']) if pd.notna(row['day_return']) else 0,
                close_price=float(row['close_price']) if pd.notna(row['close_price']) else 0,
                pattern=pattern,
                gap_percent=gap_pct,
                days_since_event=(datetime.now().date() - row['event_date']).days
            )
            events.append(event)
        
        # Enrich with current price
        events = self._enrich_with_current_prices(events)
        
        return events
    
    def _classify_pattern(self, day_return: float, close: float, prev_close: float) -> str:
        """Classify the price pattern for the volume event."""
        if pd.isna(day_return):
            return 'neutral'
        
        if day_return >= self.PATTERN_THRESHOLDS['breakout']:
            return 'breakout'
        elif day_return <= self.PATTERN_THRESHOLDS['breakdown']:
            return 'breakdown'
        elif day_return >= self.PATTERN_THRESHOLDS['gap_up']:
            return 'gap_up'
        elif day_return <= self.PATTERN_THRESHOLDS['gap_down']:
            return 'gap_down'
        else:
            return 'neutral'
    
    def _enrich_with_current_prices(self, events: List[RecentVolumeEvent]) -> List[RecentVolumeEvent]:
        """Add current prices and returns to events."""
        if not events:
            return events
        
        symbols = list(set(e.symbol for e in events))
        
        query = """
            SELECT symbol, close as current_price
            FROM yfinance_daily_quotes
            WHERE symbol IN :symbols
            AND timeframe = 'daily'
            AND date = (SELECT MAX(date) FROM yfinance_daily_quotes WHERE symbol = yfinance_daily_quotes.symbol AND timeframe = 'daily')
        """
        
        try:
            with self.engine.connect() as conn:
                # Build query with explicit symbol list
                symbol_list = ', '.join([f"'{s}'" for s in symbols])
                query_fixed = f"""
                    SELECT q.symbol, q.close as current_price
                    FROM yfinance_daily_quotes q
                    INNER JOIN (
                        SELECT symbol, MAX(date) as max_date
                        FROM yfinance_daily_quotes 
                        WHERE symbol IN ({symbol_list})
                        AND timeframe = 'daily'
                        GROUP BY symbol
                    ) latest ON q.symbol = latest.symbol AND q.date = latest.max_date
                """
                df = pd.read_sql(text(query_fixed), conn)
            
            price_map = dict(zip(df['symbol'], df['current_price']))
            
            for event in events:
                if event.symbol in price_map:
                    event.current_price = float(price_map[event.symbol])
                    if event.close_price and event.close_price > 0:
                        event.return_since_event = ((event.current_price / event.close_price) - 1) * 100
        except Exception as e:
            print(f"Warning: Could not fetch current prices: {e}")
        
        return events
    
    def scan_breakouts(self, days: int = 10) -> List[RecentVolumeEvent]:
        """Scan specifically for breakout patterns (high volume + strong price move)."""
        events = self.scan_recent_events(days=days, quintile='Very High')
        return [e for e in events if e.pattern in ['breakout', 'gap_up']]
    
    def scan_breakdowns(self, days: int = 10) -> List[RecentVolumeEvent]:
        """Scan specifically for breakdown patterns."""
        events = self.scan_recent_events(days=days, quintile='Very High')
        return [e for e in events if e.pattern in ['breakdown', 'gap_down']]
    
    def get_volume_leaders(self, days: int = 5, top_n: int = 20) -> List[RecentVolumeEvent]:
        """Get top N stocks by relative volume in recent days."""
        events = self.scan_recent_events(days=days, quintile='Very High')
        events.sort(key=lambda x: x.relative_volume, reverse=True)
        return events[:top_n]
    
    def scan_for_alerts(self, symbols: List[str] = None) -> List[VolumeAlert]:
        """Check for high volume alerts in today's data."""
        
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        query = """
            SELECT symbol, date, volume, close, open,
                   (close - open) / open * 100 as day_return
            FROM yfinance_daily_quotes
            WHERE date >= :yesterday
            AND timeframe = 'daily'
        """
        if symbols:
            symbol_list = ', '.join([f"'{s}'" for s in symbols])
            query += f" AND symbol IN ({symbol_list})"
        
        query += " ORDER BY date DESC, volume DESC"
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(query), conn, params={'yesterday': yesterday.strftime('%Y-%m-%d')})
        
        if df.empty:
            return []
        
        alerts = []
        
        # Calculate volume percentiles
        for symbol in df['symbol'].unique():
            symbol_df = df[df['symbol'] == symbol]
            if len(symbol_df) == 0:
                continue
            
            latest = symbol_df.iloc[0]
            
            # Get historical volume stats
            stats = self._get_volume_stats(symbol)
            if not stats:
                continue
            
            rel_vol = latest['volume'] / stats['avg_volume'] if stats['avg_volume'] > 0 else 0
            
            # Check for alerts
            if rel_vol >= 3.0:  # Very high volume (3x average)
                priority = 'high'
                alert_type = 'very_high_volume'
                message = f"🔥 {symbol}: Volume {rel_vol:.1f}x average! Price {latest['day_return']:+.1f}%"
            elif rel_vol >= 2.0:  # High volume
                priority = 'medium'
                alert_type = 'high_volume'
                message = f"📈 {symbol}: Volume {rel_vol:.1f}x average. Price {latest['day_return']:+.1f}%"
            else:
                continue
            
            # Check for breakout/breakdown
            if latest['day_return'] >= 3.0 and rel_vol >= 2.0:
                alert_type = 'breakout'
                message = f"🚀 BREAKOUT: {symbol} +{latest['day_return']:.1f}% on {rel_vol:.1f}x volume!"
                priority = 'high'
            elif latest['day_return'] <= -3.0 and rel_vol >= 2.0:
                alert_type = 'breakdown'
                message = f"⚠️ BREAKDOWN: {symbol} {latest['day_return']:.1f}% on {rel_vol:.1f}x volume!"
                priority = 'high'
            
            alerts.append(VolumeAlert(
                symbol=symbol,
                event_date=latest['date'],
                alert_type=alert_type,
                volume=int(latest['volume']),
                relative_volume=rel_vol,
                day_return=float(latest['day_return']) if pd.notna(latest['day_return']) else 0,
                message=message,
                priority=priority
            ))
        
        # Sort by priority and relative volume
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        alerts.sort(key=lambda x: (priority_order.get(x.priority, 2), -x.relative_volume))
        
        return alerts
    
    def _get_volume_stats(self, symbol: str) -> Optional[Dict]:
        """Get volume statistics for a symbol."""
        query = """
            SELECT 
                AVG(volume) as avg_volume,
                STDDEV(volume) as std_volume
            FROM yfinance_daily_quotes
            WHERE symbol = :symbol
            AND timeframe = 'daily'
            AND date >= DATE_SUB(CURDATE(), INTERVAL 60 DAY)
        """
        
        with self.engine.connect() as conn:
            result = conn.execute(text(query), {'symbol': symbol}).fetchone()
        
        if result and result[0]:
            return {
                'avg_volume': float(result[0]),
                'std_volume': float(result[1]) if result[1] else 0
            }
        return None
    
    def get_pattern_statistics(self) -> pd.DataFrame:
        """Get statistics on how different volume patterns perform."""
        
        query = """
            SELECT 
                CASE 
                    WHEN day_return >= 3 THEN 'Breakout (>3%)'
                    WHEN day_return <= -3 THEN 'Breakdown (<-3%)'
                    WHEN day_return >= 2 THEN 'Gap Up (2-3%)'
                    WHEN day_return <= -2 THEN 'Gap Down (-2 to -3%)'
                    ELSE 'Neutral (-2% to 2%)'
                END as pattern,
                COUNT(*) as events,
                ROUND(AVG(return_1d), 2) as avg_1d,
                ROUND(AVG(return_1w), 2) as avg_1w,
                ROUND(AVG(return_1m), 2) as avg_1m,
                ROUND(SUM(CASE WHEN return_1m > 0 THEN 1 ELSE 0 END) * 100.0 / 
                      SUM(CASE WHEN return_1m IS NOT NULL THEN 1 ELSE 0 END), 1) as win_rate_1m
            FROM volume_cluster_events
            WHERE volume_quintile = 'Very High'
            AND return_1m IS NOT NULL
            GROUP BY pattern
            ORDER BY avg_1m DESC
        """
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(query), conn)
        
        return df


def print_recent_events(events: List[RecentVolumeEvent], title: str = "Recent High Volume Events"):
    """Pretty print recent events."""
    print(f"\n{'='*80}")
    print(f" {title}")
    print(f"{'='*80}")
    
    if not events:
        print("No events found.")
        return
    
    print(f"{'Symbol':<15} {'Date':<12} {'Pattern':<12} {'Day%':>8} {'RelVol':>8} {'Since':>8} {'Ret%':>8}")
    print("-" * 80)
    
    for e in events:
        ret_str = f"{e.return_since_event:+.1f}%" if e.return_since_event else "N/A"
        print(f"{e.symbol:<15} {str(e.event_date)[:10]:<12} {e.pattern:<12} "
              f"{e.day_return:>+7.1f}% {e.relative_volume:>7.1f}x {e.days_since_event:>6}d {ret_str:>8}")


def print_alerts(alerts: List[VolumeAlert]):
    """Pretty print alerts."""
    print(f"\n{'='*80}")
    print(f" VOLUME ALERTS")
    print(f"{'='*80}")
    
    if not alerts:
        print("No alerts.")
        return
    
    for alert in alerts:
        icon = "🔴" if alert.priority == 'high' else "🟡" if alert.priority == 'medium' else "🟢"
        print(f"{icon} {alert.message}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Volume Event Scanner')
    parser.add_argument('--days', type=int, default=5, help='Days to look back')
    parser.add_argument('--breakouts', action='store_true', help='Show only breakouts')
    parser.add_argument('--breakdowns', action='store_true', help='Show only breakdowns')
    parser.add_argument('--leaders', action='store_true', help='Show volume leaders')
    parser.add_argument('--alerts', action='store_true', help='Check for alerts')
    parser.add_argument('--patterns', action='store_true', help='Show pattern statistics')
    parser.add_argument('--ultra', action='store_true', help='Show only Ultra High (4x+) events')
    args = parser.parse_args()
    
    scanner = VolumeEventScanner()
    
    if args.patterns:
        print("\nPattern Performance Statistics (Very High Volume Events):")
        print(scanner.get_pattern_statistics().to_string(index=False))
    elif args.breakouts:
        events = scanner.scan_breakouts(days=args.days)
        print_recent_events(events, "BREAKOUT Events (High Volume + Strong Up Move)")
    elif args.breakdowns:
        events = scanner.scan_breakdowns(days=args.days)
        print_recent_events(events, "BREAKDOWN Events (High Volume + Strong Down Move)")
    elif args.leaders:
        events = scanner.get_volume_leaders(days=args.days)
        print_recent_events(events, f"Top 20 Volume Leaders (Last {args.days} Days)")
    elif args.alerts:
        alerts = scanner.scan_for_alerts()
        print_alerts(alerts)
    elif args.ultra:
        events = scanner.scan_recent_events(days=args.days, quintile='Ultra High')
        print_recent_events(events, f"🔥 ULTRA HIGH Volume Events (4x+) (Last {args.days} Days)")
    else:
        events = scanner.scan_recent_events(days=args.days)
        print_recent_events(events, f"Very High Volume Events (Last {args.days} Days)")
