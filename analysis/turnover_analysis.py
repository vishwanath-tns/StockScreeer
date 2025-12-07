#!/usr/bin/env python3
"""
Turnover Analysis Tool
======================
Calculates daily, weekly, and monthly turnover using Yahoo Finance data.

Turnover = Close Price × Volume (in Crores for readability)

Features:
- Daily turnover with moving averages
- Weekly aggregated turnover
- Monthly aggregated turnover
- Unusual turnover detection
- Top turnover stocks scanner
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

# Constants
CRORE = 10_000_000  # 1 Crore = 10 Million


@dataclass
class TurnoverStats:
    """Turnover statistics for a symbol."""
    symbol: str
    period: str  # 'daily', 'weekly', 'monthly'
    date: datetime
    turnover: float  # In Crores
    turnover_avg_20: float
    turnover_avg_50: float
    relative_turnover: float  # vs 20-day avg
    volume: int
    close_price: float
    price_change_pct: float


class TurnoverAnalyzer:
    """Analyzes stock turnover patterns."""
    
    def __init__(self):
        """Initialize the turnover analyzer."""
        password = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
        self.engine = create_engine(
            f"mysql+pymysql://{os.getenv('MYSQL_USER', 'root')}:{password}"
            f"@{os.getenv('MYSQL_HOST', 'localhost')}:{os.getenv('MYSQL_PORT', '3306')}"
            f"/{os.getenv('MYSQL_DB', 'marketdata')}?charset=utf8mb4",
            pool_pre_ping=True
        )
    
    def get_daily_turnover(self, symbol: str, days: int = 252) -> pd.DataFrame:
        """
        Get daily turnover for a symbol.
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE.NS')
            days: Number of days to fetch
            
        Returns:
            DataFrame with daily turnover data
        """
        query = text("""
            SELECT 
                date,
                open, high, low, close, volume
            FROM yfinance_daily_quotes
            WHERE symbol = :symbol 
            AND timeframe = 'daily'
            ORDER BY date DESC
            LIMIT :days
        """)
        
        with self.engine.connect() as conn:
            df = pd.read_sql(query, conn, params={'symbol': symbol, 'days': days})
        
        if df.empty:
            return df
        
        # Sort ascending for calculations
        df = df.sort_values('date').reset_index(drop=True)
        df['date'] = pd.to_datetime(df['date'])
        
        # Calculate turnover (in Crores)
        df['turnover'] = (df['close'] * df['volume']) / CRORE
        
        # Moving averages of turnover
        df['turnover_avg_5'] = df['turnover'].rolling(5).mean()
        df['turnover_avg_10'] = df['turnover'].rolling(10).mean()
        df['turnover_avg_20'] = df['turnover'].rolling(20).mean()
        df['turnover_avg_50'] = df['turnover'].rolling(50).mean()
        
        # Relative turnover (vs 20-day average)
        df['relative_turnover'] = df['turnover'] / df['turnover_avg_20']
        
        # Price change
        df['prev_close'] = df['close'].shift(1)
        df['price_change'] = df['close'] - df['prev_close']
        df['price_change_pct'] = (df['price_change'] / df['prev_close']) * 100
        
        # Volume averages
        df['volume_avg_20'] = df['volume'].rolling(20).mean()
        df['relative_volume'] = df['volume'] / df['volume_avg_20']
        
        return df
    
    def get_weekly_turnover(self, symbol: str, weeks: int = 52) -> pd.DataFrame:
        """
        Get weekly aggregated turnover for a symbol.
        
        Args:
            symbol: Stock symbol
            weeks: Number of weeks to fetch
            
        Returns:
            DataFrame with weekly turnover data
        """
        # Get enough daily data
        df = self.get_daily_turnover(symbol, days=weeks * 7)
        
        if df.empty:
            return df
        
        # Set date as index for resampling
        df.set_index('date', inplace=True)
        
        # Resample to weekly (Friday close)
        weekly = df.resample('W-FRI').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
            'turnover': 'sum'
        }).dropna()
        
        weekly = weekly.reset_index()
        
        # Calculate weekly averages
        weekly['turnover_avg_4'] = weekly['turnover'].rolling(4).mean()
        weekly['turnover_avg_12'] = weekly['turnover'].rolling(12).mean()
        weekly['relative_turnover'] = weekly['turnover'] / weekly['turnover_avg_4']
        
        # Weekly price change
        weekly['prev_close'] = weekly['close'].shift(1)
        weekly['price_change_pct'] = ((weekly['close'] - weekly['prev_close']) / weekly['prev_close']) * 100
        
        return weekly
    
    def get_monthly_turnover(self, symbol: str, months: int = 24) -> pd.DataFrame:
        """
        Get monthly aggregated turnover for a symbol.
        
        Args:
            symbol: Stock symbol
            months: Number of months to fetch
            
        Returns:
            DataFrame with monthly turnover data
        """
        # Get enough daily data
        df = self.get_daily_turnover(symbol, days=months * 25)
        
        if df.empty:
            return df
        
        # Set date as index for resampling
        df.set_index('date', inplace=True)
        
        # Resample to monthly (month end)
        monthly = df.resample('ME').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
            'turnover': 'sum'
        }).dropna()
        
        monthly = monthly.reset_index()
        
        # Calculate monthly averages
        monthly['turnover_avg_3'] = monthly['turnover'].rolling(3).mean()
        monthly['turnover_avg_6'] = monthly['turnover'].rolling(6).mean()
        monthly['turnover_avg_12'] = monthly['turnover'].rolling(12).mean()
        monthly['relative_turnover'] = monthly['turnover'] / monthly['turnover_avg_3']
        
        # Monthly price change
        monthly['prev_close'] = monthly['close'].shift(1)
        monthly['price_change_pct'] = ((monthly['close'] - monthly['prev_close']) / monthly['prev_close']) * 100
        
        return monthly
    
    def get_top_turnover_stocks(self, date: str = None, top_n: int = 20) -> pd.DataFrame:
        """
        Get stocks with highest turnover on a given date.
        
        Args:
            date: Date string (YYYY-MM-DD), defaults to latest
            top_n: Number of top stocks to return
            
        Returns:
            DataFrame with top turnover stocks
        """
        if date is None:
            date_clause = "(SELECT MAX(date) FROM yfinance_daily_quotes WHERE timeframe = 'daily')"
        else:
            date_clause = f"'{date}'"
        
        query = text(f"""
            SELECT 
                symbol,
                date,
                close,
                volume,
                (close * volume) / 10000000 as turnover_cr
            FROM yfinance_daily_quotes
            WHERE timeframe = 'daily'
            AND date = {date_clause}
            AND volume > 0
            ORDER BY turnover_cr DESC
            LIMIT :top_n
        """)
        
        with self.engine.connect() as conn:
            df = pd.read_sql(query, conn, params={'top_n': top_n})
        
        return df
    
    def get_unusual_turnover(self, days: int = 5, threshold: float = 2.0) -> pd.DataFrame:
        """
        Find stocks with unusual turnover (significantly above average).
        
        Args:
            days: Look back period
            threshold: Minimum relative turnover (e.g., 2.0 = 2x average)
            
        Returns:
            DataFrame with unusual turnover stocks
        """
        query = text("""
            WITH daily_data AS (
                SELECT 
                    symbol,
                    date,
                    close,
                    volume,
                    (close * volume) / 10000000 as turnover_cr
                FROM yfinance_daily_quotes
                WHERE timeframe = 'daily'
                AND date >= DATE_SUB(CURDATE(), INTERVAL 60 DAY)
                AND volume > 0
            ),
            turnover_stats AS (
                SELECT 
                    symbol,
                    date,
                    close,
                    volume,
                    turnover_cr,
                    AVG(turnover_cr) OVER (
                        PARTITION BY symbol 
                        ORDER BY date 
                        ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING
                    ) as avg_turnover_20d
                FROM daily_data
            )
            SELECT 
                symbol,
                date,
                close,
                volume,
                turnover_cr,
                avg_turnover_20d,
                CASE WHEN avg_turnover_20d > 0 
                     THEN turnover_cr / avg_turnover_20d 
                     ELSE 0 END as relative_turnover
            FROM turnover_stats
            WHERE date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
            AND avg_turnover_20d > 0
            AND turnover_cr / avg_turnover_20d >= :threshold
            ORDER BY relative_turnover DESC
        """)
        
        with self.engine.connect() as conn:
            df = pd.read_sql(query, conn, params={'days': days, 'threshold': threshold})
        
        return df
    
    def get_turnover_summary(self, symbol: str) -> Dict:
        """
        Get comprehensive turnover summary for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with turnover summary
        """
        daily = self.get_daily_turnover(symbol, days=252)
        
        if daily.empty:
            return {'error': f'No data found for {symbol}'}
        
        latest = daily.iloc[-1]
        
        # Daily stats
        daily_turnover = latest['turnover']
        daily_avg_20 = latest['turnover_avg_20'] if pd.notna(latest['turnover_avg_20']) else 0
        daily_avg_50 = latest['turnover_avg_50'] if pd.notna(latest['turnover_avg_50']) else 0
        
        # Weekly stats (last 4 weeks)
        last_4_weeks = daily.tail(20)
        weekly_avg = last_4_weeks['turnover'].sum() / 4 if len(last_4_weeks) >= 20 else 0
        
        # Monthly stats (last month ~21 trading days)
        last_month = daily.tail(21)
        monthly_total = last_month['turnover'].sum() if len(last_month) >= 21 else 0
        
        # Yearly stats
        yearly_total = daily['turnover'].sum()
        yearly_avg_daily = daily['turnover'].mean()
        
        return {
            'symbol': symbol,
            'date': str(latest['date'].date()),
            'close_price': float(latest['close']),
            'daily': {
                'turnover_cr': round(daily_turnover, 2),
                'avg_20d_cr': round(daily_avg_20, 2),
                'avg_50d_cr': round(daily_avg_50, 2),
                'relative_turnover': round(latest['relative_turnover'], 2) if pd.notna(latest['relative_turnover']) else 0,
            },
            'weekly': {
                'avg_turnover_cr': round(weekly_avg, 2),
            },
            'monthly': {
                'total_turnover_cr': round(monthly_total, 2),
            },
            'yearly': {
                'total_turnover_cr': round(yearly_total, 2),
                'avg_daily_cr': round(yearly_avg_daily, 2),
            }
        }
    
    def print_daily_report(self, symbol: str, days: int = 20):
        """Print formatted daily turnover report."""
        df = self.get_daily_turnover(symbol, days)
        
        if df.empty:
            print(f"No data found for {symbol}")
            return
        
        print(f"\n{'='*80}")
        print(f" DAILY TURNOVER REPORT: {symbol}")
        print(f"{'='*80}")
        print(f"{'Date':<12} {'Close':>10} {'Volume':>15} {'Turnover(Cr)':>14} {'RelTurn':>8} {'Day%':>8}")
        print(f"{'-'*80}")
        
        for _, row in df.tail(days).iterrows():
            rel_turn = f"{row['relative_turnover']:.2f}x" if pd.notna(row['relative_turnover']) else "N/A"
            day_chg = f"{row['price_change_pct']:+.2f}%" if pd.notna(row['price_change_pct']) else "N/A"
            
            print(f"{str(row['date'].date()):<12} {row['close']:>10.2f} {row['volume']:>15,} "
                  f"{row['turnover']:>14.2f} {rel_turn:>8} {day_chg:>8}")
        
        # Summary
        recent = df.tail(days)
        print(f"{'-'*80}")
        print(f"{'AVERAGES':<12} {'':<10} {'':<15} "
              f"{recent['turnover'].mean():>14.2f} {'':<8} {'':<8}")
        print(f"{'='*80}")
    
    def print_weekly_report(self, symbol: str, weeks: int = 12):
        """Print formatted weekly turnover report."""
        df = self.get_weekly_turnover(symbol, weeks)
        
        if df.empty:
            print(f"No data found for {symbol}")
            return
        
        print(f"\n{'='*80}")
        print(f" WEEKLY TURNOVER REPORT: {symbol}")
        print(f"{'='*80}")
        print(f"{'Week Ending':<12} {'Close':>10} {'Volume':>15} {'Turnover(Cr)':>14} {'RelTurn':>8} {'Week%':>8}")
        print(f"{'-'*80}")
        
        for _, row in df.tail(weeks).iterrows():
            rel_turn = f"{row['relative_turnover']:.2f}x" if pd.notna(row['relative_turnover']) else "N/A"
            week_chg = f"{row['price_change_pct']:+.2f}%" if pd.notna(row['price_change_pct']) else "N/A"
            
            print(f"{str(row['date'].date()):<12} {row['close']:>10.2f} {row['volume']:>15,} "
                  f"{row['turnover']:>14.2f} {rel_turn:>8} {week_chg:>8}")
        
        print(f"{'='*80}")
    
    def print_monthly_report(self, symbol: str, months: int = 12):
        """Print formatted monthly turnover report."""
        df = self.get_monthly_turnover(symbol, months)
        
        if df.empty:
            print(f"No data found for {symbol}")
            return
        
        print(f"\n{'='*80}")
        print(f" MONTHLY TURNOVER REPORT: {symbol}")
        print(f"{'='*80}")
        print(f"{'Month':<12} {'Close':>10} {'Volume':>15} {'Turnover(Cr)':>14} {'RelTurn':>8} {'Month%':>8}")
        print(f"{'-'*80}")
        
        for _, row in df.tail(months).iterrows():
            rel_turn = f"{row['relative_turnover']:.2f}x" if pd.notna(row['relative_turnover']) else "N/A"
            month_chg = f"{row['price_change_pct']:+.2f}%" if pd.notna(row['price_change_pct']) else "N/A"
            month_str = row['date'].strftime('%Y-%m')
            
            print(f"{month_str:<12} {row['close']:>10.2f} {row['volume']:>15,} "
                  f"{row['turnover']:>14.2f} {rel_turn:>8} {month_chg:>8}")
        
        # Summary
        print(f"{'-'*80}")
        print(f"{'TOTAL':<12} {'':<10} {df['volume'].sum():>15,} "
              f"{df['turnover'].sum():>14.2f}")
        print(f"{'='*80}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Turnover Analysis Tool')
    parser.add_argument('symbol', nargs='?', default='RELIANCE.NS', help='Stock symbol')
    parser.add_argument('--daily', action='store_true', help='Show daily report')
    parser.add_argument('--weekly', action='store_true', help='Show weekly report')
    parser.add_argument('--monthly', action='store_true', help='Show monthly report')
    parser.add_argument('--summary', action='store_true', help='Show summary')
    parser.add_argument('--top', type=int, help='Show top N turnover stocks')
    parser.add_argument('--unusual', action='store_true', help='Show unusual turnover stocks')
    parser.add_argument('--days', type=int, default=20, help='Number of days/periods')
    args = parser.parse_args()
    
    analyzer = TurnoverAnalyzer()
    
    if args.top:
        print(f"\n{'='*70}")
        print(f" TOP {args.top} STOCKS BY TURNOVER")
        print(f"{'='*70}")
        df = analyzer.get_top_turnover_stocks(top_n=args.top)
        print(f"{'Symbol':<20} {'Close':>10} {'Volume':>15} {'Turnover(Cr)':>14}")
        print(f"{'-'*70}")
        for _, row in df.iterrows():
            print(f"{row['symbol']:<20} {row['close']:>10.2f} {row['volume']:>15,} {row['turnover_cr']:>14.2f}")
    
    elif args.unusual:
        print(f"\n{'='*80}")
        print(f" UNUSUAL TURNOVER STOCKS (Last {args.days} Days, >2x Average)")
        print(f"{'='*80}")
        df = analyzer.get_unusual_turnover(days=args.days)
        if df.empty:
            print("No unusual turnover found.")
        else:
            print(f"{'Symbol':<15} {'Date':<12} {'Turnover(Cr)':>12} {'Avg(Cr)':>10} {'Relative':>10}")
            print(f"{'-'*80}")
            for _, row in df.head(30).iterrows():
                print(f"{row['symbol']:<15} {str(row['date'])[:10]:<12} "
                      f"{row['turnover_cr']:>12.2f} {row['avg_turnover_20d']:>10.2f} "
                      f"{row['relative_turnover']:>9.2f}x")
    
    elif args.summary:
        summary = analyzer.get_turnover_summary(args.symbol)
        print(f"\n{'='*60}")
        print(f" TURNOVER SUMMARY: {args.symbol}")
        print(f"{'='*60}")
        print(f" Date: {summary['date']}")
        print(f" Close: ₹{summary['close_price']:.2f}")
        print(f"\n DAILY:")
        print(f"   Today's Turnover:  ₹{summary['daily']['turnover_cr']:.2f} Cr")
        print(f"   20-Day Average:    ₹{summary['daily']['avg_20d_cr']:.2f} Cr")
        print(f"   50-Day Average:    ₹{summary['daily']['avg_50d_cr']:.2f} Cr")
        print(f"   Relative Turnover: {summary['daily']['relative_turnover']:.2f}x")
        print(f"\n WEEKLY:")
        print(f"   Avg Weekly:        ₹{summary['weekly']['avg_turnover_cr']:.2f} Cr")
        print(f"\n MONTHLY:")
        print(f"   Last Month Total:  ₹{summary['monthly']['total_turnover_cr']:.2f} Cr")
        print(f"\n YEARLY (TTM):")
        print(f"   Total Turnover:    ₹{summary['yearly']['total_turnover_cr']:.2f} Cr")
        print(f"   Avg Daily:         ₹{summary['yearly']['avg_daily_cr']:.2f} Cr")
        print(f"{'='*60}")
    
    elif args.weekly:
        analyzer.print_weekly_report(args.symbol, args.days)
    
    elif args.monthly:
        analyzer.print_monthly_report(args.symbol, args.days)
    
    else:
        # Default: daily report
        analyzer.print_daily_report(args.symbol, args.days)


if __name__ == '__main__':
    main()
