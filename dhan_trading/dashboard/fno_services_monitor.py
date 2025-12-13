"""
FNO Services Real-time Monitor Dashboard
=========================================

Monitors both FNO Feed Launcher and FNO Database Writer services
without impacting their performance.

Features:
  - Real-time connection status for both services
  - Quote statistics (FNO vs Options)
  - Database growth visualization
  - Feed performance metrics
  - Error tracking
  - System health indicators

Architecture:
  - Reads from Redis pub/sub (for real-time updates)
  - Reads from database (for verification)
  - No impact on feed performance (read-only)
"""

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import threading
import json
import redis
from dataclasses import dataclass, asdict

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QTableWidget, QTableWidgetItem, QProgressBar, QGroupBox,
    QPushButton, QStatusBar, QSplitter, QTextEdit
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt5.QtGui import QColor, QFont, QIcon, QPixmap, QPalette
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QDateTimeAxis, QValueAxis
from PyQt5.QtCore import QDateTime, QPointF
from PyQt5.QtGui import QPen

from dhan_trading.db_setup import get_engine
from sqlalchemy import text


@dataclass
class ServiceMetrics:
    """Metrics for a service"""
    name: str
    is_running: bool
    connected: bool
    quotes_written: int = 0
    quotes_queued: int = 0
    last_update: datetime = None
    error_count: int = 0
    last_error: str = ""
    uptime_seconds: int = 0


@dataclass
class DatabaseStats:
    """Current database statistics"""
    fno_quotes: int = 0
    fno_quotes_today: int = 0
    options_quotes: int = 0
    options_quotes_today: int = 0
    last_fno_time: Optional[datetime] = None
    last_options_time: Optional[datetime] = None
    growth_rate_per_minute: float = 0.0


class RedisMonitor(QObject):
    """Monitor Redis for service updates"""
    
    metrics_updated = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.redis_client = None
        self.running = False
        self.last_metrics = {}
        
    def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.Redis(
                host='localhost', port=6379, decode_responses=True
            )
            self.redis_client.ping()
            return True
        except Exception as e:
            print(f"Redis connection failed: {e}")
            return False
    
    def start(self):
        """Start monitoring"""
        self.running = True
        threading.Thread(target=self._monitor_loop, daemon=True).start()
    
    def stop(self):
        """Stop monitoring"""
        self.running = False
        if self.redis_client:
            self.redis_client.close()
    
    def _monitor_loop(self):
        """Monitor loop"""
        while self.running:
            try:
                # Get FNO feed status
                fno_status = self.redis_client.hgetall('fno:feed:status') or {}
                
                # Get DB writer status
                writer_status = self.redis_client.hgetall('fno:writer:status') or {}
                
                metrics = {
                    'fno_feed': self._parse_status(fno_status),
                    'fno_writer': self._parse_status(writer_status),
                    'timestamp': datetime.now()
                }
                
                if metrics != self.last_metrics:
                    self.metrics_updated.emit(metrics)
                    self.last_metrics = metrics
                
                time.sleep(1)
            except Exception as e:
                print(f"Error in monitor loop: {e}")
                time.sleep(5)
    
    @staticmethod
    def _parse_status(status_dict: dict) -> dict:
        """Parse status from Redis"""
        return {
            'connected': status_dict.get('connected') == 'true',
            'quotes_count': int(status_dict.get('quotes_count', 0)),
            'last_update': status_dict.get('last_update', ''),
            'error_count': int(status_dict.get('error_count', 0)),
            'status': status_dict.get('status', 'unknown')
        }


class DatabaseMonitor:
    """Monitor database for statistics"""
    
    def __init__(self):
        self.engine = get_engine('dhan_trading')
        self.last_fno_count = 0
        self.last_options_count = 0
        self.last_check = datetime.now()
    
    def get_stats(self) -> DatabaseStats:
        """Get current database statistics"""
        try:
            with self.engine.connect() as conn:
                # Get total counts
                fno_count = conn.execute(
                    text("SELECT COUNT(*) FROM dhan_fno_quotes")
                ).fetchone()[0]
                
                options_count = conn.execute(
                    text("SELECT COUNT(*) FROM dhan_options_quotes")
                ).fetchone()[0]
                
                # Get today's counts
                today = datetime.now().date()
                fno_today = conn.execute(
                    text(f"SELECT COUNT(*) FROM dhan_fno_quotes WHERE DATE(received_at) = '{today}'")
                ).fetchone()[0]
                
                options_today = conn.execute(
                    text(f"SELECT COUNT(*) FROM dhan_options_quotes WHERE DATE(received_at) = '{today}'")
                ).fetchone()[0]
                
                # Get last update times
                last_fno = conn.execute(
                    text("SELECT MAX(received_at) FROM dhan_fno_quotes")
                ).fetchone()[0]
                
                last_options = conn.execute(
                    text("SELECT MAX(received_at) FROM dhan_options_quotes")
                ).fetchone()[0]
                
                # Calculate growth rate
                current_time = datetime.now()
                time_diff = (current_time - self.last_check).total_seconds() / 60
                
                if time_diff > 0:
                    growth = (fno_count + options_count - self.last_fno_count - self.last_options_count) / time_diff
                else:
                    growth = 0
                
                self.last_fno_count = fno_count
                self.last_options_count = options_count
                self.last_check = current_time
                
                return DatabaseStats(
                    fno_quotes=fno_count,
                    fno_quotes_today=fno_today,
                    options_quotes=options_count,
                    options_quotes_today=options_today,
                    last_fno_time=last_fno,
                    last_options_time=last_options,
                    growth_rate_per_minute=growth
                )
        except Exception as e:
            print(f"Error getting database stats: {e}")
            return DatabaseStats()


class FNOServicesMonitor(QMainWindow):
    """Main monitoring dashboard"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FNO Services Monitor - Real-time Dashboard")
        self.setGeometry(100, 100, 1400, 900)
        
        # Initialize monitors
        self.redis_monitor = RedisMonitor()
        self.db_monitor = DatabaseMonitor()
        
        # Connect signals
        self.redis_monitor.metrics_updated.connect(self.on_metrics_updated)
        
        # Create UI
        self.init_ui()
        
        # Setup refresh timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.refresh_data)
        self.update_timer.start(2000)  # Update every 2 seconds
        
        # Start monitoring
        if self.redis_monitor.connect():
            self.redis_monitor.start()
        
        # Service status
        self.service_metrics = {
            'fno_feed': ServiceMetrics('FNO Feed Launcher', False, False),
            'fno_writer': ServiceMetrics('FNO Database Writer', False, False)
        }
        
        # Database stats history for charts
        self.stats_history: List[Tuple[datetime, DatabaseStats]] = []
    
    def init_ui(self):
        """Initialize UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        
        # Status bar at top
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Tab widget for different views
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # Tab 1: Services Status
        tabs.addTab(self.create_services_tab(), "📊 Services Status")
        
        # Tab 2: Database Statistics
        tabs.addTab(self.create_database_tab(), "📈 Database Stats")
        
        # Tab 3: Quote Feed
        tabs.addTab(self.create_feed_tab(), "📡 Quote Feed")
        
        # Tab 4: System Health
        tabs.addTab(self.create_health_tab(), "⚕️ System Health")
        
        # Tab 5: Logs
        tabs.addTab(self.create_logs_tab(), "📝 Logs")
        
        central_widget.setLayout(layout)
        
        # Apply styling
        self.apply_styling()
    
    def create_services_tab(self) -> QWidget:
        """Create services status tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # FNO Feed Status
        feed_group = QGroupBox("FNO Feed Launcher")
        feed_layout = QVBoxLayout()
        
        self.feed_status_label = QLabel("🔴 Disconnected")
        self.feed_status_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        feed_layout.addWidget(self.feed_status_label)
        
        self.feed_info_table = QTableWidget()
        self.feed_info_table.setColumnCount(2)
        self.feed_info_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.feed_info_table.setMaximumHeight(150)
        self.feed_info_table.setRowCount(4)
        
        properties = ["Status", "Instruments", "Quotes/sec", "Uptime"]
        for i, prop in enumerate(properties):
            self.feed_info_table.setItem(i, 0, QTableWidgetItem(prop))
            self.feed_info_table.setItem(i, 1, QTableWidgetItem("--"))
        
        feed_layout.addWidget(self.feed_info_table)
        feed_group.setLayout(feed_layout)
        layout.addWidget(feed_group)
        
        # Database Writer Status
        writer_group = QGroupBox("FNO Database Writer")
        writer_layout = QVBoxLayout()
        
        self.writer_status_label = QLabel("🔴 Disconnected")
        self.writer_status_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        writer_layout.addWidget(self.writer_status_label)
        
        self.writer_info_table = QTableWidget()
        self.writer_info_table.setColumnCount(2)
        self.writer_info_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.writer_info_table.setMaximumHeight(150)
        self.writer_info_table.setRowCount(4)
        
        properties = ["Status", "FNO Batch", "Options Batch", "Uptime"]
        for i, prop in enumerate(properties):
            self.writer_info_table.setItem(i, 0, QTableWidgetItem(prop))
            self.writer_info_table.setItem(i, 1, QTableWidgetItem("--"))
        
        writer_layout.addWidget(self.writer_info_table)
        writer_group.setLayout(writer_layout)
        layout.addWidget(writer_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_database_tab(self) -> QWidget:
        """Create database statistics tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Statistics table
        stats_group = QGroupBox("Database Statistics")
        stats_layout = QVBoxLayout()
        
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(4)
        self.stats_table.setHorizontalHeaderLabels([
            "Quote Type", "Total", "Today", "Last Update"
        ])
        self.stats_table.setRowCount(2)
        self.stats_table.setMaximumHeight(120)
        
        rows = ["FNO Quotes", "Options Quotes"]
        for i, row in enumerate(rows):
            self.stats_table.setItem(i, 0, QTableWidgetItem(row))
            self.stats_table.setItem(i, 1, QTableWidgetItem("0"))
            self.stats_table.setItem(i, 2, QTableWidgetItem("0"))
            self.stats_table.setItem(i, 3, QTableWidgetItem("--"))
        
        stats_layout.addWidget(self.stats_table)
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Growth metrics
        growth_group = QGroupBox("Growth Metrics")
        growth_layout = QVBoxLayout()
        
        growth_layout.addWidget(QLabel("Quotes/minute:"))
        self.growth_bar = QProgressBar()
        self.growth_bar.setMaximum(1000)
        growth_layout.addWidget(self.growth_bar)
        
        self.growth_label = QLabel("0 quotes/min")
        growth_layout.addWidget(self.growth_label)
        
        growth_group.setLayout(growth_layout)
        layout.addWidget(growth_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_feed_tab(self) -> QWidget:
        """Create quote feed tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Feed statistics
        feed_group = QGroupBox("Real-time Feed Statistics")
        feed_layout = QVBoxLayout()
        
        self.feed_stats_table = QTableWidget()
        self.feed_stats_table.setColumnCount(3)
        self.feed_stats_table.setHorizontalHeaderLabels([
            "Feed Type", "Quotes/sec", "Avg Latency"
        ])
        self.feed_stats_table.setRowCount(2)
        self.feed_stats_table.setMaximumHeight(120)
        
        rows = ["FNO Feed", "Options Feed"]
        for i, row in enumerate(rows):
            self.feed_stats_table.setItem(i, 0, QTableWidgetItem(row))
            self.feed_stats_table.setItem(i, 1, QTableWidgetItem("0"))
            self.feed_stats_table.setItem(i, 2, QTableWidgetItem("0ms"))
        
        feed_layout.addWidget(self.feed_stats_table)
        feed_group.setLayout(feed_layout)
        layout.addWidget(feed_group)
        
        # Symbol distribution
        symbol_group = QGroupBox("Instruments by Category")
        symbol_layout = QVBoxLayout()
        
        self.symbols_table = QTableWidget()
        self.symbols_table.setColumnCount(2)
        self.symbols_table.setHorizontalHeaderLabels(["Category", "Count"])
        self.symbols_table.setRowCount(5)
        
        categories = ["Nifty Futures", "BankNifty Futures", "Nifty Options", "BankNifty Options", "Stock Options"]
        for i, cat in enumerate(categories):
            self.symbols_table.setItem(i, 0, QTableWidgetItem(cat))
            self.symbols_table.setItem(i, 1, QTableWidgetItem("0"))
        
        symbol_layout.addWidget(self.symbols_table)
        symbol_group.setLayout(symbol_layout)
        layout.addWidget(symbol_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_health_tab(self) -> QWidget:
        """Create system health tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Connection health
        health_group = QGroupBox("System Health")
        health_layout = QVBoxLayout()
        
        self.redis_health = QLabel("🔴 Redis: Disconnected")
        self.redis_health.setStyleSheet("font-size: 12px;")
        health_layout.addWidget(self.redis_health)
        
        self.db_health = QLabel("🟢 Database: Connected")
        self.db_health.setStyleSheet("font-size: 12px;")
        health_layout.addWidget(self.db_health)
        
        self.feed_health = QLabel("🔴 Feed: Disconnected")
        self.feed_health.setStyleSheet("font-size: 12px;")
        health_layout.addWidget(self.feed_health)
        
        self.writer_health = QLabel("🔴 Writer: Disconnected")
        self.writer_health.setStyleSheet("font-size: 12px;")
        health_layout.addWidget(self.writer_health)
        
        health_group.setLayout(health_layout)
        layout.addWidget(health_group)
        
        # Alerts
        alerts_group = QGroupBox("Alerts & Warnings")
        alerts_layout = QVBoxLayout()
        
        self.alerts_text = QTextEdit()
        self.alerts_text.setReadOnly(True)
        self.alerts_text.setMaximumHeight(200)
        alerts_layout.addWidget(self.alerts_text)
        
        alerts_group.setLayout(alerts_layout)
        layout.addWidget(alerts_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_logs_tab(self) -> QWidget:
        """Create logs tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Logs display
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        layout.addWidget(QLabel("Service Logs:"))
        layout.addWidget(self.logs_text)
        
        # Clear button
        clear_btn = QPushButton("Clear Logs")
        clear_btn.clicked.connect(self.logs_text.clear)
        layout.addWidget(clear_btn)
        
        widget.setLayout(layout)
        return widget
    
    def refresh_data(self):
        """Refresh all data"""
        try:
            # Get database stats
            db_stats = self.db_monitor.get_stats()
            self.stats_history.append((datetime.now(), db_stats))
            
            # Keep only last 60 minutes
            cutoff = datetime.now() - timedelta(minutes=60)
            self.stats_history = [(t, s) for t, s in self.stats_history if t > cutoff]
            
            # Update database tab
            self.update_database_tab(db_stats)
            
            # Update status bar
            self.update_status_bar(db_stats)
            
        except Exception as e:
            self.log_message(f"Error refreshing data: {e}")
    
    def on_metrics_updated(self, metrics: dict):
        """Handle metrics update from Redis"""
        try:
            # Update service metrics
            fno_feed = metrics.get('fno_feed', {})
            fno_writer = metrics.get('fno_writer', {})
            
            # Update FNO Feed status
            if fno_feed.get('connected'):
                self.feed_status_label.setText("🟢 FNO Feed: Connected")
                self.feed_status_label.setStyleSheet("color: green; font-size: 14px; font-weight: bold;")
            else:
                self.feed_status_label.setText("🔴 FNO Feed: Disconnected")
                self.feed_status_label.setStyleSheet("color: red; font-size: 14px; font-weight: bold;")
            
            # Update Writer status
            if fno_writer.get('connected'):
                self.writer_status_label.setText("🟢 Database Writer: Connected")
                self.writer_status_label.setStyleSheet("color: green; font-size: 14px; font-weight: bold;")
            else:
                self.writer_status_label.setText("🔴 Database Writer: Disconnected")
                self.writer_status_label.setStyleSheet("color: red; font-size: 14px; font-weight: bold;")
            
            # Update info tables
            self.feed_info_table.setItem(1, 1, QTableWidgetItem(
                str(fno_feed.get('quotes_count', 0))
            ))
            self.writer_info_table.setItem(1, 1, QTableWidgetItem(
                str(fno_writer.get('quotes_count', 0))
            ))
            
        except Exception as e:
            self.log_message(f"Error updating metrics: {e}")
    
    def update_database_tab(self, stats: DatabaseStats):
        """Update database statistics tab"""
        # Update stats table
        self.stats_table.setItem(0, 1, QTableWidgetItem(f"{stats.fno_quotes:,}"))
        self.stats_table.setItem(0, 2, QTableWidgetItem(f"{stats.fno_quotes_today:,}"))
        self.stats_table.setItem(1, 1, QTableWidgetItem(f"{stats.options_quotes:,}"))
        self.stats_table.setItem(1, 2, QTableWidgetItem(f"{stats.options_quotes_today:,}"))
        
        # Update times
        if stats.last_fno_time:
            self.stats_table.setItem(0, 3, QTableWidgetItem(
                stats.last_fno_time.strftime("%H:%M:%S")
            ))
        
        if stats.last_options_time:
            self.stats_table.setItem(1, 3, QTableWidgetItem(
                stats.last_options_time.strftime("%H:%M:%S")
            ))
        
        # Update growth
        growth = stats.growth_rate_per_minute
        self.growth_bar.setValue(int(min(growth, 1000)))
        self.growth_label.setText(f"{growth:.0f} quotes/min")
    
    def update_status_bar(self, stats: DatabaseStats):
        """Update main status bar"""
        total = stats.fno_quotes + stats.options_quotes
        self.status_bar.showMessage(
            f"Total Quotes: {total:,} | FNO: {stats.fno_quotes:,} | Options: {stats.options_quotes:,} | "
            f"Today FNO: {stats.fno_quotes_today:,} | Today Options: {stats.options_quotes_today:,} | "
            f"Growth: {stats.growth_rate_per_minute:.0f}/min"
        )
    
    def log_message(self, message: str):
        """Log a message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logs_text.append(f"[{timestamp}] {message}")
        
        # Keep only last 100 lines
        lines = self.logs_text.toPlainText().split('\n')
        if len(lines) > 100:
            self.logs_text.setPlainText('\n'.join(lines[-100:]))
    
    def apply_styling(self):
        """Apply dark theme styling"""
        style = """
        QMainWindow {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        QWidget {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        QGroupBox {
            color: #ffffff;
            border: 1px solid #444;
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px 0 3px;
        }
        QTableWidget {
            background-color: #2d2d2d;
            alternate-background-color: #3d3d3d;
            gridline-color: #444;
            color: #ffffff;
        }
        QHeaderView::section {
            background-color: #3d3d3d;
            color: #ffffff;
            padding: 5px;
            border: none;
        }
        QLabel {
            color: #ffffff;
        }
        QPushButton {
            background-color: #0d7377;
            color: white;
            border: none;
            padding: 5px 15px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #14b8a6;
        }
        QTextEdit {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #444;
        }
        QTabWidget::pane {
            border: 1px solid #444;
        }
        QTabBar::tab {
            background-color: #3d3d3d;
            color: #ffffff;
            padding: 8px 20px;
            border: 1px solid #444;
        }
        QTabBar::tab:selected {
            background-color: #0d7377;
        }
        """
        self.setStyleSheet(style)
    
    def closeEvent(self, event):
        """Handle window close"""
        self.update_timer.stop()
        self.redis_monitor.stop()
        event.accept()


def main():
    """Main entry point"""
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    monitor = FNOServicesMonitor()
    monitor.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
