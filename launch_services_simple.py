#!/usr/bin/env python
"""
Enhanced Service Launcher with Tabs and Monitor
===============================================
- Separate tabs for each service's logs
- START/STOP buttons per service
- Real-time monitor dashboard button
"""

import sys
import os
import subprocess
import time
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QGroupBox, QTabWidget, QFrame, QGridLayout, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QObject
from PyQt5.QtGui import QFont


# Define services
SERVICES = {
    "FNO Feed Launcher": {
        "script": "launch_fno_feed_subprocess.py",
        "args": ["--force"],
        "description": "Publishes live market data from Dhan WebSocket to Redis",
        "color": "#4CAF50"  # Green
    },
    "FNO Database Writer": {
        "script": "python",
        "module_args": ["-m", "dhan_trading.subscribers.fno_db_writer"],
        "description": "Subscribes to Redis and writes quotes to MySQL database",
        "color": "#2196F3"  # Blue
    },
}

# Visualizers that can be launched
VISUALIZERS = {
    # DHAN Trading Visualizers (Latest)
    "Market Breadth (Dhan)": {
        "script": "dhan_trading/visualizers/market_breadth_chart.py",
        "description": "Real-time market breadth with charts"
    },
    "Volume Profile": {
        "script": "python",
        "module_args": ["-m", "dhan_trading.visualizers.volume_profile"],
        "description": "Volume profile analysis charts"
    },
    
    # Legacy Visualizers
    "Market Breadth (PyQtGraph)": {
        "script": "realtime_adv_decl_dashboard_pyqt.py",
        "description": "Live A/D tracking with PyQtGraph (High-performance)"
    },
    "Breadth (Intraday)": {
        "script": "intraday_breadth/visualizer.py",
        "description": "Nifty 50 intraday % above SMA (5-min)"
    },
}


class ServiceWorker(QObject):
    """Worker thread for running a service process"""
    log_signal = pyqtSignal(str, str)  # (service_name, text)
    status_signal = pyqtSignal(str, str)  # (service_name, status)
    error_signal = pyqtSignal(str, str)  # (service_name, error)
    
    def __init__(self, service_name, script, args, module_args=None):
        super().__init__()
        self.service_name = service_name
        self.script = script
        self.args = args
        self.module_args = module_args or []
        self.process = None
        self.running = False
    
    def run_service(self):
        """Start the service and stream output"""
        try:
            self.status_signal.emit(self.service_name, "RUNNING")
            self.log_signal.emit(self.service_name, f"[{self._timestamp()}] Starting {self.service_name}...")
            
            # Build command
            if self.module_args:
                cmd = [self.script] + self.module_args + self.args
            else:
                cmd = [sys.executable, self.script] + self.args
            
            self.log_signal.emit(self.service_name, f"[{self._timestamp()}] Command: {' '.join(cmd)}")
            
            # Start process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.running = True
            self.log_signal.emit(self.service_name, f"[{self._timestamp()}] Process started (PID: {self.process.pid})")
            
            # Stream output
            for line in self.process.stdout:
                if line:
                    self.log_signal.emit(self.service_name, line.rstrip())
            
            # Wait for process to finish
            self.process.wait()
            
            if self.process.returncode != 0:
                self.error_signal.emit(self.service_name, f"Process exited with code {self.process.returncode}")
                self.status_signal.emit(self.service_name, "ERROR")
            else:
                self.log_signal.emit(self.service_name, f"[{self._timestamp()}] Process completed successfully")
                self.status_signal.emit(self.service_name, "STOPPED")
            
            self.running = False
            
        except Exception as e:
            self.error_signal.emit(self.service_name, str(e))
            self.status_signal.emit(self.service_name, "ERROR")
            self.log_signal.emit(self.service_name, f"[{self._timestamp()}] ERROR: {e}")
            self.running = False
    
    def stop_service(self):
        """Stop the running service"""
        if self.process and self.running:
            self.log_signal.emit(self.service_name, f"[{self._timestamp()}] Stopping {self.service_name}...")
            self.process.terminate()
            
            try:
                self.process.wait(timeout=5)
                self.log_signal.emit(self.service_name, f"[{self._timestamp()}] Service stopped")
            except subprocess.TimeoutExpired:
                self.log_signal.emit(self.service_name, f"[{self._timestamp()}] Force killing process...")
                self.process.kill()
                self.process.wait()
            
            self.running = False
            self.status_signal.emit(self.service_name, "STOPPED")
    
    @staticmethod
    def _timestamp():
        return datetime.now().strftime("%H:%M:%S")


class EnhancedServiceLauncher(QMainWindow):
    """Service Launcher with tabs and monitor"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dhan Services - Launcher & Monitor")
        self.setGeometry(100, 100, 1400, 900)
        
        # Storage
        self.workers = {}
        self.threads = {}
        self.buttons = {}
        self.log_widgets = {}
        self.visualizer_processes = {}
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI with tabs"""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Dhan Services Launcher & Monitor")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # ===== SERVICE CONTROL SECTION =====
        service_label = QLabel("Services (Background):")
        service_label_font = QFont()
        service_label_font.setBold(True)
        service_label.setFont(service_label_font)
        layout.addWidget(service_label)
        
        # Service control panels (top section)
        control_layout = QHBoxLayout()
        
        for service_name, config in SERVICES.items():
            panel = self.create_service_panel(service_name, config)
            control_layout.addWidget(panel)
        
        control_layout.addStretch()
        
        # Add monitor button
        monitor_btn = QPushButton("Start Monitor")
        monitor_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 10px 20px;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover { opacity: 0.9; }
            QPushButton:pressed { opacity: 0.8; }
        """)
        monitor_btn.setMinimumWidth(150)
        monitor_btn.clicked.connect(self.start_monitor)
        control_layout.addWidget(monitor_btn)
        
        layout.addLayout(control_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # ===== VISUALIZERS SECTION =====
        viz_label = QLabel("Visualizers (Launch Multiple Instances - Choose which to keep):")
        viz_label_font = QFont()
        viz_label_font.setBold(True)
        viz_label.setFont(viz_label_font)
        layout.addWidget(viz_label)
        
        # Visualizer buttons in scrollable grid
        viz_scroll = QScrollArea()
        viz_scroll.setWidgetResizable(True)
        viz_container = QWidget()
        viz_grid = QGridLayout(viz_container)
        
        row = 0
        col = 0
        max_cols = 2  # 2 buttons per row for more space
        button_num = 1
        
        for viz_name, config in VISUALIZERS.items():
            viz_btn = QPushButton(f"[{button_num}] {viz_name}")
            
            # Color code: Purple for Dhan (latest), Blue for others
            color = "#9C27B0" if "Dhan" in viz_name else "#2196F3"
            
            viz_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    padding: 12px 20px;
                    font-weight: bold;
                    border: none;
                    border-radius: 4px;
                    font-size: 11px;
                    text-align: center;
                }}
                QPushButton:hover {{ opacity: 0.9; }}
                QPushButton:pressed {{ opacity: 0.8; }}
            """)
            viz_btn.setMinimumWidth(250)  # Increased from 180
            viz_btn.setMinimumHeight(60)  # Increased from 50
            viz_btn.clicked.connect(lambda checked, name=viz_name: self.launch_visualizer(name))
            
            viz_grid.addWidget(viz_btn, row, col)
            
            col += 1
            button_num += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        viz_scroll.setWidget(viz_container)
        viz_scroll.setMaximumHeight(300)  # Increased from 200
        layout.addWidget(viz_scroll)
        
        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator2)
        
        # Tabs for service logs
        log_label = QLabel("Service Logs (Separate Tabs):")
        log_label_font = QFont()
        log_label_font.setBold(True)
        log_label.setFont(log_label_font)
        layout.addWidget(log_label)
        
        self.tabs = QTabWidget()
        
        for service_name in SERVICES.keys():
            log_widget = QTextEdit()
            log_widget.setReadOnly(True)
            log_widget.setFont(QFont("Courier", 9))
            log_widget.setStyleSheet(
                "QTextEdit { background-color: #1e1e1e; color: #d4d4d4; padding: 5px; }"
            )
            
            self.log_widgets[service_name] = log_widget
            self.tabs.addTab(log_widget, service_name)
        
        layout.addWidget(self.tabs, 1)  # Take remaining space
        
        main_widget.setLayout(layout)
    
    def create_service_panel(self, service_name, config):
        """Create control panel for a service"""
        group = QGroupBox(service_name)
        layout = QVBoxLayout()
        
        # Description
        desc_label = QLabel(config["description"])
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; font-size: 10px; font-style: italic;")
        layout.addWidget(desc_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        # START
        start_btn = QPushButton("START")
        start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {config['color']};
                color: white;
                padding: 8px;
                font-weight: bold;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{ opacity: 0.9; }}
            QPushButton:pressed {{ opacity: 0.8; }}
            QPushButton:disabled {{ background-color: #cccccc; }}
        """)
        start_btn.setMinimumWidth(100)
        start_btn.clicked.connect(lambda: self.start_service(service_name))
        btn_layout.addWidget(start_btn)
        
        # STOP
        stop_btn = QPushButton("STOP")
        stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 8px;
                font-weight: bold;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { opacity: 0.9; }
            QPushButton:pressed { opacity: 0.8; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        stop_btn.setMinimumWidth(100)
        stop_btn.setEnabled(False)
        stop_btn.clicked.connect(lambda: self.stop_service(service_name))
        btn_layout.addWidget(stop_btn)
        
        layout.addLayout(btn_layout)
        
        # Status
        status_label = QLabel("STOPPED")
        status_label.setStyleSheet("color: #ff9800; font-weight: bold; text-align: center;")
        layout.addWidget(status_label)
        
        layout.addStretch()
        group.setLayout(layout)
        group.setMinimumWidth(280)
        
        # Store references
        self.buttons[service_name] = {
            "start": start_btn,
            "stop": stop_btn,
            "status": status_label
        }
        
        return group
    
    def start_service(self, service_name):
        """Start a service"""
        config = SERVICES[service_name]
        
        # Clear log for fresh start
        self.log_widgets[service_name].clear()
        self.append_log(service_name, f"\n{'='*100}")
        self.append_log(service_name, f"[STARTING] {service_name}")
        self.append_log(service_name, f"{'='*100}\n")
        
        # Create worker
        module_args = config.get("module_args", [])
        args = config.get("args", [])
        worker = ServiceWorker(service_name, config["script"], args, module_args=module_args)
        
        # Connect signals
        worker.log_signal.connect(self.append_log)
        worker.status_signal.connect(self.update_status)
        worker.error_signal.connect(self.on_error)
        
        # Create thread
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run_service)
        
        # Store references
        self.workers[service_name] = worker
        self.threads[service_name] = thread
        
        # Update buttons
        self.buttons[service_name]["start"].setEnabled(False)
        self.buttons[service_name]["stop"].setEnabled(True)
        
        # Start thread
        thread.start()
    
    def stop_service(self, service_name):
        """Stop a service"""
        if service_name not in self.workers:
            return
        
        worker = self.workers[service_name]
        thread = self.threads[service_name]
        
        self.append_log(service_name, f"\n[STOPPING] {service_name}\n")
        
        if worker.running:
            worker.stop_service()
            
            # Wait for thread
            if thread:
                thread.quit()
                thread.wait(6000)
        
        # Update buttons
        self.buttons[service_name]["start"].setEnabled(True)
        self.buttons[service_name]["stop"].setEnabled(False)
    
    def append_log(self, service_name, text):
        """Append to service's log tab"""
        if service_name in self.log_widgets:
            log_widget = self.log_widgets[service_name]
            log_widget.append(text)
            # Auto-scroll to bottom
            log_widget.verticalScrollBar().setValue(
                log_widget.verticalScrollBar().maximum()
            )
    
    def update_status(self, service_name, status):
        """Update status label"""
        if service_name not in self.buttons:
            return
        
        status_label = self.buttons[service_name]["status"]
        status_label.setText(status)
        
        if status == "RUNNING":
            status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")  # Green
        elif status == "ERROR":
            status_label.setStyleSheet("color: #f44336; font-weight: bold;")  # Red
        else:
            status_label.setStyleSheet("color: #ff9800; font-weight: bold;")  # Orange
    
    def on_error(self, service_name, error_msg):
        """Handle error"""
        self.append_log(service_name, f"\n[ERROR] {error_msg}\n")
    
    def start_monitor(self):
        """Launch real-time monitor dashboard"""
        try:
            import os
            script_path = os.path.join(os.getcwd(), "service_monitor_dashboard.py")
            
            # Launch with output visible for debugging
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.append_log("FNO Feed Launcher", "\n[MONITOR] Dashboard launched in separate window...\n")
            
            # Check if process started successfully
            time.sleep(0.5)
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                error_msg = stderr if stderr else stdout
                self.append_log("FNO Feed Launcher", f"\n[ERROR] Monitor failed to start:\n{error_msg}\n")
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            self.append_log("FNO Feed Launcher", f"\n[ERROR] Failed to launch monitor:\n{error_trace}\n")
    
    def launch_visualizer(self, visualizer_name):
        """Launch a visualizer instance"""
        try:
            config = VISUALIZERS[visualizer_name]
            script = config["script"]
            module_args = config.get("module_args", [])
            args = config.get("args", [])
            
            # Build command
            if module_args:
                # python -m module_name
                cmd = [sys.executable] + module_args + args
            else:
                # python script.py
                cmd = [sys.executable, script] + args
            
            # Launch visualizer
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Track the process
            if visualizer_name not in self.visualizer_processes:
                self.visualizer_processes[visualizer_name] = []
            
            self.visualizer_processes[visualizer_name].append({
                'process': process,
                'pid': process.pid,
                'launched_at': datetime.now().strftime("%H:%M:%S")
            })
            
            instance_num = len(self.visualizer_processes[visualizer_name])
            self.append_log("FNO Feed Launcher", f"\n[VISUALIZER] Launched {visualizer_name} (Instance #{instance_num}, PID: {process.pid})\n")
            
            # Check if process started successfully
            time.sleep(0.5)
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                error_msg = stderr if stderr else stdout
                self.append_log("FNO Feed Launcher", f"\n[ERROR] {visualizer_name} failed:\n{error_msg}\n")
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            self.append_log("FNO Feed Launcher", f"\n[ERROR] Failed to launch {visualizer_name}:\n{error_trace}\n")
    
    def closeEvent(self, event):
        """Clean up on close"""
        # Stop all services
        for service_name in list(self.workers.keys()):
            if service_name in self.workers:
                worker = self.workers[service_name]
                thread = self.threads[service_name]
                
                if worker and worker.running:
                    worker.stop_service()
                    if thread:
                        thread.quit()
                        thread.wait(2000)
        
        # Kill all visualizer processes
        for viz_name, processes in self.visualizer_processes.items():
            for proc_info in processes:
                try:
                    proc_info['process'].terminate()
                    proc_info['process'].wait(timeout=2)
                except:
                    try:
                        proc_info['process'].kill()
                    except:
                        pass
        
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = EnhancedServiceLauncher()
    window.show()
    sys.exit(app.exec_())
