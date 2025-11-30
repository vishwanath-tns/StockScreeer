#!/usr/bin/env python3
"""
Launch Bollinger Bands Scanner GUI

Quick launcher for the BB scanner interface.
Provides access to all scanner types: squeeze, bulge, trend, pullback, reversion.
"""

import sys
from pathlib import Path

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

from bollinger import (
    SqueezeScanner, BulgeScanner, TrendScanner,
    PullbackScanner, MeanReversionScanner,
    BBCalculator, BBConfig
)


class ScanWorker(QThread):
    """Background worker for running scans."""
    
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)
    
    def __init__(self, scanner, bb_data):
        super().__init__()
        self.scanner = scanner
        self.bb_data = bb_data
    
    def run(self):
        try:
            results = self.scanner.scan(self.bb_data)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class BBScannerGUI(QMainWindow):
    """Main GUI for Bollinger Band scanning."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bollinger Bands Scanner")
        self.setMinimumSize(1000, 700)
        
        self.setup_ui()
        self.init_scanners()
    
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
        results_layout.addWidget(self.results_table)
        
        layout.addWidget(results_group)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Select a scanner and click Run Scan.")
    
    def init_scanners(self):
        """Initialize scanner instances."""
        self.scanners = {
            0: SqueezeScanner(),
            1: BulgeScanner(),
            2: TrendScanner(),
            3: TrendScanner(),
            4: PullbackScanner(),
            5: PullbackScanner(),
            6: MeanReversionScanner(),
            7: MeanReversionScanner()
        }
    
    def run_scan(self):
        """Run the selected scanner."""
        self.status_bar.showMessage("Loading data...")
        self.scan_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        
        # For now, show message that data connection is needed
        QMessageBox.information(
            self,
            "Database Connection Required",
            "This scanner requires a database connection.\n\n"
            "Please ensure:\n"
            "1. MySQL database is running\n"
            "2. BB tables have been created (run create_bb_tables())\n"
            "3. Historical data has been processed\n\n"
            "Use the BB Analyzer to calculate and store BB data first."
        )
        
        self.scan_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.status_bar.showMessage("Ready")


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
