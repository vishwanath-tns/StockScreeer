"""
NSE F&O Analysis Module - Main Launcher
Launch the FNO Import Wizard, Analysis Dashboard, or OI Reports
"""

import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QGroupBox, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPalette, QColor

# Add path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fno.database.schema import create_database, get_table_stats
from fno.gui.fno_import_wizard import FNOImportWizard
from fno.gui.fno_analysis_dashboard import FNOAnalysisDashboard
from fno.gui.fno_oi_report_gui import FNOOIReportGUI


class FNOLauncher(QMainWindow):
    """Main launcher for FNO module."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NSE F&O Analysis System")
        self.setFixedSize(700, 500)
        
        self.setup_ui()
        self.apply_theme()
        self.update_stats()
    
    def setup_ui(self):
        """Setup the UI."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("NSE F&O Analysis System")
        title.setFont(QFont("Segoe UI", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #00aaff;")
        layout.addWidget(title)
        
        subtitle = QLabel("Futures & Options Data Import and Analysis")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #888; font-size: 14px;")
        layout.addWidget(subtitle)
        
        layout.addSpacing(20)
        
        # Database status
        status_group = QGroupBox("Database Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("Checking database...")
        status_layout.addWidget(self.status_label)
        
        self.futures_label = QLabel("Futures: -")
        status_layout.addWidget(self.futures_label)
        
        self.options_label = QLabel("Options: -")
        status_layout.addWidget(self.options_label)
        
        layout.addWidget(status_group)
        
        # Buttons - Row with 3 buttons
        btn_layout = QHBoxLayout()
        
        # Import button
        import_btn = QPushButton("Import Data")
        import_btn.setMinimumHeight(60)
        import_btn.setFont(QFont("Segoe UI", 12))
        import_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        import_btn.clicked.connect(self.launch_import_wizard)
        btn_layout.addWidget(import_btn)
        
        # Analysis button
        analysis_btn = QPushButton("Analysis Dashboard")
        analysis_btn.setMinimumHeight(60)
        analysis_btn.setFont(QFont("Segoe UI", 12))
        analysis_btn.setStyleSheet("""
            QPushButton {
                background-color: #0d6efd;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
        """)
        analysis_btn.clicked.connect(self.launch_analysis_dashboard)
        btn_layout.addWidget(analysis_btn)
        
        # OI Reports button
        oi_btn = QPushButton("OI Reports")
        oi_btn.setMinimumHeight(60)
        oi_btn.setFont(QFont("Segoe UI", 12))
        oi_btn.setStyleSheet("""
            QPushButton {
                background-color: #fd7e14;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #e96d0c;
            }
        """)
        oi_btn.clicked.connect(self.launch_oi_reports)
        btn_layout.addWidget(oi_btn)
        
        layout.addLayout(btn_layout)
        
        # Info
        info = QLabel(
            "Import Data: Load daily F&O bhavcopy files\n"
            "Analysis Dashboard: Option chain analysis, support/resistance\n"
            "OI Reports: Cumulative OI buildup/unwinding reports"
        )
        info.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(info)
        
        layout.addStretch()
    
    def apply_theme(self):
        """Apply dark theme."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QLabel {
                color: white;
            }
            QGroupBox {
                color: #00aaff;
                font-weight: bold;
                border: 1px solid #444;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
    
    def update_stats(self):
        """Update database statistics."""
        try:
            create_database()
            stats = get_table_stats()
            self.status_label.setText("Database connected")
            self.status_label.setStyleSheet("color: #28a745;")
            self.futures_label.setText(f"Futures records: {stats.get('nse_futures', 0):,}")
            self.options_label.setText(f"Options records: {stats.get('nse_options', 0):,}")
        except Exception as e:
            self.status_label.setText(f"Database error: {str(e)}")
            self.status_label.setStyleSheet("color: #dc3545;")
    
    def launch_import_wizard(self):
        """Launch the import wizard."""
        wizard = FNOImportWizard(self)
        wizard.finished.connect(self.update_stats)
        wizard.exec_()
    
    def launch_analysis_dashboard(self):
        """Launch the analysis dashboard."""
        self.dashboard = FNOAnalysisDashboard()
        self.dashboard.show()
    
    def launch_oi_reports(self):
        """Launch the OI Report generator."""
        self.oi_report = FNOOIReportGUI()
        self.oi_report.show()


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    launcher = FNOLauncher()
    launcher.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
