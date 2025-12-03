"""
Stock Alert System - Desktop GUI
================================

A PyQt6-based desktop application for managing stock price alerts.
Features:
- Create/edit/delete price alerts
- View triggered alerts history
- System tray integration
- Real-time price display
"""

import sys
import logging
from typing import Optional, List
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QComboBox, QLineEdit,
    QLabel, QDoubleSpinBox, QCheckBox, QMessageBox, QDialog,
    QFormLayout, QDialogButtonBox, QSystemTrayIcon, QMenu,
    QHeaderView, QTabWidget, QGroupBox, QSpinBox, QTextEdit,
    QStatusBar, QToolBar, QFrame, QSplitter
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QIcon, QAction, QFont, QColor

from ..core.enums import AssetType, AlertType, AlertCondition, AlertStatus, NotificationChannel, Priority
from ..services.alert_service import AlertService
from ..services.symbol_service import SymbolService
from ..services.user_service import UserService
from ..infrastructure.database import init_database

logger = logging.getLogger(__name__)


class CreateAlertDialog(QDialog):
    """Dialog for creating a new alert."""
    
    def __init__(self, parent=None, user_id: int = 1):
        super().__init__(parent)
        self.user_id = user_id
        self.symbol_service = SymbolService()
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Create New Alert")
        self.setMinimumWidth(400)
        
        layout = QFormLayout(self)
        
        # Symbol input
        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("e.g., RELIANCE, BTC, GOLD")
        layout.addRow("Symbol:", self.symbol_input)
        
        # Asset type
        self.asset_type_combo = QComboBox()
        for at in AssetType:
            self.asset_type_combo.addItem(at.value.replace('_', ' ').title(), at)
        layout.addRow("Asset Type:", self.asset_type_combo)
        
        # Alert type
        self.alert_type_combo = QComboBox()
        self.alert_type_combo.addItem("Price", AlertType.PRICE)
        self.alert_type_combo.addItem("Volume", AlertType.VOLUME)
        self.alert_type_combo.addItem("Technical", AlertType.TECHNICAL)
        self.alert_type_combo.currentIndexChanged.connect(self.on_alert_type_changed)
        layout.addRow("Alert Type:", self.alert_type_combo)
        
        # Condition
        self.condition_combo = QComboBox()
        self.populate_conditions(AlertType.PRICE)
        layout.addRow("Condition:", self.condition_combo)
        
        # Target value
        self.target_value_spin = QDoubleSpinBox()
        self.target_value_spin.setRange(0.01, 9999999.99)
        self.target_value_spin.setDecimals(2)
        layout.addRow("Target Value:", self.target_value_spin)
        
        # Target value 2 (for BETWEEN)
        self.target_value_2_spin = QDoubleSpinBox()
        self.target_value_2_spin.setRange(0.01, 9999999.99)
        self.target_value_2_spin.setDecimals(2)
        self.target_value_2_spin.setEnabled(False)
        layout.addRow("Target Value 2:", self.target_value_2_spin)
        
        # Priority
        self.priority_combo = QComboBox()
        for p in Priority:
            self.priority_combo.addItem(p.value.title(), p)
        self.priority_combo.setCurrentIndex(1)  # Normal
        layout.addRow("Priority:", self.priority_combo)
        
        # Notification channels
        notifications_group = QGroupBox("Notifications")
        notif_layout = QVBoxLayout(notifications_group)
        
        self.desktop_check = QCheckBox("Desktop Notification")
        self.desktop_check.setChecked(True)
        notif_layout.addWidget(self.desktop_check)
        
        self.sound_check = QCheckBox("Sound Alert")
        self.sound_check.setChecked(True)
        notif_layout.addWidget(self.sound_check)
        
        layout.addRow(notifications_group)
        
        # Trigger once
        self.trigger_once_check = QCheckBox("Trigger once (then deactivate)")
        self.trigger_once_check.setChecked(True)
        layout.addRow(self.trigger_once_check)
        
        # Notes
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(60)
        self.notes_input.setPlaceholderText("Optional notes...")
        layout.addRow("Notes:", self.notes_input)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)
        
        self.condition_combo.currentIndexChanged.connect(self.on_condition_changed)
    
    def populate_conditions(self, alert_type: AlertType):
        """Populate conditions based on alert type."""
        self.condition_combo.clear()
        
        if alert_type == AlertType.PRICE:
            conditions = [
                ("Price Above", AlertCondition.PRICE_ABOVE),
                ("Price Below", AlertCondition.PRICE_BELOW),
                ("Price Between", AlertCondition.PRICE_BETWEEN),
                ("Crosses Above", AlertCondition.PRICE_CROSSES_ABOVE),
                ("Crosses Below", AlertCondition.PRICE_CROSSES_BELOW),
                ("% Change Up", AlertCondition.PCT_CHANGE_UP),
                ("% Change Down", AlertCondition.PCT_CHANGE_DOWN),
            ]
        elif alert_type == AlertType.VOLUME:
            conditions = [
                ("Volume Above", AlertCondition.VOLUME_ABOVE),
                ("Volume Spike", AlertCondition.VOLUME_SPIKE),
            ]
        else:
            conditions = [
                ("RSI Overbought", AlertCondition.RSI_OVERBOUGHT),
                ("RSI Oversold", AlertCondition.RSI_OVERSOLD),
                ("MACD Bullish Cross", AlertCondition.MACD_BULLISH_CROSS),
                ("MACD Bearish Cross", AlertCondition.MACD_BEARISH_CROSS),
                ("52W High", AlertCondition.HIGH_52W),
                ("52W Low", AlertCondition.LOW_52W),
            ]
        
        for name, condition in conditions:
            self.condition_combo.addItem(name, condition)
    
    def on_alert_type_changed(self, index):
        alert_type = self.alert_type_combo.currentData()
        self.populate_conditions(alert_type)
    
    def on_condition_changed(self, index):
        condition = self.condition_combo.currentData()
        self.target_value_2_spin.setEnabled(condition == AlertCondition.PRICE_BETWEEN)
    
    def get_alert_data(self) -> dict:
        """Get alert data from form."""
        channels = []
        if self.desktop_check.isChecked():
            channels.append(NotificationChannel.DESKTOP)
        if self.sound_check.isChecked():
            channels.append(NotificationChannel.SOUND)
        
        return {
            'user_id': self.user_id,
            'symbol': self.symbol_input.text().strip().upper(),
            'asset_type': self.asset_type_combo.currentData(),
            'alert_type': self.alert_type_combo.currentData(),
            'condition': self.condition_combo.currentData(),
            'target_value': self.target_value_spin.value(),
            'target_value_2': self.target_value_2_spin.value() if self.target_value_2_spin.isEnabled() else None,
            'priority': self.priority_combo.currentData(),
            'notification_channels': channels,
            'trigger_once': self.trigger_once_check.isChecked(),
            'notes': self.notes_input.toPlainText().strip() or None,
        }


class EditAlertDialog(QDialog):
    """Dialog for editing an existing alert."""
    
    def __init__(self, parent=None, alert=None, user_id: int = 1):
        super().__init__(parent)
        self.user_id = user_id
        self.alert = alert
        self.symbol_service = SymbolService()
        self.setup_ui()
        self.populate_from_alert()
    
    def setup_ui(self):
        self.setWindowTitle(f"Edit Alert: {self.alert.symbol}")
        self.setMinimumWidth(400)
        
        layout = QFormLayout(self)
        
        # Symbol (read-only for edit)
        self.symbol_label = QLabel(self.alert.symbol)
        self.symbol_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addRow("Symbol:", self.symbol_label)
        
        # Asset type (read-only)
        self.asset_type_label = QLabel(self.alert.asset_type.value.replace('_', ' ').title())
        layout.addRow("Asset Type:", self.asset_type_label)
        
        # Condition
        self.condition_combo = QComboBox()
        conditions = [
            ("Price Above", AlertCondition.PRICE_ABOVE),
            ("Price Below", AlertCondition.PRICE_BELOW),
            ("Price Between", AlertCondition.PRICE_BETWEEN),
            ("Crosses Above", AlertCondition.PRICE_CROSSES_ABOVE),
            ("Crosses Below", AlertCondition.PRICE_CROSSES_BELOW),
            ("% Change Up", AlertCondition.PCT_CHANGE_UP),
            ("% Change Down", AlertCondition.PCT_CHANGE_DOWN),
        ]
        for name, condition in conditions:
            self.condition_combo.addItem(name, condition)
        self.condition_combo.currentIndexChanged.connect(self.on_condition_changed)
        layout.addRow("Condition:", self.condition_combo)
        
        # Target value
        self.target_value_spin = QDoubleSpinBox()
        self.target_value_spin.setRange(0.01, 9999999.99)
        self.target_value_spin.setDecimals(2)
        layout.addRow("Target Value:", self.target_value_spin)
        
        # Target value 2 (for BETWEEN)
        self.target_value_2_spin = QDoubleSpinBox()
        self.target_value_2_spin.setRange(0.01, 9999999.99)
        self.target_value_2_spin.setDecimals(2)
        self.target_value_2_spin.setEnabled(False)
        layout.addRow("Target Value 2:", self.target_value_2_spin)
        
        # Status
        self.status_combo = QComboBox()
        for status in AlertStatus:
            self.status_combo.addItem(status.value.title(), status)
        layout.addRow("Status:", self.status_combo)
        
        # Priority
        self.priority_combo = QComboBox()
        for p in Priority:
            self.priority_combo.addItem(p.value.title(), p)
        layout.addRow("Priority:", self.priority_combo)
        
        # Notification channels
        notifications_group = QGroupBox("Notifications")
        notif_layout = QVBoxLayout(notifications_group)
        
        self.desktop_check = QCheckBox("Desktop Notification")
        notif_layout.addWidget(self.desktop_check)
        
        self.sound_check = QCheckBox("Sound Alert")
        notif_layout.addWidget(self.sound_check)
        
        layout.addRow(notifications_group)
        
        # Trigger once
        self.trigger_once_check = QCheckBox("Trigger once (then deactivate)")
        layout.addRow(self.trigger_once_check)
        
        # Notes
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(60)
        layout.addRow("Notes:", self.notes_input)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)
    
    def on_condition_changed(self, index):
        condition = self.condition_combo.currentData()
        self.target_value_2_spin.setEnabled(condition == AlertCondition.PRICE_BETWEEN)
    
    def populate_from_alert(self):
        """Populate form with existing alert data."""
        # Set condition
        for i in range(self.condition_combo.count()):
            if self.condition_combo.itemData(i) == self.alert.condition:
                self.condition_combo.setCurrentIndex(i)
                break
        
        # Set target values
        self.target_value_spin.setValue(self.alert.target_value)
        if self.alert.target_value_2:
            self.target_value_2_spin.setValue(self.alert.target_value_2)
        
        # Set status
        for i in range(self.status_combo.count()):
            if self.status_combo.itemData(i) == self.alert.status:
                self.status_combo.setCurrentIndex(i)
                break
        
        # Set priority
        for i in range(self.priority_combo.count()):
            if self.priority_combo.itemData(i) == self.alert.priority:
                self.priority_combo.setCurrentIndex(i)
                break
        
        # Set notification channels
        if self.alert.notification_channels:
            self.desktop_check.setChecked(NotificationChannel.DESKTOP in self.alert.notification_channels)
            self.sound_check.setChecked(NotificationChannel.SOUND in self.alert.notification_channels)
        else:
            self.desktop_check.setChecked(True)
            self.sound_check.setChecked(True)
        
        # Trigger once
        self.trigger_once_check.setChecked(self.alert.trigger_once)
        
        # Notes
        if self.alert.notes:
            self.notes_input.setText(self.alert.notes)
    
    def get_update_data(self) -> dict:
        """Get updated alert data from form."""
        channels = []
        if self.desktop_check.isChecked():
            channels.append(NotificationChannel.DESKTOP)
        if self.sound_check.isChecked():
            channels.append(NotificationChannel.SOUND)
        
        return {
            'condition': self.condition_combo.currentData(),
            'target_value': self.target_value_spin.value(),
            'target_value_2': self.target_value_2_spin.value() if self.target_value_2_spin.isEnabled() else None,
            'status': self.status_combo.currentData(),
            'priority': self.priority_combo.currentData(),
            'notification_channels': channels,
            'trigger_once': self.trigger_once_check.isChecked(),
            'notes': self.notes_input.toPlainText().strip() or None,
        }


class AlertManagerGUI(QMainWindow):
    """Main window for the Stock Alert Manager."""
    
    def __init__(self, user_id: int = 1):
        super().__init__()
        self.user_id = user_id
        self.alert_service = AlertService()
        self.symbol_service = SymbolService()
        
        self.setup_ui()
        self.setup_tray()
        self.load_alerts()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_alerts)
        self.refresh_timer.start(30000)  # 30 seconds
        
        # Auto-start monitoring after 2 seconds
        QTimer.singleShot(2000, self.start_demo_monitoring)
    
    def setup_ui(self):
        self.setWindowTitle("Stock Alert Manager")
        self.setMinimumSize(900, 600)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Alert banner (hidden by default)
        self.alert_banner = QFrame()
        self.alert_banner.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #ff6600, stop:0.5 #ff9933, stop:1 #ff6600);
                border: 2px solid #ff4400;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        self.alert_banner.setVisible(False)
        
        banner_layout = QHBoxLayout(self.alert_banner)
        banner_layout.setContentsMargins(10, 5, 10, 5)
        
        self.alert_banner_icon = QLabel("🔔")
        self.alert_banner_icon.setStyleSheet("font-size: 24px;")
        banner_layout.addWidget(self.alert_banner_icon)
        
        self.alert_banner_text = QLabel("")
        self.alert_banner_text.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        self.alert_banner_text.setWordWrap(True)
        banner_layout.addWidget(self.alert_banner_text, 1)
        
        dismiss_btn = QPushButton("✕")
        dismiss_btn.setStyleSheet("background: transparent; color: white; font-size: 16px; border: none;")
        dismiss_btn.setFixedSize(30, 30)
        dismiss_btn.clicked.connect(lambda: self.alert_banner.setVisible(False))
        banner_layout.addWidget(dismiss_btn)
        
        layout.addWidget(self.alert_banner)
        
        # Toolbar
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        new_alert_action = QAction("➕ New Alert", self)
        new_alert_action.triggered.connect(self.create_alert)
        toolbar.addAction(new_alert_action)
        
        refresh_action = QAction("🔄 Refresh", self)
        refresh_action.triggered.connect(self.load_alerts)
        toolbar.addAction(refresh_action)
        
        toolbar.addSeparator()
        
        # Tabs
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # Active alerts tab
        active_tab = QWidget()
        active_layout = QVBoxLayout(active_tab)
        
        # Filter bar
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("Filter:"))
        
        self.status_filter = QComboBox()
        self.status_filter.addItem("All Statuses", None)
        for status in AlertStatus:
            self.status_filter.addItem(status.value.title(), status)
        self.status_filter.currentIndexChanged.connect(self.load_alerts)
        filter_layout.addWidget(self.status_filter)
        
        self.asset_filter = QComboBox()
        self.asset_filter.addItem("All Assets", None)
        for at in AssetType:
            self.asset_filter.addItem(at.value.replace('_', ' ').title(), at)
        self.asset_filter.currentIndexChanged.connect(self.load_alerts)
        filter_layout.addWidget(self.asset_filter)
        
        filter_layout.addStretch()
        active_layout.addLayout(filter_layout)
        
        # Alerts table
        self.alerts_table = QTableWidget()
        self.alerts_table.setColumnCount(8)
        self.alerts_table.setHorizontalHeaderLabels([
            "Symbol", "Type", "Condition", "Target", "Status", "Created", "Triggers", "Actions"
        ])
        self.alerts_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.alerts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        active_layout.addWidget(self.alerts_table)
        
        tabs.addTab(active_tab, "📊 Alerts")
        
        # History tab
        history_tab = QWidget()
        history_layout = QVBoxLayout(history_tab)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels([
            "Symbol", "Condition", "Target", "Actual", "Triggered At"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        history_layout.addWidget(self.history_table)
        
        tabs.addTab(history_tab, "📜 History")
        
        # Quick price check tab
        price_tab = QWidget()
        price_layout = QVBoxLayout(price_tab)
        
        price_input_layout = QHBoxLayout()
        
        self.price_symbol_input = QLineEdit()
        self.price_symbol_input.setPlaceholderText("Enter symbol...")
        price_input_layout.addWidget(self.price_symbol_input)
        
        self.price_asset_combo = QComboBox()
        for at in AssetType:
            self.price_asset_combo.addItem(at.value.replace('_', ' ').title(), at)
        price_input_layout.addWidget(self.price_asset_combo)
        
        price_check_btn = QPushButton("Get Price")
        price_check_btn.clicked.connect(self.check_price)
        price_input_layout.addWidget(price_check_btn)
        
        price_layout.addLayout(price_input_layout)
        
        self.price_result_label = QLabel()
        self.price_result_label.setStyleSheet("font-size: 18px; padding: 20px;")
        self.price_result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        price_layout.addWidget(self.price_result_label)
        
        price_layout.addStretch()
        
        tabs.addTab(price_tab, "💰 Price Check")
        
        # Monitoring Status tab
        status_tab = QWidget()
        status_layout = QVBoxLayout(status_tab)
        
        # System status group
        system_group = QGroupBox("🔴 Monitoring Status")
        system_layout = QVBoxLayout(system_group)
        
        self.monitoring_status_label = QLabel(
            "<span style='color: orange; font-size: 16px;'>⚠️ Monitoring is NOT active</span><br><br>"
            "The GUI is for managing alerts only.<br>"
            "To enable real-time monitoring, run the full system:<br><br>"
            "<code>python stock_alerts_launcher.py</code> (requires Redis)<br><br>"
            "Or start Redis first:<br>"
            "<code>docker run -d -p 6379:6379 redis</code>"
        )
        self.monitoring_status_label.setTextFormat(Qt.TextFormat.RichText)
        self.monitoring_status_label.setStyleSheet("padding: 20px;")
        system_layout.addWidget(self.monitoring_status_label)
        
        # Check status button
        check_status_btn = QPushButton("🔍 Check System Status")
        check_status_btn.clicked.connect(self.check_system_status)
        system_layout.addWidget(check_status_btn)
        
        # Start monitoring button
        start_monitor_btn = QPushButton("▶️ Start Monitoring (Demo Mode)")
        start_monitor_btn.clicked.connect(self.start_demo_monitoring)
        system_layout.addWidget(start_monitor_btn)
        
        status_layout.addWidget(system_group)
        
        # Service status
        services_group = QGroupBox("Service Status")
        services_layout = QVBoxLayout(services_group)
        
        self.redis_status = QLabel("Redis: ❓ Unknown")
        self.db_status = QLabel("Database: ❓ Unknown") 
        self.worker_status = QLabel("Workers: ❓ Not running")
        
        services_layout.addWidget(self.redis_status)
        services_layout.addWidget(self.db_status)
        services_layout.addWidget(self.worker_status)
        
        status_layout.addWidget(services_group)
        
        # Monitored symbols
        symbols_group = QGroupBox("Monitored Symbols")
        symbols_layout = QVBoxLayout(symbols_group)
        
        self.monitored_symbols_label = QLabel("No symbols being monitored")
        symbols_layout.addWidget(self.monitored_symbols_label)
        
        status_layout.addWidget(symbols_group)
        
        # Activity Log
        activity_group = QGroupBox("📋 Activity Log")
        activity_layout = QVBoxLayout(activity_group)
        
        self.activity_log = QTextEdit()
        self.activity_log.setReadOnly(True)
        self.activity_log.setMaximumHeight(150)
        self.activity_log.setStyleSheet("font-family: Consolas, monospace; font-size: 10px;")
        activity_layout.addWidget(self.activity_log)
        
        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.clicked.connect(lambda: self.activity_log.clear())
        activity_layout.addWidget(clear_log_btn)
        
        status_layout.addWidget(activity_group)
        status_layout.addStretch()
        
        tabs.addTab(status_tab, "📡 Monitoring")
        
        # Check status on startup
        QTimer.singleShot(1000, self.check_system_status)
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
        # Alert count label
        self.alert_count_label = QLabel()
        self.statusBar().addPermanentWidget(self.alert_count_label)
    
    def setup_tray(self):
        """Setup system tray icon."""
        self.tray_icon = QSystemTrayIcon(self)
        
        # Set a default icon (or skip if no icon available)
        try:
            # Try to use app icon or a simple placeholder
            icon = self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon)
            self.tray_icon.setIcon(icon)
        except Exception:
            pass  # Tray will work without icon on some systems
        
        # Create tray menu
        tray_menu = QMenu()
        
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_activated)
        self.tray_icon.show()
    
    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()
    
    def closeEvent(self, event):
        """Minimize to tray on close."""
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Stock Alert Manager",
            "Running in background. Click tray icon to show.",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
    
    def quit_app(self):
        """Actually quit the application."""
        self.tray_icon.hide()
        QApplication.quit()
    
    def load_alerts(self):
        """Load alerts into table."""
        status_filter = self.status_filter.currentData()
        asset_filter = self.asset_filter.currentData()
        
        try:
            alerts = self.alert_service.get_user_alerts(
                user_id=self.user_id,
                status=status_filter,
                asset_type=asset_filter,
            )
            
            self.alerts_table.setRowCount(len(alerts))
            
            for row, alert in enumerate(alerts):
                self.alerts_table.setItem(row, 0, QTableWidgetItem(alert.symbol))
                self.alerts_table.setItem(row, 1, QTableWidgetItem(alert.asset_type.value))
                self.alerts_table.setItem(row, 2, QTableWidgetItem(alert.condition.value))
                self.alerts_table.setItem(row, 3, QTableWidgetItem(f"{alert.target_value:.2f}"))
                
                status_item = QTableWidgetItem(alert.status.value)
                if alert.status == AlertStatus.ACTIVE:
                    status_item.setBackground(QColor(200, 255, 200))
                elif alert.status == AlertStatus.TRIGGERED:
                    status_item.setBackground(QColor(255, 255, 200))
                elif alert.status == AlertStatus.PAUSED:
                    status_item.setBackground(QColor(200, 200, 200))
                self.alerts_table.setItem(row, 4, status_item)
                
                self.alerts_table.setItem(row, 5, QTableWidgetItem(
                    alert.created_at.strftime("%Y-%m-%d %H:%M")
                ))
                self.alerts_table.setItem(row, 6, QTableWidgetItem(str(alert.trigger_count)))
                
                # Action buttons
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(2, 2, 2, 2)
                
                if alert.status == AlertStatus.ACTIVE:
                    pause_btn = QPushButton("⏸")
                    pause_btn.setToolTip("Pause")
                    pause_btn.clicked.connect(lambda checked, a=alert: self.pause_alert(a))
                    actions_layout.addWidget(pause_btn)
                elif alert.status == AlertStatus.PAUSED:
                    resume_btn = QPushButton("▶")
                    resume_btn.setToolTip("Resume")
                    resume_btn.clicked.connect(lambda checked, a=alert: self.resume_alert(a))
                    actions_layout.addWidget(resume_btn)
                
                edit_btn = QPushButton("✏️")
                edit_btn.setToolTip("Edit")
                edit_btn.clicked.connect(lambda checked, a=alert: self.edit_alert(a))
                actions_layout.addWidget(edit_btn)
                
                delete_btn = QPushButton("🗑")
                delete_btn.setToolTip("Delete")
                delete_btn.clicked.connect(lambda checked, a=alert: self.delete_alert(a))
                actions_layout.addWidget(delete_btn)
                
                self.alerts_table.setCellWidget(row, 7, actions_widget)
            
            self.alert_count_label.setText(f"Total: {len(alerts)} alerts")
            self.statusBar().showMessage(f"Loaded {len(alerts)} alerts", 3000)
            
            # Load history
            self.load_history()
            
        except Exception as e:
            logger.error(f"Error loading alerts: {e}")
            self.statusBar().showMessage(f"Error: {e}", 5000)
    
    def load_history(self):
        """Load alert history."""
        try:
            history = self.alert_service.get_alert_history(self.user_id)
            
            self.history_table.setRowCount(len(history))
            
            for row, h in enumerate(history):
                self.history_table.setItem(row, 0, QTableWidgetItem(h['symbol']))
                self.history_table.setItem(row, 1, QTableWidgetItem(h['condition']))
                self.history_table.setItem(row, 2, QTableWidgetItem(f"{h['target_value']:.2f}"))
                self.history_table.setItem(row, 3, QTableWidgetItem(f"{h['actual_value']:.2f}"))
                
                triggered_at = h['triggered_at']
                if isinstance(triggered_at, datetime):
                    triggered_at = triggered_at.strftime("%Y-%m-%d %H:%M:%S")
                self.history_table.setItem(row, 4, QTableWidgetItem(str(triggered_at)))
                
        except Exception as e:
            logger.error(f"Error loading history: {e}")
    
    def create_alert(self):
        """Show create alert dialog."""
        dialog = CreateAlertDialog(self, self.user_id)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_alert_data()
            
            if not data['symbol']:
                QMessageBox.warning(self, "Error", "Symbol is required")
                return
            
            try:
                alert = self.alert_service.create_alert(**data)
                QMessageBox.information(
                    self, "Success",
                    f"Alert created for {alert.symbol}\n"
                    f"Condition: {alert.condition.value} {alert.target_value}"
                )
                self.load_alerts()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create alert: {e}")
    
    def pause_alert(self, alert):
        """Pause an alert."""
        try:
            self.alert_service.pause_alert(alert.id, self.user_id)
            self.load_alerts()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to pause alert: {e}")
    
    def resume_alert(self, alert):
        """Resume a paused alert."""
        try:
            self.alert_service.resume_alert(alert.id, self.user_id)
            self.load_alerts()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to resume alert: {e}")
    
    def edit_alert(self, alert):
        """Edit an existing alert."""
        dialog = EditAlertDialog(self, alert=alert, user_id=self.user_id)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                update_data = dialog.get_update_data()
                self.alert_service.update_alert(alert.id, self.user_id, **update_data)
                self.load_alerts()
                self.statusBar().showMessage(f"Alert for {alert.symbol} updated!", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update alert: {e}")
    
    def delete_alert(self, alert):
        """Delete an alert."""
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete alert for {alert.symbol}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.alert_service.delete_alert(alert.id, self.user_id)
                self.load_alerts()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete alert: {e}")
    
    def check_price(self):
        """Check current price for a symbol."""
        symbol = self.price_symbol_input.text().strip().upper()
        asset_type = self.price_asset_combo.currentData()
        
        if not symbol:
            return
        
        self.statusBar().showMessage(f"Fetching price for {symbol}...")
        
        try:
            price_data = self.symbol_service.get_current_price(symbol, asset_type)
            
            if price_data:
                change_color = "green" if price_data['change'] >= 0 else "red"
                change_symbol = "+" if price_data['change'] >= 0 else ""
                
                self.price_result_label.setText(
                    f"<b>{symbol}</b><br><br>"
                    f"<span style='font-size: 24px;'>₹{price_data['price']:.2f}</span><br>"
                    f"<span style='color: {change_color};'>"
                    f"{change_symbol}{price_data['change']:.2f} ({change_symbol}{price_data['change_pct']:.2f}%)"
                    f"</span><br><br>"
                    f"High: ₹{price_data['high']:.2f} | Low: ₹{price_data['low']:.2f}<br>"
                    f"Volume: {price_data['volume']:,}"
                )
                self.statusBar().showMessage(f"Price updated for {symbol}", 3000)
            else:
                self.price_result_label.setText(f"Could not fetch price for {symbol}")
                
        except Exception as e:
            self.price_result_label.setText(f"Error: {e}")
            self.statusBar().showMessage(f"Error: {e}", 5000)
    
    def check_system_status(self):
        """Check status of Redis, DB, and workers."""
        self.statusBar().showMessage("Checking system status...")
        
        # Check database
        db_ok = False
        try:
            from ..infrastructure.database import get_database
            db = get_database()
            db_ok = db.check_connection()
            self.db_status.setText(f"Database: {'✅ Connected' if db_ok else '❌ Not connected'}")
        except Exception as e:
            self.db_status.setText(f"Database: ❌ Error - {e}")
        
        # Check Redis
        redis_ok = False
        try:
            from ..infrastructure.redis_client import get_redis
            redis = get_redis()
            redis_ok = redis.ping()
            self.redis_status.setText(f"Redis: {'✅ Connected' if redis_ok else '❌ Not connected'}")
        except Exception as e:
            self.redis_status.setText(f"Redis: ❌ Not available")
        
        # Check for active alerts (symbols being monitored)
        try:
            alerts = self.alert_service.get_user_alerts(self.user_id, status=AlertStatus.ACTIVE)
            symbols = set(a.yahoo_symbol for a in alerts)
            if symbols:
                self.monitored_symbols_label.setText(
                    f"Active alerts for: {', '.join(list(symbols)[:10])}"
                    + (f" (+{len(symbols)-10} more)" if len(symbols) > 10 else "")
                )
            else:
                self.monitored_symbols_label.setText("No active alerts")
        except Exception as e:
            self.monitored_symbols_label.setText(f"Error: {e}")
        
        # Update overall status
        if redis_ok and db_ok:
            self.monitoring_status_label.setText(
                "<span style='color: green; font-size: 16px;'>✅ System Ready</span><br><br>"
                "All services connected. Run the full system to start monitoring:<br>"
                "<code>python stock_alerts_launcher.py</code>"
            )
            self.worker_status.setText("Workers: ⚠️ Ready (start full system)")
        elif db_ok:
            self.monitoring_status_label.setText(
                "<span style='color: orange; font-size: 16px;'>⚠️ Redis Not Available</span><br><br>"
                "Database connected but Redis is not running.<br>"
                "For full monitoring, start Redis first:<br>"
                "<code>docker run -d -p 6379:6379 redis</code>"
            )
            self.worker_status.setText("Workers: ❌ Needs Redis")
        else:
            self.monitoring_status_label.setText(
                "<span style='color: red; font-size: 16px;'>❌ System Offline</span><br><br>"
                "Check database and Redis connections."
            )
            self.worker_status.setText("Workers: ❌ Services unavailable")
        
        self.statusBar().showMessage("Status check complete", 3000)
    
    def start_demo_monitoring(self):
        """Start a simple demo monitoring thread."""
        if hasattr(self, '_demo_monitor') and self._demo_monitor and self._demo_monitor.isRunning():
            self._demo_monitor.stop()
            self._demo_monitor = None
            self.monitoring_status_label.setText(
                "<span style='color: orange; font-size: 16px;'>⚠️ Demo Monitoring Stopped</span>"
            )
            self.statusBar().showMessage("Demo monitoring stopped", 3000)
            return
        
        # Start demo monitoring
        self._demo_monitor = DemoMonitorThread(
            self.alert_service, 
            self.symbol_service,
            self.user_id
        )
        self._demo_monitor.alert_triggered.connect(self.on_alert_triggered)
        self._demo_monitor.price_update.connect(self.on_price_update)
        self._demo_monitor.start()
        
        self.monitoring_status_label.setText(
            "<span style='color: green; font-size: 16px;'>🟢 Demo Monitoring Active</span><br><br>"
            "Checking prices every 30 seconds...<br>"
            "Click again to stop."
        )
        self.worker_status.setText("Workers: ✅ Demo mode running")
        self.statusBar().showMessage("Demo monitoring started", 3000)
        
        # Log to activity
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.activity_log.append(f"[{timestamp}] 🚀 Monitoring started - checking prices every 30 seconds")
    
    def on_alert_triggered(self, alert_id: str, symbol: str, message: str):
        """Handle triggered alert from demo monitor."""
        from datetime import datetime
        
        # Update trigger_count in database
        try:
            alert = self.alert_service.get_alert(alert_id, self.user_id)
            if alert:
                new_count = alert.trigger_count + 1
                self.alert_service.update_alert(
                    alert_id, 
                    self.user_id,
                    trigger_count=new_count,
                    last_triggered_at=datetime.now()
                )
        except Exception as e:
            logger.error(f"Failed to update trigger count: {e}")
        
        # Refresh the alerts table
        self.load_alerts()
        
        # Show visual notification banner (non-blocking)
        self._show_alert_banner(symbol, message)
        
        # Log to activity
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.activity_log.append(f"<span style='color: #ff6600; font-weight: bold;'>[{timestamp}] 🔔 TRIGGERED: {symbol} - {message}</span>")
        
        # Show tray notification (non-blocking)
        self.tray_icon.showMessage(
            f"🔔 Alert: {symbol}",
            message,
            QSystemTrayIcon.MessageIcon.Information,
            5000
        )
        
        # Play sound (non-blocking)
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except:
            pass
    
    def _show_alert_banner(self, symbol: str, message: str):
        """Show a non-blocking visual alert banner at the top of the window."""
        # Update banner text
        self.alert_banner_text.setText(f"ALERT TRIGGERED: {symbol}\n{message}")
        
        # Show the banner with animation effect
        self.alert_banner.setVisible(True)
        
        # Flash effect using stylesheet
        self.alert_banner.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #ff3300, stop:0.5 #ff6600, stop:1 #ff3300);
                border: 3px solid #ff0000;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        # Auto-hide after 10 seconds
        QTimer.singleShot(10000, lambda: self.alert_banner.setVisible(False))
        
        # Reset style after flash
        QTimer.singleShot(500, lambda: self.alert_banner.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #ff6600, stop:0.5 #ff9933, stop:1 #ff6600);
                border: 2px solid #ff4400;
                border-radius: 8px;
                padding: 10px;
            }
        """))
        
        # Bring window to front
        self.activateWindow()
        self.raise_()
    
    def on_price_update(self, symbol: str, price: float, change_pct: float):
        """Handle price update from demo monitor."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Use $ for crypto/commodities, ₹ for Indian stocks
        currency = "₹"
        if hasattr(self, '_last_asset_types') and symbol in self._last_asset_types:
            if self._last_asset_types[symbol] in ('crypto', 'commodity'):
                currency = "$"
        
        # Log to activity log
        log_msg = f"[{timestamp}] ✓ {symbol}: {currency}{price:,.2f} ({change_pct:+.2f}%)"
        self.activity_log.append(log_msg)
        
        # Keep log from getting too long
        if self.activity_log.document().blockCount() > 100:
            cursor = self.activity_log.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.KeepAnchor, 10)
            cursor.removeSelectedText()
        
        self.statusBar().showMessage(
            f"Price update: {symbol} = {currency}{price:.2f} ({change_pct:+.2f}%)", 
            5000
        )


class DemoMonitorThread(QThread):
    """Simple demo monitoring thread that doesn't require Redis."""
    
    alert_triggered = pyqtSignal(str, str, str)  # alert_id, symbol, message
    price_update = pyqtSignal(str, float, float)  # symbol, price, change_pct
    
    def __init__(self, alert_service, symbol_service, user_id):
        super().__init__()
        self.alert_service = alert_service
        self.symbol_service = symbol_service
        self.user_id = user_id
        self._running = True
        self._interval = 30  # seconds
        self._triggered_alerts = set()  # Track already triggered alerts to avoid duplicates
    
    def stop(self):
        self._running = False
    
    def run(self):
        """Monitor loop."""
        import time
        
        while self._running:
            try:
                # Get active alerts
                alerts = self.alert_service.get_user_alerts(
                    self.user_id, 
                    status=AlertStatus.ACTIVE
                )
                
                if not alerts:
                    time.sleep(self._interval)
                    continue
                
                # Group by symbol to avoid duplicate fetches
                symbols_to_check = {}
                for alert in alerts:
                    if alert.yahoo_symbol not in symbols_to_check:
                        symbols_to_check[alert.yahoo_symbol] = []
                    symbols_to_check[alert.yahoo_symbol].append(alert)
                
                # Check each symbol
                for yahoo_symbol, symbol_alerts in symbols_to_check.items():
                    if not self._running:
                        break
                    
                    alert = symbol_alerts[0]  # Use first alert to get asset type
                    price_data = self.symbol_service.get_current_price(
                        alert.symbol, 
                        alert.asset_type
                    )
                    
                    if price_data:
                        self.price_update.emit(
                            alert.symbol,
                            price_data['price'],
                            price_data['change_pct']
                        )
                        
                        # Check each alert for this symbol
                        for a in symbol_alerts:
                            # Skip if already triggered this session
                            if a.id in self._triggered_alerts:
                                continue
                                
                            triggered, msg = self._check_alert(a, price_data)
                            if triggered:
                                # Mark as triggered to avoid duplicate notifications
                                self._triggered_alerts.add(a.id)
                                
                                # Update database - mark alert as triggered
                                try:
                                    self.alert_service.update_alert(
                                        a.id, 
                                        self.user_id,
                                        status=AlertStatus.TRIGGERED
                                    )
                                except Exception as e:
                                    logger.error(f"Failed to update alert status: {e}")
                                
                                # Emit signal to show notification
                                self.alert_triggered.emit(a.id, a.symbol, msg)
                    
                    time.sleep(1)  # Brief pause between symbols
                
            except Exception as e:
                logger.error(f"Demo monitor error: {e}")
            
            time.sleep(self._interval)
    
    def _check_alert(self, alert, price_data: dict) -> tuple:
        """Check if alert condition is met."""
        price = price_data['price']
        target = alert.target_value
        
        # Use $ for crypto/commodity, ₹ for Indian stocks
        from ..core.enums import AlertCondition, AssetType
        currency = "$" if alert.asset_type in (AssetType.CRYPTO, AssetType.COMMODITY) else "₹"
        
        if alert.condition == AlertCondition.PRICE_ABOVE:
            if price > target:
                return True, f"{alert.symbol} is ABOVE {currency}{target:,.2f}\nCurrent: {currency}{price:,.2f}"
        
        elif alert.condition == AlertCondition.PRICE_BELOW:
            if price < target:
                return True, f"{alert.symbol} is BELOW {currency}{target:,.2f}\nCurrent: {currency}{price:,.2f}"
        
        elif alert.condition == AlertCondition.PCT_CHANGE_UP:
            if price_data['change_pct'] >= target:
                return True, f"{alert.symbol} UP {price_data['change_pct']:.2f}%\nPrice: {currency}{price:,.2f}"
        
        elif alert.condition == AlertCondition.PCT_CHANGE_DOWN:
            if price_data['change_pct'] <= -target:
                return True, f"{alert.symbol} DOWN {abs(price_data['change_pct']):.2f}%\nPrice: {currency}{price:,.2f}"
        
        return False, ""


def run_gui():
    """Run the GUI application."""
    # Initialize database
    try:
        init_database()
    except Exception as e:
        logger.warning(f"Database init: {e}")
    
    app = QApplication(sys.argv)
    app.setApplicationName("Stock Alert Manager")
    
    window = AlertManagerGUI()
    window.show()
    
    sys.exit(app.exec())


# Alias for convenience
main = run_gui


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    run_gui()
