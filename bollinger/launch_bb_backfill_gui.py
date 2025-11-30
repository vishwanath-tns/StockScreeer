#!/usr/bin/env python3
"""
Historical Bollinger Bands Backfill GUI

GUI application to compute and store historical BB indicators for all stocks AND indices.
Uses Yahoo Finance daily data (yfinance_daily_quotes table).
Features parallel processing with real-time progress visualization.

Usage:
    python bollinger/launch_bb_backfill_gui.py
"""

import sys
import os
import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
import threading
import queue

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QTableWidget, QTableWidgetItem,
    QGroupBox, QSpinBox, QDateEdit, QTextEdit, QSplitter,
    QHeaderView, QMessageBox, QCheckBox, QFrame, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDate, QTimer
from PyQt6.QtGui import QFont, QColor, QBrush

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SymbolProgress:
    """Progress tracking for a single symbol."""
    symbol: str
    status: str = "pending"  # pending, running, completed, failed
    records: int = 0
    error: str = ""
    start_time: datetime = None
    end_time: datetime = None
    
    @property
    def duration_ms(self) -> int:
        if self.start_time and self.end_time:
            return int((self.end_time - self.start_time).total_seconds() * 1000)
        return 0


class BBCalculator:
    """Bollinger Bands calculator for a single symbol using Yahoo Finance data."""
    
    def __init__(self, engine: Engine):
        self.engine = engine
    
    def fetch_ohlc(self, symbol: str, start_date: date, end_date: date, is_index: bool = False) -> pd.DataFrame:
        """Fetch OHLC data from Yahoo Finance tables with buffer for BB calculation."""
        buffer_start = start_date - timedelta(days=90)  # Extra buffer for BB calc
        
        # Use appropriate table based on symbol type
        table = 'yfinance_daily_quotes'
        
        query = f"""
            SELECT date as trade_date, open, high, low, close, volume
            FROM {table}
            WHERE symbol = :symbol
              AND date BETWEEN :start AND :end
            ORDER BY date ASC
        """
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(query), conn, params={
                'symbol': symbol, 'start': buffer_start, 'end': end_date
            })
        return df
    
    def get_existing_dates(self, symbol: str) -> set:
        """Get dates already in database."""
        query = "SELECT trade_date FROM stock_bollinger_daily WHERE symbol = :symbol"
        with self.engine.connect() as conn:
            result = conn.execute(text(query), {"symbol": symbol})
            return {row[0] for row in result}
    
    def calculate_bb(self, df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
        """Calculate BB indicators for the dataframe."""
        if len(df) < period:
            return pd.DataFrame()
        
        df = df.copy()
        
        # Middle band (SMA)
        df['middle_band'] = df['close'].rolling(window=period).mean()
        df['std'] = df['close'].rolling(window=period).std()
        
        # Upper and lower bands
        df['upper_band'] = df['middle_band'] + (std_dev * df['std'])
        df['lower_band'] = df['middle_band'] - (std_dev * df['std'])
        
        # %b and Bandwidth
        df['percent_b'] = (df['close'] - df['lower_band']) / (df['upper_band'] - df['lower_band'])
        df['bandwidth'] = ((df['upper_band'] - df['lower_band']) / df['middle_band']) * 100
        
        # Bandwidth percentile (126-day rolling)
        df['bandwidth_percentile'] = df['bandwidth'].rolling(window=126, min_periods=20).apply(
            lambda x: (x.values < x.values[-1]).sum() / len(x) * 100 if len(x) > 0 else 50
        )
        
        # Squeeze and Bulge detection
        df['is_squeeze'] = df['bandwidth_percentile'] <= 10
        df['is_bulge'] = df['bandwidth_percentile'] >= 90
        
        # Squeeze days count
        df['squeeze_days'] = 0
        squeeze_count = 0
        for i in range(len(df)):
            if df.iloc[i]['is_squeeze']:
                squeeze_count += 1
            else:
                squeeze_count = 0
            df.iloc[i, df.columns.get_loc('squeeze_days')] = squeeze_count
        
        # Trend classification
        df['pb_avg'] = df['percent_b'].rolling(window=5).mean()
        
        def classify_trend(pb):
            if pd.isna(pb):
                return 'neutral', 50.0
            if pb > 0.7:
                return 'uptrend', min((pb - 0.5) * 200, 100)
            elif pb < 0.3:
                return 'downtrend', min((0.5 - pb) * 200, 100)
            return 'neutral', 50 - abs(pb - 0.5) * 100
        
        trends = df['pb_avg'].apply(classify_trend)
        df['trend'] = trends.apply(lambda x: x[0])
        df['trend_strength'] = trends.apply(lambda x: x[1])
        
        # Trend days
        df['trend_days'] = 1
        last_trend = None
        count = 0
        for i in range(len(df)):
            t = df.iloc[i]['trend']
            if t == last_trend and t != 'neutral':
                count += 1
            else:
                count = 1
            df.iloc[i, df.columns.get_loc('trend_days')] = count
            last_trend = t
        
        # Distance from middle
        df['distance_from_middle'] = ((df['close'] - df['middle_band']) / df['middle_band']) * 100
        df['sma_20'] = df['middle_band']
        
        return df.dropna(subset=['middle_band', 'percent_b'])
    
    def process_symbol(self, symbol: str, start_date: date, end_date: date, 
                       skip_existing: bool = True) -> Tuple[int, str]:
        """Process a symbol and return (records_inserted, error_message)."""
        try:
            # Get existing dates
            existing = self.get_existing_dates(symbol) if skip_existing else set()
            
            # Fetch OHLC
            df = self.fetch_ohlc(symbol, start_date, end_date)
            if df.empty or len(df) < 30:
                return 0, f"Insufficient data ({len(df)} rows)"
            
            # Calculate BB
            bb_df = self.calculate_bb(df)
            if bb_df.empty:
                return 0, "BB calculation failed"
            
            # Filter date range and skip existing
            bb_df = bb_df[(bb_df['trade_date'] >= start_date) & (bb_df['trade_date'] <= end_date)]
            if existing:
                bb_df = bb_df[~bb_df['trade_date'].isin(existing)]
            
            if bb_df.empty:
                return 0, ""  # All dates exist
            
            # Prepare insert
            bb_df['symbol'] = symbol
            columns = [
                'symbol', 'trade_date', 'close', 'upper_band', 'middle_band',
                'lower_band', 'percent_b', 'bandwidth', 'bandwidth_percentile',
                'is_squeeze', 'is_bulge', 'squeeze_days', 'trend',
                'trend_strength', 'trend_days', 'sma_20', 'distance_from_middle'
            ]
            
            insert_df = bb_df[columns]
            
            with self.engine.begin() as conn:
                insert_df.to_sql('stock_bollinger_daily', conn, if_exists='append',
                               index=False, method='multi', chunksize=500)
            
            return len(insert_df), ""
            
        except Exception as e:
            return 0, str(e)


class BackfillWorker(QThread):
    """Worker thread for parallel backfill processing."""
    
    # Signals
    symbol_started = pyqtSignal(str)
    symbol_completed = pyqtSignal(str, int, str)  # symbol, records, error
    progress_update = pyqtSignal(int, int, int, int)  # completed, failed, total, records
    finished_all = pyqtSignal()
    log_message = pyqtSignal(str)
    
    def __init__(self, engine: Engine, symbols: List[str], 
                 start_date: date, end_date: date,
                 workers: int = 4, skip_existing: bool = True):
        super().__init__()
        self.engine = engine
        self.symbols = symbols
        self.start_date = start_date
        self.end_date = end_date
        self.workers = workers
        self.skip_existing = skip_existing
        self.is_cancelled = False
        
    def cancel(self):
        self.is_cancelled = True
    
    def run(self):
        calculator = BBCalculator(self.engine)
        completed = 0
        failed = 0
        total_records = 0
        total = len(self.symbols)
        
        self.log_message.emit(f"Starting backfill for {total} symbols with {self.workers} workers...")
        
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            # Submit all tasks
            futures = {}
            for symbol in self.symbols:
                if self.is_cancelled:
                    break
                future = executor.submit(
                    calculator.process_symbol,
                    symbol, self.start_date, self.end_date, self.skip_existing
                )
                futures[future] = symbol
            
            # Process completed futures
            for future in as_completed(futures):
                if self.is_cancelled:
                    break
                    
                symbol = futures[future]
                self.symbol_started.emit(symbol)
                
                try:
                    records, error = future.result()
                    
                    if error:
                        failed += 1
                        self.symbol_completed.emit(symbol, 0, error)
                    else:
                        completed += 1
                        total_records += records
                        self.symbol_completed.emit(symbol, records, "")
                        
                except Exception as e:
                    failed += 1
                    self.symbol_completed.emit(symbol, 0, str(e))
                
                self.progress_update.emit(completed, failed, total, total_records)
        
        self.log_message.emit(f"Backfill complete: {completed} succeeded, {failed} failed, {total_records:,} records")
        self.finished_all.emit()


class BBBackfillGUI(QMainWindow):
    """Main GUI for historical BB backfill."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📊 Bollinger Bands Historical Backfill")
        self.setMinimumSize(1200, 800)
        
        self.engine = self._get_engine()
        self.worker = None
        self.symbol_progress: Dict[str, SymbolProgress] = {}
        
        self._setup_ui()
        self._load_symbols()
    
    def _get_engine(self) -> Engine:
        """Create database engine."""
        from urllib.parse import quote_plus
        
        host = os.getenv('MYSQL_HOST', 'localhost')
        port = os.getenv('MYSQL_PORT', '3306')
        user = os.getenv('MYSQL_USER', 'root')
        password = os.getenv('MYSQL_PASSWORD', '')
        database = os.getenv('MYSQL_DB', 'stockdata')
        
        # URL-encode password to handle special characters like @
        encoded_password = quote_plus(password)
        
        conn_str = f"mysql+pymysql://{user}:{encoded_password}@{host}:{port}/{database}?charset=utf8mb4"
        return create_engine(conn_str, pool_pre_ping=True, pool_size=10)
    
    def _setup_ui(self):
        """Setup the user interface."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        
        # Header
        header = QLabel("📊 Bollinger Bands Historical Backfill")
        header.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Configuration section
        config_group = QGroupBox("Configuration")
        config_layout = QHBoxLayout(config_group)
        
        # Date range
        config_layout.addWidget(QLabel("Start Date:"))
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate(2020, 1, 1))
        self.start_date.setCalendarPopup(True)
        config_layout.addWidget(self.start_date)
        
        config_layout.addWidget(QLabel("End Date:"))
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        config_layout.addWidget(self.end_date)
        
        config_layout.addSpacing(20)
        
        # Workers
        config_layout.addWidget(QLabel("Workers:"))
        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(1, 16)
        self.workers_spin.setValue(4)
        config_layout.addWidget(self.workers_spin)
        
        config_layout.addSpacing(20)
        
        # Skip existing
        self.skip_existing = QCheckBox("Skip existing dates")
        self.skip_existing.setChecked(True)
        config_layout.addWidget(self.skip_existing)
        
        config_layout.addStretch()
        layout.addWidget(config_group)
        
        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        # Overall progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(30)
        self.progress_bar.setFormat("%v / %m symbols (%p%)")
        progress_layout.addWidget(self.progress_bar)
        
        # Stats row
        stats_layout = QHBoxLayout()
        
        self.completed_label = QLabel("Completed: 0")
        self.completed_label.setStyleSheet("color: green; font-weight: bold;")
        stats_layout.addWidget(self.completed_label)
        
        self.failed_label = QLabel("Failed: 0")
        self.failed_label.setStyleSheet("color: red; font-weight: bold;")
        stats_layout.addWidget(self.failed_label)
        
        self.records_label = QLabel("Records: 0")
        self.records_label.setStyleSheet("color: blue; font-weight: bold;")
        stats_layout.addWidget(self.records_label)
        
        self.speed_label = QLabel("Speed: -- records/sec")
        stats_layout.addWidget(self.speed_label)
        
        stats_layout.addStretch()
        progress_layout.addLayout(stats_layout)
        
        layout.addWidget(progress_group)
        
        # Splitter for table and log
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Symbol progress table
        table_group = QGroupBox("Symbol Progress")
        table_layout = QVBoxLayout(table_group)
        
        self.progress_table = QTableWidget()
        self.progress_table.setColumnCount(5)
        self.progress_table.setHorizontalHeaderLabels([
            "Symbol", "Status", "Records", "Duration (ms)", "Error"
        ])
        self.progress_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.progress_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.progress_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.progress_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.progress_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.progress_table.setAlternatingRowColors(True)
        table_layout.addWidget(self.progress_table)
        
        splitter.addWidget(table_group)
        
        # Log
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)
        
        splitter.addWidget(log_group)
        splitter.setSizes([500, 150])
        
        layout.addWidget(splitter)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶ Start Backfill")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.start_btn.clicked.connect(self._start_backfill)
        button_layout.addWidget(self.start_btn)
        
        self.cancel_btn = QPushButton("⏹ Cancel")
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_backfill)
        button_layout.addWidget(self.cancel_btn)
        
        self.create_tables_btn = QPushButton("🗃 Create Tables")
        self.create_tables_btn.setMinimumHeight(40)
        self.create_tables_btn.clicked.connect(self._create_tables)
        button_layout.addWidget(self.create_tables_btn)
        
        layout.addLayout(button_layout)
        
        # Status bar
        self.statusBar().showMessage("Ready. Click 'Start Backfill' to begin.")
        
        # Timer for speed calculation
        self.start_time = None
        self.speed_timer = QTimer()
        self.speed_timer.timeout.connect(self._update_speed)
    
    def _load_symbols(self):
        """Load symbols from Yahoo Finance database (stocks + indices)."""
        try:
            # Load stocks from yfinance_daily_quotes
            stocks_query = """
                SELECT DISTINCT symbol 
                FROM yfinance_daily_quotes 
                WHERE symbol NOT LIKE '^%%'
                ORDER BY symbol
            """
            
            # Load indices (symbols starting with ^)
            indices_query = """
                SELECT DISTINCT symbol 
                FROM yfinance_daily_quotes 
                WHERE symbol LIKE '^%%'
                ORDER BY symbol
            """
            
            with self.engine.connect() as conn:
                stocks_result = conn.execute(text(stocks_query))
                stocks = [row[0] for row in stocks_result]
                
                indices_result = conn.execute(text(indices_query))
                indices = [row[0] for row in indices_result]
            
            # Combine: indices first, then stocks
            self.symbols = indices + stocks
            self.indices_set = set(indices)
            
            self.progress_bar.setMaximum(len(self.symbols))
            self._log(f"Loaded {len(self.symbols)} symbols ({len(indices)} indices + {len(stocks)} stocks) from Yahoo Finance")
            
            # Initialize progress table
            self.progress_table.setRowCount(len(self.symbols))
            for i, symbol in enumerate(self.symbols):
                self.progress_table.setItem(i, 0, QTableWidgetItem(symbol))
                self.progress_table.setItem(i, 1, QTableWidgetItem("pending"))
                self.progress_table.setItem(i, 2, QTableWidgetItem("-"))
                self.progress_table.setItem(i, 3, QTableWidgetItem("-"))
                self.progress_table.setItem(i, 4, QTableWidgetItem(""))
                self.symbol_progress[symbol] = SymbolProgress(symbol=symbol)
                
        except Exception as e:
            self._log(f"Error loading symbols: {e}")
            self.symbols = []
    
    def _log(self, message: str):
        """Add message to log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
    
    def _create_tables(self):
        """Create BB tables in database."""
        try:
            from bollinger.services.daily_bb_compute import create_bb_tables
            create_bb_tables(self.engine)
            self._log("BB tables created successfully")
            QMessageBox.information(self, "Success", "BB tables created successfully!")
        except Exception as e:
            self._log(f"Error creating tables: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create tables:\n{e}")
    
    def _start_backfill(self):
        """Start the backfill process."""
        if not self.symbols:
            QMessageBox.warning(self, "No Symbols", "No symbols loaded from database")
            return
        
        # Reset UI
        self.progress_bar.setValue(0)
        self.completed_label.setText("Completed: 0")
        self.failed_label.setText("Failed: 0")
        self.records_label.setText("Records: 0")
        
        # Reset table
        for i, symbol in enumerate(self.symbols):
            self.progress_table.item(i, 1).setText("pending")
            self.progress_table.item(i, 1).setBackground(QBrush(QColor(255, 255, 255)))
            self.progress_table.item(i, 2).setText("-")
            self.progress_table.item(i, 3).setText("-")
            self.progress_table.item(i, 4).setText("")
            self.symbol_progress[symbol] = SymbolProgress(symbol=symbol)
        
        # Get config
        start_date = self.start_date.date().toPyDate()
        end_date = self.end_date.date().toPyDate()
        workers = self.workers_spin.value()
        skip = self.skip_existing.isChecked()
        
        self._log(f"Starting backfill: {start_date} to {end_date}, {workers} workers")
        
        # Create and start worker
        self.worker = BackfillWorker(
            self.engine, self.symbols, start_date, end_date, workers, skip
        )
        self.worker.symbol_started.connect(self._on_symbol_started)
        self.worker.symbol_completed.connect(self._on_symbol_completed)
        self.worker.progress_update.connect(self._on_progress_update)
        self.worker.finished_all.connect(self._on_finished)
        self.worker.log_message.connect(self._log)
        
        self.worker.start()
        
        # Update UI state
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.start_time = datetime.now()
        self.speed_timer.start(1000)
        self.statusBar().showMessage("Backfill in progress...")
    
    def _cancel_backfill(self):
        """Cancel the backfill."""
        if self.worker:
            self.worker.cancel()
            self._log("Cancelling backfill...")
    
    def _on_symbol_started(self, symbol: str):
        """Handle symbol started."""
        if symbol in self.symbol_progress:
            self.symbol_progress[symbol].status = "running"
            self.symbol_progress[symbol].start_time = datetime.now()
            
            # Update table
            row = self.symbols.index(symbol) if symbol in self.symbols else -1
            if row >= 0:
                self.progress_table.item(row, 1).setText("running")
                self.progress_table.item(row, 1).setBackground(QBrush(QColor(255, 255, 150)))
    
    def _on_symbol_completed(self, symbol: str, records: int, error: str):
        """Handle symbol completed."""
        if symbol not in self.symbol_progress:
            return
            
        prog = self.symbol_progress[symbol]
        prog.end_time = datetime.now()
        prog.records = records
        prog.error = error
        prog.status = "failed" if error else "completed"
        
        # Update table
        row = self.symbols.index(symbol) if symbol in self.symbols else -1
        if row >= 0:
            if error:
                self.progress_table.item(row, 1).setText("failed")
                self.progress_table.item(row, 1).setBackground(QBrush(QColor(255, 200, 200)))
                self.progress_table.item(row, 4).setText(error[:50])
            else:
                self.progress_table.item(row, 1).setText("completed")
                self.progress_table.item(row, 1).setBackground(QBrush(QColor(200, 255, 200)))
            
            self.progress_table.item(row, 2).setText(str(records))
            self.progress_table.item(row, 3).setText(str(prog.duration_ms))
    
    def _on_progress_update(self, completed: int, failed: int, total: int, records: int):
        """Handle progress update."""
        self.progress_bar.setValue(completed + failed)
        self.completed_label.setText(f"Completed: {completed}")
        self.failed_label.setText(f"Failed: {failed}")
        self.records_label.setText(f"Records: {records:,}")
    
    def _update_speed(self):
        """Update speed calculation."""
        if self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            if elapsed > 0:
                records = int(self.records_label.text().split(": ")[1].replace(",", ""))
                speed = records / elapsed
                self.speed_label.setText(f"Speed: {speed:.0f} records/sec")
    
    def _on_finished(self):
        """Handle backfill finished."""
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.speed_timer.stop()
        
        elapsed = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        self.statusBar().showMessage(f"Backfill completed in {elapsed:.1f} seconds")
        self._log(f"Backfill finished in {elapsed:.1f} seconds")
        
        QMessageBox.information(self, "Complete", 
            f"Backfill completed!\n\n"
            f"Completed: {self.completed_label.text()}\n"
            f"Failed: {self.failed_label.text()}\n"
            f"Records: {self.records_label.text()}\n"
            f"Duration: {elapsed:.1f} seconds"
        )


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = BBBackfillGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
