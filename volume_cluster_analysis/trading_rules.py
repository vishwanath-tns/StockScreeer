#!/usr/bin/env python3
"""
Volume-Based Trading Rules Engine
=================================
Generates actionable trading signals based on volume events and patterns.

Key Rules:
1. Volume Breakout Buy - High volume + positive price + above key MAs
2. Volume Breakdown Short/Avoid - High volume + negative price + below MAs
3. Accumulation Confirmed - Multiple high volume up days in sequence
4. Distribution Warning - Multiple high volume down days
5. Climax/Exhaustion - Extreme volume often signals reversal
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

load_dotenv()


class SignalType(Enum):
    """Trading signal types."""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    WATCH = "watch"
    HOLD = "hold"
    REDUCE = "reduce"
    SELL = "sell"
    AVOID = "avoid"


class SignalConfidence(Enum):
    """Signal confidence levels."""
    HIGH = "high"      # Multiple confirming factors, >65% historical win rate
    MEDIUM = "medium"  # Some confirming factors, 55-65% win rate
    LOW = "low"        # Single factor, <55% win rate


@dataclass
class TradingSignal:
    """A trading signal generated from volume analysis."""
    symbol: str
    signal_date: datetime
    signal_type: SignalType
    confidence: SignalConfidence
    
    # Signal details
    pattern: str
    entry_price: float
    
    # Risk management
    stop_loss: float
    target_1: float
    target_2: float
    risk_reward: float
    
    # Context
    volume: int
    relative_volume: float
    day_return: float
    volume_quintile: str
    
    # Historical edge
    historical_win_rate: float
    historical_avg_return: float
    sample_size: int
    
    # Reasoning
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class RulePerformance:
    """Performance metrics for a trading rule."""
    rule_name: str
    total_signals: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_winner: float
    avg_loser: float
    expectancy: float  # (win_rate * avg_win) - (loss_rate * avg_loss)
    profit_factor: float  # gross_profit / gross_loss
    max_drawdown: float
    best_stock: str
    worst_stock: str


class TradingRulesEngine:
    """
    Engine for generating trading signals based on volume events.
    
    Rules are based on:
    1. Volume-price patterns with proven edge
    2. Technical context (trend, support/resistance)
    3. Historical performance of similar setups
    """
    
    # Rule definitions with entry/exit criteria
    RULES = {
        'volume_breakout_buy': {
            'name': 'Volume Breakout Buy',
            'description': 'Buy when stock breaks out on high volume',
            'entry_criteria': {
                'min_relative_volume': 2.0,
                'min_day_return': 2.0,
                'volume_quintile': ['Very High', 'Ultra High'],
                'prefer_above_sma_20': True,
            },
            'exit_criteria': {
                'stop_loss_pct': -5.0,
                'target_1_pct': 5.0,
                'target_2_pct': 10.0,
                'trailing_stop': -3.0,
            },
            'historical_edge': {
                'win_rate': 0.60,
                'avg_return_1w': 2.5,
            }
        },
        'ultra_volume_breakout': {
            'name': 'Ultra High Volume Breakout',
            'description': 'Very strong buy on 4x+ volume breakout',
            'entry_criteria': {
                'min_relative_volume': 4.0,
                'min_day_return': 3.0,
                'volume_quintile': ['Ultra High'],
            },
            'exit_criteria': {
                'stop_loss_pct': -4.0,
                'target_1_pct': 8.0,
                'target_2_pct': 15.0,
                'trailing_stop': -3.0,
            },
            'historical_edge': {
                'win_rate': 0.65,
                'avg_return_1w': 4.0,
            }
        },
        'accumulation_buy': {
            'name': 'Accumulation Day Buy',
            'description': 'Buy on high volume up day closing in upper range',
            'entry_criteria': {
                'min_relative_volume': 1.5,
                'min_day_return': 0.5,
                'close_in_upper_half': True,
                'volume_quintile': ['High', 'Very High', 'Ultra High'],
            },
            'exit_criteria': {
                'stop_loss_pct': -4.0,
                'target_1_pct': 4.0,
                'target_2_pct': 8.0,
            },
            'historical_edge': {
                'win_rate': 0.58,
                'avg_return_1w': 1.8,
            }
        },
        'gap_up_continuation': {
            'name': 'Gap Up on Volume',
            'description': 'Buy continuation after gap up on high volume',
            'entry_criteria': {
                'min_relative_volume': 2.0,
                'min_gap_pct': 2.0,
                'volume_quintile': ['High', 'Very High', 'Ultra High'],
            },
            'exit_criteria': {
                'stop_loss_pct': -3.0,
                'target_1_pct': 5.0,
                'target_2_pct': 10.0,
            },
            'historical_edge': {
                'win_rate': 0.55,
                'avg_return_1w': 2.3,
            }
        },
        'climax_top_warning': {
            'name': 'Climax Top Warning',
            'description': 'Reduce/avoid after extreme volume spike at highs',
            'entry_criteria': {
                'min_relative_volume': 3.5,
                'near_52w_high': True,
                'wide_range': True,
            },
            'action': 'reduce',
            'historical_edge': {
                'pullback_probability': 0.65,
                'avg_pullback': -3.5,
            }
        },
        'breakdown_avoid': {
            'name': 'Volume Breakdown Avoid',
            'description': 'Avoid/short when stock breaks down on volume',
            'entry_criteria': {
                'min_relative_volume': 2.0,
                'max_day_return': -3.0,
                'volume_quintile': ['Very High', 'Ultra High'],
            },
            'action': 'avoid',
            'historical_edge': {
                'continuation_probability': 0.60,
                'avg_decline_1w': -2.0,
            }
        },
        'distribution_warning': {
            'name': 'Distribution Day Warning',
            'description': 'Warning when institutions are distributing',
            'entry_criteria': {
                'min_relative_volume': 1.5,
                'max_day_return': -0.5,
                'close_in_lower_half': True,
            },
            'action': 'watch',
            'historical_edge': {
                'pullback_probability': 0.55,
            }
        },
        'capitulation_buy': {
            'name': 'Capitulation Buy',
            'description': 'Buy after extreme selling exhaustion',
            'entry_criteria': {
                'min_relative_volume': 4.0,
                'max_day_return': -5.0,
                'oversold': True,
            },
            'exit_criteria': {
                'stop_loss_pct': -8.0,
                'target_1_pct': 10.0,
                'target_2_pct': 20.0,
            },
            'historical_edge': {
                'bounce_probability': 0.70,
                'avg_bounce_1w': 5.0,
            }
        },
    }
    
    def __init__(self):
        """Initialize the trading rules engine."""
        password = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
        self.engine = create_engine(
            f"mysql+pymysql://{os.getenv('MYSQL_USER', 'root')}:{password}"
            f"@{os.getenv('MYSQL_HOST', 'localhost')}:{os.getenv('MYSQL_PORT', '3306')}"
            f"/{os.getenv('MYSQL_DB', 'marketdata')}?charset=utf8mb4",
            pool_pre_ping=True
        )
        
        # Load historical pattern performance
        self._load_pattern_stats()
    
    def _load_pattern_stats(self):
        """Load historical pattern performance from database."""
        query = """
        SELECT 
            volume_quintile,
            CASE 
                WHEN day_return >= 3 THEN 'breakout'
                WHEN day_return <= -3 THEN 'breakdown'
                WHEN day_return >= 0 THEN 'accumulation'
                ELSE 'distribution'
            END as pattern_type,
            COUNT(*) as sample_size,
            AVG(return_1d) as avg_return_1d,
            AVG(return_1w) as avg_return_1w,
            AVG(return_1m) as avg_return_1m,
            SUM(CASE WHEN return_1w > 0 THEN 1 ELSE 0 END) * 100.0 / 
                NULLIF(SUM(CASE WHEN return_1w IS NOT NULL THEN 1 ELSE 0 END), 0) as win_rate_1w
        FROM volume_cluster_events
        WHERE return_1w IS NOT NULL
        GROUP BY volume_quintile, pattern_type
        """
        
        try:
            with self.engine.connect() as conn:
                self.pattern_stats = pd.read_sql(text(query), conn)
        except Exception as e:
            print(f"Warning: Could not load pattern stats: {e}")
            self.pattern_stats = pd.DataFrame()
    
    def get_historical_edge(self, quintile: str, pattern_type: str) -> Dict:
        """Get historical performance for a pattern."""
        if self.pattern_stats.empty:
            return {'win_rate': 0.5, 'avg_return': 0, 'sample_size': 0}
        
        mask = (
            (self.pattern_stats['volume_quintile'] == quintile) &
            (self.pattern_stats['pattern_type'] == pattern_type)
        )
        
        if not mask.any():
            return {'win_rate': 0.5, 'avg_return': 0, 'sample_size': 0}
        
        row = self.pattern_stats[mask].iloc[0]
        return {
            'win_rate': row['win_rate_1w'] / 100 if pd.notna(row['win_rate_1w']) else 0.5,
            'avg_return': row['avg_return_1w'] if pd.notna(row['avg_return_1w']) else 0,
            'sample_size': int(row['sample_size'])
        }
    
    def generate_signals(self, days: int = 3) -> List[TradingSignal]:
        """Generate trading signals from recent volume events."""
        query = """
        SELECT 
            e.symbol, e.event_date, e.volume, e.volume_quintile,
            e.relative_volume, e.day_return, e.close_price,
            e.return_1d, e.return_1w, e.return_1m,
            q.open as open_price, q.high, q.low
        FROM volume_cluster_events e
        LEFT JOIN yfinance_daily_quotes q 
            ON e.symbol = q.symbol 
            AND e.event_date = q.date
            AND q.timeframe = 'daily'
        WHERE e.event_date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
        AND e.volume_quintile IN ('High', 'Very High', 'Ultra High')
        ORDER BY e.event_date DESC, e.relative_volume DESC
        """
        
        signals = []
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(query), conn, params={'days': days})
        
        for _, row in df.iterrows():
            signal = self._evaluate_event(row)
            if signal:
                signals.append(signal)
        
        # Sort by confidence and signal type
        signals.sort(key=lambda s: (
            s.confidence == SignalConfidence.HIGH,
            s.signal_type == SignalType.STRONG_BUY,
            s.relative_volume
        ), reverse=True)
        
        return signals
    
    def _evaluate_event(self, row) -> Optional[TradingSignal]:
        """Evaluate a volume event and generate appropriate signal."""
        symbol = row['symbol']
        quintile = row['volume_quintile']
        day_return = row['day_return']
        rel_vol = row['relative_volume']
        close = row['close_price']
        
        # Determine pattern type
        if day_return >= 3:
            pattern_type = 'breakout'
        elif day_return <= -3:
            pattern_type = 'breakdown'
        elif day_return >= 0:
            pattern_type = 'accumulation'
        else:
            pattern_type = 'distribution'
        
        # Get historical edge
        edge = self.get_historical_edge(quintile, pattern_type)
        
        # Calculate close position in day's range
        if row['high'] and row['low'] and row['high'] != row['low']:
            close_position = (close - row['low']) / (row['high'] - row['low'])
        else:
            close_position = 0.5
        
        # Apply rules
        signal = None
        reasons = []
        warnings = []
        
        # Rule 1: Ultra High Volume Breakout (Strong Buy)
        if quintile == 'Ultra High' and day_return >= 3:
            signal_type = SignalType.STRONG_BUY
            confidence = SignalConfidence.HIGH
            rule = self.RULES['ultra_volume_breakout']
            
            reasons.append(f"🔥 Ultra High volume ({rel_vol:.1f}x average)")
            reasons.append(f"📈 Strong breakout (+{day_return:.1f}%)")
            reasons.append(f"📊 Historical win rate: {edge['win_rate']*100:.0f}%")
            
            if close_position < 0.5:
                warnings.append("⚠️ Closed in lower half of range")
            
            signal = self._create_signal(
                row, signal_type, confidence, 'Ultra Volume Breakout',
                rule, edge, reasons, warnings
            )
        
        # Rule 2: Volume Breakout Buy (Buy)
        elif quintile in ['Very High', 'Ultra High'] and 2 <= day_return < 3:
            signal_type = SignalType.BUY
            confidence = SignalConfidence.MEDIUM if edge['win_rate'] >= 0.55 else SignalConfidence.LOW
            rule = self.RULES['volume_breakout_buy']
            
            reasons.append(f"📈 Volume breakout ({rel_vol:.1f}x, +{day_return:.1f}%)")
            reasons.append(f"📊 Historical win rate: {edge['win_rate']*100:.0f}%")
            
            signal = self._create_signal(
                row, signal_type, confidence, 'Volume Breakout',
                rule, edge, reasons, warnings
            )
        
        # Rule 3: Volume Breakdown Avoid
        elif quintile in ['Very High', 'Ultra High'] and day_return <= -3:
            signal_type = SignalType.AVOID
            confidence = SignalConfidence.HIGH if rel_vol >= 3 else SignalConfidence.MEDIUM
            rule = self.RULES['breakdown_avoid']
            
            reasons.append(f"⚠️ Heavy selling on {rel_vol:.1f}x volume")
            reasons.append(f"📉 Breakdown: {day_return:.1f}%")
            reasons.append("🔴 Avoid new positions")
            
            signal = self._create_signal(
                row, signal_type, confidence, 'Volume Breakdown',
                rule, edge, reasons, warnings
            )
        
        # Rule 4: Accumulation Day
        elif quintile in ['High', 'Very High'] and 0.5 <= day_return < 2 and close_position >= 0.6:
            signal_type = SignalType.BUY
            confidence = SignalConfidence.LOW
            rule = self.RULES['accumulation_buy']
            
            reasons.append(f"📈 Accumulation day ({rel_vol:.1f}x volume)")
            reasons.append(f"💪 Strong close in upper {(close_position*100):.0f}%")
            
            signal = self._create_signal(
                row, signal_type, confidence, 'Accumulation',
                rule, edge, reasons, warnings
            )
        
        # Rule 5: Capitulation (Extreme Selling) - Contrarian Buy
        elif quintile == 'Ultra High' and day_return <= -5:
            signal_type = SignalType.WATCH
            confidence = SignalConfidence.MEDIUM
            rule = self.RULES['capitulation_buy']
            
            reasons.append(f"💥 Potential capitulation ({rel_vol:.1f}x, {day_return:.1f}%)")
            reasons.append("⏳ Wait for stabilization before entry")
            warnings.append("⚠️ High risk - use smaller position size")
            
            signal = self._create_signal(
                row, signal_type, confidence, 'Capitulation',
                rule, edge, reasons, warnings
            )
        
        # Rule 6: Distribution Warning
        elif quintile in ['High', 'Very High'] and -2 <= day_return < -0.5 and close_position <= 0.4:
            signal_type = SignalType.REDUCE
            confidence = SignalConfidence.LOW
            rule = self.RULES['distribution_warning']
            
            reasons.append(f"⚠️ Distribution day ({rel_vol:.1f}x volume)")
            reasons.append(f"📉 Weak close in lower {((1-close_position)*100):.0f}%")
            
            signal = self._create_signal(
                row, signal_type, confidence, 'Distribution',
                rule, edge, reasons, warnings
            )
        
        return signal
    
    def _create_signal(self, row, signal_type: SignalType, confidence: SignalConfidence,
                       pattern: str, rule: Dict, edge: Dict, 
                       reasons: List[str], warnings: List[str]) -> TradingSignal:
        """Create a TradingSignal from event data."""
        close = row['close_price']
        
        # Get exit criteria from rule
        exit_criteria = rule.get('exit_criteria', {
            'stop_loss_pct': -5.0,
            'target_1_pct': 5.0,
            'target_2_pct': 10.0,
        })
        
        stop_loss = close * (1 + exit_criteria['stop_loss_pct'] / 100)
        target_1 = close * (1 + exit_criteria['target_1_pct'] / 100)
        target_2 = close * (1 + exit_criteria['target_2_pct'] / 100)
        
        risk = abs(close - stop_loss)
        reward = target_1 - close
        risk_reward = reward / risk if risk > 0 else 0
        
        return TradingSignal(
            symbol=row['symbol'],
            signal_date=row['event_date'],
            signal_type=signal_type,
            confidence=confidence,
            pattern=pattern,
            entry_price=close,
            stop_loss=round(stop_loss, 2),
            target_1=round(target_1, 2),
            target_2=round(target_2, 2),
            risk_reward=round(risk_reward, 2),
            volume=int(row['volume']),
            relative_volume=round(row['relative_volume'], 2),
            day_return=round(row['day_return'], 2),
            volume_quintile=row['volume_quintile'],
            historical_win_rate=round(edge['win_rate'] * 100, 1),
            historical_avg_return=round(edge['avg_return'], 2),
            sample_size=edge['sample_size'],
            reasons=reasons,
            warnings=warnings
        )
    
    def get_rule_performance(self, days: int = 90) -> List[RulePerformance]:
        """Calculate historical performance for each rule."""
        query = """
        SELECT 
            volume_quintile,
            day_return,
            relative_volume,
            return_1w,
            return_1m,
            symbol
        FROM volume_cluster_events
        WHERE event_date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
        AND return_1w IS NOT NULL
        """
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(query), conn, params={'days': days})
        
        if df.empty:
            return []
        
        performances = []
        
        # Evaluate each rule
        for rule_id, rule in self.RULES.items():
            entry = rule.get('entry_criteria', {})
            
            # Filter events matching this rule
            mask = pd.Series(True, index=df.index)
            
            if 'min_relative_volume' in entry:
                mask &= df['relative_volume'] >= entry['min_relative_volume']
            
            if 'min_day_return' in entry:
                mask &= df['day_return'] >= entry['min_day_return']
            
            if 'max_day_return' in entry:
                mask &= df['day_return'] <= entry['max_day_return']
            
            if 'volume_quintile' in entry:
                mask &= df['volume_quintile'].isin(entry['volume_quintile'])
            
            rule_df = df[mask]
            
            if len(rule_df) < 5:
                continue
            
            # Calculate performance
            winners = rule_df[rule_df['return_1w'] > 0]
            losers = rule_df[rule_df['return_1w'] <= 0]
            
            win_rate = len(winners) / len(rule_df) if len(rule_df) > 0 else 0
            avg_winner = winners['return_1w'].mean() if len(winners) > 0 else 0
            avg_loser = losers['return_1w'].mean() if len(losers) > 0 else 0
            
            expectancy = (win_rate * avg_winner) + ((1 - win_rate) * avg_loser)
            
            gross_profit = winners['return_1w'].sum() if len(winners) > 0 else 0
            gross_loss = abs(losers['return_1w'].sum()) if len(losers) > 0 else 1
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
            
            # Best/worst stocks
            by_stock = rule_df.groupby('symbol')['return_1w'].mean()
            best_stock = by_stock.idxmax() if len(by_stock) > 0 else 'N/A'
            worst_stock = by_stock.idxmin() if len(by_stock) > 0 else 'N/A'
            
            performances.append(RulePerformance(
                rule_name=rule['name'],
                total_signals=len(rule_df),
                winning_trades=len(winners),
                losing_trades=len(losers),
                win_rate=round(win_rate * 100, 1),
                avg_winner=round(avg_winner, 2),
                avg_loser=round(avg_loser, 2),
                expectancy=round(expectancy, 2),
                profit_factor=round(profit_factor, 2),
                max_drawdown=round(losers['return_1w'].min(), 2) if len(losers) > 0 else 0,
                best_stock=best_stock,
                worst_stock=worst_stock
            ))
        
        # Sort by expectancy
        performances.sort(key=lambda p: p.expectancy, reverse=True)
        
        return performances
    
    def print_signals(self, signals: List[TradingSignal]):
        """Print formatted trading signals."""
        if not signals:
            print("\n📭 No trading signals found.")
            return
        
        print("\n" + "=" * 80)
        print(" 📊 VOLUME-BASED TRADING SIGNALS")
        print("=" * 80)
        
        # Group by signal type
        buy_signals = [s for s in signals if s.signal_type in [SignalType.STRONG_BUY, SignalType.BUY]]
        watch_signals = [s for s in signals if s.signal_type == SignalType.WATCH]
        avoid_signals = [s for s in signals if s.signal_type in [SignalType.AVOID, SignalType.REDUCE]]
        
        if buy_signals:
            print("\n🟢 BUY SIGNALS")
            print("-" * 80)
            for s in buy_signals:
                self._print_signal(s)
        
        if watch_signals:
            print("\n🟡 WATCH LIST")
            print("-" * 80)
            for s in watch_signals:
                self._print_signal(s)
        
        if avoid_signals:
            print("\n🔴 AVOID / REDUCE")
            print("-" * 80)
            for s in avoid_signals:
                self._print_signal(s)
        
        print("\n" + "=" * 80)
        print(f"Total Signals: {len(signals)} | Buy: {len(buy_signals)} | Watch: {len(watch_signals)} | Avoid: {len(avoid_signals)}")
        print("=" * 80)
    
    def _print_signal(self, s: TradingSignal):
        """Print a single signal."""
        emoji = {
            SignalType.STRONG_BUY: "🚀",
            SignalType.BUY: "📈",
            SignalType.WATCH: "👀",
            SignalType.HOLD: "✋",
            SignalType.REDUCE: "📉",
            SignalType.SELL: "🔻",
            SignalType.AVOID: "⛔",
        }.get(s.signal_type, "❓")
        
        conf_emoji = {
            SignalConfidence.HIGH: "⭐⭐⭐",
            SignalConfidence.MEDIUM: "⭐⭐",
            SignalConfidence.LOW: "⭐",
        }.get(s.confidence, "")
        
        print(f"\n{emoji} {s.symbol} - {s.pattern} {conf_emoji}")
        print(f"   Date: {str(s.signal_date)[:10]} | Price: ₹{s.entry_price:.2f}")
        print(f"   Volume: {s.volume:,} ({s.relative_volume}x) | Day: {s.day_return:+.1f}%")
        
        if s.signal_type in [SignalType.STRONG_BUY, SignalType.BUY, SignalType.WATCH]:
            print(f"   Stop: ₹{s.stop_loss:.2f} | Target 1: ₹{s.target_1:.2f} | Target 2: ₹{s.target_2:.2f}")
            print(f"   Risk/Reward: 1:{s.risk_reward:.1f}")
        
        print(f"   Win Rate: {s.historical_win_rate:.0f}% | Avg Return: {s.historical_avg_return:+.1f}% (n={s.sample_size})")
        
        for reason in s.reasons:
            print(f"   ✓ {reason}")
        
        for warning in s.warnings:
            print(f"   {warning}")


def print_rule_performance(performances: List[RulePerformance]):
    """Print rule performance table."""
    print("\n" + "=" * 90)
    print(" 📈 TRADING RULE PERFORMANCE (Last 90 Days)")
    print("=" * 90)
    print(f"{'Rule Name':<30} {'Signals':>8} {'Win%':>7} {'Avg Win':>8} {'Avg Loss':>9} {'Expect':>8} {'PF':>6}")
    print("-" * 90)
    
    for p in performances:
        print(f"{p.rule_name:<30} {p.total_signals:>8} {p.win_rate:>6.1f}% {p.avg_winner:>7.2f}% {p.avg_loser:>8.2f}% {p.expectancy:>7.2f}% {p.profit_factor:>5.2f}")
    
    print("-" * 90)
    print("Expect = Expectancy per trade | PF = Profit Factor (gross profit / gross loss)")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Volume-Based Trading Rules')
    parser.add_argument('--days', type=int, default=3, help='Days to look back for signals')
    parser.add_argument('--performance', action='store_true', help='Show rule performance')
    parser.add_argument('--buy-only', action='store_true', help='Show only buy signals')
    args = parser.parse_args()
    
    engine = TradingRulesEngine()
    
    if args.performance:
        performances = engine.get_rule_performance(days=90)
        print_rule_performance(performances)
    else:
        signals = engine.generate_signals(days=args.days)
        
        if args.buy_only:
            signals = [s for s in signals if s.signal_type in [SignalType.STRONG_BUY, SignalType.BUY]]
        
        engine.print_signals(signals)


if __name__ == '__main__':
    main()
