"""
Service Dashboard GUI
=====================
PyQt6-based dashboard to monitor and control market data services.

Features:
- Start/Stop services individually or all at once
- Monitor service health (running, errors, resource usage)
- View real-time logs
- Auto-start during market hours
- Redis connection monitoring

Usage:
    python -m dhan_trading.dashboard.service_dashboard
"""
import os
import sys
import logging
from datetime import datetime, time as dt_time
from typing import Dict, Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QTextEdit,
    QGroupBox, QGridLayout, QSplitter, QTabWidget, QCheckBox,
    QStatusBar, QMessageBox, QHeaderView, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QColor, QFont, QIcon, QPalette, QBrush

import redis
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dhan_trading.dashboard.service_manager import (
    ServiceManager, ServiceStatus, ServiceInfo, get_service_manager
)
from dhan_trading.db_setup import get_engine, DHAN_DB_NAME

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ServiceControlWidget(QWidget):
    """Widget for controlling a single service."""
    
    # Colors for status
    STATUS_COLORS = {
        ServiceStatus.STOPPED: "#6c757d",   # Gray
        ServiceStatus.STARTING: "#ffc107",  # Yellow
        ServiceStatus.RUNNING: "#28a745",   # Green
        ServiceStatus.ERROR: "#dc3545",     # Red
        ServiceStatus.STOPPING: "#ffc107",  # Yellow
    }
    
    start_clicked = pyqtSignal(str)
    stop_clicked = pyqtSignal(str)
    
    def __init__(self, service_id: str, service_info: ServiceInfo, parent=None):
        super().__init__(parent)
        self.service_id = service_id
        self.service_info = service_info
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Status indicator
        self.status_indicator = QLabel("●")
        self.status_indicator.setFixedWidth(20)
        self.status_indicator.setStyleSheet(f"color: {self.STATUS_COLORS[ServiceStatus.STOPPED]}; font-size: 16px;")
        layout.addWidget(self.status_indicator)
        
        # Service name and description
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        self.name_label = QLabel(self.service_info.name)
        self.name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        info_layout.addWidget(self.name_label)
        
        self.desc_label = QLabel(self.service_info.description)
        self.desc_label.setStyleSheet("color: #666; font-size: 10px;")
        self.desc_label.setWordWrap(True)
        info_layout.addWidget(self.desc_label)
        
        layout.addLayout(info_layout, stretch=1)
        
        # Stats
        stats_layout = QVBoxLayout()
        stats_layout.setSpacing(2)
        
        self.pid_label = QLabel("PID: -")
        self.pid_label.setStyleSheet("font-size: 10px;")
        stats_layout.addWidget(self.pid_label)
        
        self.uptime_label = QLabel("Uptime: -")
        self.uptime_label.setStyleSheet("font-size: 10px;")
        stats_layout.addWidget(self.uptime_label)
        
        self.resource_label = QLabel("CPU: 0% | Mem: 0 MB")
        self.resource_label.setStyleSheet("font-size: 10px;")
        stats_layout.addWidget(self.resource_label)
        
        layout.addLayout(stats_layout)
        
        # Control buttons
        self.start_btn = QPushButton("Start")
        self.start_btn.setFixedWidth(70)
        self.start_btn.clicked.connect(lambda: self.start_clicked.emit(self.service_id))
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setFixedWidth(70)
        self.stop_btn.clicked.connect(lambda: self.stop_clicked.emit(self.service_id))
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        layout.addWidget(self.stop_btn)
    
    def update_status(self, status: ServiceStatus, service_info: ServiceInfo):
        """Update display based on service status."""
        self.service_info = service_info
        
        # Update status indicator
        self.status_indicator.setStyleSheet(
            f"color: {self.STATUS_COLORS[status]}; font-size: 16px;"
        )
        
        # Update buttons
        is_running = status == ServiceStatus.RUNNING
        is_starting = status == ServiceStatus.STARTING
        is_stopping = status == ServiceStatus.STOPPING
        
        self.start_btn.setEnabled(not is_running and not is_starting and not is_stopping)
        self.stop_btn.setEnabled(is_running or is_starting)
        
        # Update stats
        if service_info.pid:
            self.pid_label.setText(f"PID: {service_info.pid}")
        else:
            self.pid_label.setText("PID: -")
        
        if service_info.start_time and is_running:
            uptime = datetime.now() - service_info.start_time
            hours, remainder = divmod(int(uptime.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.uptime_label.setText(f"Uptime: {hours:02d}:{minutes:02d}:{seconds:02d}")
        else:
            self.uptime_label.setText("Uptime: -")
        
        self.resource_label.setText(
            f"CPU: {service_info.cpu_percent:.1f}% | Mem: {service_info.memory_mb:.1f} MB"
        )


class ServiceDashboard(QMainWindow):
    """Main dashboard window."""
    
    def __init__(self):
        super().__init__()
        self.manager = get_service_manager()
        self.service_widgets: Dict[str, ServiceControlWidget] = {}
        
        self._setup_ui()
        self._setup_callbacks()
        self._setup_timers()
        
        # Initial update
        self._update_all()
    
    def _setup_ui(self):
        """Setup the main UI."""
        self.setWindowTitle("Dhan Market Data Services Dashboard")
        self.setMinimumSize(900, 700)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = self._create_header()
        main_layout.addWidget(header)
        
        # Main content - splitter for services and logs
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Services panel
        services_panel = self._create_services_panel()
        splitter.addWidget(services_panel)
        
        # Tabs for logs and stats
        tabs = self._create_tabs()
        splitter.addWidget(tabs)
        
        splitter.setSizes([300, 400])
        main_layout.addWidget(splitter)
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self._update_status_bar()
    
    def _create_header(self) -> QWidget:
        """Create header with title and global controls."""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #1a1a2e;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        layout = QHBoxLayout(header)
        
        # Title
        title_layout = QVBoxLayout()
        title = QLabel("🚀 Dhan Market Data Services")
        title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        title_layout.addWidget(title)
        
        self.market_status_label = QLabel("Market: Checking...")
        self.market_status_label.setStyleSheet("color: #aaa; font-size: 12px;")
        title_layout.addWidget(self.market_status_label)
        
        layout.addLayout(title_layout)
        layout.addStretch()
        
        # Auto-start checkbox
        self.auto_start_cb = QCheckBox("Auto-start during market hours")
        self.auto_start_cb.setStyleSheet("color: white;")
        self.auto_start_cb.setChecked(True)
        layout.addWidget(self.auto_start_cb)
        
        # Global buttons
        self.start_all_btn = QPushButton("▶ Start All")
        self.start_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.start_all_btn.clicked.connect(self._start_all)
        layout.addWidget(self.start_all_btn)
        
        self.stop_all_btn = QPushButton("⏹ Stop All")
        self.stop_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        self.stop_all_btn.clicked.connect(self._stop_all)
        layout.addWidget(self.stop_all_btn)
        
        return header
    
    def _create_services_panel(self) -> QWidget:
        """Create services control panel."""
        group = QGroupBox("Services")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        layout = QVBoxLayout(group)
        
        # Create widget for each service
        for service_id, service_info in self.manager.services.items():
            widget = ServiceControlWidget(service_id, service_info)
            widget.start_clicked.connect(self._start_service)
            widget.stop_clicked.connect(self._stop_service)
            self.service_widgets[service_id] = widget
            layout.addWidget(widget)
            
            # Add separator
            if service_id != list(self.manager.services.keys())[-1]:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setStyleSheet("background-color: #eee;")
                layout.addWidget(line)
        
        layout.addStretch()
        return group
    
    def _create_quotes_tab(self) -> QWidget:
        """Create Live Quotes tab with real-time quote display."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Header with stats
        header = QHBoxLayout()
        
        self.quotes_count_label = QLabel("Quotes: 0")
        self.quotes_count_label.setStyleSheet("font-weight: bold;")
        header.addWidget(self.quotes_count_label)
        
        self.quotes_rate_label = QLabel("Rate: 0/sec")
        header.addWidget(self.quotes_rate_label)
        
        header.addStretch()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_quotes)
        header.addWidget(refresh_btn)
        
        layout.addLayout(header)
        
        # Quotes table
        self.quotes_table = QTableWidget()
        self.quotes_table.setColumnCount(8)
        self.quotes_table.setHorizontalHeaderLabels([
            "Security ID", "Symbol", "LTP", "Change", "Bid Qty", 
            "Ask Qty", "Volume", "Last Update"
        ])
        
        # Style the table
        self.quotes_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #ddd;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 5px;
                border: 1px solid #ddd;
                font-weight: bold;
            }
        """)
        
        # Stretch columns
        header = self.quotes_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.quotes_table)
        
        # Initialize quote tracking
        self._quote_data: Dict[int, dict] = {}
        self._last_quote_count = 0
        self._quote_rate_timestamp = datetime.now()
        
        return widget
    
    def _refresh_quotes(self):
        """Refresh quotes from Redis stream."""
        try:
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            
            # Read latest entries from stream
            try:
                entries = r.xrevrange('dhan:quotes:stream', count=100)
            except redis.ResponseError:
                return
            
            # Parse entries
            quotes = {}
            for entry_id, data in entries:
                security_id = int(data.get('security_id', 0))
                if security_id not in quotes:  # Keep only latest per security
                    quotes[security_id] = {
                        'security_id': security_id,
                        'ltp': float(data.get('ltp', 0)),
                        'open': float(data.get('open', 0)),
                        'high': float(data.get('high', 0)),
                        'low': float(data.get('low', 0)),
                        'close': float(data.get('close', 0)),
                        'bid_qty': int(data.get('total_buy_qty', 0)),
                        'ask_qty': int(data.get('total_sell_qty', 0)),
                        'volume': int(data.get('volume', 0)),
                        'timestamp': data.get('timestamp', '')
                    }
            
            self._quote_data = quotes
            self._update_quotes_table()
            
        except Exception as e:
            logger.error(f"Error refreshing quotes: {e}")
    
    def _update_quotes_table(self):
        """Update the quotes table with current data."""
        # Load instrument names if not loaded
        if not hasattr(self, '_instrument_names'):
            self._load_instrument_names()
        
        self.quotes_table.setRowCount(len(self._quote_data))
        
        for row, (security_id, quote) in enumerate(sorted(self._quote_data.items())):
            # Security ID
            self.quotes_table.setItem(row, 0, QTableWidgetItem(str(security_id)))
            
            # Symbol name
            symbol = self._instrument_names.get(security_id, f"ID:{security_id}")
            self.quotes_table.setItem(row, 1, QTableWidgetItem(symbol))
            
            # LTP
            ltp = quote.get('ltp', 0)
            ltp_item = QTableWidgetItem(f"{ltp:,.2f}")
            ltp_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.quotes_table.setItem(row, 2, ltp_item)
            
            # Change (LTP vs Close)
            close = quote.get('close', 0)
            if close > 0:
                change = ((ltp - close) / close) * 100
                change_item = QTableWidgetItem(f"{change:+.2f}%")
                change_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if change > 0:
                    change_item.setForeground(QBrush(QColor("#28a745")))
                elif change < 0:
                    change_item.setForeground(QBrush(QColor("#dc3545")))
                self.quotes_table.setItem(row, 3, change_item)
            else:
                self.quotes_table.setItem(row, 3, QTableWidgetItem("-"))
            
            # Bid Qty
            bid_item = QTableWidgetItem(f"{quote.get('bid_qty', 0):,}")
            bid_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.quotes_table.setItem(row, 4, bid_item)
            
            # Ask Qty
            ask_item = QTableWidgetItem(f"{quote.get('ask_qty', 0):,}")
            ask_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.quotes_table.setItem(row, 5, ask_item)
            
            # Volume
            vol_item = QTableWidgetItem(f"{quote.get('volume', 0):,}")
            vol_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.quotes_table.setItem(row, 6, vol_item)
            
            # Last Update
            ts = quote.get('timestamp', '')
            if ts:
                try:
                    dt = datetime.fromisoformat(ts)
                    ts_display = dt.strftime("%H:%M:%S")
                except:
                    ts_display = ts[-8:]  # Last 8 chars
            else:
                ts_display = "-"
            self.quotes_table.setItem(row, 7, QTableWidgetItem(ts_display))
        
        # Update stats
        self.quotes_count_label.setText(f"Quotes: {len(self._quote_data)}")
        
        # Calculate rate
        now = datetime.now()
        elapsed = (now - self._quote_rate_timestamp).total_seconds()
        if elapsed > 0:
            rate = (len(self._quote_data) - self._last_quote_count) / elapsed
            self.quotes_rate_label.setText(f"Rate: {rate:.1f}/sec")
        self._last_quote_count = len(self._quote_data)
        self._quote_rate_timestamp = now
    
    def _load_instrument_names(self):
        """Load instrument names from database."""
        self._instrument_names = {}
        try:
            from dhan_trading.market_feed.instrument_selector import InstrumentSelector
            selector = InstrumentSelector()
            
            # Get Nifty futures
            for inst in selector.get_nifty_futures(expiries=[0, 1, 2]):
                self._instrument_names[inst['security_id']] = inst.get('display_name', inst['symbol'])
            
            # Get Bank Nifty futures
            for inst in selector.get_banknifty_futures(expiries=[0, 1, 2]):
                self._instrument_names[inst['security_id']] = inst.get('display_name', inst['symbol'])
            
            # Get MCX Commodity futures
            for inst in selector.get_major_commodity_futures(expiries=[0, 1]):
                self._instrument_names[inst['security_id']] = inst.get('display_name', inst['symbol'])
            
            # Get Nifty 50 stocks
            for inst in selector.get_nifty50_stocks():
                self._instrument_names[inst['security_id']] = inst.get('display_name', inst['symbol'])
            
            logger.info(f"Loaded {len(self._instrument_names)} instrument names")
        except Exception as e:
            logger.error(f"Failed to load instrument names: {e}")

    def _create_tabs(self) -> QTabWidget:
        """Create tabs for logs and stats."""
        tabs = QTabWidget()
        
        # Live Quotes tab
        quotes_widget = self._create_quotes_tab()
        tabs.addTab(quotes_widget, "📈 Live Quotes")
        
        # Logs tab
        logs_widget = QWidget()
        logs_layout = QVBoxLayout(logs_widget)
        
        # Service log selector
        log_header = QHBoxLayout()
        log_header.addWidget(QLabel("Select Service:"))
        
        self.log_service_btns: Dict[str, QPushButton] = {}
        for service_id, service_info in self.manager.services.items():
            btn = QPushButton(service_info.name)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, sid=service_id: self._select_log_service(sid))
            self.log_service_btns[service_id] = btn
            log_header.addWidget(btn)
        
        log_header.addStretch()
        
        self.clear_log_btn = QPushButton("Clear")
        self.clear_log_btn.clicked.connect(self._clear_log)
        log_header.addWidget(self.clear_log_btn)
        
        logs_layout.addLayout(log_header)
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #333;
            }
        """)
        logs_layout.addWidget(self.log_text)
        
        tabs.addTab(logs_widget, "📋 Logs")
        
        # Redis stats tab
        redis_widget = QWidget()
        redis_layout = QVBoxLayout(redis_widget)
        
        # Redis connection status
        self.redis_status_label = QLabel("Redis: Checking...")
        self.redis_status_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        redis_layout.addWidget(self.redis_status_label)
        
        # Streams info
        self.streams_text = QTextEdit()
        self.streams_text.setReadOnly(True)
        self.streams_text.setFont(QFont("Consolas", 10))
        redis_layout.addWidget(self.streams_text)
        
        tabs.addTab(redis_widget, "📊 Redis Stats")
        
        # Database stats tab
        db_widget = QWidget()
        db_layout = QVBoxLayout(db_widget)
        
        self.db_status_label = QLabel("Database: Checking...")
        self.db_status_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        db_layout.addWidget(self.db_status_label)
        
        self.db_stats_text = QTextEdit()
        self.db_stats_text.setReadOnly(True)
        self.db_stats_text.setFont(QFont("Consolas", 10))
        db_layout.addWidget(self.db_stats_text)
        
        tabs.addTab(db_widget, "🗄️ Database")
        
        # Select first log service
        if self.log_service_btns:
            first_service = list(self.log_service_btns.keys())[0]
            self.log_service_btns[first_service].setChecked(True)
            self._current_log_service = first_service
        
        return tabs
    
    def _setup_callbacks(self):
        """Setup manager callbacks."""
        self.manager.set_status_callback(self._on_status_change)
        self.manager.set_output_callback(self._on_output)
    
    def _setup_timers(self):
        """Setup update timers."""
        # Fast timer for UI updates (1 second)
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self._update_ui)
        self.ui_timer.start(1000)
        
        # Quotes refresh timer (2 seconds)
        self.quotes_timer = QTimer()
        self.quotes_timer.timeout.connect(self._refresh_quotes)
        self.quotes_timer.start(2000)
        
        # Slow timer for health checks (5 seconds)
        self.health_timer = QTimer()
        self.health_timer.timeout.connect(self._health_check)
        self.health_timer.start(5000)
        
        # Market hours check timer (1 minute)
        self.market_timer = QTimer()
        self.market_timer.timeout.connect(self._check_market_hours)
        self.market_timer.start(60000)
    
    def _update_all(self):
        """Update all UI elements."""
        self._update_ui()
        self._update_redis_stats()
        self._check_market_hours()
        self._refresh_quotes()
    
    def _update_ui(self):
        """Update UI elements."""
        self.manager.update_resource_usage()
        
        for service_id, widget in self.service_widgets.items():
            service = self.manager.services[service_id]
            widget.update_status(service.status, service)
        
        self._update_status_bar()
    
    def _health_check(self):
        """Check service health."""
        self.manager.check_process_health()
        self._update_redis_stats()
    
    def _check_market_hours(self):
        """Check market hours and auto-start if needed."""
        is_market_hours = self.manager.is_market_hours()
        now = datetime.now()
        
        if is_market_hours:
            self.market_status_label.setText(
                f"🟢 Market OPEN | {now.strftime('%H:%M:%S')}"
            )
            self.market_status_label.setStyleSheet("color: #28a745; font-size: 12px;")
            
            # Auto-start if enabled
            if self.auto_start_cb.isChecked():
                for service_id, service in self.manager.services.items():
                    if service.status == ServiceStatus.STOPPED:
                        logger.info(f"Auto-starting {service.name} (market hours)")
                        self.manager.start_service(service_id)
        else:
            # Check if weekend
            if now.weekday() >= 5:
                self.market_status_label.setText(f"🔴 Weekend | {now.strftime('%A')}")
            else:
                self.market_status_label.setText(
                    f"🔴 Market CLOSED | {now.strftime('%H:%M:%S')}"
                )
            self.market_status_label.setStyleSheet("color: #dc3545; font-size: 12px;")
    
    def _update_redis_stats(self):
        """Update Redis statistics display."""
        stats = self.manager.get_redis_stats()
        
        if stats.get('connected'):
            self.redis_status_label.setText("🟢 Redis: Connected")
            self.redis_status_label.setStyleSheet("color: #28a745; font-size: 14px; font-weight: bold;")
            
            # Build streams info
            lines = ["=" * 50, "REDIS STREAMS STATUS", "=" * 50, ""]
            
            for stream_name, info in stats.get('streams', {}).items():
                lines.append(f"Stream: {stream_name}")
                lines.append(f"  Length: {info.get('length', 0):,}")
                if info.get('last_entry'):
                    entry_id = info['last_entry'][0]
                    # Parse timestamp from stream ID
                    try:
                        ts = int(entry_id.split('-')[0]) / 1000
                        dt = datetime.fromtimestamp(ts)
                        lines.append(f"  Last Entry: {dt.strftime('%H:%M:%S')}")
                    except:
                        pass
                lines.append("")
            
            lines.append("=" * 50)
            lines.append(f"Active Channels: {len(stats.get('channels', []))}")
            for ch in stats.get('channels', []):
                lines.append(f"  - {ch}")
            
            self.streams_text.setText("\n".join(lines))
        else:
            self.redis_status_label.setText("🔴 Redis: Disconnected")
            self.redis_status_label.setStyleSheet("color: #dc3545; font-size: 14px; font-weight: bold;")
            self.streams_text.setText(f"Error: {stats.get('error', 'Unknown')}")
        
        # Also update DB stats
        self._update_db_stats()
    
    def _update_db_stats(self):
        """Update database statistics display."""
        try:
            from sqlalchemy import text
            from dotenv import load_dotenv
            load_dotenv()
            
            engine = get_engine(DHAN_DB_NAME)
            with engine.connect() as conn:
                # Get quote count
                result = conn.execute(text("SELECT COUNT(*) FROM dhan_quotes"))
                quote_count = result.fetchone()[0]
                
                # Get latest quote time
                result = conn.execute(text("""
                    SELECT MAX(timestamp) as latest 
                    FROM dhan_quotes
                """))
                latest = result.fetchone()[0]
                
                # Get unique instruments
                result = conn.execute(text("""
                    SELECT COUNT(DISTINCT security_id) as instruments
                    FROM dhan_quotes
                """))
                instruments = result.fetchone()[0]
                
                # Get quotes in last hour
                result = conn.execute(text("""
                    SELECT COUNT(*) 
                    FROM dhan_quotes 
                    WHERE timestamp >= NOW() - INTERVAL 1 HOUR
                """))
                recent_quotes = result.fetchone()[0]
            
            self.db_status_label.setText("🟢 Database: Connected")
            self.db_status_label.setStyleSheet("color: #28a745; font-size: 14px; font-weight: bold;")
            
            lines = [
                "=" * 50,
                "DATABASE STATISTICS",
                "=" * 50,
                "",
                f"📊 Total Quotes: {quote_count:,}",
                f"🏷️ Unique Instruments: {instruments}",
                f"⏰ Quotes in Last Hour: {recent_quotes:,}",
                f"📅 Latest Quote: {latest}" if latest else "📅 Latest Quote: N/A",
                "",
                "=" * 50,
            ]
            
            self.db_stats_text.setText("\n".join(lines))
            
        except Exception as e:
            self.db_status_label.setText("🔴 Database: Error")
            self.db_status_label.setStyleSheet("color: #dc3545; font-size: 14px; font-weight: bold;")
            self.db_stats_text.setText(f"Error: {str(e)}")
    
    def _update_status_bar(self):
        """Update status bar."""
        running_count = sum(
            1 for s in self.manager.services.values() 
            if s.status == ServiceStatus.RUNNING
        )
        total_count = len(self.manager.services)
        
        self.statusBar.showMessage(
            f"Services: {running_count}/{total_count} running | "
            f"Last update: {datetime.now().strftime('%H:%M:%S')}"
        )
    
    def _start_service(self, service_id: str):
        """Start a single service."""
        logger.info(f"Starting service: {service_id}")
        self.manager.start_service(service_id)
    
    def _stop_service(self, service_id: str):
        """Stop a single service."""
        logger.info(f"Stopping service: {service_id}")
        self.manager.stop_service(service_id)
    
    def _start_all(self):
        """Start all services."""
        logger.info("Starting all services")
        self.manager.start_all()
    
    def _stop_all(self):
        """Stop all services."""
        reply = QMessageBox.question(
            self,
            "Stop All Services",
            "Are you sure you want to stop all services?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            logger.info("Stopping all services")
            self.manager.stop_all()
    
    def _on_status_change(self, service_id: str, status: ServiceStatus):
        """Handle service status change callback."""
        if service_id in self.service_widgets:
            service = self.manager.services[service_id]
            self.service_widgets[service_id].update_status(status, service)
    
    def _on_output(self, service_id: str, line: str):
        """Handle service output callback."""
        if hasattr(self, '_current_log_service') and service_id == self._current_log_service:
            self.log_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] {line}")
            # Auto-scroll to bottom
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def _select_log_service(self, service_id: str):
        """Select service for log display."""
        self._current_log_service = service_id
        
        # Update button states
        for sid, btn in self.log_service_btns.items():
            btn.setChecked(sid == service_id)
        
        # Load existing logs
        service = self.manager.services[service_id]
        self.log_text.clear()
        for line in service.output_lines[-100:]:  # Last 100 lines
            self.log_text.append(line)
    
    def _clear_log(self):
        """Clear log display."""
        self.log_text.clear()
        if hasattr(self, '_current_log_service'):
            service = self.manager.services.get(self._current_log_service)
            if service:
                service.output_lines.clear()
    
    def closeEvent(self, event):
        """Handle window close."""
        # Check if any services are running
        running = [s for s in self.manager.services.values() if s.status == ServiceStatus.RUNNING]
        
        if running:
            reply = QMessageBox.question(
                self,
                "Services Running",
                f"{len(running)} service(s) are still running.\n\n"
                "Do you want to stop all services before closing?",
                QMessageBox.StandardButton.Yes | 
                QMessageBox.StandardButton.No | 
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.manager.stop_all()
                event.accept()
            elif reply == QMessageBox.StandardButton.No:
                event.accept()
            else:
                event.ignore()
                return
        
        # Cleanup
        self.manager.cleanup()
        event.accept()


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Dark palette (optional)
    # palette = QPalette()
    # palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    # app.setPalette(palette)
    
    dashboard = ServiceDashboard()
    dashboard.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
