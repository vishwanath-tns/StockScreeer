#!/usr/bin/env python3
"""
Mean Reversion Strategy Backtester
==================================

Backtests two classic mean reversion strategies on Nifty 500 stocks using
daily data from the local MySQL database.

Strategies:
1. RSI(2) Mean Reversion:
   - Buy: RSI(2) < 10
   - Sell: RSI(2) > 90 or Close > 5-day SMA

2. Bollinger Band Mean Reversion:
   - Buy: Close < Lower Band (20, 2)
   - Sell: Close > 20-day SMA

Author: StockScreeer Project
Date: December 2025
"""

import sys
import os
import pandas as pd
import numpy as np
import mysql.connector
from sqlalchemy import create_engine
from datetime import datetime, date, timedelta
import warnings

# Suppress pandas warnings
warnings.filterwarnings('ignore')

# Add parent directory to path to import utilities
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from utilities.nifty500_stocks_list import NIFTY_500_STOCKS
except ImportError:
    # Fallback list if import fails
    NIFTY_500_STOCKS = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK']

from dotenv import load_dotenv
load_dotenv()


class DataService:
    """Handles database connections and data fetching"""
    
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
        if self._engine is None:
            from urllib.parse import quote_plus
            password = quote_plus(self.db_config['password']) if self.db_config['password'] else ''
            conn_str = f"mysql+mysqlconnector://{self.db_config['user']}:{password}@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
            self._engine = create_engine(conn_str)
        return self._engine
    
    def get_data(self, symbol, lookback_days=1000):
        """Fetch OHLCV data for a symbol"""
        engine = self.get_engine()
        
        # Convert to Yahoo symbol format if needed
        yahoo_symbol = f"{symbol}.NS" if not symbol.endswith('.NS') else symbol
        
        query = """
            SELECT date, open, high, low, close, volume
            FROM yfinance_daily_quotes
            WHERE symbol = %s 
            ORDER BY date ASC
        """
        
        try:
            df = pd.read_sql(query, engine, params=(yahoo_symbol,))
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
            return df
        except Exception as e:
            # print(f"Error fetching {symbol}: {e}")
            return pd.DataFrame()


class BacktestEngine:
    """Simple vectorized backtesting engine"""
    
    @staticmethod
    def calculate_rsi(series, period=2):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def run_rsi_strategy(df):
        """
        RSI(2) Strategy:
        Buy: RSI(2) < 10
        Sell: RSI(2) > 90 OR Close > SMA(5)
        """
        if len(df) < 50: return None
        
        data = df.copy()
        data['rsi2'] = BacktestEngine.calculate_rsi(data['close'], 2)
        data['sma5'] = data['close'].rolling(window=5).mean()
        
        # Signals
        data['in_position'] = 0
        data['buy_signal'] = (data['rsi2'] < 10)
        data['sell_signal'] = (data['rsi2'] > 90) | (data['close'] > data['sma5'])
        
        # Simulate trades
        in_pos = False
        entry_price = 0
        trades = []
        
        for i in range(1, len(data)):
            # Entry (Execute on next open)
            if not in_pos and data['buy_signal'].iloc[i-1]:
                # Buy on today's open (simplified assumption) 
                # or realistically next day open. Let's assume next day Open.
                if i < len(data):
                    entry_date = data.index[i]
                    entry_price = data['open'].iloc[i]
                    in_pos = True
            
            # Exit
            elif in_pos and data['sell_signal'].iloc[i-1]:
                exit_date = data.index[i]
                exit_price = data['open'].iloc[i]
                pct_change = ((exit_price - entry_price) / entry_price) * 100
                trades.append({
                    'entry_date': entry_date,
                    'exit_date': exit_date,
                    'return_pct': pct_change,
                    'holding_days': (exit_date - entry_date).days
                })
                in_pos = False
                
        return trades

    @staticmethod
    def run_bb_strategy(df):
        """
        Bollinger Band Strategy:
        Buy: Close < Lower Band (20, 2)
        Sell: Close > SMA(20)
        """
        if len(df) < 50: return None
        
        data = df.copy()
        data['sma20'] = data['close'].rolling(window=20).mean()
        data['std20'] = data['close'].rolling(window=20).std()
        data['lower_bb'] = data['sma20'] - (2 * data['std20'])
        
        # Signals
        data['buy_signal'] = (data['close'] < data['lower_bb'])
        data['sell_signal'] = (data['close'] > data['sma20'])
        
        in_pos = False
        entry_price = 0
        trades = []
        
        for i in range(1, len(data)):
            # Buy
            if not in_pos and data['buy_signal'].iloc[i-1]:
                entry_date = data.index[i]
                entry_price = data['open'].iloc[i]
                in_pos = True
            
            # Sell
            elif in_pos and data['sell_signal'].iloc[i-1]:
                exit_date = data.index[i]
                exit_price = data['open'].iloc[i]
                pct_change = ((exit_price - entry_price) / entry_price) * 100
                trades.append({
                    'entry_date': entry_date,
                    'exit_date': exit_date,
                    'return_pct': pct_change,
                    'holding_days': (exit_date - entry_date).days
                })
                in_pos = False
                
        return trades

def analyze_performance(all_trades):
    if not all_trades:
        return "No trades generated."
        
    df_trades = pd.DataFrame(all_trades)
    
    total_trades = len(df_trades)
    win_rate = len(df_trades[df_trades['return_pct'] > 0]) / total_trades * 100
    avg_return = df_trades['return_pct'].mean()
    total_return = df_trades['return_pct'].sum() # Simple sum of returns
    avg_holding = df_trades['holding_days'].mean()
    
    # Max Drawdown (simplified based on cumulative returns)
    df_trades['cum_return'] = df_trades['return_pct'].cumsum()
    df_trades['peak'] = df_trades['cum_return'].cummax()
    df_trades['drawdown'] = df_trades['cum_return'] - df_trades['peak']
    max_drawdown = df_trades['drawdown'].min()
    
    report = f"""
    Performance Metrics:
    --------------------
    Total Trades:       {total_trades}
    Win Rate:           {win_rate:.2f}%
    Avg Return/Trade:   {avg_return:.2f}%
    Avg Holding Days:   {avg_holding:.1f}
    Max Drawdown (pts): {max_drawdown:.2f}
    """
    return report

def main():
    print("="*60)
    print(" MEAN REVERSION STRATEGY BACKTESTER")
    print("="*60)
    
    service = DataService()
    
    # We'll use a subset of NIFTY 50 to test first for speed
    # Or get all if user wants full research
    subset_size = 50
    print(f"Fetching data for top {subset_size} stocks from Nifty 500...")
    
    # Prioritize liquid stocks (Nifty 50 usually)
    target_stocks = NIFTY_500_STOCKS[:subset_size]
    
    all_rsi_trades = []
    all_bb_trades = []
    
    stocks_processed = 0
    
    for i, symbol in enumerate(target_stocks):
        # Progress indicator
        if i % 5 == 0:
            print(f"Processing {i}/{len(target_stocks)} stocks...", end='\r')
            
        df = service.get_data(symbol)
        
        if df.empty or len(df) < 100:
            continue
            
        # Run RSI Strategy
        rsi_trades = BacktestEngine.run_rsi_strategy(df)
        if rsi_trades:
            all_rsi_trades.extend(rsi_trades)
            
        # Run BB Strategy
        bb_trades = BacktestEngine.run_bb_strategy(df)
        if bb_trades:
            all_bb_trades.extend(bb_trades)
            
        stocks_processed += 1
        
    print(f"\nProcessed {stocks_processed} stocks.")
    print("\n" + "="*40)
    print(" STRATEGY 1: RSI(2) MEAN REVERSION")
    print("="*40)
    print(analyze_performance(all_rsi_trades))
    
    print("\n" + "="*40)
    print(" STRATEGY 2: BOLLINGER BAND MEAN REVERSION")
    print("="*40)
    print(analyze_performance(all_bb_trades))
    
    # Export trades to CSV for further analysis
    if all_rsi_trades:
        # pd.DataFrame(all_rsi_trades).to_csv('rsi_trades.csv', index=False)
        pass # dont spam user with files unless asked

if __name__ == "__main__":
    main()
