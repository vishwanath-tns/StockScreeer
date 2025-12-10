"""
Dhan Market Services Scheduler
==============================
A background service with system tray GUI that automatically starts/stops
Dhan market data services based on Indian market hours.

Schedule (IST - Indian Standard Time):
- Start: 9:00 AM Monday-Friday
- Stop: 12:00 AM (Midnight)

Features:
- System tray icon with status display
- Auto-start on Windows boot
- Manual start/stop controls
- Service status monitoring
"""

import sys
import os
import subprocess
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSystemTrayIcon, QMenu, QGroupBox,
    QTextEdit, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QIcon, QAction, QColor, QFont, QPixmap, QPainter

import pytz

# Indian timezone
IST = pytz.timezone('Asia/Kolkata')


class ServiceStatus:
    """Track status of a service"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class SignalEmitter(QObject):
    """Signal emitter for thread-safe GUI updates"""
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str, str)  # service_name, status


class DhanServiceManager:
    """Manages Dhan market data services"""
    
    def __init__(self, signal_emitter: SignalEmitter):
        self.signal_emitter = signal_emitter
        self.processes = {}
        self.service_status = {
            'websocket': ServiceStatus.STOPPED,
            'dbwriter': ServiceStatus.STOPPED,
            'redis': ServiceStatus.STOPPED
        }
        self.project_root = PROJECT_ROOT
        
    def log(self, message: str):
        """Log message with timestamp"""
        timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
        self.signal_emitter.log_signal.emit(f"[{timestamp}] {message}")
        
    def update_status(self, service: str, status: str):
        """Update service status"""
        self.service_status[service] = status
        self.signal_emitter.status_signal.emit(service, status)
        
    def is_redis_running(self) -> bool:
        """Check if Redis server is running"""
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379)
            r.ping()
            return True
        except:
            return False
            
    def start_redis(self):
        """Start Redis server if not running"""
        if self.is_redis_running():
            self.log("Redis already running")
            self.update_status('redis', ServiceStatus.RUNNING)
            return True
            
        self.log("Starting Redis server...")
        self.update_status('redis', ServiceStatus.STARTING)
        
        try:
            # Try to start Redis (assumes redis-server is in PATH or installed)
            if sys.platform == 'win32':
                # Windows - try common Redis installation paths
                redis_paths = [
                    r"C:\Program Files\Redis\redis-server.exe",
                    r"C:\Redis\redis-server.exe",
                    "redis-server"
                ]
                for redis_path in redis_paths:
                    try:
                        process = subprocess.Popen(
                            [redis_path],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                        self.processes['redis'] = process
                        time.sleep(2)
                        if self.is_redis_running():
                            self.log("Redis server started")
                            self.update_status('redis', ServiceStatus.RUNNING)
                            return True
                    except FileNotFoundError:
                        continue
                        
            self.log("Could not start Redis - please start manually")
            self.update_status('redis', ServiceStatus.ERROR)
            return False
            
        except Exception as e:
            self.log(f"Error starting Redis: {e}")
            self.update_status('redis', ServiceStatus.ERROR)
            return False
            
    def start_websocket_service(self):
        """Start WebSocket market feed service"""
        self.log("Starting WebSocket service...")
        self.update_status('websocket', ServiceStatus.STARTING)
        
        try:
            script_path = self.project_root / "dhan_trading" / "market_feed" / "websocket_service.py"
            
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                cwd=str(self.project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            self.processes['websocket'] = process
            time.sleep(3)
            
            if process.poll() is None:
                self.log("WebSocket service started")
                self.update_status('websocket', ServiceStatus.RUNNING)
                return True
            else:
                self.log("WebSocket service failed to start")
                self.update_status('websocket', ServiceStatus.ERROR)
                return False
                
        except Exception as e:
            self.log(f"Error starting WebSocket service: {e}")
            self.update_status('websocket', ServiceStatus.ERROR)
            return False
            
    def start_dbwriter_service(self):
        """Start database writer service"""
        self.log("Starting DBWriter service...")
        self.update_status('dbwriter', ServiceStatus.STARTING)
        
        try:
            script_path = self.project_root / "dhan_trading" / "database" / "dbwriter_service.py"
            
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                cwd=str(self.project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            self.processes['dbwriter'] = process
            time.sleep(2)
            
            if process.poll() is None:
                self.log("DBWriter service started")
                self.update_status('dbwriter', ServiceStatus.RUNNING)
                return True
            else:
                self.log("DBWriter service failed to start")
                self.update_status('dbwriter', ServiceStatus.ERROR)
                return False
                
        except Exception as e:
            self.log(f"Error starting DBWriter service: {e}")
            self.update_status('dbwriter', ServiceStatus.ERROR)
            return False
            
    def start_all_services(self):
        """Start all Dhan services"""
        self.log("=" * 50)
        self.log("Starting all Dhan services...")
        
        # Start Redis first
        if not self.start_redis():
            self.log("Warning: Redis not available, services may not work properly")
            
        # Start WebSocket service
        self.start_websocket_service()
        time.sleep(2)
        
        # Start DBWriter service
        self.start_dbwriter_service()
        
        self.log("All services start sequence completed")
        self.log("=" * 50)
        
    def stop_service(self, service_name: str):
        """Stop a specific service"""
        if service_name in self.processes:
            process = self.processes[service_name]
            if process and process.poll() is None:
                self.log(f"Stopping {service_name} service...")
                self.update_status(service_name, ServiceStatus.STOPPING)
                
                try:
                    process.terminate()
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    
                self.log(f"{service_name} service stopped")
                self.update_status(service_name, ServiceStatus.STOPPED)
                del self.processes[service_name]
                
    def stop_all_services(self):
        """Stop all Dhan services"""
        self.log("=" * 50)
        self.log("Stopping all Dhan services...")
        
        for service_name in ['dbwriter', 'websocket']:
            self.stop_service(service_name)
            
        # Don't stop Redis as other apps might use it
        self.log("All services stopped")
        self.log("=" * 50)
        
    def check_service_health(self):
        """Check if services are still running"""
        for service_name, process in list(self.processes.items()):
            if service_name == 'redis':
                if self.is_redis_running():
                    self.update_status('redis', ServiceStatus.RUNNING)
                else:
                    self.update_status('redis', ServiceStatus.STOPPED)
            elif process and process.poll() is not None:
                self.log(f"{service_name} service has stopped unexpectedly")
                self.update_status(service_name, ServiceStatus.STOPPED)
                del self.processes[service_name]


class MarketScheduler:
    """Scheduler for market hours"""
    
    def __init__(self, service_manager: DhanServiceManager, signal_emitter: SignalEmitter):
        self.service_manager = service_manager
        self.signal_emitter = signal_emitter
        self.running = False
        self.scheduler_thread = None
        
        # Schedule times (IST)
        # Start at 8:55 AM (before MCX 9:00 AM and NSE 9:15 AM)
        self.start_hour = 8
        self.start_minute = 55
        self.stop_hour = 0
        self.stop_minute = 0
        
    def log(self, message: str):
        timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
        self.signal_emitter.log_signal.emit(f"[{timestamp}] [SCHEDULER] {message}")
        
    def is_weekday(self) -> bool:
        """Check if today is a weekday (Mon-Fri)"""
        now = datetime.now(IST)
        return now.weekday() < 5  # 0=Mon, 4=Fri
        
    def should_services_be_running(self) -> bool:
        """Check if services should be running based on current time"""
        if not self.is_weekday():
            return False
            
        now = datetime.now(IST)
        current_minutes = now.hour * 60 + now.minute
        
        start_minutes = self.start_hour * 60 + self.start_minute  # 9:00 = 540
        stop_minutes = self.stop_hour * 60 + self.stop_minute      # 0:00 = 0 (midnight)
        
        # Services should run from 9:00 AM to midnight
        # Since stop is midnight (0), we check if current time >= 9:00 AM
        return current_minutes >= start_minutes
        
    def get_next_start_time(self) -> datetime:
        """Get the next scheduled start time"""
        now = datetime.now(IST)
        next_start = now.replace(hour=self.start_hour, minute=self.start_minute, second=0, microsecond=0)
        
        # If it's past start time today, next start is tomorrow
        if now >= next_start:
            next_start += timedelta(days=1)
            
        # Skip weekends
        while next_start.weekday() >= 5:
            next_start += timedelta(days=1)
            
        return next_start
        
    def get_next_stop_time(self) -> datetime:
        """Get the next scheduled stop time (midnight)"""
        now = datetime.now(IST)
        # Next midnight
        next_stop = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return next_stop
        
    def scheduler_loop(self):
        """Main scheduler loop"""
        self.log("Scheduler started")
        last_action_date = None
        services_started_today = False
        
        while self.running:
            try:
                now = datetime.now(IST)
                today = now.date()
                
                # Reset daily flag at midnight
                if last_action_date != today:
                    services_started_today = False
                    last_action_date = today
                    
                # Check if we should start services
                if self.is_weekday() and not services_started_today:
                    if now.hour == self.start_hour and now.minute == self.start_minute:
                        self.log("Scheduled start time reached - starting services")
                        self.service_manager.start_all_services()
                        services_started_today = True
                        
                # Check if we should stop services (midnight)
                if now.hour == self.stop_hour and now.minute == self.stop_minute:
                    self.log("Scheduled stop time reached - stopping services")
                    self.service_manager.stop_all_services()
                    
                # Health check every minute
                self.service_manager.check_service_health()
                
            except Exception as e:
                self.log(f"Scheduler error: {e}")
                
            # Sleep for 30 seconds before next check
            for _ in range(30):
                if not self.running:
                    break
                time.sleep(1)
                
        self.log("Scheduler stopped")
        
    def start(self):
        """Start the scheduler"""
        if not self.running:
            self.running = True
            self.scheduler_thread = threading.Thread(target=self.scheduler_loop, daemon=True)
            self.scheduler_thread.start()
            
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)


class StatusIndicator(QFrame):
    """Visual status indicator widget"""
    
    def __init__(self, service_name: str, parent=None):
        super().__init__(parent)
        self.service_name = service_name
        self.status = ServiceStatus.STOPPED
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Status LED
        self.led = QLabel()
        self.led.setFixedSize(16, 16)
        self.update_led()
        
        # Service name
        self.name_label = QLabel(service_name.upper())
        self.name_label.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        self.name_label.setStyleSheet("color: #FFFFFF;")
        
        # Status text
        self.status_label = QLabel(self.status.upper())
        self.status_label.setFont(QFont("Consolas", 10))
        self.status_label.setMinimumWidth(80)
        
        layout.addWidget(self.led)
        layout.addWidget(self.name_label)
        layout.addStretch()
        layout.addWidget(self.status_label)
        
        self.setStyleSheet("""
            QFrame {
                background-color: #2D2D30;
                border: 1px solid #3E3E42;
                border-radius: 5px;
            }
        """)
        
    def update_led(self):
        """Update LED color based on status"""
        colors = {
            ServiceStatus.STOPPED: "#666666",
            ServiceStatus.STARTING: "#FFA500",
            ServiceStatus.RUNNING: "#00C853",
            ServiceStatus.STOPPING: "#FFA500",
            ServiceStatus.ERROR: "#FF1744"
        }
        color = colors.get(self.status, "#666666")
        
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()
        
        self.led.setPixmap(pixmap)
        
    def set_status(self, status: str):
        """Set the status"""
        self.status = status
        self.update_led()
        
        status_colors = {
            ServiceStatus.STOPPED: "#888888",
            ServiceStatus.STARTING: "#FFA500",
            ServiceStatus.RUNNING: "#00C853",
            ServiceStatus.STOPPING: "#FFA500",
            ServiceStatus.ERROR: "#FF1744"
        }
        color = status_colors.get(status, "#888888")
        self.status_label.setText(status.upper())
        self.status_label.setStyleSheet(f"color: {color};")


class SchedulerWindow(QMainWindow):
    """Main scheduler window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dhan Market Services Scheduler")
        self.setMinimumSize(600, 500)
        
        # Signal emitter for thread-safe updates
        self.signal_emitter = SignalEmitter()
        self.signal_emitter.log_signal.connect(self.append_log)
        self.signal_emitter.status_signal.connect(self.update_service_status)
        
        # Service manager and scheduler
        self.service_manager = DhanServiceManager(self.signal_emitter)
        self.scheduler = MarketScheduler(self.service_manager, self.signal_emitter)
        
        self.setup_ui()
        self.setup_tray()
        self.setup_timers()
        
        # Apply dark theme
        self.apply_dark_theme()
        
        # Start scheduler
        self.scheduler.start()
        self.append_log("Scheduler initialized and running")
        self.append_log(f"Schedule: Start at 8:55 AM IST (Mon-Fri), Stop at 12:00 AM IST")
        self.append_log(f"MCX opens at 9:00 AM, NSE opens at 9:15 AM")
        
        # Check if services should be running now
        if self.scheduler.should_services_be_running():
            self.append_log("Services should be running - starting now...")
            threading.Thread(target=self.service_manager.start_all_services, daemon=True).start()
            
    def setup_ui(self):
        """Setup the user interface"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header = QLabel("🕐 Dhan Market Services Scheduler")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setStyleSheet("color: #00D4FF;")
        layout.addWidget(header)
        
        # Schedule info
        schedule_group = QGroupBox("Schedule (IST - Indian Standard Time)")
        schedule_layout = QVBoxLayout(schedule_group)
        
        self.schedule_label = QLabel("📅 Start: 8:55 AM Mon-Fri | Stop: 12:00 AM (Midnight)")
        self.schedule_label.setFont(QFont("Consolas", 11))
        schedule_layout.addWidget(self.schedule_label)
        
        self.next_action_label = QLabel()
        self.next_action_label.setFont(QFont("Consolas", 10))
        self.next_action_label.setStyleSheet("color: #888888;")
        schedule_layout.addWidget(self.next_action_label)
        
        self.current_time_label = QLabel()
        self.current_time_label.setFont(QFont("Consolas", 10))
        self.current_time_label.setStyleSheet("color: #00C853;")
        schedule_layout.addWidget(self.current_time_label)
        
        layout.addWidget(schedule_group)
        
        # Service status
        status_group = QGroupBox("Service Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_indicators = {}
        for service in ['redis', 'websocket', 'dbwriter']:
            indicator = StatusIndicator(service)
            self.status_indicators[service] = indicator
            status_layout.addWidget(indicator)
            
        layout.addWidget(status_group)
        
        # Control buttons
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶ Start All")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.clicked.connect(self.manual_start)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ Stop All")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.clicked.connect(self.manual_stop)
        btn_layout.addWidget(self.stop_btn)
        
        layout.addLayout(btn_layout)
        
        # Log area
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setMinimumHeight(150)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
        
    def setup_tray(self):
        """Setup system tray icon"""
        self.tray_icon = QSystemTrayIcon(self)
        
        # Create a simple icon
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#00D4FF"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(4, 4, 24, 24)
        painter.setBrush(QColor("#1E1E1E"))
        painter.drawEllipse(8, 8, 16, 16)
        # Draw clock hands
        painter.setBrush(QColor("#00D4FF"))
        painter.drawRect(15, 10, 2, 8)  # Hour hand
        painter.drawRect(16, 15, 6, 2)  # Minute hand
        painter.end()
        
        self.tray_icon.setIcon(QIcon(pixmap))
        self.tray_icon.setToolTip("Dhan Market Scheduler")
        
        # Tray menu
        tray_menu = QMenu()
        
        show_action = QAction("Show Window", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        start_action = QAction("Start Services", self)
        start_action.triggered.connect(self.manual_start)
        tray_menu.addAction(start_action)
        
        stop_action = QAction("Stop Services", self)
        stop_action.triggered.connect(self.manual_stop)
        tray_menu.addAction(stop_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_activated)
        self.tray_icon.show()
        
    def setup_timers(self):
        """Setup update timers"""
        # Update time display every second
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self.update_time_display)
        self.time_timer.start(1000)
        
    def update_time_display(self):
        """Update current time and next action display"""
        now = datetime.now(IST)
        self.current_time_label.setText(f"⏰ Current Time: {now.strftime('%Y-%m-%d %H:%M:%S')} IST")
        
        if self.scheduler.should_services_be_running():
            next_stop = self.scheduler.get_next_stop_time()
            self.next_action_label.setText(f"⏭ Next Stop: {next_stop.strftime('%Y-%m-%d %H:%M')} IST")
        else:
            next_start = self.scheduler.get_next_start_time()
            self.next_action_label.setText(f"⏭ Next Start: {next_start.strftime('%Y-%m-%d %H:%M')} IST")
            
    def apply_dark_theme(self):
        """Apply dark theme stylesheet"""
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1E1E1E;
                color: #FFFFFF;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #3E3E42;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: #00D4FF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #0E639C;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1177BB;
            }
            QPushButton:pressed {
                background-color: #0D5A8C;
            }
            QTextEdit {
                background-color: #252526;
                color: #D4D4D4;
                border: 1px solid #3E3E42;
                border-radius: 3px;
            }
            QLabel {
                color: #FFFFFF;
            }
        """)
        
    def append_log(self, message: str):
        """Append message to log"""
        self.log_text.append(message)
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def update_service_status(self, service: str, status: str):
        """Update service status indicator"""
        if service in self.status_indicators:
            self.status_indicators[service].set_status(status)
            
        # Update tray tooltip
        statuses = [f"{s}: {self.service_manager.service_status.get(s, 'unknown')}" 
                   for s in ['redis', 'websocket', 'dbwriter']]
        self.tray_icon.setToolTip(f"Dhan Scheduler\n" + "\n".join(statuses))
        
    def manual_start(self):
        """Manually start all services"""
        threading.Thread(target=self.service_manager.start_all_services, daemon=True).start()
        
    def manual_stop(self):
        """Manually stop all services"""
        threading.Thread(target=self.service_manager.stop_all_services, daemon=True).start()
        
    def tray_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.raise_()
            self.activateWindow()
            
    def closeEvent(self, event):
        """Handle close event - minimize to tray instead"""
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Dhan Scheduler",
            "Running in background. Double-click to open.",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
        
    def quit_app(self):
        """Quit the application"""
        self.scheduler.stop()
        self.service_manager.stop_all_services()
        QApplication.quit()


def create_startup_shortcut():
    """Create a Windows startup shortcut"""
    try:
        import winshell
        from win32com.client import Dispatch
        
        startup_path = winshell.startup()
        shortcut_path = os.path.join(startup_path, "Dhan Market Scheduler.lnk")
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = sys.executable
        shortcut.Arguments = f'"{__file__}"'
        shortcut.WorkingDirectory = str(PROJECT_ROOT)
        shortcut.IconLocation = sys.executable
        shortcut.Description = "Dhan Market Services Scheduler"
        shortcut.save()
        
        return True, shortcut_path
    except ImportError:
        return False, "Install pywin32 and winshell: pip install pywin32 winshell"
    except Exception as e:
        return False, str(e)


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running in tray
    
    window = SchedulerWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
