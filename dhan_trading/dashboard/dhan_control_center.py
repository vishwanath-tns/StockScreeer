"""
DHAN CONTROL CENTER - Unified Hub for All Dhan Trading Applications
Launches, monitors, and controls all Dhan services from one place
"""

import sys
import subprocess
import json
import time
from pathlib import Path
from datetime import datetime
from enum import Enum

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStatusBar, QTabWidget, QTableWidget, QTableWidgetItem,
    QTextEdit, QComboBox, QSpinBox, QMessageBox, QGroupBox, QGridLayout,
    QDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QProcess
from PyQt5.QtGui import QFont, QColor, QPixmap, QIcon
import redis
import psutil


class ServiceStatus(Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"


class DhanService:
    """Represents a Dhan service"""
    def __init__(self, name, script, description, icon_color="blue"):
        self.name = name
        self.script = script
        self.description = description
        self.icon_color = icon_color
        self.status = ServiceStatus.STOPPED
        self.process = None
        self.pid = None
        self.start_time = None
        self.quote_count = 0
        self.error_log = []

    def is_running(self):
        return self.process is not None and self.process.poll() is None

    def get_uptime(self):
        if self.start_time:
            return int(time.time() - self.start_time)
        return 0

    def get_memory_usage(self):
        if self.pid:
            try:
                process = psutil.Process(self.pid)
                return process.memory_info().rss / (1024 * 1024)  # MB
            except:
                return 0
        return 0

    def get_status_display(self):
        if self.is_running():
            return f"RUNNING (PID: {self.pid}, Uptime: {self.get_uptime()}s)"
        else:
            return "STOPPED"


class ServiceMonitorThread(QThread):
    """Background thread to monitor Redis and service health"""
    status_updated = pyqtSignal(str, dict)  # service_name, data

    def __init__(self, services):
        super().__init__()
        self.services = services
        self.running = True
        try:
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True
            )
            self.redis_client.ping()
        except:
            self.redis_client = None

    def run(self):
        while self.running:
            try:
                # Monitor each service
                for service in self.services.values():
                    data = {
                        'status': service.get_status_display(),
                        'memory_mb': f"{service.get_memory_usage():.1f}",
                        'running': service.is_running()
                    }

                    # Get quote counts from Redis if available
                    if self.redis_client and service.name == "FNO Feed Launcher":
                        try:
                            quotes = self.redis_client.get('dhan:quote_count')
                            if quotes:
                                data['quotes'] = quotes
                        except:
                            pass

                    self.status_updated.emit(service.name, data)

                time.sleep(2)
            except Exception as e:
                print(f"Monitor thread error: {e}")
                time.sleep(5)

    def stop(self):
        self.running = False


class DhanControlCenter(QMainWindow):
    """Main Control Center Application"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DHAN Control Center - Trading Services Hub")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize services
        self.services = {
            "FNO Feed Launcher": DhanService(
                "FNO Feed Launcher",
                "launch_fno_feed.py",
                "Real-time NIFTY & BANKNIFTY futures/options feed (128 instruments)",
                "green"
            ),
            "FNO+MCX Feed": DhanService(
                "FNO+MCX Feed",
                "launch_fno_feed.py --include-commodities",
                "FNO + MCX commodities (Gold, Crude, Silver, Natural Gas)",
                "darkgreen"
            ),
            "FNO Services Monitor": DhanService(
                "FNO Services Monitor",
                "python -m dhan_trading.dashboard.fno_services_monitor",
                "PyQt5 Dashboard - Services status, quotes, system health",
                "blue"
            ),
            "FNO Database Writer": DhanService(
                "FNO Database Writer",
                "python -m dhan_trading.subscribers.fno_db_writer",
                "Writes FNO quotes to MySQL database",
                "purple"
            ),
            "Market Scheduler": DhanService(
                "Market Scheduler",
                "launch_market_scheduler.py",
                "Auto-start/stop services at market hours (8:55 AM - 12 AM IST)",
                "teal"
            ),
            "Instrument Display": DhanService(
                "Instrument Display",
                "display_fno_instruments.py",
                "Show all subscribed instruments (Nifty/BankNifty/Options/MCX)",
                "orange"
            ),
            "Volume Profile": DhanService(
                "Volume Profile",
                "python -m dhan_trading.visualizers.volume_profile",
                "Real-time volume distribution across price levels (POC, Value Area)",
                "darkblue"
            ),
            "Market Breadth": DhanService(
                "Market Breadth",
                "python -m dhan_trading.visualizers.market_breadth",
                "Nifty 50 market sentiment - Advances vs Declines tracker",
                "darkgreen"
            ),
            "Tick Chart": DhanService(
                "Tick Chart",
                "python -m dhan_trading.visualizers.tick_chart",
                "Price movement based on tick count (10, 25, 50, 100, 200 ticks per bar)",
                "darkred"
            ),
            "Volume Profile Chart": DhanService(
                "Volume Profile Chart",
                "python -m dhan_trading.visualizers.volume_profile_chart",
                "5-minute volume profiles with VAH/VAL/POC over time",
                "purple"
            ),
            "Quote Visualizer": DhanService(
                "Quote Visualizer",
                "python -m dhan_trading.visualizers.quote_visualizer",
                "Terminal-based real-time quote display (lightweight monitoring)",
                "cyan"
            ),
        }

        # Setup UI
        self.setup_ui()
        
        # Start monitoring thread
        self.monitor_thread = ServiceMonitorThread(self.services)
        self.monitor_thread.status_updated.connect(self.update_service_status)
        self.monitor_thread.start()

        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_overview)
        self.refresh_timer.start(3000)  # Every 3 seconds

    def setup_ui(self):
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        
        # Header
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Tab widget
        tabs = QTabWidget()
        
        # Tab 1: Control Panel
        control_tab = self.create_control_tab()
        tabs.addTab(control_tab, "Control Panel")
        
        # Tab 2: Services Status
        status_tab = self.create_status_tab()
        tabs.addTab(status_tab, "Services Status")
        
        # Tab 3: Real-time Monitor
        monitor_tab = self.create_monitor_tab()
        tabs.addTab(monitor_tab, "Real-time Monitor")
        
        # Tab 4: Logs
        logs_tab = self.create_logs_tab()
        tabs.addTab(logs_tab, "System Logs")
        
        # Tab 5: Configuration
        config_tab = self.create_config_tab()
        tabs.addTab(config_tab, "Configuration")
        
        main_layout.addWidget(tabs)
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("DHAN Control Center Ready")
        
        central_widget.setLayout(main_layout)

    def create_header(self):
        """Create header with title and quick info"""
        header = QGroupBox()
        layout = QHBoxLayout()
        
        title = QLabel("DHAN Control Center")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        layout.addStretch()
        
        self.status_label = QLabel("Status: All Services Offline")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        self.time_label = QLabel()
        self.update_time_label()
        layout.addWidget(self.time_label)
        
        # Auto-update time
        time_timer = QTimer()
        time_timer.timeout.connect(self.update_time_label)
        time_timer.start(1000)
        
        header.setLayout(layout)
        return header

    def update_time_label(self):
        self.time_label.setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def create_control_tab(self):
        """Create the main control panel tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Quick start section
        quick_start = QGroupBox("Quick Start")
        quick_layout = QGridLayout()
        
        row = 0
        for service_name, service in self.services.items():
            start_btn = QPushButton(f"Start {service_name}")
            start_btn.clicked.connect(lambda checked, s=service_name: self.start_service(s))
            start_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px;")
            
            stop_btn = QPushButton(f"Stop")
            stop_btn.clicked.connect(lambda checked, s=service_name: self.stop_service(s))
            stop_btn.setStyleSheet("background-color: #f44336; color: white; padding: 10px;")
            
            status_label = QLabel("OFFLINE")
            status_label.setStyleSheet("color: red;")
            self.services[service_name].status_label = status_label
            
            quick_layout.addWidget(QLabel(f"{service_name}:"), row, 0)
            quick_layout.addWidget(start_btn, row, 1)
            quick_layout.addWidget(stop_btn, row, 2)
            quick_layout.addWidget(status_label, row, 3)
            row += 1
        
        quick_start.setLayout(quick_layout)
        layout.addWidget(quick_start)
        
        # Service descriptions
        desc_group = QGroupBox("Service Descriptions")
        desc_layout = QVBoxLayout()
        
        for service_name, service in self.services.items():
            desc = QLabel(f"• {service_name}: {service.description}")
            desc_layout.addWidget(desc)
        
        desc_group.setLayout(desc_layout)
        layout.addWidget(desc_group)
        
        # Batch operations
        batch_group = QGroupBox("Batch Operations")
        batch_layout = QHBoxLayout()
        
        start_all_btn = QPushButton("Start All Services")
        start_all_btn.clicked.connect(self.start_all_services)
        start_all_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 10px;")
        
        stop_all_btn = QPushButton("Stop All Services")
        stop_all_btn.clicked.connect(self.stop_all_services)
        stop_all_btn.setStyleSheet("background-color: #FF9800; color: white; padding: 10px;")
        
        restart_all_btn = QPushButton("Restart All Services")
        restart_all_btn.clicked.connect(self.restart_all_services)
        restart_all_btn.setStyleSheet("background-color: #9C27B0; color: white; padding: 10px;")
        
        batch_layout.addWidget(start_all_btn)
        batch_layout.addWidget(stop_all_btn)
        batch_layout.addWidget(restart_all_btn)
        
        batch_group.setLayout(batch_layout)
        layout.addWidget(batch_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_status_tab(self):
        """Create services status tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        self.status_table = QTableWidget()
        self.status_table.setColumnCount(5)
        self.status_table.setHorizontalHeaderLabels(
            ["Service Name", "Status", "PID", "Uptime (s)", "Memory (MB)"]
        )
        self.status_table.setRowCount(len(self.services))
        
        row = 0
        for service_name in self.services:
            self.status_table.setItem(row, 0, QTableWidgetItem(service_name))
            row += 1
        
        layout.addWidget(self.status_table)
        widget.setLayout(layout)
        return widget

    def create_monitor_tab(self):
        """Create real-time monitor tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        self.monitor_text = QTextEdit()
        self.monitor_text.setReadOnly(True)
        self.monitor_text.setFont(QFont("Courier", 9))
        
        layout.addWidget(QLabel("Real-time Service Monitor"))
        layout.addWidget(self.monitor_text)
        
        widget.setLayout(layout)
        return widget

    def create_logs_tab(self):
        """Create system logs tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setFont(QFont("Courier", 9))
        
        clear_btn = QPushButton("Clear Logs")
        clear_btn.clicked.connect(self.logs_text.clear)
        
        layout.addWidget(QLabel("System Logs"))
        layout.addWidget(self.logs_text)
        layout.addWidget(clear_btn)
        
        widget.setLayout(layout)
        return widget

    def create_config_tab(self):
        """Create configuration tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        config_text = QTextEdit()
        config_text.setReadOnly(True)
        
        config_info = "DHAN CONTROL CENTER CONFIGURATION\n\n"
        config_info += "Services Configured:\n"
        for service_name, service in self.services.items():
            config_info += f"  • {service_name}\n"
            config_info += f"    Script: {service.script}\n"
            config_info += f"    Description: {service.description}\n\n"
        
        config_info += "\nDatabase Configuration:\n"
        config_info += "  MySQL Host: localhost\n"
        config_info += "  MySQL Port: 3306\n"
        config_info += "  Database: marketdata\n"
        config_info += "  Redis Host: localhost\n"
        config_info += "  Redis Port: 6379\n"
        
        config_info += "\nInstruments Configuration:\n"
        config_info += "  NSE FNO (Futures & Options):\n"
        config_info += "    • NIFTY Futures (2 contracts)\n"
        config_info += "    • BANKNIFTY Futures (2 contracts)\n"
        config_info += "    • NIFTY Weekly Options (82 contracts, Dec 16 expiry)\n"
        config_info += "    • BANKNIFTY Options (42 contracts, Dec 30 expiry)\n"
        config_info += "    Total: 128 instruments\n\n"
        config_info += "  MCX Commodities (Optional):\n"
        config_info += "    • GOLD (Gold futures)\n"
        config_info += "    • CRUDE (Crude Oil futures)\n"
        config_info += "    • SILVER (Silver futures)\n"
        config_info += "    • NATGAS (Natural Gas futures)\n"
        config_info += "    • COPPER (Copper futures)\n"
        config_info += "    Run with --include-commodities flag to enable\n"
        
        config_info += "\nVisualizers (Data Analysis & Display):\n"
        config_info += "  1. Volume Profile\n"
        config_info += "     - Volume distribution across price levels\n"
        config_info += "     - Shows POC (Point of Control) and Value Area\n"
        config_info += "     - Real-time updates from Redis\n\n"
        config_info += "  2. Market Breadth\n"
        config_info += "     - Tracks all Nifty 50 stocks\n"
        config_info += "     - Advances vs Declines visualization\n"
        config_info += "     - Market sentiment indicator\n\n"
        config_info += "  3. Tick Chart\n"
        config_info += "     - Price movement by tick count (not time)\n"
        config_info += "     - Configurable: 10, 25, 50, 100, 200 ticks/bar\n"
        config_info += "     - OHLC candles with volume\n\n"
        config_info += "  4. Volume Profile Chart\n"
        config_info += "     - 5-minute volume profiles over time\n"
        config_info += "     - VAH, VAL, POC with time series\n"
        config_info += "     - Intraday volume analysis\n\n"
        config_info += "  5. Quote Visualizer\n"
        config_info += "     - Terminal-based real-time quotes\n"
        config_info += "     - Lightweight monitoring\n"
        config_info += "     - No GUI overhead\n"
        
        config_text.setText(config_info)
        
        layout.addWidget(QLabel("Configuration"))
        layout.addWidget(config_text)
        
        widget.setLayout(layout)
        return widget

    def start_service(self, service_name):
        """Start a service"""
        service = self.services[service_name]
        
        if service.is_running():
            QMessageBox.warning(self, "Service Running", 
                              f"{service_name} is already running!")
            return
        
        try:
            # Start the service
            service.process = subprocess.Popen(
                f"python {service.script}",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(Path.cwd())
            )
            service.pid = service.process.pid
            service.start_time = time.time()
            service.status = ServiceStatus.RUNNING
            
            self.log_message(f"✓ Started: {service_name} (PID: {service.pid})")
            self.statusBar.showMessage(f"Started {service_name}")
            
        except Exception as e:
            service.status = ServiceStatus.ERROR
            service.error_log.append(str(e))
            self.log_message(f"✗ Failed to start {service_name}: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start {service_name}:\n{e}")

    def stop_service(self, service_name):
        """Stop a service"""
        service = self.services[service_name]
        
        if not service.is_running():
            QMessageBox.warning(self, "Service Not Running", 
                              f"{service_name} is not running!")
            return
        
        try:
            service.process.terminate()
            service.process.wait(timeout=5)
            service.process = None
            service.pid = None
            service.status = ServiceStatus.STOPPED
            
            self.log_message(f"✓ Stopped: {service_name}")
            self.statusBar.showMessage(f"Stopped {service_name}")
            
        except Exception as e:
            service.process.kill()
            service.status = ServiceStatus.ERROR
            self.log_message(f"✗ Error stopping {service_name}: {e}")

    def start_all_services(self):
        """Start all services"""
        reply = QMessageBox.question(self, "Start All Services",
                                    "Start all FNO services?\n\nThis will launch:\n" + 
                                    "\n".join([f"  • {s}" for s in self.services.keys()]),
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            for service_name in self.services:
                self.start_service(service_name)
                time.sleep(1)  # Stagger startup
            
            self.log_message("All services started")

    def stop_all_services(self):
        """Stop all services"""
        reply = QMessageBox.question(self, "Stop All Services",
                                    "Stop all FNO services?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            for service_name in self.services:
                self.stop_service(service_name)
            
            self.log_message("All services stopped")

    def restart_all_services(self):
        """Restart all services"""
        self.stop_all_services()
        time.sleep(2)
        self.start_all_services()

    def update_service_status(self, service_name, data):
        """Update service status display"""
        try:
            service = self.services[service_name]
            
            # Update status label if available
            if hasattr(service, 'status_label'):
                if data.get('running'):
                    service.status_label.setText("ONLINE")
                    service.status_label.setStyleSheet("color: green; font-weight: bold;")
                else:
                    service.status_label.setText("OFFLINE")
                    service.status_label.setStyleSheet("color: red;")
            
            # Update table
            row = list(self.services.keys()).index(service_name)
            self.status_table.setItem(row, 1, QTableWidgetItem(data['status']))
            
            pid = service.pid if service.is_running() else "N/A"
            self.status_table.setItem(row, 2, QTableWidgetItem(str(pid)))
            self.status_table.setItem(row, 3, QTableWidgetItem(str(service.get_uptime())))
            self.status_table.setItem(row, 4, QTableWidgetItem(data['memory_mb']))
            
        except Exception as e:
            print(f"Error updating status: {e}")

    def refresh_overview(self):
        """Refresh overview information"""
        running_count = sum(1 for s in self.services.values() if s.is_running())
        total = len(self.services)
        
        if running_count == 0:
            self.status_label.setText("Status: All Services Offline")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
        elif running_count == total:
            self.status_label.setText(f"Status: All Services Online ({running_count}/{total})")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.status_label.setText(f"Status: Partial ({running_count}/{total} running)")
            self.status_label.setStyleSheet("color: orange; font-weight: bold;")

    def log_message(self, message):
        """Log a message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.logs_text.append(log_entry)
        self.monitor_text.append(log_entry)

    def closeEvent(self, event):
        """Handle window close"""
        reply = QMessageBox.question(self, "Exit DHAN Control Center",
                                    "Close DHAN Control Center?\n\nRunning services will continue.",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.monitor_thread.stop()
            self.monitor_thread.wait()
            event.accept()
        else:
            event.ignore()


def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    window = DhanControlCenter()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
