#!/usr/bin/env python3
"""
Volume Alert System
===================
Monitors for high volume events and sends alerts.
Can run as a background service or be triggered manually.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
import json
import time
import threading
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Alert storage file
ALERTS_FILE = Path(__file__).parent / "output" / "volume_alerts.json"


@dataclass
class VolumeAlert:
    """High volume alert."""
    id: str
    symbol: str
    event_date: str
    alert_type: str  # 'very_high_volume', 'breakout', 'breakdown', 'accumulation', 'distribution'
    volume: int
    relative_volume: float
    day_return: float
    close_price: float
    message: str
    priority: str  # 'critical', 'high', 'medium', 'low'
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    acknowledged: bool = False
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'symbol': self.symbol,
            'event_date': self.event_date,
            'alert_type': self.alert_type,
            'volume': self.volume,
            'relative_volume': self.relative_volume,
            'day_return': self.day_return,
            'close_price': self.close_price,
            'message': self.message,
            'priority': self.priority,
            'created_at': self.created_at,
            'acknowledged': self.acknowledged,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'VolumeAlert':
        return cls(**data)


class VolumeAlertSystem:
    """
    Volume Alert System - Monitors and alerts on high volume events.
    
    Alert Types:
    - very_high_volume: Volume > 3x 20-day average
    - breakout: High volume + price up > 3%
    - breakdown: High volume + price down > 3%
    - accumulation: Consecutive high volume up days
    - distribution: Consecutive high volume down days
    """
    
    THRESHOLDS = {
        'ultra_high_volume': 4.0,  # 4x average volume (Ultra High)
        'very_high_volume': 3.0,   # 3x average volume
        'high_volume': 2.0,        # 2x average volume
        'breakout_return': 3.0,    # 3% price increase
        'breakdown_return': -3.0,  # 3% price decrease
    }
    
    def __init__(self, watchlist: List[str] = None):
        self.engine = self._create_engine()
        self.watchlist = watchlist or self._get_default_watchlist()
        self.alerts: List[VolumeAlert] = []
        self.callbacks: List[Callable] = []
        self._load_alerts()
    
    def _create_engine(self):
        """Create database engine."""
        password = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
        host = os.getenv('MYSQL_HOST', 'localhost')
        port = os.getenv('MYSQL_PORT', '3306')
        db = os.getenv('MYSQL_DB', 'marketdata')
        user = os.getenv('MYSQL_USER', 'root')
        return create_engine(f'mysql+pymysql://{user}:{password}@{host}:{port}/{db}', pool_pre_ping=True)
    
    def _get_default_watchlist(self) -> List[str]:
        """Get default watchlist (Nifty 50)."""
        query = "SELECT DISTINCT symbol FROM volume_cluster_events ORDER BY symbol"
        with self.engine.connect() as conn:
            result = conn.execute(text(query))
            return [row[0] for row in result]
    
    def _load_alerts(self):
        """Load existing alerts from file."""
        if ALERTS_FILE.exists():
            try:
                with open(ALERTS_FILE, 'r') as f:
                    data = json.load(f)
                    self.alerts = [VolumeAlert.from_dict(a) for a in data]
            except Exception as e:
                print(f"Warning: Could not load alerts: {e}")
                self.alerts = []
    
    def _save_alerts(self):
        """Save alerts to file."""
        ALERTS_FILE.parent.mkdir(exist_ok=True)
        with open(ALERTS_FILE, 'w') as f:
            json.dump([a.to_dict() for a in self.alerts], f, indent=2)
    
    def add_callback(self, callback: Callable[[VolumeAlert], None]):
        """Add callback to be notified of new alerts."""
        self.callbacks.append(callback)
    
    def _notify(self, alert: VolumeAlert):
        """Notify all callbacks of new alert."""
        for callback in self.callbacks:
            try:
                callback(alert)
            except Exception as e:
                print(f"Callback error: {e}")
    
    def check_for_alerts(self) -> List[VolumeAlert]:
        """Check for new volume alerts."""
        
        today = datetime.now().date()
        yesterday = today - timedelta(days=3)  # Look back 3 days for weekend coverage
        
        new_alerts = []
        
        for symbol in self.watchlist:
            alerts = self._check_symbol(symbol, yesterday)
            for alert in alerts:
                # Check if we already have this alert
                existing = [a for a in self.alerts if a.id == alert.id]
                if not existing:
                    self.alerts.append(alert)
                    new_alerts.append(alert)
                    self._notify(alert)
        
        if new_alerts:
            self._save_alerts()
        
        return new_alerts
    
    def _check_symbol(self, symbol: str, since_date) -> List[VolumeAlert]:
        """Check a single symbol for alerts."""
        
        # Get recent data
        query = """
            SELECT date, open, high, low, close, volume
            FROM yfinance_daily_quotes
            WHERE symbol = :symbol
            AND timeframe = 'daily'
            AND date >= :since_date
            ORDER BY date DESC
        """
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(query), conn, params={
                'symbol': symbol,
                'since_date': since_date.strftime('%Y-%m-%d')
            })
        
        if df.empty:
            return []
        
        # Get volume stats
        stats = self._get_volume_stats(symbol)
        if not stats or stats['avg_volume'] == 0:
            return []
        
        alerts = []
        
        for _, row in df.iterrows():
            rel_vol = row['volume'] / stats['avg_volume']
            day_return = ((row['close'] - row['open']) / row['open'] * 100) if row['open'] > 0 else 0
            
            alert = None
            
            # Check for ultra high volume (4x+)
            if rel_vol >= self.THRESHOLDS['ultra_high_volume']:
                # Check for breakout
                if day_return >= self.THRESHOLDS['breakout_return']:
                    alert = self._create_alert(
                        symbol=symbol,
                        row=row,
                        rel_vol=rel_vol,
                        day_return=day_return,
                        alert_type='breakout',
                        priority='critical',
                        message=f"🚀 BREAKOUT: {symbol} +{day_return:.1f}% on {rel_vol:.1f}x volume!"
                    )
                # Check for breakdown
                elif day_return <= self.THRESHOLDS['breakdown_return']:
                    alert = self._create_alert(
                        symbol=symbol,
                        row=row,
                        rel_vol=rel_vol,
                        day_return=day_return,
                        alert_type='breakdown',
                        priority='critical',
                        message=f"⚠️ BREAKDOWN: {symbol} {day_return:.1f}% on {rel_vol:.1f}x volume!"
                    )
                else:
                    alert = self._create_alert(
                        symbol=symbol,
                        row=row,
                        rel_vol=rel_vol,
                        day_return=day_return,
                        alert_type='ultra_high_volume',
                        priority='critical',
                        message=f"💥 {symbol}: ULTRA HIGH volume ({rel_vol:.1f}x), price {day_return:+.1f}%"
                    )
            # Check for very high volume (3x+)
            elif rel_vol >= self.THRESHOLDS['very_high_volume']:
                # Check for breakout
                if day_return >= self.THRESHOLDS['breakout_return']:
                    alert = self._create_alert(
                        symbol=symbol,
                        row=row,
                        rel_vol=rel_vol,
                        day_return=day_return,
                        alert_type='breakout',
                        priority='high',
                        message=f"🚀 BREAKOUT: {symbol} +{day_return:.1f}% on {rel_vol:.1f}x volume!"
                    )
                # Check for breakdown
                elif day_return <= self.THRESHOLDS['breakdown_return']:
                    alert = self._create_alert(
                        symbol=symbol,
                        row=row,
                        rel_vol=rel_vol,
                        day_return=day_return,
                        alert_type='breakdown',
                        priority='high',
                        message=f"⚠️ BREAKDOWN: {symbol} {day_return:.1f}% on {rel_vol:.1f}x volume!"
                    )
                else:
                    alert = self._create_alert(
                        symbol=symbol,
                        row=row,
                        rel_vol=rel_vol,
                        day_return=day_return,
                        alert_type='very_high_volume',
                        priority='high',
                        message=f"🔥 {symbol}: Very high volume ({rel_vol:.1f}x), price {day_return:+.1f}%"
                    )
            
            elif rel_vol >= self.THRESHOLDS['high_volume']:
                alert = self._create_alert(
                    symbol=symbol,
                    row=row,
                    rel_vol=rel_vol,
                    day_return=day_return,
                    alert_type='high_volume',
                    priority='medium',
                    message=f"📈 {symbol}: High volume ({rel_vol:.1f}x), price {day_return:+.1f}%"
                )
            
            if alert:
                alerts.append(alert)
        
        return alerts
    
    def _create_alert(self, symbol: str, row, rel_vol: float, day_return: float,
                      alert_type: str, priority: str, message: str) -> VolumeAlert:
        """Create a volume alert."""
        event_date = str(row['date'])[:10]
        alert_id = f"{symbol}_{event_date}_{alert_type}"
        
        return VolumeAlert(
            id=alert_id,
            symbol=symbol,
            event_date=event_date,
            alert_type=alert_type,
            volume=int(row['volume']),
            relative_volume=round(rel_vol, 2),
            day_return=round(day_return, 2),
            close_price=round(float(row['close']), 2),
            message=message,
            priority=priority
        )
    
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
    
    def get_unacknowledged_alerts(self) -> List[VolumeAlert]:
        """Get all unacknowledged alerts."""
        return [a for a in self.alerts if not a.acknowledged]
    
    def get_alerts_by_priority(self, priority: str) -> List[VolumeAlert]:
        """Get alerts by priority level."""
        return [a for a in self.alerts if a.priority == priority]
    
    def get_alerts_by_type(self, alert_type: str) -> List[VolumeAlert]:
        """Get alerts by type."""
        return [a for a in self.alerts if a.alert_type == alert_type]
    
    def get_recent_alerts(self, days: int = 3) -> List[VolumeAlert]:
        """Get alerts from the last N days."""
        cutoff = datetime.now() - timedelta(days=days)
        return [a for a in self.alerts 
                if datetime.fromisoformat(a.created_at) >= cutoff]
    
    def acknowledge_alert(self, alert_id: str):
        """Mark an alert as acknowledged."""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                self._save_alerts()
                return True
        return False
    
    def acknowledge_all(self):
        """Acknowledge all alerts."""
        for alert in self.alerts:
            alert.acknowledged = True
        self._save_alerts()
    
    def clear_old_alerts(self, days: int = 7):
        """Remove alerts older than N days."""
        cutoff = datetime.now() - timedelta(days=days)
        self.alerts = [a for a in self.alerts 
                       if datetime.fromisoformat(a.created_at) >= cutoff]
        self._save_alerts()
    
    def get_summary(self) -> Dict:
        """Get alert summary statistics."""
        recent = self.get_recent_alerts(days=3)
        return {
            'total_alerts': len(self.alerts),
            'unacknowledged': len(self.get_unacknowledged_alerts()),
            'recent_3d': len(recent),
            'critical': len([a for a in recent if a.priority == 'critical']),
            'high': len([a for a in recent if a.priority == 'high']),
            'medium': len([a for a in recent if a.priority == 'medium']),
            'breakouts': len([a for a in recent if a.alert_type == 'breakout']),
            'breakdowns': len([a for a in recent if a.alert_type == 'breakdown']),
        }


def print_alert_summary(system: VolumeAlertSystem):
    """Print alert summary."""
    summary = system.get_summary()
    
    print("\n" + "="*60)
    print(" VOLUME ALERT SUMMARY")
    print("="*60)
    print(f" Total Alerts:     {summary['total_alerts']}")
    print(f" Unacknowledged:   {summary['unacknowledged']}")
    print(f" Last 3 Days:      {summary['recent_3d']}")
    print("-"*60)
    print(f" 🔴 Critical:      {summary['critical']}")
    print(f" 🟠 High:          {summary['high']}")
    print(f" 🟡 Medium:        {summary['medium']}")
    print("-"*60)
    print(f" 🚀 Breakouts:     {summary['breakouts']}")
    print(f" ⚠️ Breakdowns:    {summary['breakdowns']}")
    print("="*60)


def print_alerts(alerts: List[VolumeAlert], title: str = "Alerts"):
    """Print alerts in formatted output."""
    print(f"\n{title}")
    print("-"*80)
    
    if not alerts:
        print("No alerts.")
        return
    
    priority_icons = {
        'critical': '🔴',
        'high': '🟠',
        'medium': '🟡',
        'low': '🟢'
    }
    
    for alert in alerts:
        icon = priority_icons.get(alert.priority, '⚪')
        ack = "✓" if alert.acknowledged else " "
        print(f"[{ack}] {icon} {alert.message}")
        print(f"      Date: {alert.event_date} | Vol: {alert.volume:,} ({alert.relative_volume}x)")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Volume Alert System')
    parser.add_argument('--check', action='store_true', help='Check for new alerts')
    parser.add_argument('--summary', action='store_true', help='Show alert summary')
    parser.add_argument('--recent', action='store_true', help='Show recent alerts')
    parser.add_argument('--breakouts', action='store_true', help='Show breakout alerts')
    parser.add_argument('--ack-all', action='store_true', help='Acknowledge all alerts')
    parser.add_argument('--clear', type=int, help='Clear alerts older than N days')
    args = parser.parse_args()
    
    system = VolumeAlertSystem()
    
    if args.check:
        print("Checking for new alerts...")
        new_alerts = system.check_for_alerts()
        if new_alerts:
            print(f"\n🔔 {len(new_alerts)} NEW ALERTS!")
            print_alerts(new_alerts, "New Alerts")
        else:
            print("No new alerts.")
        print_alert_summary(system)
    
    elif args.summary:
        print_alert_summary(system)
    
    elif args.recent:
        alerts = system.get_recent_alerts(days=3)
        print_alerts(alerts, "Recent Alerts (Last 3 Days)")
    
    elif args.breakouts:
        alerts = system.get_alerts_by_type('breakout')
        print_alerts(alerts, "Breakout Alerts")
    
    elif args.ack_all:
        system.acknowledge_all()
        print("All alerts acknowledged.")
    
    elif args.clear:
        system.clear_old_alerts(days=args.clear)
        print(f"Cleared alerts older than {args.clear} days.")
    
    else:
        # Default: check and show summary
        system.check_for_alerts()
        print_alert_summary(system)
        
        unack = system.get_unacknowledged_alerts()
        if unack:
            print_alerts(unack[:10], "Unacknowledged Alerts (Top 10)")
