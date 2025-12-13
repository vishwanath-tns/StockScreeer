#!/usr/bin/env python3
"""
RSI Overbought/Oversold GUI Dashboard
======================================

Interactive PyQt5 dashboard for RSI analysis.

Features:
- Real-time RSI status display
- Filter by NIFTY 50 or NIFTY 500
- Interactive tables with sorting/filtering
- RSI history charts per symbol
- Auto-refresh capability

Usage:
    python rsi_overbought_oversold_gui.py

Author: StockScreener Project
Date: December 2025
"""

import os
import sys
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import numpy as np
from pathlib import Path

try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QTabWidget, QTableWidget, QTableWidgetItem, QPushButton, QLabel,
        QSpinBox, QComboBox, QCheckBox, QMessageBox, QFileDialog,
        QProgressBar, QStatusBar, QHeaderView, QDialog, QLineEdit,
        QDialogButtonBox
    )
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
    from PyQt5.QtGui import QColor, QFont, QIcon, QDoubleValidator
    from PyQt5.QtChart import QChart, QChartView, QLineSeries, QDateTimeAxis, QValueAxis
    from PyQt5.QtCore import QDateTime, QDateTime as QtDateTime
    PYQT_AVAILABLE = True
except ImportError as e:
    PYQT_AVAILABLE = False
    print(f"PyQt5 not available: {e}")

from sqlalchemy import create_engine, text

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import analyzer
from rsi_overbought_oversold_analyzer import (
    RSIAnalyzerDB, RSIAnalyzer, NIFTY_50_SYMBOLS,
    RSI_OVERBOUGHT, RSI_OVERSOLD
)

try:
    from utilities.nifty500_stocks_list import NIFTY_500_STOCKS
except ImportError:
    NIFTY_500_STOCKS = []

# =============================================================================
# CONSTANTS
# =============================================================================

REFRESH_INTERVAL = 60000  # 1 minute
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 800


# =============================================================================
# WORKER THREAD
# =============================================================================

class DataWorker(QThread):
    """Worker thread for loading data"""
    
    data_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, analyzer: RSIAnalyzer, analysis_type: str):
        super().__init__()
        self.analyzer = analyzer
        self.analysis_type = analysis_type
    
    def run(self):
        try:
            if self.analysis_type == 'nifty50':
                result = self.analyzer.analyze_nifty50()
            else:
                result = self.analyzer.analyze_nifty500()
            self.data_ready.emit(result)
        except Exception as e:
            logger.error(f"Error in worker: {e}")
            self.error_occurred.emit(str(e))


# =============================================================================
# GUI COMPONENTS
# =============================================================================

class RSIStatusLabel(QLabel):
    """Color-coded RSI status label"""
    
    def __init__(self, rsi: float):
        super().__init__()
        self.set_rsi(rsi)
    
    def set_rsi(self, rsi: float):
        """Update RSI value and color"""
        self.setText(f"{rsi:.2f}")
        
        if pd.isna(rsi):
            self.setStyleSheet("color: gray;")
        elif rsi >= RSI_OVERBOUGHT:
            self.setStyleSheet("color: red; font-weight: bold;")
        elif rsi <= RSI_OVERSOLD:
            self.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.setStyleSheet("color: black;")


class RSIAnalyzerGUI(QMainWindow):
    """Main GUI window"""
    
    def __init__(self):
        super().__init__()
        self.db = RSIAnalyzerDB()
        self.analyzer = RSIAnalyzer(self.db)
        self.current_data = {}
        
        self.init_ui()
        self.load_data('nifty50')
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.auto_refresh)
        self.refresh_timer.start(REFRESH_INTERVAL)
    
    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("RSI Overbought/Oversold Analyzer")
        self.setGeometry(100, 100, WINDOW_WIDTH, WINDOW_HEIGHT)
        
        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        
        # Controls layout
        controls_layout = QHBoxLayout()
        
        # Analysis type selector
        controls_layout.addWidget(QLabel("Analysis Type:"))
        self.analysis_combo = QComboBox()
        self.analysis_combo.addItem("NIFTY 50", "nifty50")
        self.analysis_combo.addItem("NIFTY 500", "nifty500")
        self.analysis_combo.currentIndexChanged.connect(self.on_analysis_type_changed)
        controls_layout.addWidget(self.analysis_combo)
        
        controls_layout.addSpacing(20)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh Now")
        refresh_btn.clicked.connect(lambda: self.load_data(self.get_analysis_type()))
        controls_layout.addWidget(refresh_btn)
        
        # Auto-refresh checkbox
        self.auto_refresh_check = QCheckBox("Auto-refresh (60s)")
        self.auto_refresh_check.setChecked(True)
        controls_layout.addWidget(self.auto_refresh_check)
        
        # Export button
        export_btn = QPushButton("Export to CSV")
        export_btn.clicked.connect(self.export_to_csv)
        controls_layout.addWidget(export_btn)
        
        controls_layout.addStretch()
        
        # Status label
        self.status_label = QLabel()
        controls_layout.addWidget(self.status_label)
        
        main_layout.addLayout(controls_layout)
        
        # Tab widget
        self.tabs = QTabWidget()
        
        # Tab 1: Overbought
        self.overbought_table = self.create_table()
        self.tabs.addTab(self.overbought_table, "Overbought (RSI >= 80)")
        
        # Tab 2: Oversold
        self.oversold_table = self.create_table()
        self.tabs.addTab(self.oversold_table, "Oversold (RSI <= 20)")
        
        # Tab 3: Neutral (Top 50)
        self.neutral_table = self.create_table()
        self.tabs.addTab(self.neutral_table, "Neutral (Top 50)")
        
        # Tab 4: Summary Stats
        self.summary_widget = QWidget()
        self.summary_layout = QVBoxLayout(self.summary_widget)
        self.tabs.addTab(self.summary_widget, "Summary")
        
        main_layout.addWidget(self.tabs)
        
        main_widget.setLayout(main_layout)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def create_table(self) -> QTableWidget:
        """Create a data table"""
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(['Symbol', 'Date', 'Close', 'RSI (9)', 'Status'])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        return table
    
    def load_data(self, analysis_type: str):
        """Load data in background thread"""
        self.statusBar().showMessage(f"Loading {analysis_type} data...")
        
        self.worker = DataWorker(self.analyzer, analysis_type)
        self.worker.data_ready.connect(self.on_data_ready)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()
    
    def on_data_ready(self, data: dict):
        """Handle data ready signal"""
        self.current_data = data
        self.update_ui()
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.statusBar().showMessage(f"Data loaded at {timestamp}")
    
    def on_error(self, error_msg: str):
        """Handle error signal"""
        QMessageBox.critical(self, "Error", f"Failed to load data:\n{error_msg}")
        self.statusBar().showMessage("Error loading data")
    
    def update_ui(self):
        """Update UI with current data"""
        data = self.current_data
        
        # Update tables
        self.populate_table(self.overbought_table, data.get('overbought', []))
        self.populate_table(self.oversold_table, data.get('oversold', []))
        
        # Top 50 neutral
        neutral = data.get('neutral', [])[:50]
        self.populate_table(self.neutral_table, neutral)
        
        # Summary
        self.update_summary(data)
    
    def populate_table(self, table: QTableWidget, records: List[Dict]):
        """Populate table with records"""
        table.setRowCount(len(records))
        
        for row, record in enumerate(records):
            symbol = record.get('symbol', '')
            date = record.get('date', '')
            close = record.get('close', 0)
            rsi = record.get('rsi_9', 0)
            
            # Classify status
            if pd.isna(rsi):
                status = "NO DATA"
            elif rsi >= RSI_OVERBOUGHT:
                status = "OVERBOUGHT"
            elif rsi <= RSI_OVERSOLD:
                status = "OVERSOLD"
            else:
                status = "NEUTRAL"
            
            # Add items
            table.setItem(row, 0, QTableWidgetItem(symbol))
            table.setItem(row, 1, QTableWidgetItem(str(date)))
            
            close_item = QTableWidgetItem(f"{close:.2f}")
            close_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(row, 2, close_item)
            
            rsi_item = QTableWidgetItem(f"{rsi:.2f}")
            rsi_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            # Color code RSI
            if rsi >= RSI_OVERBOUGHT:
                rsi_item.setForeground(QColor("red"))
            elif rsi <= RSI_OVERSOLD:
                rsi_item.setForeground(QColor("green"))
            
            table.setItem(row, 3, rsi_item)
            
            status_item = QTableWidgetItem(status)
            table.setItem(row, 4, status_item)
    
    def update_summary(self, data: dict):
        """Update summary tab"""
        # Clear previous layout
        for i in reversed(range(self.summary_layout.count())):
            self.summary_layout.itemAt(i).widget().setParent(None)
        
        total = data.get('total', 0)
        available = data.get('data_available', 0)
        overbought = len(data.get('overbought', []))
        oversold = len(data.get('oversold', []))
        neutral = len(data.get('neutral', []))
        
        # Summary statistics
        stats_text = f"""
<h2>Analysis Summary</h2>

<table style='font-size: 14px; line-height: 1.8;'>
<tr><td><b>Total Stocks Analyzed:</b></td><td>{total}</td></tr>
<tr><td><b>Data Available:</b></td><td>{available} ({100*available/max(total,1):.1f}%)</td></tr>
</table>

<h3>Breakdown by RSI Status:</h3>

<table style='font-size: 14px; line-height: 1.8;'>
<tr style='color: red;'>
    <td><b>Overbought (RSI >= {RSI_OVERBOUGHT}):</b></td>
    <td><b>{overbought}</b> stocks ({100*overbought/max(available,1):.1f}%)</td>
</tr>
<tr style='color: green;'>
    <td><b>Oversold (RSI <= {RSI_OVERSOLD}):</b></td>
    <td><b>{oversold}</b> stocks ({100*oversold/max(available,1):.1f}%)</td>
</tr>
<tr>
    <td><b>Neutral ({RSI_OVERSOLD} < RSI < {RSI_OVERBOUGHT}):</b></td>
    <td><b>{neutral}</b> stocks ({100*neutral/max(available,1):.1f}%)</td>
</tr>
</table>

<h3>Thresholds:</h3>
<table style='font-size: 13px;'>
<tr><td>Overbought:</td><td>RSI >= {RSI_OVERBOUGHT}</td></tr>
<tr><td>Oversold:</td><td>RSI <= {RSI_OVERSOLD}</td></tr>
<tr><td>RSI Period:</td><td>9 days</td></tr>
<tr><td>Timeframe:</td><td>Daily</td></tr>
</table>

<h3>Data Source:</h3>
<table style='font-size: 13px;'>
<tr><td>Database:</td><td>marketdata</td></tr>
<tr><td>Table:</td><td>yfinance_daily_rsi</td></tr>
<tr><td>Updated by:</td><td>Daily Data Wizard</td></tr>
</table>
        """
        
        summary_label = QLabel(stats_text)
        summary_label.setStyleSheet("padding: 20px;")
        self.summary_layout.addWidget(summary_label)
        self.summary_layout.addStretch()
    
    def get_analysis_type(self) -> str:
        """Get current analysis type"""
        return self.analysis_combo.currentData()
    
    def on_analysis_type_changed(self):
        """Handle analysis type change"""
        analysis_type = self.get_analysis_type()
        self.load_data(analysis_type)
    
    def auto_refresh(self):
        """Auto-refresh if enabled"""
        if self.auto_refresh_check.isChecked():
            self.load_data(self.get_analysis_type())
    
    def export_to_csv(self):
        """Export current data to CSV"""
        if not self.current_data:
            QMessageBox.warning(self, "Warning", "No data to export")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export RSI Analysis", "",
            "CSV Files (*.csv);;Excel Files (*.xlsx)"
        )
        
        if not filename:
            return
        
        try:
            df = self.current_data['raw_df'].copy()
            df['status'] = df['rsi_9'].apply(
                lambda x: 'OVERBOUGHT' if x >= RSI_OVERBOUGHT else
                ('OVERSOLD' if x <= RSI_OVERSOLD else 'NEUTRAL')
            )
            
            # Sort by status
            status_order = {'OVERBOUGHT': 0, 'OVERSOLD': 1, 'NEUTRAL': 2}
            df['status_order'] = df['status'].map(status_order)
            df = df.sort_values(['status_order', 'rsi_9'], ascending=[True, False])
            df = df.drop('status_order', axis=1)
            
            if filename.endswith('.xlsx'):
                df.to_excel(filename, index=False)
            else:
                df.to_csv(filename, index=False)
            
            QMessageBox.information(self, "Success", f"Data exported to {filename}")
            logger.info(f"Exported data to {filename}")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export:\n{str(e)}")
            logger.error(f"Export error: {e}")
    
    def closeEvent(self, event):
        """Handle window close"""
        self.refresh_timer.stop()
        if hasattr(self, 'worker'):
            self.worker.quit()
            self.worker.wait()
        event.accept()


# =============================================================================
# MAIN
# =============================================================================

def main():
    if not PYQT_AVAILABLE:
        print("Error: PyQt5 is not installed.")
        print("Install with: pip install PyQt5 PyQtChart")
        sys.exit(1)
    
    app = QApplication(sys.argv)
    window = RSIAnalyzerGUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
