#!/usr/bin/env python3
"""
Daily Data Wizard
=================

A step-by-step wizard that runs daily to synchronize and process market data.

Steps:
1. Sync daily data for all Nifty 500 stocks
2. Sync intraday data (1min, 5min, 60min) for all stocks
3. Verify data synchronization with Yahoo Finance
4. Calculate Moving Averages (EMA 21, SMA 5/50/150/200) for daily data
5. Calculate Moving Averages (EMA 21, SMA 50/200) for intraday data
6. Calculate RSI (9 period) for daily and intraday data

Usage:
    python wizards/daily_data_wizard.py

Author: StockScreener Project
Version: 1.0.0
Date: November 2025
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date, timedelta
import threading
import sys
import os
import time
import json
import pandas as pd
import numpy as np
import logging
from typing import List, Dict, Tuple, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue
import random

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import mysql.connector
from mysql.connector import Error
from sqlalchemy import create_engine, text
import yfinance as yf

from utilities.nifty500_stocks_list import NIFTY_500_STOCKS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# NSE Indices to track
NSE_INDICES = [
    "^NSEI",      # Nifty 50
    "^NSEBANK",   # Bank Nifty
    "^CNXIT",     # Nifty IT
    "^CNXPHARMA", # Nifty Pharma
    "^CNXAUTO",   # Nifty Auto
    "^CNXFMCG",   # Nifty FMCG
    "^CNXMETAL",  # Nifty Metal
    "^CNXREALTY", # Nifty Realty
    "^CNXENERGY", # Nifty Energy
    "^CNXINFRA",  # Nifty Infra
    "^CNXPSUBANK",# Nifty PSU Bank
    "^CNXMEDIA",  # Nifty Media
]

# Intraday intervals
INTRADAY_INTERVALS = ['1m', '5m', '60m']

# Moving Average periods
DAILY_MA_PERIODS = {
    'ema': [21],
    'sma': [5, 50, 150, 200]
}

INTRADAY_MA_PERIODS = {
    'ema': [21],
    'sma': [50, 200]
}

RSI_PERIOD = 9

# Parallel processing settings (to avoid Yahoo rate limits)
MAX_WORKERS_DOWNLOAD = 5   # Concurrent downloads (Yahoo is rate-limited)
MAX_WORKERS_CALCULATE = 10  # Concurrent calculations (DB operations)
RATE_LIMIT_DELAY = 0.2     # Delay between batches in seconds

# Deadlock retry settings
MAX_RETRIES = 3
RETRY_DELAY_BASE = 0.5  # Base delay in seconds (will be multiplied by attempt number)

# State file path
WIZARD_STATE_FILE = os.path.join(os.path.dirname(__file__), 'wizard_state.json')


# =============================================================================
# WIZARD STATE PERSISTENCE
# =============================================================================

@dataclass
class StepState:
    """Persistent state for a single step"""
    step_id: int
    step_name: str
    last_run_start: Optional[str] = None
    last_run_end: Optional[str] = None
    last_status: str = "never_run"  # never_run, completed, partial, failed
    symbols_processed: int = 0
    symbols_total: int = 0
    symbols_failed: List[str] = None
    error_message: str = ""
    
    def __post_init__(self):
        if self.symbols_failed is None:
            self.symbols_failed = []
    
    def to_dict(self) -> dict:
        return {
            'step_id': self.step_id,
            'step_name': self.step_name,
            'last_run_start': self.last_run_start,
            'last_run_end': self.last_run_end,
            'last_status': self.last_status,
            'symbols_processed': self.symbols_processed,
            'symbols_total': self.symbols_total,
            'symbols_failed': self.symbols_failed,
            'error_message': self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'StepState':
        return cls(
            step_id=data.get('step_id', 0),
            step_name=data.get('step_name', ''),
            last_run_start=data.get('last_run_start'),
            last_run_end=data.get('last_run_end'),
            last_status=data.get('last_status', 'never_run'),
            symbols_processed=data.get('symbols_processed', 0),
            symbols_total=data.get('symbols_total', 0),
            symbols_failed=data.get('symbols_failed', []),
            error_message=data.get('error_message', '')
        )


class WizardStateManager:
    """Manages persistent wizard state"""
    
    def __init__(self):
        self.state_file = WIZARD_STATE_FILE
        self.steps_state: Dict[int, StepState] = {}
        self.load_state()
    
    def load_state(self):
        """Load state from JSON file"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    for step_data in data.get('steps', []):
                        step_state = StepState.from_dict(step_data)
                        self.steps_state[step_state.step_id] = step_state
                    logger.info(f"Loaded wizard state from {self.state_file}")
        except Exception as e:
            logger.error(f"Error loading wizard state: {e}")
            self.steps_state = {}
    
    def save_state(self):
        """Save state to JSON file"""
        try:
            data = {
                'last_updated': datetime.now().isoformat(),
                'steps': [step.to_dict() for step in self.steps_state.values()]
            }
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved wizard state to {self.state_file}")
        except Exception as e:
            logger.error(f"Error saving wizard state: {e}")
    
    def get_step_state(self, step_id: int, step_name: str = "") -> StepState:
        """Get state for a step, creating if not exists"""
        if step_id not in self.steps_state:
            self.steps_state[step_id] = StepState(step_id=step_id, step_name=step_name)
        return self.steps_state[step_id]
    
    def start_step(self, step_id: int, step_name: str, total_symbols: int):
        """Mark step as started"""
        state = self.get_step_state(step_id, step_name)
        state.step_name = step_name
        state.last_run_start = datetime.now().isoformat()
        state.last_run_end = None
        state.last_status = "running"
        state.symbols_processed = 0
        state.symbols_total = total_symbols
        state.symbols_failed = []
        state.error_message = ""
        self.save_state()
    
    def update_step_progress(self, step_id: int, processed: int, failed_symbols: List[str] = None):
        """Update step progress"""
        state = self.get_step_state(step_id)
        state.symbols_processed = processed
        if failed_symbols:
            state.symbols_failed = failed_symbols
        # Save periodically (every 50 symbols)
        if processed % 50 == 0:
            self.save_state()
    
    def complete_step(self, step_id: int, success: bool, message: str = "", failed_symbols: List[str] = None):
        """Mark step as completed"""
        state = self.get_step_state(step_id)
        state.last_run_end = datetime.now().isoformat()
        if failed_symbols:
            state.symbols_failed = failed_symbols
        
        if success:
            if state.symbols_failed:
                state.last_status = "partial"  # Completed but with some failures
            else:
                state.last_status = "completed"
        else:
            if state.symbols_processed > 0:
                state.last_status = "partial"  # Interrupted/stopped
            else:
                state.last_status = "failed"
        
        state.error_message = message
        self.save_state()
    
    def get_step_summary(self, step_id: int) -> str:
        """Get human-readable summary of step state"""
        state = self.get_step_state(step_id)
        if state.last_status == "never_run":
            return "Never run"
        
        status_emoji = {
            "completed": "✅",
            "partial": "⚠️",
            "failed": "❌",
            "running": "🔄",
            "never_run": "⏸️"
        }
        
        emoji = status_emoji.get(state.last_status, "❓")
        
        if state.last_run_end:
            run_time = state.last_run_end
        elif state.last_run_start:
            run_time = state.last_run_start
        else:
            run_time = "Unknown"
        
        # Format the time nicely
        try:
            dt = datetime.fromisoformat(run_time)
            run_time = dt.strftime("%Y-%m-%d %H:%M")
        except:
            pass
        
        summary = f"{emoji} {state.last_status.replace('_', ' ').title()}"
        summary += f" | Last: {run_time}"
        summary += f" | {state.symbols_processed}/{state.symbols_total}"
        
        if state.symbols_failed:
            summary += f" | ⚠️ {len(state.symbols_failed)} failed"
        
        return summary


# =============================================================================
# STEP STATUS
# =============================================================================

class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WizardStep:
    """Represents a wizard step"""
    id: int
    name: str
    description: str
    status: StepStatus = StepStatus.PENDING
    progress: int = 0
    message: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def duration(self) -> str:
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return str(delta).split('.')[0]
        return "--:--:--"


# =============================================================================
# DATABASE SERVICE
# =============================================================================

class WizardDBService:
    """Database service for the wizard"""
    
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
            self._engine = create_engine(conn_str)
        return self._engine
    
    def get_connection(self):
        """Get raw MySQL connection"""
        return mysql.connector.connect(**self.db_config)
    
    def execute_query(self, query: str, params: tuple = None) -> pd.DataFrame:
        """Execute a query and return results as DataFrame"""
        engine = self.get_engine()
        return pd.read_sql(query, engine, params=params)
    
    def execute_update(self, query: str, params: tuple = None):
        """Execute an update/insert query"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
        finally:
            cursor.close()
            conn.close()
    
    def ensure_tables_exist(self):
        """Create necessary tables if they don't exist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Daily Moving Averages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS yfinance_daily_ma (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    symbol VARCHAR(50) NOT NULL,
                    date DATE NOT NULL,
                    close DECIMAL(15,4),
                    ema_21 DECIMAL(15,4),
                    sma_5 DECIMAL(15,4),
                    sma_50 DECIMAL(15,4),
                    sma_150 DECIMAL(15,4),
                    sma_200 DECIMAL(15,4),
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_symbol_date (symbol, date),
                    INDEX idx_symbol (symbol),
                    INDEX idx_date (date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            
            # Intraday Moving Averages tables (one per interval)
            for interval in INTRADAY_INTERVALS:
                table_name = f"yfinance_intraday_ma_{interval.replace('m', 'min')}"
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        symbol VARCHAR(50) NOT NULL,
                        datetime DATETIME NOT NULL,
                        close DECIMAL(15,4),
                        ema_21 DECIMAL(15,4),
                        sma_50 DECIMAL(15,4),
                        sma_200 DECIMAL(15,4),
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY unique_symbol_datetime (symbol, datetime),
                        INDEX idx_symbol (symbol),
                        INDEX idx_datetime (datetime)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
            
            # Daily RSI table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS yfinance_daily_rsi (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    symbol VARCHAR(50) NOT NULL,
                    date DATE NOT NULL,
                    close DECIMAL(15,4),
                    rsi_9 DECIMAL(8,4),
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_symbol_date (symbol, date),
                    INDEX idx_symbol (symbol),
                    INDEX idx_date (date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            
            # Intraday RSI tables
            for interval in INTRADAY_INTERVALS:
                table_name = f"yfinance_intraday_rsi_{interval.replace('m', 'min')}"
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        symbol VARCHAR(50) NOT NULL,
                        datetime DATETIME NOT NULL,
                        close DECIMAL(15,4),
                        rsi_9 DECIMAL(8,4),
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY unique_symbol_datetime (symbol, datetime),
                        INDEX idx_symbol (symbol),
                        INDEX idx_datetime (datetime)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
            
            # Note: yfinance_intraday_quotes already exists with 'timeframe' column
            # We use the existing table structure (symbol, datetime, timeframe, open, high, low, close, volume, source)
            
            conn.commit()
            logger.info("All required tables created/verified")
            
        finally:
            cursor.close()
            conn.close()


# =============================================================================
# CALCULATION UTILITIES
# =============================================================================

def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average"""
    return data.ewm(span=period, adjust=False).mean()


def calculate_sma(data: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average"""
    return data.rolling(window=period).mean()


def calculate_rsi(data: pd.Series, period: int = 9) -> pd.Series:
    """Calculate Relative Strength Index"""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


# =============================================================================
# WIZARD STEPS IMPLEMENTATION
# =============================================================================

class WizardStepsExecutor:
    """Executes wizard steps"""
    
    def __init__(self, db_service: WizardDBService, progress_callback: Callable, state_manager: WizardStateManager = None):
        self.db = db_service
        self.progress_callback = progress_callback
        self.symbols = [f"{s}.NS" for s in NIFTY_500_STOCKS]
        self.all_symbols = self.symbols + NSE_INDICES
        self.stop_requested = False
        self.state_manager = state_manager or WizardStateManager()
        self.failed_symbols: List[str] = []  # Track failed symbols per step
    
    def stop(self):
        """Request stop"""
        self.stop_requested = True
    
    def get_step_summary(self, step_id: int) -> str:
        """Get summary of a step's last run state"""
        return self.state_manager.get_step_summary(step_id)
    
    # =========================================================================
    # STEP 1: Sync Daily Data (PARALLEL)
    # =========================================================================
    
    def _sync_daily_symbol(self, symbol: str, engine) -> Tuple[str, bool, str]:
        """Sync daily data for a single symbol (worker function)"""
        try:
            # Get last date for this symbol
            query = "SELECT MAX(date) as last_date FROM yfinance_daily_quotes WHERE symbol = %s"
            df = pd.read_sql(query, engine, params=(symbol,))
            last_date = df['last_date'].iloc[0] if not df.empty and df['last_date'].iloc[0] else None
            
            # Determine start date
            if last_date:
                start_date = (pd.to_datetime(last_date) + timedelta(days=1)).strftime('%Y-%m-%d')
            else:
                start_date = (datetime.now() - timedelta(days=365*5)).strftime('%Y-%m-%d')
            
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            # Skip if already up to date
            if last_date and pd.to_datetime(last_date).date() >= (datetime.now().date() - timedelta(days=1)):
                return symbol, True, "up to date"
            
            # Download from Yahoo Finance
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, interval='1d')
            
            if not df.empty:
                df = df.reset_index()
                df['symbol'] = symbol
                df = df.rename(columns={
                    'Date': 'date', 'Open': 'open', 'High': 'high',
                    'Low': 'low', 'Close': 'close', 'Volume': 'volume'
                })
                df = df[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']]
                df['date'] = pd.to_datetime(df['date']).dt.date
                
                # Insert into database
                df.to_sql('yfinance_daily_quotes', engine, if_exists='append', 
                         index=False, method='multi', chunksize=500)
                return symbol, True, f"{len(df)} rows"
            else:
                return symbol, True, "no new data"
                
        except Exception as e:
            logger.error(f"Error syncing {symbol}: {e}")
            return symbol, False, str(e)
    
    def step1_sync_daily_data(self) -> Tuple[bool, str]:
        """Sync daily data for all Nifty 500 stocks and indices (PARALLEL)"""
        step_id = 1
        self.failed_symbols = []
        
        try:
            engine = self.db.get_engine()
            total = len(self.all_symbols)
            synced = 0
            failed = 0
            processed = 0
            
            # Start tracking this step
            self.state_manager.start_step(step_id, "Sync Daily Data", total)
            
            self.progress_callback(0, f"Syncing daily data for {total} symbols (parallel)...")
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS_DOWNLOAD) as executor:
                # Submit all tasks
                futures = {
                    executor.submit(self._sync_daily_symbol, symbol, engine): symbol 
                    for symbol in self.all_symbols
                }
                
                # Process completed tasks
                for future in as_completed(futures):
                    if self.stop_requested:
                        executor.shutdown(wait=False, cancel_futures=True)
                        self.state_manager.complete_step(step_id, False, "Stopped by user", self.failed_symbols)
                        return False, "Stopped by user"
                    
                    symbol, success, msg = future.result()
                    processed += 1
                    
                    if success:
                        synced += 1
                    else:
                        failed += 1
                        self.failed_symbols.append(symbol)
                    
                    # Update state periodically
                    self.state_manager.update_step_progress(step_id, processed, self.failed_symbols)
                    
                    self.progress_callback(
                        int(processed / total * 100), 
                        f"Daily: {symbol} ({msg}) [{processed}/{total}]"
                    )
            
            # Mark step complete
            self.state_manager.complete_step(step_id, True, f"{synced} synced, {failed} failed", self.failed_symbols)
            return True, f"Daily sync complete: {synced} synced, {failed} failed"
            
        except Exception as e:
            logger.error(f"Step 1 failed: {e}")
            self.state_manager.complete_step(step_id, False, str(e), self.failed_symbols)
            return False, str(e)
    
    # =========================================================================
    # STEP 2: Sync Intraday Data (PARALLEL)
    # =========================================================================
    
    def _execute_with_retry(self, operation_func, *args, max_retries=MAX_RETRIES):
        """Execute a database operation with retry logic for deadlocks"""
        for attempt in range(max_retries):
            try:
                return operation_func(*args)
            except Exception as e:
                error_str = str(e)
                if "Deadlock" in error_str or "1213" in error_str:
                    if attempt < max_retries - 1:
                        # Exponential backoff with jitter
                        delay = RETRY_DELAY_BASE * (attempt + 1) + random.uniform(0, 0.5)
                        time.sleep(delay)
                        continue
                raise  # Re-raise if not a deadlock or max retries exceeded
        return None
    
    def _batch_upsert_intraday(self, df: pd.DataFrame) -> int:
        """Batch upsert intraday data with deadlock retry"""
        if df.empty:
            return 0
        
        def do_upsert():
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Prepare batch data
            values = []
            for _, row in df.iterrows():
                values.append((
                    row['symbol'], row['datetime'], row['timeframe'],
                    row['open'], row['high'], row['low'], row['close'], 
                    row['volume'], row['source']
                ))
            
            # Batch insert with executemany
            cursor.executemany("""
                INSERT INTO yfinance_intraday_quotes 
                (symbol, datetime, timeframe, open, high, low, close, volume, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                open = VALUES(open), high = VALUES(high), low = VALUES(low),
                close = VALUES(close), volume = VALUES(volume)
            """, values)
            
            conn.commit()
            cursor.close()
            conn.close()
            return len(values)
        
        return self._execute_with_retry(do_upsert)
    
    def _sync_intraday_symbol(self, symbol: str, interval: str) -> Tuple[str, str, bool, str]:
        """Sync intraday data for a single symbol/interval (worker function)"""
        try:
            # Check last datetime in database for this symbol/interval
            engine = self.db.get_engine()
            query = """
                SELECT MAX(datetime) as last_dt FROM yfinance_intraday_quotes 
                WHERE symbol = %s AND timeframe = %s
            """
            result = pd.read_sql(query, engine, params=(symbol, interval))
            last_dt = result['last_dt'].iloc[0] if not result.empty and result['last_dt'].iloc[0] else None
            
            # Yahoo limits: 1m = 7 days, 5m = 60 days, 60m = 730 days
            days_map = {'1m': 7, '5m': 60, '60m': 60}
            max_days = days_map[interval]
            
            # If we have recent data, skip download
            if last_dt:
                last_dt = pd.to_datetime(last_dt)
                # Make timezone-naive for comparison
                if last_dt.tzinfo is not None:
                    last_dt = last_dt.tz_localize(None)
                
                hours_ago = (datetime.now() - last_dt).total_seconds() / 3600
                
                # Skip if data is less than 2 hours old (market hours buffer)
                if hours_ago < 2:
                    return symbol, interval, True, "up to date"
                
                # For 1m data, only download last 1 day if we have recent data
                if interval == '1m' and hours_ago < 24:
                    period = "1d"
                elif interval == '1m':
                    period = f"{min(int(hours_ago / 24) + 1, max_days)}d"
                else:
                    # For 5m/60m, calculate days needed
                    days_needed = min(int(hours_ago / 24) + 1, max_days)
                    period = f"{days_needed}d"
            else:
                # No data exists, download full period
                period = f"{max_days}d"
            
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            
            if not df.empty:
                df = df.reset_index()
                df['symbol'] = symbol
                df['timeframe'] = interval
                df['source'] = 'yfinance'
                df = df.rename(columns={
                    'Datetime': 'datetime', 'Date': 'datetime',
                    'Open': 'open', 'High': 'high',
                    'Low': 'low', 'Close': 'close', 'Volume': 'volume'
                })
                
                if 'datetime' not in df.columns and 'index' in df.columns:
                    df = df.rename(columns={'index': 'datetime'})
                
                df = df[['symbol', 'datetime', 'timeframe', 'open', 'high', 'low', 'close', 'volume', 'source']]
                df['datetime'] = pd.to_datetime(df['datetime'])
                
                # Make datetime column timezone-naive for comparison and storage
                if df['datetime'].dt.tz is not None:
                    df['datetime'] = df['datetime'].dt.tz_localize(None)
                
                # Filter to only new data if we have last_dt
                if last_dt:
                    df = df[df['datetime'] > last_dt]
                
                if not df.empty:
                    # Batch upsert with deadlock retry
                    rows = self._batch_upsert_intraday(df)
                    return symbol, interval, True, f"{rows} new rows"
                else:
                    return symbol, interval, True, "up to date"
            else:
                return symbol, interval, True, "no data"
                
        except Exception as e:
            logger.error(f"Error syncing {symbol} {interval}: {e}")
            return symbol, interval, False, str(e)
    
    def step2_sync_intraday_data(self) -> Tuple[bool, str]:
        """Sync intraday data (1min, 5min, 60min) for all stocks (PARALLEL)"""
        step_id = 2
        self.failed_symbols = []
        
        try:
            # Create all symbol/interval combinations
            tasks = [(symbol, interval) for symbol in self.all_symbols for interval in INTRADAY_INTERVALS]
            total = len(tasks)
            synced = 0
            failed = 0
            processed = 0
            
            # Start tracking this step
            self.state_manager.start_step(step_id, "Sync Intraday Data", total)
            
            self.progress_callback(0, f"Syncing intraday data for {len(self.all_symbols)} symbols x {len(INTRADAY_INTERVALS)} intervals...")
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS_DOWNLOAD) as executor:
                # Submit all tasks
                futures = {
                    executor.submit(self._sync_intraday_symbol, symbol, interval): (symbol, interval)
                    for symbol, interval in tasks
                }
                
                # Process completed tasks
                for future in as_completed(futures):
                    if self.stop_requested:
                        executor.shutdown(wait=False, cancel_futures=True)
                        self.state_manager.complete_step(step_id, False, "Stopped by user", self.failed_symbols)
                        return False, "Stopped by user"
                    
                    symbol, interval, success, msg = future.result()
                    processed += 1
                    
                    if success:
                        synced += 1
                    else:
                        failed += 1
                        self.failed_symbols.append(f"{symbol}:{interval}")
                    
                    # Update state periodically
                    self.state_manager.update_step_progress(step_id, processed, self.failed_symbols)
                    
                    self.progress_callback(
                        int(processed / total * 100),
                        f"Intraday: {symbol} ({interval}) [{processed}/{total}]"
                    )
            
            # Mark step complete
            self.state_manager.complete_step(step_id, True, f"{synced} synced, {failed} failed", self.failed_symbols)
            return True, f"Intraday sync complete: {synced} synced, {failed} failed"
            
        except Exception as e:
            logger.error(f"Step 2 failed: {e}")
            self.state_manager.complete_step(step_id, False, str(e), self.failed_symbols)
            return False, str(e)
    
    # =========================================================================
    # STEP 3: Verify Data Sync
    # =========================================================================
    
    def step3_verify_data_sync(self) -> Tuple[bool, str]:
        """Verify data is in sync with Yahoo Finance"""
        step_id = 3
        self.failed_symbols = []
        sample_size = 50
        
        try:
            engine = self.db.get_engine()
            verified = 0
            mismatched = 0
            
            # Start tracking this step
            self.state_manager.start_step(step_id, "Verify Data Sync", sample_size)
            
            today = datetime.now().date()
            
            for i, symbol in enumerate(self.all_symbols[:sample_size]):  # Sample verification
                if self.stop_requested:
                    self.state_manager.complete_step(step_id, False, "Stopped by user", self.failed_symbols)
                    return False, "Stopped by user"
                
                try:
                    # Get latest from database
                    query = """
                        SELECT date, close FROM yfinance_daily_quotes 
                        WHERE symbol = %s ORDER BY date DESC LIMIT 1
                    """
                    db_data = pd.read_sql(query, engine, params=(symbol,))
                    
                    if db_data.empty:
                        mismatched += 1
                        self.failed_symbols.append(symbol)
                        continue
                    
                    db_date = pd.to_datetime(db_data['date'].iloc[0]).date()
                    db_close = float(db_data['close'].iloc[0])
                    
                    # Get latest from Yahoo
                    ticker = yf.Ticker(symbol)
                    yf_data = ticker.history(period='5d')
                    
                    if not yf_data.empty:
                        yf_date = yf_data.index[-1].date()
                        yf_close = float(yf_data['Close'].iloc[-1])
                        
                        # Allow 1 day difference (market may be closed)
                        date_diff = abs((yf_date - db_date).days)
                        price_diff = abs(db_close - yf_close) / yf_close * 100
                        
                        if date_diff <= 1 and price_diff < 1:  # Within 1%
                            verified += 1
                        else:
                            mismatched += 1
                            self.failed_symbols.append(symbol)
                            logger.warning(f"{symbol}: DB={db_date}/{db_close:.2f}, YF={yf_date}/{yf_close:.2f}")
                    
                except Exception as e:
                    logger.error(f"Verification error for {symbol}: {e}")
                    mismatched += 1
                    self.failed_symbols.append(symbol)
                
                # Update state
                self.state_manager.update_step_progress(step_id, i + 1, self.failed_symbols)
                self.progress_callback(int((i + 1) / sample_size * 100), f"Verifying: {symbol}")
                time.sleep(0.1)
            
            # If more than 90% verified, consider it a pass
            success = verified >= 45  # 90% of 50 samples
            msg = f"Verification: {verified}/{sample_size} symbols verified, {mismatched} mismatched"
            self.state_manager.complete_step(step_id, success, msg, self.failed_symbols)
            return success, msg
            
        except Exception as e:
            logger.error(f"Step 3 failed: {e}")
            self.state_manager.complete_step(step_id, False, str(e), self.failed_symbols)
            return False, str(e)
            return False, str(e)
    
    # =========================================================================
    # STEP 4: Calculate Daily Moving Averages (PARALLEL)
    # =========================================================================
    
    def _batch_upsert_daily_ma(self, df: pd.DataFrame) -> int:
        """Batch upsert daily MA data with deadlock retry"""
        if df.empty:
            return 0
        
        def do_upsert():
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            values = []
            for _, row in df.iterrows():
                values.append((
                    row['symbol'], row['date'], row['close'], row['ema_21'],
                    row['sma_5'], row['sma_50'], row['sma_150'], row['sma_200']
                ))
            
            cursor.executemany("""
                INSERT INTO yfinance_daily_ma 
                (symbol, date, close, ema_21, sma_5, sma_50, sma_150, sma_200)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                close = VALUES(close), ema_21 = VALUES(ema_21),
                sma_5 = VALUES(sma_5), sma_50 = VALUES(sma_50),
                sma_150 = VALUES(sma_150), sma_200 = VALUES(sma_200)
            """, values)
            
            conn.commit()
            cursor.close()
            conn.close()
            return len(values)
        
        return self._execute_with_retry(do_upsert)
    
    def _calc_daily_ma_symbol(self, symbol: str) -> Tuple[str, bool, str]:
        """Calculate daily MA for a single symbol (worker function) - INCREMENTAL"""
        try:
            engine = self.db.get_engine()
            
            # Check last calculated date
            last_calc_query = "SELECT MAX(date) as last_date FROM yfinance_daily_ma WHERE symbol = %s"
            last_calc = pd.read_sql(last_calc_query, engine, params=(symbol,))
            last_calc_date = last_calc['last_date'].iloc[0] if not last_calc.empty and last_calc['last_date'].iloc[0] else None
            
            # Check last data date
            last_data_query = "SELECT MAX(date) as last_date FROM yfinance_daily_quotes WHERE symbol = %s"
            last_data = pd.read_sql(last_data_query, engine, params=(symbol,))
            last_data_date = last_data['last_date'].iloc[0] if not last_data.empty and last_data['last_date'].iloc[0] else None
            
            # Skip if already calculated up to latest data
            if last_calc_date and last_data_date:
                if pd.to_datetime(last_calc_date).date() >= pd.to_datetime(last_data_date).date():
                    return symbol, True, "up to date"
            
            # Load data - need 200 days before the start date for SMA 200
            query = """
                SELECT date, close FROM yfinance_daily_quotes 
                WHERE symbol = %s ORDER BY date
            """
            df = pd.read_sql(query, engine, params=(symbol,))
            
            if len(df) < 200:
                return symbol, True, "insufficient data"
            
            df['symbol'] = symbol
            df['ema_21'] = calculate_ema(df['close'], 21)
            df['sma_5'] = calculate_sma(df['close'], 5)
            df['sma_50'] = calculate_sma(df['close'], 50)
            df['sma_150'] = calculate_sma(df['close'], 150)
            df['sma_200'] = calculate_sma(df['close'], 200)
            
            # Only keep valid data
            df = df.dropna(subset=['sma_200'])
            
            if df.empty:
                return symbol, True, "no valid data"
            
            # Filter to only new dates if we have last_calc_date
            if last_calc_date:
                df = df[df['date'] > last_calc_date]
            else:
                # First time: only keep last 500 days
                df = df.tail(500)
            
            if df.empty:
                return symbol, True, "up to date"
            
            rows = self._batch_upsert_daily_ma(df)
            return symbol, True, f"{rows} new rows"
            
        except Exception as e:
            logger.error(f"MA calculation error for {symbol}: {e}")
            return symbol, False, str(e)
    
    def step4_calculate_daily_ma(self) -> Tuple[bool, str]:
        """Calculate Moving Averages for daily data (PARALLEL)"""
        step_id = 4
        self.failed_symbols = []
        
        try:
            total = len(self.all_symbols)
            processed = 0
            success_count = 0
            
            # Start tracking this step
            self.state_manager.start_step(step_id, "Calculate Daily MA", total)
            
            self.progress_callback(0, f"Calculating daily MAs for {total} symbols (parallel)...")
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS_CALCULATE) as executor:
                futures = {
                    executor.submit(self._calc_daily_ma_symbol, symbol): symbol
                    for symbol in self.all_symbols
                }
                
                for future in as_completed(futures):
                    if self.stop_requested:
                        executor.shutdown(wait=False, cancel_futures=True)
                        self.state_manager.complete_step(step_id, False, "Stopped by user", self.failed_symbols)
                        return False, "Stopped by user"
                    
                    symbol, success, msg = future.result()
                    processed += 1
                    if success:
                        success_count += 1
                    else:
                        self.failed_symbols.append(symbol)
                    
                    # Update state periodically
                    self.state_manager.update_step_progress(step_id, processed, self.failed_symbols)
                    
                    self.progress_callback(
                        int(processed / total * 100),
                        f"Daily MA: {symbol} ({msg}) [{processed}/{total}]"
                    )
            
            # Mark step complete
            msg = f"Daily MA calculation complete: {success_count}/{total} symbols processed"
            self.state_manager.complete_step(step_id, True, msg, self.failed_symbols)
            return True, msg
            
        except Exception as e:
            logger.error(f"Step 4 failed: {e}")
            self.state_manager.complete_step(step_id, False, str(e), self.failed_symbols)
            return False, str(e)
    
    # =========================================================================
    # STEP 5: Calculate Intraday Moving Averages (PARALLEL)
    # =========================================================================
    
    def _batch_upsert_intraday_ma(self, df: pd.DataFrame, table_name: str) -> int:
        """Batch upsert intraday MA data with deadlock retry"""
        if df.empty:
            return 0
        
        def do_upsert():
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            values = []
            for _, row in df.iterrows():
                values.append((
                    row['symbol'], row['datetime'], row['close'],
                    row['ema_21'], row['sma_50'], row['sma_200']
                ))
            
            cursor.executemany(f"""
                INSERT INTO {table_name} 
                (symbol, datetime, close, ema_21, sma_50, sma_200)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                close = VALUES(close), ema_21 = VALUES(ema_21),
                sma_50 = VALUES(sma_50), sma_200 = VALUES(sma_200)
            """, values)
            
            conn.commit()
            cursor.close()
            conn.close()
            return len(values)
        
        return self._execute_with_retry(do_upsert)
    
    def _calc_intraday_ma_symbol(self, symbol: str, interval: str) -> Tuple[str, str, bool, str]:
        """Calculate intraday MA for a single symbol/interval (worker function) - INCREMENTAL"""
        try:
            engine = self.db.get_engine()
            table_name = f"yfinance_intraday_ma_{interval.replace('m', 'min')}"
            
            # Check last calculated datetime
            last_calc_query = f"SELECT MAX(datetime) as last_dt FROM {table_name} WHERE symbol = %s"
            last_calc = pd.read_sql(last_calc_query, engine, params=(symbol,))
            last_calc_dt = last_calc['last_dt'].iloc[0] if not last_calc.empty and last_calc['last_dt'].iloc[0] else None
            
            # Check last data datetime
            last_data_query = """
                SELECT MAX(datetime) as last_dt FROM yfinance_intraday_quotes 
                WHERE symbol = %s AND timeframe = %s
            """
            last_data = pd.read_sql(last_data_query, engine, params=(symbol, interval))
            last_data_dt = last_data['last_dt'].iloc[0] if not last_data.empty and last_data['last_dt'].iloc[0] else None
            
            # Skip if already calculated up to latest data
            if last_calc_dt and last_data_dt:
                if pd.to_datetime(last_calc_dt) >= pd.to_datetime(last_data_dt):
                    return symbol, interval, True, "up to date"
            
            # Load all data for calculation (need 200 periods for SMA 200)
            query = """
                SELECT datetime, close FROM yfinance_intraday_quotes 
                WHERE symbol = %s AND timeframe = %s ORDER BY datetime
            """
            df = pd.read_sql(query, engine, params=(symbol, interval))
            
            if len(df) < 200:
                return symbol, interval, True, "insufficient data"
            
            df['symbol'] = symbol
            df['ema_21'] = calculate_ema(df['close'], 21)
            df['sma_50'] = calculate_sma(df['close'], 50)
            df['sma_200'] = calculate_sma(df['close'], 200)
            
            df = df.dropna(subset=['sma_200'])
            
            if df.empty:
                return symbol, interval, True, "no valid data"
            
            # Filter to only new datetimes if we have last_calc_dt
            if last_calc_dt:
                df = df[df['datetime'] > last_calc_dt]
            
            if df.empty:
                return symbol, interval, True, "up to date"
            
            rows = self._batch_upsert_intraday_ma(df, table_name)
            return symbol, interval, True, f"{rows} rows"
            
        except Exception as e:
            logger.error(f"Intraday MA error for {symbol} {interval}: {e}")
            return symbol, interval, False, str(e)
    
    def step5_calculate_intraday_ma(self) -> Tuple[bool, str]:
        """Calculate Moving Averages for intraday data (PARALLEL)"""
        step_id = 5
        self.failed_symbols = []
        
        try:
            tasks = [(symbol, interval) for symbol in self.all_symbols for interval in INTRADAY_INTERVALS]
            total = len(tasks)
            processed = 0
            success_count = 0
            
            # Start tracking this step
            self.state_manager.start_step(step_id, "Calculate Intraday MA", total)
            
            self.progress_callback(0, f"Calculating intraday MAs for {len(self.all_symbols)} symbols x {len(INTRADAY_INTERVALS)} intervals...")
            
            with ThreadPoolExecutor(max_workers=MAX_WORKERS_CALCULATE) as executor:
                futures = {
                    executor.submit(self._calc_intraday_ma_symbol, symbol, interval): (symbol, interval)
                    for symbol, interval in tasks
                }
                
                for future in as_completed(futures):
                    if self.stop_requested:
                        executor.shutdown(wait=False, cancel_futures=True)
                        self.state_manager.complete_step(step_id, False, "Stopped by user", self.failed_symbols)
                        return False, "Stopped by user"
                    
                    symbol, interval, success, msg = future.result()
                    processed += 1
                    if success:
                        success_count += 1
                    else:
                        self.failed_symbols.append(f"{symbol}:{interval}")
                    
                    # Update state periodically
                    self.state_manager.update_step_progress(step_id, processed, self.failed_symbols)
                    
                    self.progress_callback(
                        int(processed / total * 100),
                        f"Intraday MA: {symbol} ({interval}) [{processed}/{total}]"
                    )
            
            # Mark step complete
            msg = f"Intraday MA calculation complete: {success_count}/{total} processed"
            self.state_manager.complete_step(step_id, True, msg, self.failed_symbols)
            return True, msg
            
        except Exception as e:
            logger.error(f"Step 5 failed: {e}")
            self.state_manager.complete_step(step_id, False, str(e), self.failed_symbols)
            return False, str(e)
    
    # =========================================================================
    # STEP 6: Calculate RSI (PARALLEL)
    # =========================================================================
    
    def _batch_upsert_daily_rsi(self, df: pd.DataFrame) -> int:
        """Batch upsert daily RSI data with deadlock retry"""
        if df.empty:
            return 0
        
        def do_upsert():
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            values = []
            for _, row in df.iterrows():
                values.append((row['symbol'], row['date'], row['close'], row['rsi_9']))
            
            cursor.executemany("""
                INSERT INTO yfinance_daily_rsi (symbol, date, close, rsi_9)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                close = VALUES(close), rsi_9 = VALUES(rsi_9)
            """, values)
            
            conn.commit()
            cursor.close()
            conn.close()
            return len(values)
        
        return self._execute_with_retry(do_upsert)
    
    def _batch_upsert_intraday_rsi(self, df: pd.DataFrame, table_name: str) -> int:
        """Batch upsert intraday RSI data with deadlock retry"""
        if df.empty:
            return 0
        
        def do_upsert():
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            values = []
            for _, row in df.iterrows():
                values.append((row['symbol'], row['datetime'], row['close'], row['rsi_9']))
            
            cursor.executemany(f"""
                INSERT INTO {table_name} (symbol, datetime, close, rsi_9)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                close = VALUES(close), rsi_9 = VALUES(rsi_9)
            """, values)
            
            conn.commit()
            cursor.close()
            conn.close()
            return len(values)
        
        return self._execute_with_retry(do_upsert)
    
    def _calc_daily_rsi_symbol(self, symbol: str) -> Tuple[str, bool, str]:
        """Calculate daily RSI for a single symbol (worker function) - INCREMENTAL"""
        try:
            engine = self.db.get_engine()
            
            # Check last calculated date
            last_calc_query = "SELECT MAX(date) as last_date FROM yfinance_daily_rsi WHERE symbol = %s"
            last_calc = pd.read_sql(last_calc_query, engine, params=(symbol,))
            last_calc_date = last_calc['last_date'].iloc[0] if not last_calc.empty and last_calc['last_date'].iloc[0] else None
            
            # Check last data date
            last_data_query = "SELECT MAX(date) as last_date FROM yfinance_daily_quotes WHERE symbol = %s"
            last_data = pd.read_sql(last_data_query, engine, params=(symbol,))
            last_data_date = last_data['last_date'].iloc[0] if not last_data.empty and last_data['last_date'].iloc[0] else None
            
            # Skip if already calculated up to latest data
            if last_calc_date and last_data_date:
                if pd.to_datetime(last_calc_date).date() >= pd.to_datetime(last_data_date).date():
                    return symbol, True, "up to date"
            
            query = """
                SELECT date, close FROM yfinance_daily_quotes 
                WHERE symbol = %s ORDER BY date
            """
            df = pd.read_sql(query, engine, params=(symbol,))
            
            if len(df) < RSI_PERIOD + 1:
                return symbol, True, "insufficient data"
            
            df['symbol'] = symbol
            df['rsi_9'] = calculate_rsi(df['close'], RSI_PERIOD)
            df = df.dropna(subset=['rsi_9'])
            
            if df.empty:
                return symbol, True, "no valid data"
            
            # Filter to only new dates if we have last_calc_date
            if last_calc_date:
                df = df[df['date'] > last_calc_date]
            else:
                # First time: only keep last 500 days
                df = df.tail(500)
            
            if df.empty:
                return symbol, True, "up to date"
            
            rows = self._batch_upsert_daily_rsi(df)
            return symbol, True, f"{rows} new rows"
            
        except Exception as e:
            logger.error(f"Daily RSI error for {symbol}: {e}")
            return symbol, False, str(e)
    
    def _calc_intraday_rsi_symbol(self, symbol: str, interval: str) -> Tuple[str, str, bool, str]:
        """Calculate intraday RSI for a single symbol/interval (worker function) - INCREMENTAL"""
        try:
            engine = self.db.get_engine()
            table_name = f"yfinance_intraday_rsi_{interval.replace('m', 'min')}"
            
            # Check last calculated datetime
            last_calc_query = f"SELECT MAX(datetime) as last_dt FROM {table_name} WHERE symbol = %s"
            last_calc = pd.read_sql(last_calc_query, engine, params=(symbol,))
            last_calc_dt = last_calc['last_dt'].iloc[0] if not last_calc.empty and last_calc['last_dt'].iloc[0] else None
            
            # Check last data datetime
            last_data_query = """
                SELECT MAX(datetime) as last_dt FROM yfinance_intraday_quotes 
                WHERE symbol = %s AND timeframe = %s
            """
            last_data = pd.read_sql(last_data_query, engine, params=(symbol, interval))
            last_data_dt = last_data['last_dt'].iloc[0] if not last_data.empty and last_data['last_dt'].iloc[0] else None
            
            # Skip if already calculated up to latest data
            if last_calc_dt and last_data_dt:
                if pd.to_datetime(last_calc_dt) >= pd.to_datetime(last_data_dt):
                    return symbol, interval, True, "up to date"
            
            query = """
                SELECT datetime, close FROM yfinance_intraday_quotes 
                WHERE symbol = %s AND timeframe = %s ORDER BY datetime
            """
            df = pd.read_sql(query, engine, params=(symbol, interval))
            
            if len(df) < RSI_PERIOD + 1:
                return symbol, interval, True, "insufficient data"
            
            df['symbol'] = symbol
            df['rsi_9'] = calculate_rsi(df['close'], RSI_PERIOD)
            df = df.dropna(subset=['rsi_9'])
            
            if df.empty:
                return symbol, interval, True, "no valid data"
            
            # Filter to only new datetimes if we have last_calc_dt
            if last_calc_dt:
                df = df[df['datetime'] > last_calc_dt]
            
            if df.empty:
                return symbol, interval, True, "up to date"
            
            rows = self._batch_upsert_intraday_rsi(df, table_name)
            return symbol, interval, True, f"{rows} new rows"
            
        except Exception as e:
            logger.error(f"Intraday RSI error for {symbol} {interval}: {e}")
            return symbol, interval, False, str(e)
    
    def step6_calculate_rsi(self) -> Tuple[bool, str]:
        """Calculate RSI for daily and intraday data (PARALLEL)"""
        step_id = 6
        self.failed_symbols = []
        
        try:
            total_daily = len(self.all_symbols)
            tasks_intraday = [(symbol, interval) for symbol in self.all_symbols for interval in INTRADAY_INTERVALS]
            total_intraday = len(tasks_intraday)
            grand_total = total_daily + total_intraday
            
            processed = 0
            success_count = 0
            
            # Start tracking this step
            self.state_manager.start_step(step_id, "Calculate RSI", grand_total)
            
            self.progress_callback(0, "Calculating RSI (daily + intraday)...")
            
            # Part A: Daily RSI (parallel)
            with ThreadPoolExecutor(max_workers=MAX_WORKERS_CALCULATE) as executor:
                futures = {
                    executor.submit(self._calc_daily_rsi_symbol, symbol): symbol
                    for symbol in self.all_symbols
                }
                
                for future in as_completed(futures):
                    if self.stop_requested:
                        executor.shutdown(wait=False, cancel_futures=True)
                        self.state_manager.complete_step(step_id, False, "Stopped by user", self.failed_symbols)
                        return False, "Stopped by user"
                    
                    symbol, success, msg = future.result()
                    processed += 1
                    if success:
                        success_count += 1
                    else:
                        self.failed_symbols.append(symbol)
                    
                    # Update state periodically
                    self.state_manager.update_step_progress(step_id, processed, self.failed_symbols)
                    
                    self.progress_callback(
                        int(processed / grand_total * 100),
                        f"Daily RSI: {symbol} ({msg}) [{processed}/{grand_total}]"
                    )
            
            # Part B: Intraday RSI (parallel)
            with ThreadPoolExecutor(max_workers=MAX_WORKERS_CALCULATE) as executor:
                futures = {
                    executor.submit(self._calc_intraday_rsi_symbol, symbol, interval): (symbol, interval)
                    for symbol, interval in tasks_intraday
                }
                
                for future in as_completed(futures):
                    if self.stop_requested:
                        executor.shutdown(wait=False, cancel_futures=True)
                        self.state_manager.complete_step(step_id, False, "Stopped by user", self.failed_symbols)
                        return False, "Stopped by user"
                    
                    symbol, interval, success, msg = future.result()
                    processed += 1
                    if success:
                        success_count += 1
                    else:
                        self.failed_symbols.append(f"{symbol}:{interval}")
                    
                    # Update state periodically
                    self.state_manager.update_step_progress(step_id, processed, self.failed_symbols)
                    
                    self.progress_callback(
                        int(processed / grand_total * 100),
                        f"Intraday RSI: {symbol} ({interval}) [{processed}/{grand_total}]"
                    )
            
            # Mark step complete
            msg = f"RSI calculation complete: {success_count}/{grand_total} processed"
            self.state_manager.complete_step(step_id, True, msg, self.failed_symbols)
            return True, msg
            
        except Exception as e:
            logger.error(f"Step 6 failed: {e}")
            self.state_manager.complete_step(step_id, False, str(e), self.failed_symbols)
            return False, str(e)


# =============================================================================
# WIZARD GUI
# =============================================================================

class DailyDataWizardGUI:
    """Daily Data Wizard GUI"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🧙 Daily Data Wizard")
        self.root.geometry("900x900")
        
        # Services
        self.db = WizardDBService()
        self.state_manager = WizardStateManager()
        self.executor = None
        
        # State
        self.is_running = False
        self.current_step = 0
        
        # Define steps
        self.steps = [
            WizardStep(1, "Sync Daily Data", "Download/sync daily OHLCV data for all Nifty 500 stocks and indices"),
            WizardStep(2, "Sync Intraday Data", "Download 1min, 5min, 60min intraday data for all stocks"),
            WizardStep(3, "Verify Data Sync", "Verify data is synchronized with Yahoo Finance"),
            WizardStep(4, "Calculate Daily MA", "Calculate EMA(21), SMA(5,50,150,200) for daily data"),
            WizardStep(5, "Calculate Intraday MA", "Calculate EMA(21), SMA(50,200) for 1min, 5min, 60min data"),
            WizardStep(6, "Calculate RSI", "Calculate 9-period RSI for daily and intraday data"),
        ]
        
        # Colors
        self.colors = {
            'bg': '#f5f7fa',
            'card': '#ffffff',
            'primary': '#2563eb',
            'success': '#16a34a',
            'warning': '#ea580c',
            'error': '#dc2626',
            'text': '#0f172a',
            'secondary': '#64748b',
            'pending': '#94a3b8',
            'running': '#3b82f6',
        }
        
        self.root.configure(bg=self.colors['bg'])
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main container
        main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(
            title_frame,
            text="🧙 Daily Data Wizard",
            font=('Segoe UI', 24, 'bold'),
            fg=self.colors['primary'],
            bg=self.colors['bg']
        ).pack(side=tk.LEFT)
        
        tk.Label(
            title_frame,
            text=f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            font=('Segoe UI', 11),
            fg=self.colors['secondary'],
            bg=self.colors['bg']
        ).pack(side=tk.RIGHT)
        
        # Steps list
        steps_frame = tk.LabelFrame(
            main_frame, text="Wizard Steps",
            font=('Segoe UI', 12, 'bold'),
            fg=self.colors['text'], bg=self.colors['card']
        )
        steps_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.step_widgets = []
        self.step_frames = []  # Track frames for refresh
        for step in self.steps:
            step_widget = self._create_step_widget(steps_frame, step)
            self.step_widgets.append(step_widget)
            self.step_frames.append(step_widget['frame'])
        
        # Progress section
        progress_frame = tk.Frame(main_frame, bg=self.colors['card'])
        progress_frame.pack(fill=tk.X, pady=10)
        
        self.overall_label = tk.Label(
            progress_frame,
            text="Overall Progress: 0%",
            font=('Segoe UI', 11, 'bold'),
            fg=self.colors['text'],
            bg=self.colors['card']
        )
        self.overall_label.pack(anchor='w', padx=10, pady=5)
        
        self.overall_progress = ttk.Progressbar(
            progress_frame, length=800, mode='determinate'
        )
        self.overall_progress.pack(padx=10, pady=5)
        
        self.status_label = tk.Label(
            progress_frame,
            text="Click 'Start Wizard' to begin",
            font=('Segoe UI', 10),
            fg=self.colors['secondary'],
            bg=self.colors['card']
        )
        self.status_label.pack(anchor='w', padx=10, pady=5)
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        button_frame.pack(fill=tk.X, pady=10)
        
        self.start_btn = tk.Button(
            button_frame, text="▶️ Start Wizard",
            command=self.start_wizard,
            font=('Segoe UI', 12, 'bold'),
            fg='white', bg=self.colors['primary'],
            activebackground='#1d4ed8',
            relief='flat', cursor='hand2', padx=30, pady=10
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = tk.Button(
            button_frame, text="⏹️ Stop",
            command=self.stop_wizard,
            font=('Segoe UI', 12, 'bold'),
            fg='white', bg=self.colors['error'],
            activebackground='#b91c1c',
            relief='flat', cursor='hand2', padx=30, pady=10,
            state='disabled'
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.reset_btn = tk.Button(
            button_frame, text="🔄 Reset",
            command=self.reset_wizard,
            font=('Segoe UI', 12),
            fg=self.colors['text'], bg='#e2e8f0',
            relief='flat', cursor='hand2', padx=20, pady=10
        )
        self.reset_btn.pack(side=tk.LEFT, padx=5)
        
        # Log area
        log_frame = tk.LabelFrame(
            main_frame, text="Log",
            font=('Segoe UI', 10, 'bold'),
            fg=self.colors['text'], bg=self.colors['card']
        )
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_text = tk.Text(
            log_frame, height=8, font=('Consolas', 9),
            bg='#1e293b', fg='#e2e8f0', wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(self.log_text, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
    
    def _create_step_widget(self, parent, step: WizardStep) -> dict:
        """Create a widget for a wizard step"""
        frame = tk.Frame(parent, bg=self.colors['card'])
        frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Status indicator
        status_label = tk.Label(
            frame, text="○",
            font=('Segoe UI', 14),
            fg=self.colors['pending'],
            bg=self.colors['card'], width=3
        )
        status_label.pack(side=tk.LEFT)
        
        # Step info
        info_frame = tk.Frame(frame, bg=self.colors['card'])
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        name_label = tk.Label(
            info_frame,
            text=f"Step {step.id}: {step.name}",
            font=('Segoe UI', 11, 'bold'),
            fg=self.colors['text'],
            bg=self.colors['card'],
            anchor='w'
        )
        name_label.pack(anchor='w')
        
        desc_label = tk.Label(
            info_frame,
            text=step.description,
            font=('Segoe UI', 9),
            fg=self.colors['secondary'],
            bg=self.colors['card'],
            anchor='w'
        )
        desc_label.pack(anchor='w')
        
        # Last run status label
        last_run_summary = self.state_manager.get_step_summary(step.id)
        last_run_label = tk.Label(
            info_frame,
            text=f"Last: {last_run_summary}",
            font=('Segoe UI', 8),
            fg=self.colors['secondary'],
            bg=self.colors['card'],
            anchor='w'
        )
        last_run_label.pack(anchor='w')
        
        # Progress bar
        progress = ttk.Progressbar(frame, length=150, mode='determinate')
        progress.pack(side=tk.RIGHT, padx=10)
        
        # Duration label
        duration_label = tk.Label(
            frame, text="--:--:--",
            font=('Segoe UI', 9),
            fg=self.colors['secondary'],
            bg=self.colors['card'], width=10
        )
        duration_label.pack(side=tk.RIGHT)
        
        return {
            'frame': frame,
            'status': status_label,
            'name': name_label,
            'desc': desc_label,
            'last_run': last_run_label,
            'progress': progress,
            'duration': duration_label
        }
    
    def _update_step_widget(self, step_idx: int, step: WizardStep):
        """Update a step widget"""
        widget = self.step_widgets[step_idx]
        
        status_symbols = {
            StepStatus.PENDING: ("○", self.colors['pending']),
            StepStatus.RUNNING: ("●", self.colors['running']),
            StepStatus.COMPLETED: ("✓", self.colors['success']),
            StepStatus.FAILED: ("✗", self.colors['error']),
            StepStatus.SKIPPED: ("−", self.colors['warning']),
        }
        
        symbol, color = status_symbols.get(step.status, ("○", self.colors['pending']))
        widget['status'].configure(text=symbol, fg=color)
        widget['progress']['value'] = step.progress
        widget['duration'].configure(text=step.duration)
    
    def log(self, message: str):
        """Add message to log"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
    
    def start_wizard(self):
        """Start the wizard"""
        self.is_running = True
        self.start_btn.configure(state='disabled')
        self.stop_btn.configure(state='normal')
        self.reset_btn.configure(state='disabled')
        
        # Ensure tables exist
        self.log("Ensuring database tables exist...")
        self.db.ensure_tables_exist()
        self.log("Database tables ready")
        
        # Start execution in background
        thread = threading.Thread(target=self._run_wizard)
        thread.daemon = True
        thread.start()
    
    def stop_wizard(self):
        """Stop the wizard"""
        if self.executor:
            self.executor.stop()
        self.is_running = False
        self.log("Stop requested...")
    
    def reset_wizard(self):
        """Reset the wizard"""
        for i, step in enumerate(self.steps):
            step.status = StepStatus.PENDING
            step.progress = 0
            step.message = ""
            step.start_time = None
            step.end_time = None
            self._update_step_widget(i, step)
        
        self.overall_progress['value'] = 0
        self.overall_label.configure(text="Overall Progress: 0%")
        self.status_label.configure(text="Click 'Start Wizard' to begin")
        self.current_step = 0
        self.start_btn.configure(state='normal')
        self.stop_btn.configure(state='disabled')
    
    def _run_wizard(self):
        """Run the wizard steps"""
        # Create executor FIRST with state manager for persistence
        self.executor = WizardStepsExecutor(self.db, self._step_progress_callback, self.state_manager)
        
        step_methods = [
            self.executor.step1_sync_daily_data,
            self.executor.step2_sync_intraday_data,
            self.executor.step3_verify_data_sync,
            self.executor.step4_calculate_daily_ma,
            self.executor.step5_calculate_intraday_ma,
            self.executor.step6_calculate_rsi,
        ]
        
        for i, (step, method) in enumerate(zip(self.steps, step_methods)):
            if not self.is_running:
                step.status = StepStatus.SKIPPED
                self._update_step_widget(i, step)
                continue
            
            self.current_step = i
            step.status = StepStatus.RUNNING
            step.start_time = datetime.now()
            step.progress = 0
            self._update_step_widget(i, step)
            
            self.root.after(0, lambda s=step: self.log(f"Starting: {s.name}"))
            self.root.after(0, lambda s=step: self.status_label.configure(text=f"Running: {s.name}"))
            
            try:
                success, message = method()
                step.end_time = datetime.now()
                step.message = message
                
                if success:
                    step.status = StepStatus.COMPLETED
                    step.progress = 100
                else:
                    step.status = StepStatus.FAILED
                
                self.root.after(0, lambda m=message: self.log(m))
                
            except Exception as e:
                step.status = StepStatus.FAILED
                step.end_time = datetime.now()
                step.message = str(e)
                self.root.after(0, lambda e=e: self.log(f"Error: {e}"))
            
            self._update_step_widget(i, step)
            
            # Update overall progress
            completed = sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)
            overall = int(completed / len(self.steps) * 100)
            self.root.after(0, lambda p=overall: self.overall_progress.configure(value=p))
            self.root.after(0, lambda p=overall: self.overall_label.configure(text=f"Overall Progress: {p}%"))
        
        self.is_running = False
        self.root.after(0, lambda: self.start_btn.configure(state='normal'))
        self.root.after(0, lambda: self.stop_btn.configure(state='disabled'))
        self.root.after(0, lambda: self.reset_btn.configure(state='normal'))
        self.root.after(0, lambda: self.status_label.configure(text="Wizard completed!"))
        self.root.after(0, lambda: self.log("Wizard completed!"))
        # Refresh last run labels to show updated status
        self.root.after(0, self._refresh_last_run_labels)
    
    def _refresh_last_run_labels(self):
        """Refresh the last run status labels for all steps"""
        for i, step in enumerate(self.steps):
            summary = self.state_manager.get_step_summary(step.id)
            # Use step_widgets directly which has 'last_run' key
            if i < len(self.step_widgets):
                widget = self.step_widgets[i]
                if 'last_run' in widget:
                    widget['last_run'].configure(text=f"Last: {summary}")
    
    def _step_progress_callback(self, progress: int, message: str):
        """Callback for step progress updates"""
        if self.current_step < len(self.steps):
            step = self.steps[self.current_step]
            step.progress = progress
            self.root.after(0, lambda: self._update_step_widget(self.current_step, step))
            self.root.after(0, lambda m=message: self.status_label.configure(text=m))
    
    def run(self):
        """Start the GUI"""
        self.root.mainloop()


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main entry point"""
    app = DailyDataWizardGUI()
    app.run()


if __name__ == "__main__":
    main()
