"""
DHAN CONTROL CENTER WITH SERVICE ORCHESTRATION WIZARD
======================================================
Unified Hub for All Dhan Trading Services with intelligent startup orchestration.

Features:
- Single window control of all 11 services
- Sequential startup wizard (smart ordering)
- Auto-restart on service failure
- Real-time monitoring and health checks
- Comprehensive logging
- One-click "Start All" orchestration
"""

import sys
import subprocess
import json
import time
import threading
import os
from pathlib import Path
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QStatusBar, QTabWidget, QTableWidget, QTableWidgetItem,
    QTextEdit, QComboBox, QSpinBox, QMessageBox, QGroupBox, QGridLayout,
    QDialog, QDialogButtonBox, QProgressBar, QCheckBox, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QProcess, QSize, QRect
from PyQt5.QtGui import QFont, QColor, QPixmap, QIcon, QTextCursor
import redis
import psutil


class ServiceStatus(Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    ERROR = "ERROR"
    RESTARTING = "RESTARTING"


class ServiceStartupSequence:
    """Defines the order and dependencies of service startup"""
    
    # Startup sequence: Critical services first
    SEQUENCE = [
        ("FNO Feed Launcher", 1, "CRITICAL - Market data source"),
        ("FNO Database Writer", 2, "CRITICAL - Data persistence"),
        ("FNO Services Monitor", 3, "IMPORTANT - Service dashboard"),
        ("Volume Profile", 4, "OPTIONAL - Visualization"),
        ("Market Breadth", 4, "OPTIONAL - Visualization"),
        ("Tick Chart", 4, "OPTIONAL - Visualization"),
        ("Volume Profile Chart", 4, "OPTIONAL - Visualization"),
        ("Quote Visualizer", 4, "OPTIONAL - Visualization"),
        ("Market Scheduler", 5, "UTILITY - Auto management"),
        ("Instrument Display", 5, "UTILITY - Reference data"),
        ("FNO+MCX Feed", 5, "OPTIONAL - Commodities"),
    ]
    
    @classmethod
    def get_critical_services(cls) -> List[str]:
        """Services that must run for system to work"""
        return [name for name, _, _ in cls.SEQUENCE if _ <= 2]
    
    @classmethod
    def get_visualization_services(cls) -> List[str]:
        """Optional visualization services"""
        return [name for name, _, _ in cls.SEQUENCE if _ == 4]
    
    @classmethod
    def get_sorted_services(cls) -> List[tuple]:
        """Get services sorted by startup priority"""
        return sorted(cls.SEQUENCE, key=lambda x: x[1])


class DhanService:
    """Represents a Dhan service with lifecycle management"""
    def __init__(self, name, script, description, priority=5, icon_color="blue"):
        self.name = name
        self.script = script
        self.description = description
        self.priority = priority
        self.icon_color = icon_color
        self.status = ServiceStatus.STOPPED
        self.process = None
        self.pid = None
        self.start_time = None
        self.stop_time = None
        self.error_log = []
        self.output_log = []
        self.restart_count = 0
        self.max_restarts = 3
        self.auto_restart = True

    def is_running(self) -> bool:
        if self.process is None:
            return False
        return self.process.poll() is None

    def get_uptime(self) -> int:
        if self.start_time:
            return int(time.time() - self.start_time)
        return 0

    def get_memory_usage(self) -> float:
        if self.pid:
            try:
                process = psutil.Process(self.pid)
                return process.memory_info().rss / (1024 * 1024)  # MB
            except:
                return 0
        return 0

    def get_cpu_usage(self) -> float:
        if self.pid:
            try:
                process = psutil.Process(self.pid)
                return process.cpu_percent(interval=0.1)
            except:
                return 0
        return 0

    def get_status_display(self) -> str:
        if self.is_running():
            uptime = self.get_uptime()
            memory = self.get_memory_usage()
            return f"RUNNING ({uptime}s, {memory:.0f}MB)"
        elif self.status == ServiceStatus.RESTARTING:
            return f"RESTARTING (attempt {self.restart_count}/{self.max_restarts})"
        else:
            return "STOPPED"


class ServiceOrchestratorThread(QThread):
    """Background thread that manages service startup sequence"""
    
    status_changed = pyqtSignal(str, str)  # service_name, status
    log_message = pyqtSignal(str, str)  # service_name, message
    startup_progress = pyqtSignal(int, int)  # current, total
    startup_complete = pyqtSignal(bool)  # success

    def __init__(self, services: Dict[str, DhanService], start_visualizers: bool = False):
        super().__init__()
        self.services = services
        self.start_visualizers = start_visualizers
        self.running = True
        self.startup_in_progress = False
        self.sequence = ServiceStartupSequence()

    def run(self):
        """Main orchestration loop"""
        while self.running:
            time.sleep(1)
            # Health monitoring
            self._monitor_services()

    def start_all_services(self, start_visualizers: bool = True):
        """Orchestrated startup of all services in sequence"""
        self.startup_in_progress = True
        self.start_visualizers = start_visualizers
        self.log_message.emit("SYSTEM", "Starting service orchestration...")
        
        sorted_services = self.sequence.get_sorted_services()
        total = len(sorted_services)
        
        for idx, (service_name, priority, description) in enumerate(sorted_services):
            if not self.running:
                break
            
            # Skip visualizers if not requested
            if priority == 4 and not self.start_visualizers:
                self.log_message.emit(service_name, f"⊘ Skipped (visualizations disabled)")
                continue
            
            if service_name not in self.services:
                continue
            
            service = self.services[service_name]
            
            self.log_message.emit("SYSTEM", f"[{idx+1}/{total}] Starting {service_name}...")
            self.status_changed.emit(service_name, "STARTING")
            
            # Start service
            success = self._start_service(service)
            
            if success:
                self.log_message.emit(service_name, f"✅ Started successfully (PID: {service.pid})")
                self.status_changed.emit(service_name, "RUNNING")
            else:
                if priority <= 2:  # Critical service
                    self.log_message.emit("SYSTEM", f"❌ CRITICAL: {service_name} failed to start")
                    self.startup_complete.emit(False)
                    return
                else:
                    self.log_message.emit(service_name, f"⚠️  Non-critical service failed")
            
            # Wait between service starts (let each stabilize)
            time.sleep(2)
            self.startup_progress.emit(idx + 1, total)
        
        self.log_message.emit("SYSTEM", "✅ All configured services started")
        self.startup_complete.emit(True)
        self.startup_in_progress = False

    def _start_service(self, service: DhanService) -> bool:
        """Start a single service"""
        try:
            # Build command
            if service.script.startswith("python -m"):
                cmd = service.script.split()
            else:
                cmd = [sys.executable, service.script]
            
            # Start process
            service.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            service.pid = service.process.pid
            service.start_time = time.time()
            service.status = ServiceStatus.RUNNING
            service.restart_count = 0
            
            return True
        except Exception as e:
            service.status = ServiceStatus.ERROR
            service.error_log.append(f"{datetime.now()}: {str(e)}")
            return False

    def _monitor_services(self):
        """Check health of running services"""
        for service_name, service in self.services.items():
            if service.status == ServiceStatus.RUNNING:
                if not service.is_running():
                    # Service crashed
                    service.status = ServiceStatus.ERROR
                    self.log_message.emit(service_name, "❌ Process crashed")
                    
                    # Auto-restart if enabled
                    if service.auto_restart and service.restart_count < service.max_restarts:
                        service.restart_count += 1
                        service.status = ServiceStatus.RESTARTING
                        self.log_message.emit(
                            service_name, 
                            f"🔄 Auto-restarting ({service.restart_count}/{service.max_restarts})..."
                        )
                        time.sleep(2)
                        
                        if self._start_service(service):
                            self.log_message.emit(service_name, "✅ Restarted successfully")
                        else:
                            self.log_message.emit(service_name, "❌ Restart failed")

    def stop_all_services(self):
        """Stop all services gracefully"""
        self.log_message.emit("SYSTEM", "Stopping all services...")
        
        for service_name, service in list(self.services.items()):
            if service.is_running():
                try:
                    service.process.terminate()
                    service.process.wait(timeout=5)
                    self.log_message.emit(service_name, "✅ Stopped")
                except:
                    service.process.kill()
                    self.log_message.emit(service_name, "⚠️  Force killed")
                
                service.status = ServiceStatus.STOPPED
                service.stop_time = time.time()


class DhanControlCenterGUI(QMainWindow):
    """Main GUI for DHAN Control Center with orchestration wizard"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DHAN Control Center - Service Orchestration Hub")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize services
        self.services = self._initialize_services()
        
        # Start orchestrator thread
        self.orchestrator = ServiceOrchestratorThread(self.services)
        self.orchestrator.status_changed.connect(self.update_service_status)
        self.orchestrator.log_message.connect(self.add_log_message)
        self.orchestrator.startup_progress.connect(self.update_startup_progress)
        self.orchestrator.startup_complete.connect(self.on_startup_complete)
        self.orchestrator.start()
        
        # Setup UI
        self.setup_ui()
        
        # Start health monitoring timer
        self.health_timer = QTimer()
        self.health_timer.timeout.connect(self.update_health_display)
        self.health_timer.start(2000)  # Every 2 seconds
    
    def _initialize_services(self) -> Dict[str, DhanService]:
        """Initialize all services with their configurations"""
        services = {}
        
        service_configs = [
            ("FNO Feed Launcher", "launch_fno_feed.py --force", 
             "Real-time NIFTY & BANKNIFTY futures/options feed", 1, "green"),
            
            ("FNO Database Writer", "python -m dhan_trading.subscribers.fno_db_writer",
             "Persist quotes to MySQL database", 2, "purple"),
            
            ("FNO Services Monitor", "python -m dhan_trading.dashboard.fno_services_monitor",
             "PyQt5 dashboard for monitoring all services", 3, "blue"),
            
            ("Volume Profile", "python -m dhan_trading.visualizers.volume_profile",
             "Real-time volume distribution analysis", 4, "darkblue"),
            
            ("Market Breadth", "python -m dhan_trading.visualizers.market_breadth",
             "Nifty 50 market sentiment tracker", 4, "darkgreen"),
            
            ("Tick Chart", "python -m dhan_trading.visualizers.tick_chart",
             "Price movement based on tick count", 4, "darkred"),
            
            ("Volume Profile Chart", "python -m dhan_trading.visualizers.volume_profile_chart",
             "5-minute volume profiles with VAH/VAL/POC", 4, "purple"),
            
            ("Quote Visualizer", "python -m dhan_trading.visualizers.quote_visualizer",
             "Terminal-based quote display", 4, "cyan"),
            
            ("Market Scheduler", "launch_market_scheduler.py",
             "Auto-start/stop services at market hours", 5, "teal"),
            
            ("Instrument Display", "display_fno_instruments.py",
             "Show all subscribed instruments", 5, "orange"),
            
            ("FNO+MCX Feed", "python launch_fno_feed.py --include-commodities",
             "FNO + MCX commodities data", 5, "darkgreen"),
        ]
        
        for name, script, description, priority, color in service_configs:
            services[name] = DhanService(name, script, description, priority, color)
        
        return services
    
    def setup_ui(self):
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        
        # Header
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Main content: Tabs
        tabs = QTabWidget()
        
        # Tab 1: Startup Wizard (NEW)
        wizard_tab = self.create_wizard_tab()
        tabs.addTab(wizard_tab, "🚀 Startup Wizard")
        
        # Tab 2: Service Status
        status_tab = self.create_status_tab()
        tabs.addTab(status_tab, "📊 Service Status")
        
        # Tab 3: System Monitor
        monitor_tab = self.create_monitor_tab()
        tabs.addTab(monitor_tab, "📈 System Monitor")
        
        # Tab 4: Logs
        logs_tab = self.create_logs_tab()
        tabs.addTab(logs_tab, "📋 Logs")
        
        main_layout.addWidget(tabs)
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("DHAN Control Center Ready")
        
        central_widget.setLayout(main_layout)
    
    def create_header(self) -> QGroupBox:
        """Create header with title and quick info"""
        header = QGroupBox()
        layout = QHBoxLayout()
        
        title = QLabel("DHAN Control Center - Service Orchestration Hub")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        layout.addStretch()
        
        self.status_label = QLabel("Status: Ready")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
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
    
    def create_wizard_tab(self) -> QWidget:
        """Create the Startup Wizard tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Service Startup Orchestration Wizard")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "This wizard will start background services automatically:\n"
            "✓ Feed Launcher (CRITICAL) - WebSocket market data\n"
            "✓ Database Writer (CRITICAL) - Persist quotes to MySQL\n"
            "✓ Services Monitor (IMPORTANT) - Dashboard\n"
            "✗ Visualizations - Start manually one by one after setup\n"
            "\nAll services run within this window. No need for multiple terminals!\n"
            "Services will auto-restart if they crash.\n\n"
            "💡 Tip: After background services are running, start visualizers\n"
            "one-by-one from the 'Service Status' tab to manage resources."
        )
        instructions.setStyleSheet("color: #333; background-color: #e3f2fd; padding: 10px; border-radius: 5px;")
        layout.addWidget(instructions)
        
        # Options
        options_group = QGroupBox("Startup Options")
        options_layout = QGridLayout()
        
        self.visualizations_checkbox = QCheckBox("Include Visualization Services (Start Manually)")
        self.visualizations_checkbox.setChecked(False)
        self.visualizations_checkbox.setToolTip("Visualizers are heavy - start them manually one by one after background services are running")
        self.visualizations_checkbox.stateChanged.connect(self.toggle_visualizations)
        options_layout.addWidget(self.visualizations_checkbox, 0, 0)
        
        self.auto_restart_checkbox = QCheckBox("Auto-Restart on Crash")
        self.auto_restart_checkbox.setChecked(True)
        self.auto_restart_checkbox.stateChanged.connect(self.toggle_auto_restart)
        options_layout.addWidget(self.auto_restart_checkbox, 0, 1)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Progress
        progress_group = QGroupBox("Startup Progress")
        progress_layout = QVBoxLayout()
        
        self.startup_progress_bar = QProgressBar()
        self.startup_progress_bar.setValue(0)
        progress_layout.addWidget(self.startup_progress_bar)
        
        self.startup_status_label = QLabel("Ready to start")
        progress_layout.addWidget(self.startup_status_label)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.start_all_btn = QPushButton("▶️  Start All Services (Wizard)")
        self.start_all_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 10px; font-weight: bold; }"
        )
        self.start_all_btn.clicked.connect(self.start_all_services_wizard)
        button_layout.addWidget(self.start_all_btn)
        
        self.stop_all_btn = QPushButton("⏹️  Stop All Services")
        self.stop_all_btn.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; padding: 10px; font-weight: bold; }"
        )
        self.stop_all_btn.clicked.connect(self.stop_all_services)
        button_layout.addWidget(self.stop_all_btn)
        
        layout.addLayout(button_layout)
        
        # Service checklist
        checklist_group = QGroupBox("Service Startup Sequence")
        checklist_layout = QVBoxLayout()
        
        self.service_checkboxes = {}
        for service_name, service in self.services.items():
            chk = QCheckBox(f"{service_name} ({service.description})")
            # Start unchecked if visualization service, checked if background service
            is_viz = service.priority >= 4
            chk.setChecked(not is_viz)
            if is_viz:
                chk.setEnabled(False)  # Visualizations controlled by main checkbox
            self.service_checkboxes[service_name] = chk
            checklist_layout.addWidget(chk)
        
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_widget.setLayout(checklist_layout)
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        
        checklist_group.setLayout(QVBoxLayout())
        checklist_group.layout().addWidget(scroll)
        
        layout.addWidget(checklist_group)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def create_status_tab(self) -> QWidget:
        """Create service status monitoring tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Status table
        self.status_table = QTableWidget()
        self.status_table.setColumnCount(6)
        self.status_table.setHorizontalHeaderLabels(
            ["Service", "Status", "PID", "Memory (MB)", "CPU (%)", "Uptime (s)"]
        )
        self.status_table.setColumnWidth(0, 200)
        
        # Populate table
        for idx, (service_name, service) in enumerate(self.services.items()):
            self.status_table.insertRow(idx)
            self.status_table.setItem(idx, 0, QTableWidgetItem(service_name))
            self.status_table.setItem(idx, 1, QTableWidgetItem("STOPPED"))
            self.status_table.setItem(idx, 2, QTableWidgetItem("---"))
            self.status_table.setItem(idx, 3, QTableWidgetItem("0"))
            self.status_table.setItem(idx, 4, QTableWidgetItem("0"))
            self.status_table.setItem(idx, 5, QTableWidgetItem("0"))
        
        layout.addWidget(self.status_table)
        
        widget.setLayout(layout)
        return widget
    
    def create_monitor_tab(self) -> QWidget:
        """Create system monitoring tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # System info
        info_label = QLabel("System Health Dashboard")
        info_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(info_label)
        
        # Health display
        self.health_display = QTextEdit()
        self.health_display.setReadOnly(True)
        self.health_display.setFont(QFont("Courier", 9))
        self.health_display.setStyleSheet("background-color: #1e1e1e; color: #00ff00;")
        layout.addWidget(self.health_display)
        
        widget.setLayout(layout)
        return widget
    
    def create_logs_tab(self) -> QWidget:
        """Create logs display tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Log level filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        
        self.log_filter = QComboBox()
        self.log_filter.addItems(["All", "SYSTEM", "Feed Launcher", "Database Writer"])
        self.log_filter.currentTextChanged.connect(self.refresh_logs)
        filter_layout.addWidget(self.log_filter)
        filter_layout.addStretch()
        
        layout.addLayout(filter_layout)
        
        # Log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Courier", 9))
        layout.addWidget(self.log_display)
        
        widget.setLayout(layout)
        return widget
    
    def start_all_services_wizard(self):
        """Start the orchestration wizard"""
        self.start_all_btn.setEnabled(False)
        self.startup_status_label.setText("⏳ Starting services...")
        
        include_viz = self.visualizations_checkbox.isChecked()
        
        # Run orchestration in thread
        orchestrator_thread = threading.Thread(
            target=self.orchestrator.start_all_services,
            args=(include_viz,),
            daemon=True
        )
        orchestrator_thread.start()
    
    def stop_all_services(self):
        """Stop all services"""
        reply = QMessageBox.question(
            self, "Stop All Services",
            "Are you sure you want to stop all services?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            stop_thread = threading.Thread(
                target=self.orchestrator.stop_all_services,
                daemon=True
            )
            stop_thread.start()
    
    def toggle_auto_restart(self):
        """Toggle auto-restart for all services"""
        enabled = self.auto_restart_checkbox.isChecked()
        for service in self.services.values():
            service.auto_restart = enabled
    
    def toggle_visualizations(self):
        """Toggle visualization services checkboxes"""
        enabled = self.visualizations_checkbox.isChecked()
        for service_name, chk in self.service_checkboxes.items():
            service = self.services.get(service_name)
            if service and service.priority >= 4:  # Visualization services
                chk.setChecked(enabled)
    
    def update_service_status(self, service_name: str, status: str):
        """Update service status in the table"""
        for row in range(self.status_table.rowCount()):
            if self.status_table.item(row, 0).text() == service_name:
                self.status_table.setItem(row, 1, QTableWidgetItem(status))
                break
    
    def update_health_display(self):
        """Update system health display"""
        health_info = f"""
=== DHAN System Health ===
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Services Status:
"""
        
        running_count = 0
        for service_name, service in self.services.items():
            if service.is_running():
                running_count += 1
                memory = service.get_memory_usage()
                cpu = service.get_cpu_usage()
                uptime = service.get_uptime()
                health_info += f"  ✓ {service_name:25s} | PID:{service.pid:6d} | Mem:{memory:6.0f}MB | CPU:{cpu:5.1f}% | ⏱️ {uptime}s\n"
            else:
                health_info += f"  ✗ {service_name:25s} | STOPPED\n"
        
        health_info += f"\n Running Services: {running_count}/{len(self.services)}\n"
        
        # System stats
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            health_info += f"\nSystem Resources:\n"
            health_info += f"  CPU Usage: {cpu_percent}%\n"
            health_info += f"  Memory: {memory.used / (1024**3):.1f}GB / {memory.total / (1024**3):.1f}GB ({memory.percent}%)\n"
        except:
            pass
        
        self.health_display.setText(health_info)
    
    def add_log_message(self, service_name: str, message: str):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {service_name:25s} | {message}"
        
        # Keep in memory
        if not hasattr(self, 'all_logs'):
            self.all_logs = []
        self.all_logs.append((service_name, log_entry))
        
        # Update status label
        if "✅" in message or "RUNNING" in message:
            self.statusBar.showMessage(f"✅ {service_name}: {message[:50]}")
        elif "❌" in message or "ERROR" in message:
            self.statusBar.showMessage(f"❌ {service_name}: {message[:50]}")
        
        self.refresh_logs()
    
    def refresh_logs(self):
        """Refresh log display based on filter"""
        filter_text = self.log_filter.currentText()
        
        log_text = ""
        if hasattr(self, 'all_logs'):
            for service_name, log_entry in self.all_logs:
                if filter_text == "All" or filter_text == service_name:
                    log_text += log_entry + "\n"
        
        self.log_display.setText(log_text)
        # Scroll to bottom
        self.log_display.moveCursor(QTextCursor.End)
    
    def update_startup_progress(self, current: int, total: int):
        """Update startup progress bar"""
        if total > 0:
            progress = int((current / total) * 100)
            self.startup_progress_bar.setValue(progress)
            self.startup_status_label.setText(f"Progress: {current}/{total} services")
    
    def on_startup_complete(self, success: bool):
        """Called when startup wizard completes"""
        self.start_all_btn.setEnabled(True)
        
        if success:
            self.startup_status_label.setText("✅ All services started successfully!")
            self.statusBar.showMessage("✅ All services running - System operational")
        else:
            self.startup_status_label.setText("❌ Startup failed - Check logs")
            self.statusBar.showMessage("❌ Startup failed - See logs for details")
    
    def update_time_label(self):
        """Update time display"""
        self.time_label.setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    def closeEvent(self, event):
        """Handle window close"""
        reply = QMessageBox.question(
            self, "Close DHAN Control Center",
            "Closing the Control Center will stop all services. Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.orchestrator.running = False
            self.orchestrator.stop_all_services()
            event.accept()
        else:
            event.ignore()


def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    window = DhanControlCenterGUI()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
