#!/usr/bin/env python3
"""
Launch Bollinger Bands Scanner GUI

Quick launcher for the BB scanner interface.
Provides access to all scanner types: squeeze, bulge, trend, pullback, reversion.
"""

import sys
import os
from pathlib import Path
from datetime import date, timedelta
from typing import Dict, List, Optional, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QTabWidget, QGroupBox, QSpinBox, QProgressBar, QStatusBar,
    QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

from bollinger import (
    SqueezeScanner, BulgeScanner, TrendScanner,
    PullbackScanner, MeanReversionScanner,
    BBCalculator, BBConfig
)
from bollinger.models import BollingerBands
from bollinger.db import check_bb_tables_exist, get_bb_engine


class ScanWorker(QThread):
    """Background worker for running scans."""
    
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)  # (percent, message)
    
    def __init__(self, scanner_type: int, engine: Engine):
        super().__init__()
        self.scanner_type = scanner_type
        self.engine = engine
    
    def run(self):
        try:
            self.progress.emit(10, "Fetching BB data from database...")
            
            # Fetch BB data for all symbols (recent 30 days for scanning)
            bb_data = self._fetch_bb_data()
            
            if not bb_data:
                self.error.emit("No BB data found in database. Run BB Backfill first.")
                return
            
            self.progress.emit(50, f"Scanning {len(bb_data)} symbols...")
            
            # Get the appropriate scan function and run
            scan_func = self._get_scan_function()
            results = scan_func(bb_data)
            
            self.progress.emit(100, f"Found {len(results)} matches")
            self.finished.emit(results)
            
        except Exception as e:
            import traceback
            self.error.emit(f"{str(e)}\n\n{traceback.format_exc()}")
    
    def _get_scan_function(self):
        """Get the appropriate scan function based on scanner type."""
        if self.scanner_type == 0:
            # Squeeze Scanner
            scanner = SqueezeScanner(squeeze_threshold=10.0, min_squeeze_days=3)
            return scanner.scan
        elif self.scanner_type == 1:
            # Bulge Scanner
            scanner = BulgeScanner()
            return scanner.scan
        elif self.scanner_type == 2:
            # Uptrend Scanner
            scanner = TrendScanner()
            return scanner.scan_uptrends
        elif self.scanner_type == 3:
            # Downtrend Scanner
            scanner = TrendScanner()
            return scanner.scan_downtrends
        elif self.scanner_type == 4:
            # Bullish Pullback
            scanner = PullbackScanner()
            return scanner.scan_bullish_pullbacks
        elif self.scanner_type == 5:
            # Bearish Pullback
            scanner = PullbackScanner()
            return scanner.scan_bearish_rallies
        elif self.scanner_type == 6:
            # Mean Reversion Long (Oversold)
            scanner = MeanReversionScanner()
            return scanner.scan_oversold
        else:
            # Mean Reversion Short (Overbought)
            scanner = MeanReversionScanner()
            return scanner.scan_overbought
    
    def _fetch_bb_data(self) -> Dict[str, List[BollingerBands]]:
        """Fetch BB data from database and convert to scanner format."""
        # Get last 30 days of BB data
        # Use actual column names from stock_bollinger_daily table
        sql = """
        SELECT symbol, trade_date, close, upper_band, middle_band, lower_band,
               percent_b, bandwidth, bandwidth_percentile
        FROM stock_bollinger_daily
        WHERE trade_date >= DATE_SUB((SELECT MAX(trade_date) FROM stock_bollinger_daily), INTERVAL 30 DAY)
        ORDER BY symbol, trade_date DESC
        """
        
        with self.engine.connect() as conn:
            df = pd.read_sql(text(sql), conn)
        
        if df.empty:
            return {}
        
        # Convert to Dict[symbol, List[BollingerBands]]
        result: Dict[str, List[BollingerBands]] = {}
        
        for symbol, group in df.groupby('symbol'):
            bb_list = []
            for _, row in group.iterrows():
                bb = BollingerBands(
                    date=row['trade_date'],
                    close=float(row['close']),
                    upper=float(row['upper_band']),
                    middle=float(row['middle_band']),
                    lower=float(row['lower_band']),
                    percent_b=float(row['percent_b']),
                    bandwidth=float(row['bandwidth']),
                    bandwidth_percentile=float(row['bandwidth_percentile'])
                )
                bb_list.append(bb)
            result[symbol] = bb_list
        
        return result


class BBScannerGUI(QMainWindow):
    """Main GUI for Bollinger Band scanning."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bollinger Bands Scanner")
        self.setMinimumSize(1000, 700)
        
        self.engine = None
        self.worker = None
        
        self.setup_ui()
        self.init_database()
    
    def setup_ui(self):
        """Setup the user interface."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Header
        header = QLabel("📊 Bollinger Bands Scanner")
        header.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Scanner selection
        scanner_group = QGroupBox("Scanner Selection")
        scanner_layout = QHBoxLayout(scanner_group)
        
        scanner_layout.addWidget(QLabel("Scanner Type:"))
        self.scanner_combo = QComboBox()
        self.scanner_combo.addItems([
            "Squeeze Scanner - Low Volatility",
            "Bulge Scanner - High Volatility", 
            "Uptrend Scanner - Strong Uptrends",
            "Downtrend Scanner - Strong Downtrends",
            "Bullish Pullback - Buy on Dips",
            "Bearish Pullback - Sell on Rallies",
            "Mean Reversion Long - Oversold Bounce",
            "Mean Reversion Short - Overbought Fade"
        ])
        scanner_layout.addWidget(self.scanner_combo, 1)
        
        self.scan_btn = QPushButton("🔍 Run Scan")
        self.scan_btn.clicked.connect(self.run_scan)
        scanner_layout.addWidget(self.scan_btn)
        
        layout.addWidget(scanner_group)
        
        # Database status
        self.db_status_label = QLabel("Database: Checking...")
        self.db_status_label.setStyleSheet("padding: 5px; border-radius: 4px;")
        layout.addWidget(self.db_status_label)
        
        # Results table
        results_group = QGroupBox("Scan Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(8)
        self.results_table.setHorizontalHeaderLabels([
            "Symbol", "Close", "%b", "Bandwidth", 
            "Days", "Strength/Intensity", "Bias", "Score"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setStyleSheet("""
            QTableWidget { 
                gridline-color: #ccc;
                font-size: 13px;
            }
            QTableWidget::item:selected {
                background-color: #3daee9;
                color: white;
            }
            QHeaderView::section {
                background-color: #2c3e50;
                color: white;
                padding: 8px;
                font-weight: bold;
            }
        """)
        results_layout.addWidget(self.results_table)
        
        layout.addWidget(results_group)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3daee9;
                width: 10px;
            }
        """)
        layout.addWidget(self.progress)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Select a scanner and click Run Scan.")
    
    def init_database(self):
        """Initialize database connection."""
        try:
            self.engine = get_bb_engine()
            
            # Check if BB tables exist and have data
            table_status = check_bb_tables_exist(self.engine)
            
            # Check for data in main table (use correct column name: trade_date)
            with self.engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT COUNT(*) as cnt, MAX(trade_date) as max_date FROM stock_bollinger_daily"
                )).fetchone()
                row_count = result[0] if result else 0
                max_date = result[1] if result else None
            
            if not table_status.get('stock_bollinger_daily', False):
                self.db_status_label.setText("⚠️ Database: BB tables not created. Run 'create_bb_tables()' first.")
                self.db_status_label.setStyleSheet("color: orange; padding: 5px;")
                self.scan_btn.setEnabled(False)
            elif row_count == 0:
                self.db_status_label.setText("⚠️ Database: No BB data. Run BB Backfill first.")
                self.db_status_label.setStyleSheet("color: orange; padding: 5px;")
                self.scan_btn.setEnabled(False)
            else:
                self.db_status_label.setText(
                    f"✅ Database: Connected | {row_count:,} BB records | Latest: {max_date}"
                )
                self.db_status_label.setStyleSheet("color: green; padding: 5px;")
                self.scan_btn.setEnabled(True)
                
        except Exception as e:
            self.db_status_label.setText(f"❌ Database Error: {str(e)[:50]}...")
            self.db_status_label.setStyleSheet("color: red; padding: 5px;")
            self.scan_btn.setEnabled(False)
    
    def run_scan(self):
        """Run the selected scanner."""
        if not self.engine:
            QMessageBox.warning(self, "Error", "Database not connected.")
            return
        
        self.status_bar.showMessage("Starting scan...")
        self.scan_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.results_table.setRowCount(0)
        
        # Start worker thread
        scanner_type = self.scanner_combo.currentIndex()
        self.worker = ScanWorker(scanner_type, self.engine)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_scan_finished)
        self.worker.error.connect(self._on_scan_error)
        self.worker.start()
    
    def _on_progress(self, percent: int, message: str):
        """Handle progress updates."""
        self.progress.setValue(percent)
        self.status_bar.showMessage(message)
    
    def _on_scan_finished(self, results: list):
        """Handle scan completion."""
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)
        
        if not results:
            self.status_bar.showMessage("Scan complete. No matches found.")
            return
        
        # Populate table
        self.results_table.setRowCount(len(results))
        
        for i, result in enumerate(results):
            # Symbol
            self.results_table.setItem(i, 0, QTableWidgetItem(result.symbol))
            
            # Close price
            close_item = QTableWidgetItem(f"{result.close:.2f}")
            close_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.results_table.setItem(i, 1, close_item)
            
            # %b
            pb_item = QTableWidgetItem(f"{result.percent_b:.3f}")
            pb_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            # Color code %b
            if result.percent_b > 0.8:
                pb_item.setForeground(QColor('#00aa00'))  # Green
            elif result.percent_b < 0.2:
                pb_item.setForeground(QColor('#aa0000'))  # Red
            self.results_table.setItem(i, 2, pb_item)
            
            # Bandwidth (or distance from middle for trend results)
            bandwidth = getattr(result, 'bandwidth', None)
            if bandwidth is not None:
                bw_item = QTableWidgetItem(f"{bandwidth:.2f}%")
            else:
                # For trend results, show distance from middle
                dist = getattr(result, 'distance_from_middle_pct', 0)
                bw_item = QTableWidgetItem(f"{dist:.2f}%")
            bw_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.results_table.setItem(i, 3, bw_item)
            
            # Days (squeeze days, trend days, etc.)
            days = getattr(result, 'squeeze_days', 
                    getattr(result, 'trend_days',
                    getattr(result, 'days_extreme', 0)))
            days_item = QTableWidgetItem(str(days))
            days_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(i, 4, days_item)
            
            # Strength/Intensity
            intensity = getattr(result, 'squeeze_intensity',
                        getattr(result, 'trend_strength',
                        getattr(result, 'setup_quality',
                        getattr(result, 'extremity_score', 0))))
            intensity_item = QTableWidgetItem(f"{intensity:.1f}")
            intensity_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.results_table.setItem(i, 5, intensity_item)
            
            # Bias/Direction/Type
            bias = getattr(result, 'bias',
                   getattr(result, 'trend_direction',
                   getattr(result, 'pullback_type',
                   getattr(result, 'reversion_type',
                   getattr(result, 'trend_phase', 'N/A')))))
            bias_item = QTableWidgetItem(str(bias))
            bias_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if bias in ('BULLISH', 'UPTREND', 'OVERSOLD'):
                bias_item.setForeground(QColor('#00aa00'))
            elif bias in ('BEARISH', 'DOWNTREND', 'OVERBOUGHT'):
                bias_item.setForeground(QColor('#aa0000'))
            self.results_table.setItem(i, 6, bias_item)
            
            # Score (bandwidth percentile, trend strength, quality, etc.)
            score = getattr(result, 'bandwidth_percentile',
                    getattr(result, 'trend_strength',
                    getattr(result, 'setup_quality',
                    getattr(result, 'extremity_score', 50.0))))
            score_item = QTableWidgetItem(f"{score:.1f}")
            score_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.results_table.setItem(i, 7, score_item)
        
        self.status_bar.showMessage(f"Scan complete. Found {len(results)} matches.")
    
    def _on_scan_error(self, error_msg: str):
        """Handle scan error."""
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.status_bar.showMessage("Scan failed.")
        
        QMessageBox.critical(
            self,
            "Scan Error",
            f"An error occurred during the scan:\n\n{error_msg}"
        )


def main():
    """Launch the BB Scanner GUI."""
    app = QApplication(sys.argv)
    
    app.setApplicationName("Bollinger Bands Scanner")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("StockScreeer")
    
    window = BBScannerGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
