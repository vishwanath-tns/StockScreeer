#!/usr/bin/env python3
"""
RSI Overbought/Oversold Analyzer
=================================

Analyzes RSI (9-period) values for NIFTY and NIFTY 50 stocks.
Uses daily data from marketdata database (yfinance_daily_rsi table).

Thresholds:
- Overbought: RSI >= 80
- Oversold: RSI <= 20
- Neutral: 20 < RSI < 80

Data Source:
- Table: yfinance_daily_rsi (populated by Daily Data Wizard)
- RSI Period: 9
- Timeframe: Daily

Usage:
    python rsi_overbought_oversold_analyzer.py

Author: StockScreener Project
Date: December 2025
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import logging
from tabulate import tabulate
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import mysql.connector
from mysql.connector import Error
from sqlalchemy import create_engine, text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

# RSI Thresholds
RSI_OVERBOUGHT = 80
RSI_OVERSOLD = 20

# NIFTY 50 symbols (as per database)
NIFTY_50_SYMBOLS = [
    'ADANIENT', 'ADANIPORTS', 'APOLLOHOSP', 'ASIANPAINT', 'AXISBANK',
    'BAJAJ-AUTO', 'BAJFINANCE', 'BAJAJFINSV', 'BEL', 'BPCL',
    'BHARTIARTL', 'BRITANNIA', 'CIPLA', 'COALINDIA', 'DRREDDY',
    'EICHERMOT', 'GRASIM', 'HCLTECH', 'HDFCBANK', 'HDFCLIFE',
    'HEROMOTOCO', 'HINDALCO', 'HINDUNILVR', 'ICICIBANK', 'ITC',
    'INDUSINDBK', 'INFY', 'JSWSTEEL', 'KOTAKBANK', 'LT',
    'M&M', 'MARUTI', 'NTPC', 'NESTLEIND', 'ONGC',
    'POWERGRID', 'RELIANCE', 'SBILIFE', 'SHRIRAMFIN', 'SBIN',
    'SUNPHARMA', 'TCS', 'TATACONSUM', 'TATAMOTORS', 'TATASTEEL',
    'TECHM', 'TITAN', 'TRENT', 'ULTRACEMCO', 'WIPRO'
]

# NIFTY 500 stocks (import from utilities)
try:
    from utilities.nifty500_stocks_list import NIFTY_500_STOCKS
except ImportError:
    logger.warning("Could not import NIFTY_500_STOCKS")
    NIFTY_500_STOCKS = []


# =============================================================================
# DATABASE SERVICE
# =============================================================================

class RSIAnalyzerDB:
    """Database service for RSI analysis"""
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DATABASE', 'marketdata'),
            'charset': 'utf8mb4'
        }
        self._engine = None
    
    def get_engine(self):
        """Get SQLAlchemy engine"""
        if self._engine is None:
            from urllib.parse import quote_plus
            password = quote_plus(self.db_config['password']) if self.db_config['password'] else ''
            conn_str = f"mysql+mysqlconnector://{self.db_config['user']}:{password}@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
            self._engine = create_engine(conn_str, echo=False)
        return self._engine
    
    def table_exists(self, table_name: str) -> bool:
        """Check if table exists"""
        engine = self.get_engine()
        try:
            with engine.connect() as conn:
                result = conn.execute(text(f"SHOW TABLES LIKE '{table_name}'"))
                return bool(result.fetchone())
        except Exception as e:
            logger.error(f"Error checking table: {e}")
            return False
    
    def get_latest_rsi_data(self, symbols: List[str], as_of_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get latest RSI data for given symbols.
        
        Args:
            symbols: List of symbols (without .NS suffix)
            as_of_date: Date to fetch data for (YYYY-MM-DD). If None, uses latest available date.
        
        Returns:
            DataFrame with columns: symbol, date, close, rsi_9
        """
        engine = self.get_engine()
        
        # Check if table exists
        if not self.table_exists('yfinance_daily_rsi'):
            logger.error("Table yfinance_daily_rsi does not exist")
            return pd.DataFrame()
        
        # Build symbol list for SQL
        symbol_placeholders = ', '.join([f"'{s}'" for s in symbols])
        
        if as_of_date:
            query = f"""
            SELECT symbol, date, close, rsi_9
            FROM yfinance_daily_rsi
            WHERE symbol IN ({symbol_placeholders})
            AND date = '{as_of_date}'
            ORDER BY symbol
            """
        else:
            # Get latest date's data
            query = f"""
            SELECT symbol, date, close, rsi_9
            FROM yfinance_daily_rsi r
            WHERE symbol IN ({symbol_placeholders})
            AND date = (SELECT MAX(date) FROM yfinance_daily_rsi WHERE symbol = r.symbol)
            ORDER BY symbol
            """
        
        try:
            df = pd.read_sql(query, engine)
            logger.info(f"Fetched {len(df)} records from yfinance_daily_rsi")
            return df
        except Exception as e:
            logger.error(f"Error fetching RSI data: {e}")
            return pd.DataFrame()
    
    def get_rsi_history(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """Get RSI history for a symbol over last N days"""
        engine = self.get_engine()
        
        query = f"""
        SELECT date, close, rsi_9
        FROM yfinance_daily_rsi
        WHERE symbol = '{symbol}'
        ORDER BY date DESC
        LIMIT {days}
        """
        
        try:
            df = pd.read_sql(query, engine)
            df['date'] = pd.to_datetime(df['date'])
            return df.sort_values('date')
        except Exception as e:
            logger.error(f"Error fetching history for {symbol}: {e}")
            return pd.DataFrame()


# =============================================================================
# RSI ANALYSIS
# =============================================================================

class RSIAnalyzer:
    """RSI analysis engine"""
    
    def __init__(self, db: RSIAnalyzerDB):
        self.db = db
    
    def classify_rsi(self, rsi: float) -> str:
        """Classify RSI value"""
        if pd.isna(rsi):
            return "NO DATA"
        elif rsi >= RSI_OVERBOUGHT:
            return "OVERBOUGHT"
        elif rsi <= RSI_OVERSOLD:
            return "OVERSOLD"
        else:
            return "NEUTRAL"
    
    def analyze_nifty50(self) -> Dict:
        """Analyze NIFTY 50 stocks"""
        logger.info(f"Analyzing NIFTY 50 ({len(NIFTY_50_SYMBOLS)} stocks)...")
        
        df = self.db.get_latest_rsi_data(NIFTY_50_SYMBOLS)
        
        if df.empty:
            logger.warning("No data fetched for NIFTY 50")
            return {
                'total': len(NIFTY_50_SYMBOLS),
                'data_available': 0,
                'overbought': [],
                'oversold': [],
                'neutral': [],
                'raw_df': df
            }
        
        # Add classification
        df['status'] = df['rsi_9'].apply(self.classify_rsi)
        
        # Separate by status
        overbought = df[df['status'] == 'OVERBOUGHT'].sort_values('rsi_9', ascending=False).to_dict('records')
        oversold = df[df['status'] == 'OVERSOLD'].sort_values('rsi_9').to_dict('records')
        neutral = df[df['status'] == 'NEUTRAL'].sort_values('rsi_9', ascending=False).to_dict('records')
        
        return {
            'total': len(NIFTY_50_SYMBOLS),
            'data_available': len(df),
            'overbought': overbought,
            'oversold': oversold,
            'neutral': neutral,
            'raw_df': df
        }
    
    def analyze_nifty500(self) -> Dict:
        """Analyze NIFTY 500 stocks"""
        logger.info(f"Analyzing NIFTY 500 ({len(NIFTY_500_STOCKS)} stocks)...")
        
        df = self.db.get_latest_rsi_data(NIFTY_500_STOCKS)
        
        if df.empty:
            logger.warning("No data fetched for NIFTY 500")
            return {
                'total': len(NIFTY_500_STOCKS),
                'data_available': 0,
                'overbought': [],
                'oversold': [],
                'neutral': [],
                'raw_df': df
            }
        
        # Add classification
        df['status'] = df['rsi_9'].apply(self.classify_rsi)
        
        # Separate by status
        overbought = df[df['status'] == 'OVERBOUGHT'].sort_values('rsi_9', ascending=False).to_dict('records')
        oversold = df[df['status'] == 'OVERSOLD'].sort_values('rsi_9').to_dict('records')
        neutral = df[df['status'] == 'NEUTRAL'].sort_values('rsi_9', ascending=False).to_dict('records')
        
        return {
            'total': len(NIFTY_500_STOCKS),
            'data_available': len(df),
            'overbought': overbought,
            'oversold': oversold,
            'neutral': neutral,
            'raw_df': df
        }


# =============================================================================
# REPORTING & OUTPUT
# =============================================================================

def format_table(records: List[Dict], columns: List[str] = None) -> str:
    """Format records as table"""
    if not records:
        return "(None)"
    
    if columns is None:
        columns = ['symbol', 'date', 'close', 'rsi_9']
    
    table_data = []
    for record in records:
        row = []
        for col in columns:
            val = record.get(col, '')
            if isinstance(val, float):
                if col == 'rsi_9':
                    row.append(f"{val:.2f}")
                else:
                    row.append(f"{val:.2f}")
            else:
                row.append(str(val))
        table_data.append(row)
    
    return tabulate(table_data, headers=columns, tablefmt='grid')


def print_analysis(analysis: Dict, title: str):
    """Print analysis results"""
    print(f"\n{'='*80}")
    print(f"{title}")
    print(f"{'='*80}")
    
    print(f"\nTotal Stocks: {analysis['total']}")
    print(f"Data Available: {analysis['data_available']}")
    
    if analysis['data_available'] == 0:
        print("\nNo data available for analysis.")
        return
    
    # Latest date from data
    if not analysis['raw_df'].empty:
        latest_date = analysis['raw_df']['date'].max()
        print(f"Latest Data: {latest_date}")
    
    # Summary statistics
    print(f"\nSummary:")
    print(f"  - Overbought (RSI >= {RSI_OVERBOUGHT}): {len(analysis['overbought'])} stocks")
    print(f"  - Oversold (RSI <= {RSI_OVERSOLD}): {len(analysis['oversold'])} stocks")
    print(f"  - Neutral ({RSI_OVERSOLD} < RSI < {RSI_OVERBOUGHT}): {len(analysis['neutral'])} stocks")
    
    # Overbought
    if analysis['overbought']:
        print(f"\n{'-'*80}")
        print(f"OVERBOUGHT Stocks (RSI >= {RSI_OVERBOUGHT}):")
        print(f"{'-'*80}")
        print(format_table(analysis['overbought']))
    
    # Oversold
    if analysis['oversold']:
        print(f"\n{'-'*80}")
        print(f"OVERSOLD Stocks (RSI <= {RSI_OVERSOLD}):")
        print(f"{'-'*80}")
        print(format_table(analysis['oversold']))
    
    # Neutral (top 20)
    if analysis['neutral']:
        print(f"\n{'-'*80}")
        print(f"Top 20 NEUTRAL Stocks (highest RSI):")
        print(f"{'-'*80}")
        print(format_table(analysis['neutral'][:20]))


def save_to_csv(analysis: Dict, filename: str):
    """Save analysis to CSV"""
    if analysis['raw_df'].empty:
        logger.warning(f"No data to save for {filename}")
        return
    
    df = analysis['raw_df'].copy()
    df['status'] = df['rsi_9'].apply(lambda x: 'OVERBOUGHT' if x >= RSI_OVERBOUGHT else ('OVERSOLD' if x <= RSI_OVERSOLD else 'NEUTRAL'))
    
    # Sort by status then RSI
    df['status_order'] = df['status'].map({'OVERBOUGHT': 0, 'OVERSOLD': 1, 'NEUTRAL': 2})
    df = df.sort_values(['status_order', 'rsi_9'], ascending=[True, False]).drop('status_order', axis=1)
    
    df.to_csv(filename, index=False)
    logger.info(f"Saved analysis to {filename}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main entry point"""
    print("\n" + "="*80)
    print("RSI OVERBOUGHT/OVERSOLD ANALYZER")
    print("="*80)
    print(f"Thresholds: Overbought >= {RSI_OVERBOUGHT}, Oversold <= {RSI_OVERSOLD}")
    print(f"Data Source: marketdata.yfinance_daily_rsi (RSI Period: 9)")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize database
    db = RSIAnalyzerDB()
    analyzer = RSIAnalyzer(db)
    
    # Check if table exists
    if not db.table_exists('yfinance_daily_rsi'):
        print("\nERROR: Table yfinance_daily_rsi does not exist in marketdata database.")
        print("Please run 'Daily Data Wizard' to populate RSI data first.")
        return
    
    # Analyze NIFTY 50
    nifty50_analysis = analyzer.analyze_nifty50()
    print_analysis(nifty50_analysis, "NIFTY 50 ANALYSIS")
    
    # Analyze NIFTY 500
    if NIFTY_500_STOCKS:
        nifty500_analysis = analyzer.analyze_nifty500()
        print_analysis(nifty500_analysis, "NIFTY 500 ANALYSIS")
    else:
        logger.warning("NIFTY 500 stocks list not available")
        nifty500_analysis = None
    
    # Save to CSV
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if nifty50_analysis['data_available'] > 0:
        nifty50_file = f"reports_output/rsi_analysis_nifty50_{timestamp}.csv"
        Path("reports_output").mkdir(parents=True, exist_ok=True)
        save_to_csv(nifty50_analysis, nifty50_file)
    
    if nifty500_analysis and nifty500_analysis['data_available'] > 0:
        nifty500_file = f"reports_output/rsi_analysis_nifty500_{timestamp}.csv"
        Path("reports_output").mkdir(parents=True, exist_ok=True)
        save_to_csv(nifty500_analysis, nifty500_file)
    
    print("\n" + "="*80)
    print("Analysis complete!")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()
