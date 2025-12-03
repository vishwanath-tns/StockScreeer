#!/usr/bin/env python3
"""
Volume Analysis GUI
===================

A visual dashboard showing stocks to BUY (accumulation) and SELL (distribution).
Uses PyQt6 for the GUI with color-coded tables.

Usage:
    python volume_analysis_gui.py
"""

import sys
import logging
from datetime import datetime
from typing import List, Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QLabel, QProgressBar,
    QTabWidget, QGroupBox, QSpinBox, QComboBox, QSplitter, QStatusBar,
    QHeaderView, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont, QBrush

from volume_analysis import VolumeScanner
from volume_analysis.analysis.accumulation_detector import (
    AccumulationSignal, PhaseType, SignalStrength
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScanWorker(QThread):
    """Background worker for scanning stocks."""
    
    progress = pyqtSignal(int, int, str)  # current, total, symbol
    finished = pyqtSignal(object)  # ScanResults
    error = pyqtSignal(str)
    
    def __init__(self, scanner: VolumeScanner, symbols: List[str] = None):
        super().__init__()
        self.scanner = scanner
        self.symbols = symbols
        self._running = True
    
    def run(self):
        try:
            if self.symbols:
                results = self.scanner.scan_symbols(
                    self.symbols,
                    progress_callback=lambda c, t, s: self.progress.emit(c, t, s)
                )
            else:
                results = self.scanner.scan_nifty500(
                    progress_callback=lambda c, t, s: self.progress.emit(c, t, s)
                )
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))
    
    def stop(self):
        self._running = False


class VolumeAnalysisGUI(QMainWindow):
    """Main GUI window for volume analysis."""
    
    def __init__(self):
        super().__init__()
        self.scanner = VolumeScanner(
            lookback_days=180,
            min_volume=50000,
            min_price=10.0
        )
        self.results = None
        self.worker = None
        
        self.setup_ui()
        self.setWindowTitle("📊 Volume Analysis - Buy/Sell Scanner")
        self.setMinimumSize(1000, 600)
        
        # Auto-scan on startup after 1 second
        QTimer.singleShot(1000, self.start_scan)
    
    def setup_ui(self):
        """Setup the user interface."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)
        
        # Compact controls row
        controls = QHBoxLayout()
        controls.setSpacing(8)
        
        # Scan button
        self.scan_btn = QPushButton("🔍 Scan All Stocks")
        self.scan_btn.setStyleSheet("padding: 4px 12px; font-weight: bold;")
        self.scan_btn.clicked.connect(self.start_scan)
        controls.addWidget(self.scan_btn)
        
        # Stock count spinner
        controls.addWidget(QLabel("Max Stocks:"))
        self.stock_count_spin = QSpinBox()
        self.stock_count_spin.setRange(50, 1000)
        self.stock_count_spin.setValue(500)
        self.stock_count_spin.setSingleStep(50)
        self.stock_count_spin.setFixedWidth(70)
        controls.addWidget(self.stock_count_spin)
        
        # Min volume filter
        controls.addWidget(QLabel("Min Volume:"))
        self.min_volume_combo = QComboBox()
        self.min_volume_combo.addItems(["50,000", "100,000", "500,000", "1,000,000"])
        self.min_volume_combo.setCurrentIndex(1)
        self.min_volume_combo.setFixedWidth(100)
        controls.addWidget(self.min_volume_combo)
        
        controls.addStretch()
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedWidth(150)
        controls.addWidget(self.progress_bar)
        
        # Progress label
        self.progress_label = QLabel("")
        controls.addWidget(self.progress_label)
        
        layout.addLayout(controls)
        
        # Main content - split view (takes all remaining space)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # LEFT: BUY Candidates (Accumulation)
        buy_group = QGroupBox("🟢 BUY CANDIDATES (Accumulation)")
        buy_group.setStyleSheet("""
            QGroupBox {
                font-size: 11px;
                font-weight: bold;
                border: 2px solid #00aa00;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 5px;
            }
            QGroupBox::title {
                color: #00cc00;
                subcontrol-position: top left;
                padding: 0 5px;
            }
        """)
        buy_layout = QVBoxLayout(buy_group)
        buy_layout.setContentsMargins(3, 8, 3, 3)
        buy_layout.setSpacing(2)
        
        self.buy_table = QTableWidget()
        self.buy_table.setColumnCount(6)
        self.buy_table.setHorizontalHeaderLabels([
            "Symbol", "Score", "CMF", "OBV Trend", "Strength", "Signal"
        ])
        self.buy_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.buy_table.setAlternatingRowColors(True)
        self.buy_table.verticalHeader().setDefaultSectionSize(20)  # Compact rows
        self.buy_table.verticalHeader().setVisible(True)
        self.buy_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #333;
                background-color: #1a1a1a;
                alternate-background-color: #222;
                font-size: 10px;
            }
            QHeaderView::section {
                background-color: #006600;
                color: white;
                padding: 3px;
                font-weight: bold;
                font-size: 10px;
                border: 1px solid #004400;
            }
            QTableWidget::item {
                padding: 2px;
            }
        """)
        buy_layout.addWidget(self.buy_table, 1)
        
        self.buy_count_label = QLabel("0 stocks showing accumulation")
        self.buy_count_label.setStyleSheet("color: #00cc00; font-size: 10px;")
        buy_layout.addWidget(self.buy_count_label)
        
        splitter.addWidget(buy_group)
        
        # RIGHT: SELL Candidates (Distribution)
        sell_group = QGroupBox("🔴 SELL / AVOID (Distribution)")
        sell_group.setStyleSheet("""
            QGroupBox {
                font-size: 11px;
                font-weight: bold;
                border: 2px solid #aa0000;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 5px;
            }
            QGroupBox::title {
                color: #cc0000;
                subcontrol-position: top left;
                padding: 0 5px;
            }
        """)
        sell_layout = QVBoxLayout(sell_group)
        sell_layout.setContentsMargins(3, 8, 3, 3)
        sell_layout.setSpacing(2)
        
        self.sell_table = QTableWidget()
        self.sell_table.setColumnCount(6)
        self.sell_table.setHorizontalHeaderLabels([
            "Symbol", "Score", "CMF", "OBV Trend", "Strength", "Signal"
        ])
        self.sell_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.sell_table.setAlternatingRowColors(True)
        self.sell_table.verticalHeader().setDefaultSectionSize(20)  # Compact rows
        self.sell_table.verticalHeader().setVisible(True)
        self.sell_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #333;
                background-color: #1a1a1a;
                alternate-background-color: #222;
                font-size: 10px;
            }
            QHeaderView::section {
                background-color: #660000;
                color: white;
                padding: 3px;
                font-weight: bold;
                font-size: 10px;
                border: 1px solid #440000;
            }
            QTableWidget::item {
                padding: 2px;
            }
        """)
        sell_layout.addWidget(self.sell_table, 1)
        
        self.sell_count_label = QLabel("0 stocks showing distribution")
        self.sell_count_label.setStyleSheet("color: #cc0000; font-size: 10px;")
        sell_layout.addWidget(self.sell_count_label)
        
        splitter.addWidget(sell_group)
        
        # Set splitter stretch - both sides equal
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter, 1)  # stretch factor 1 = take all remaining space
        
        # Compact Legend
        legend = QFrame()
        legend.setStyleSheet("background: #1a1a1a; padding: 2px; border-radius: 3px;")
        legend.setMaximumHeight(25)
        legend_layout = QHBoxLayout(legend)
        legend_layout.setContentsMargins(5, 2, 5, 2)
        legend_layout.setSpacing(10)
        
        legend_style = "font-size: 9px;"
        lbl = QLabel("📊 <b>Score Legend:</b>")
        lbl.setStyleSheet(legend_style)
        legend_layout.addWidget(lbl)
        
        for text in ["⭐⭐⭐ Strong (70+)", "⭐⭐ Moderate (60-70)", "⭐ Watch (55-60)", 
                     "|", "⛔⛔⛔ Strong Sell (<30)", "⛔⛔ Sell (30-40)", "⛔ Avoid (40-45)"]:
            lbl = QLabel(text)
            lbl.setStyleSheet(legend_style)
            legend_layout.addWidget(lbl)
        
        legend_layout.addStretch()
        layout.addWidget(legend)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Click 'Scan All Stocks' to begin.")
    
    def start_scan(self):
        """Start scanning stocks."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            return
        
        # Get settings
        max_stocks = self.stock_count_spin.value()
        min_vol_text = self.min_volume_combo.currentText().replace(",", "")
        min_volume = int(min_vol_text)
        
        # Update scanner settings
        self.scanner.min_volume = min_volume
        
        # Get symbols
        all_symbols = self.scanner.get_nifty500_symbols()
        symbols = all_symbols[:max_stocks]
        
        # Setup progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(symbols))
        self.progress_bar.setValue(0)
        self.scan_btn.setText("⏹ Stop Scan")
        self.scan_btn.setStyleSheet("padding: 4px 12px; font-weight: bold; background: #aa0000;")
        
        # Clear tables
        self.buy_table.setRowCount(0)
        self.sell_table.setRowCount(0)
        
        # Start worker
        self.worker = ScanWorker(self.scanner, symbols)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_scan_finished)
        self.worker.error.connect(self.on_scan_error)
        self.worker.start()
        
        self.status_bar.showMessage(f"Scanning {len(symbols)} stocks...")
    
    def on_progress(self, current: int, total: int, symbol: str):
        """Handle progress updates."""
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"{current}/{total} - {symbol}")
    
    def on_scan_finished(self, results):
        """Handle scan completion."""
        self.results = results
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        self.scan_btn.setText("🔍 Scan All Stocks")
        self.scan_btn.setStyleSheet("padding: 4px 12px; font-weight: bold;")
        
        # Populate BUY table (accumulation)
        self.buy_table.setRowCount(len(results.accumulation))
        for row, signal in enumerate(results.accumulation):
            self._add_buy_row(row, signal)
        
        self.buy_count_label.setText(f"{len(results.accumulation)} stocks showing accumulation")
        
        # Populate SELL table (distribution)
        self.sell_table.setRowCount(len(results.distribution))
        for row, signal in enumerate(results.distribution):
            self._add_sell_row(row, signal)
        
        self.sell_count_label.setText(f"{len(results.distribution)} stocks showing distribution")
        
        self.status_bar.showMessage(
            f"Scan complete! Found {len(results.accumulation)} BUY candidates, "
            f"{len(results.distribution)} SELL candidates"
        )
    
    def _add_buy_row(self, row: int, signal: AccumulationSignal):
        """Add a row to the BUY table."""
        # Symbol
        symbol_item = QTableWidgetItem(signal.symbol.replace('.NS', ''))
        symbol_item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        symbol_item.setForeground(QBrush(QColor("#00ff00")))
        self.buy_table.setItem(row, 0, symbol_item)
        
        # Score
        score_item = QTableWidgetItem(f"{signal.score:.1f}")
        score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if signal.score >= 70:
            score_item.setBackground(QBrush(QColor("#004400")))
        elif signal.score >= 60:
            score_item.setBackground(QBrush(QColor("#003300")))
        self.buy_table.setItem(row, 1, score_item)
        
        # CMF
        cmf = signal.details.get('cmf', {}).get('current', 0)
        cmf_item = QTableWidgetItem(f"{cmf:.3f}")
        cmf_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        cmf_item.setForeground(QBrush(QColor("#00ff00" if cmf > 0 else "#ff4444")))
        self.buy_table.setItem(row, 2, cmf_item)
        
        # OBV Trend
        obv_up = signal.details.get('obv', {}).get('trending_up', False)
        obv_item = QTableWidgetItem("↑ UP" if obv_up else "↓ DOWN")
        obv_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        obv_item.setForeground(QBrush(QColor("#00ff00" if obv_up else "#ff4444")))
        self.buy_table.setItem(row, 3, obv_item)
        
        # Strength
        strength_item = QTableWidgetItem(signal.strength.value.upper())
        strength_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.buy_table.setItem(row, 4, strength_item)
        
        # Signal
        if signal.score >= 70:
            signal_text = "⭐⭐⭐ STRONG BUY"
        elif signal.score >= 60:
            signal_text = "⭐⭐ BUY"
        else:
            signal_text = "⭐ WATCH"
        signal_item = QTableWidgetItem(signal_text)
        signal_item.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        self.buy_table.setItem(row, 5, signal_item)
    
    def _add_sell_row(self, row: int, signal: AccumulationSignal):
        """Add a row to the SELL table."""
        # Symbol
        symbol_item = QTableWidgetItem(signal.symbol.replace('.NS', ''))
        symbol_item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        symbol_item.setForeground(QBrush(QColor("#ff4444")))
        self.sell_table.setItem(row, 0, symbol_item)
        
        # Score
        score_item = QTableWidgetItem(f"{signal.score:.1f}")
        score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if signal.score <= 30:
            score_item.setBackground(QBrush(QColor("#440000")))
        elif signal.score <= 40:
            score_item.setBackground(QBrush(QColor("#330000")))
        self.sell_table.setItem(row, 1, score_item)
        
        # CMF
        cmf = signal.details.get('cmf', {}).get('current', 0)
        cmf_item = QTableWidgetItem(f"{cmf:.3f}")
        cmf_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        cmf_item.setForeground(QBrush(QColor("#00ff00" if cmf > 0 else "#ff4444")))
        self.sell_table.setItem(row, 2, cmf_item)
        
        # OBV Trend
        obv_up = signal.details.get('obv', {}).get('trending_up', False)
        obv_item = QTableWidgetItem("↑ UP" if obv_up else "↓ DOWN")
        obv_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        obv_item.setForeground(QBrush(QColor("#00ff00" if obv_up else "#ff4444")))
        self.sell_table.setItem(row, 3, obv_item)
        
        # Strength
        strength_item = QTableWidgetItem(signal.strength.value.upper())
        strength_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sell_table.setItem(row, 4, strength_item)
        
        # Signal
        if signal.score <= 30:
            signal_text = "⛔⛔⛔ STRONG SELL"
        elif signal.score <= 40:
            signal_text = "⛔⛔ SELL"
        else:
            signal_text = "⛔ AVOID"
        signal_item = QTableWidgetItem(signal_text)
        signal_item.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        self.sell_table.setItem(row, 5, signal_item)
    
    def on_scan_error(self, error: str):
        """Handle scan error."""
        self.progress_bar.setVisible(False)
        self.scan_btn.setText("🔍 Scan All Stocks")
        self.scan_btn.setStyleSheet("padding: 4px 12px; font-weight: bold;")
        QMessageBox.critical(self, "Scan Error", f"Error during scan: {error}")


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    
    # Dark theme
    app.setStyle("Fusion")
    
    # Dark palette
    from PyQt6.QtGui import QPalette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(35, 35, 35))
    palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    app.setPalette(palette)
    
    window = VolumeAnalysisGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
