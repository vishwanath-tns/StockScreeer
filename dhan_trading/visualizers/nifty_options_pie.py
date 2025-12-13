#!/usr/bin/env python
"""
NIFTY Options Strike Pie Chart Visualizer
==========================================
Displays pie charts for total buy/sell quantities for each NIFTY option strike.

Reads from Redis stream and looks up instrument info from database.
Shows only NIFTY Index Options (exchange_segment=6).

Features:
- One pie chart per strike price
- Shows Buy (green) vs Sell (red) quantities
- Auto-adjusts grid layout for all strikes
- Real-time updates from Redis

Usage:
    python -m dhan_trading.visualizers.nifty_options_pie
"""

import sys
import os
import time
import redis
import json
import math
import re
from datetime import datetime
from collections import defaultdict
from typing import Dict, Optional, Tuple

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QLabel, QScrollArea, QGridLayout, QFrame,
    QSizePolicy, QGroupBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QPainter, QColor, QPen, QBrush

import pyqtgraph as pg
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()

# Exchange segment for NIFTY Index Options
OPTIDX_SEGMENT = 6


def load_nifty_futures_security_id(expiry_date) -> Optional[int]:
    """
    Load the NIFTY futures security_id for the given expiry date.
    This is used to track the futures LTP for ATM strike calculation.
    """
    try:
        from sqlalchemy import create_engine, text
        from urllib.parse import quote_plus
        
        pw = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
        engine = create_engine(
            f"mysql+pymysql://root:{pw}@localhost:3306/dhan_trading",
            pool_pre_ping=True
        )
        
        with engine.connect() as conn:
            # Find NIFTY futures for the same month as options expiry
            result = conn.execute(text("""
                SELECT security_id, symbol, expiry_date
                FROM dhan_instruments 
                WHERE underlying_symbol = 'NIFTY'
                  AND strike_price IS NULL
                  AND option_type IS NULL
                  AND expiry_date >= CURDATE()
                ORDER BY expiry_date
                LIMIT 1
            """))
            
            row = result.fetchone()
            if row:
                sec_id = int(row[0])
                symbol = row[1]
                exp_date = row[2]
                print(f"NIFTY Futures: {symbol} (ID: {sec_id}, Expiry: {exp_date})")
                return sec_id
            else:
                print("No NIFTY futures found!")
                return None
                
    except Exception as e:
        print(f"Could not load NIFTY futures: {e}")
        return None


def get_nifty_futures_ltp(security_id: int) -> Optional[float]:
    """
    Get the last traded price of NIFTY futures from database.
    Looks up the latest quote for the given security_id.
    """
    if not security_id:
        return None
        
    try:
        from sqlalchemy import create_engine, text
        from urllib.parse import quote_plus
        
        pw = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
        engine = create_engine(
            f"mysql+pymysql://root:{pw}@localhost:3306/dhan_trading",
            pool_pre_ping=True
        )
        
        with engine.connect() as conn:
            # Try to get LTP from fno_quotes table
            result = conn.execute(text("""
                SELECT ltp, updated_at
                FROM fno_quotes 
                WHERE security_id = :sec_id
                ORDER BY updated_at DESC
                LIMIT 1
            """), {"sec_id": security_id})
            
            row = result.fetchone()
            if row and row[0]:
                ltp = float(row[0])
                print(f"NIFTY Futures LTP from DB: {ltp}")
                return ltp
            
            print("No NIFTY futures LTP found in database")
            return None
                
    except Exception as e:
        print(f"Could not get NIFTY futures LTP: {e}")
        return None


def load_nifty_options_map() -> Tuple[Dict[int, Tuple[int, str]], Optional[datetime]]:
    """
    Load NIFTY options from database: security_id -> (strike, option_type).
    Only loads instruments for the NEAREST EXPIRY.
    
    Returns:
        (instrument_map, nearest_expiry_date)
    """
    instrument_map = {}
    nearest_expiry = None
    
    try:
        from sqlalchemy import create_engine, text
        from urllib.parse import quote_plus
        
        pw = quote_plus(os.getenv('MYSQL_PASSWORD', ''))
        engine = create_engine(
            f"mysql+pymysql://root:{pw}@localhost:3306/dhan_trading",
            pool_pre_ping=True
        )
        
        with engine.connect() as conn:
            # First, find the nearest expiry date for NIFTY options
            expiry_result = conn.execute(text("""
                SELECT MIN(expiry_date) as nearest_expiry
                FROM dhan_instruments 
                WHERE underlying_symbol = 'NIFTY'
                  AND strike_price IS NOT NULL
                  AND option_type IN ('CE', 'PE')
                  AND expiry_date >= CURDATE()
            """))
            
            row = expiry_result.fetchone()
            if row and row[0]:
                nearest_expiry = row[0]
                print(f"Nearest NIFTY expiry: {nearest_expiry}")
            else:
                print("No future NIFTY expiry dates found!")
                return instrument_map, None
            
            # Now load only instruments for the nearest expiry
            result = conn.execute(text("""
                SELECT security_id, strike_price, option_type, symbol
                FROM dhan_instruments 
                WHERE underlying_symbol = 'NIFTY'
                  AND strike_price IS NOT NULL
                  AND option_type IN ('CE', 'PE')
                  AND expiry_date = :expiry
            """), {"expiry": nearest_expiry})
            
            for row in result:
                sec_id = int(row[0])
                strike = int(row[1]) if row[1] else 0
                opt_type = row[2]
                
                if strike > 0:
                    instrument_map[sec_id] = (strike, opt_type)
        
        print(f"Loaded {len(instrument_map)} NIFTY options for expiry {nearest_expiry}")
        
    except Exception as e:
        print(f"Could not load instruments from database: {e}")
        import traceback
        traceback.print_exc()
    
    return instrument_map, nearest_expiry


class PieChartWidget(QWidget):
    """Custom pie chart widget using QPainter."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.buy_qty = 0
        self.sell_qty = 0
        self.strike = 0
        self.option_type = ""  # CE or PE
        self.ltp = 0.0
        self.setMinimumSize(150, 180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    
    def set_data(self, strike: int, option_type: str, buy_qty: int, sell_qty: int, ltp: float = 0):
        """Update pie chart data."""
        self.strike = strike
        self.option_type = option_type
        self.buy_qty = buy_qty
        self.sell_qty = sell_qty
        self.ltp = ltp
        self.update()
    
    def paintEvent(self, event):
        """Draw the pie chart."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Get widget dimensions
        w = self.width()
        h = self.height()
        
        # Calculate pie dimensions (leave space for labels)
        pie_size = min(w - 20, h - 60)
        pie_x = (w - pie_size) // 2
        pie_y = 10
        
        total = self.buy_qty + self.sell_qty
        
        if total > 0:
            buy_angle = int(360 * 16 * self.buy_qty / total)  # Qt uses 1/16th degree
            sell_angle = 360 * 16 - buy_angle
            
            # Draw sell portion (red) - start from top
            painter.setBrush(QBrush(QColor(255, 68, 68)))
            painter.setPen(QPen(QColor(200, 50, 50), 1))
            painter.drawPie(pie_x, pie_y, pie_size, pie_size, 90 * 16, -sell_angle)
            
            # Draw buy portion (green)
            painter.setBrush(QBrush(QColor(0, 255, 0)))
            painter.setPen(QPen(QColor(0, 200, 0), 1))
            painter.drawPie(pie_x, pie_y, pie_size, pie_size, 90 * 16 - sell_angle, -buy_angle)
        else:
            # Empty pie - gray
            painter.setBrush(QBrush(QColor(80, 80, 80)))
            painter.setPen(QPen(QColor(100, 100, 100), 1))
            painter.drawEllipse(pie_x, pie_y, pie_size, pie_size)
        
        # Draw labels
        painter.setPen(QPen(QColor(255, 255, 255)))
        font = QFont("Arial", 9, QFont.Bold)
        painter.setFont(font)
        
        # Strike and type label
        label_y = pie_y + pie_size + 15
        color = QColor(0, 200, 255) if self.option_type == "CE" else QColor(255, 150, 0)
        painter.setPen(QPen(color))
        painter.drawText(0, label_y, w, 20, Qt.AlignCenter, 
                        f"{self.strike} {self.option_type}")
        
        # LTP
        painter.setPen(QPen(QColor(255, 215, 0)))
        font.setPointSize(8)
        painter.setFont(font)
        painter.drawText(0, label_y + 18, w, 16, Qt.AlignCenter, 
                        f"₹{self.ltp:.2f}")
        
        # Buy/Sell percentages
        if total > 0:
            buy_pct = 100 * self.buy_qty / total
            sell_pct = 100 * self.sell_qty / total
            
            font.setPointSize(7)
            painter.setFont(font)
            painter.setPen(QPen(QColor(0, 255, 0)))
            painter.drawText(0, label_y + 34, w//2, 14, Qt.AlignCenter, 
                            f"B:{buy_pct:.0f}%")
            painter.setPen(QPen(QColor(255, 68, 68)))
            painter.drawText(w//2, label_y + 34, w//2, 14, Qt.AlignCenter, 
                            f"S:{sell_pct:.0f}%")


class StrikeData:
    """Store data for a single strike."""
    
    def __init__(self):
        self.ce_buy_qty = 0
        self.ce_sell_qty = 0
        self.ce_ltp = 0.0
        self.ce_security_id = None
        
        self.pe_buy_qty = 0
        self.pe_sell_qty = 0
        self.pe_ltp = 0.0
        self.pe_security_id = None
        
        self.last_update = 0


class RedisQuoteReader(QThread):
    """Background thread to read quotes from Redis."""
    
    quote_received = pyqtSignal(dict)
    connection_status = pyqtSignal(bool, str)
    history_loaded = pyqtSignal(int)  # Emits count of historical quotes loaded
    
    # Instrument map reference for filtering during history load
    instrument_map: Dict[int, Tuple[int, str]] = {}
    futures_security_id: Optional[int] = None  # NIFTY futures security_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._client = None
        self._pubsub = None
        self._stream_name = 'dhan:quotes:stream'
    
    def run(self):
        """Main thread loop."""
        self._running = True
        
        try:
            self._client = redis.Redis(
                host='localhost',
                port=6379,
                decode_responses=True
            )
            self._client.ping()
            self.connection_status.emit(True, "Connected to Redis")
            
            # First, load historical data from the stream
            self._load_historical_data()
            
            # Then subscribe to pub/sub for real-time updates
            self._pubsub = self._client.pubsub()
            self._pubsub.subscribe('dhan:quotes')
            
            while self._running:
                message = self._pubsub.get_message(timeout=0.1)
                if message and message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        self.quote_received.emit(data)
                    except json.JSONDecodeError:
                        pass
                        
        except redis.ConnectionError as e:
            self.connection_status.emit(False, f"Redis connection failed: {e}")
        except Exception as e:
            self.connection_status.emit(False, f"Error: {e}")
        finally:
            if self._pubsub:
                self._pubsub.unsubscribe()
            self._running = False
    
    def _load_historical_data(self):
        """Load historical quotes from Redis stream - get latest quote per security_id.
        
        Reads from the END of the stream (most recent first) to quickly get
        the latest state of each instrument.
        """
        try:
            # Get stream length
            stream_len = self._client.xlen(self._stream_name)
            print(f"Redis stream '{self._stream_name}' has {stream_len:,} messages")
            
            if stream_len == 0:
                self.history_loaded.emit(0)
                return
            
            # Dictionary to store latest quote per security_id
            # Since we read from end, first occurrence IS the latest
            latest_quotes: Dict[int, dict] = {}
            
            count = 0
            last_id = '+'  # Start from end (newest)
            batch_size = 5000
            
            # Debug: check what segments are in the stream (sample only)
            segment_counts = {}
            sample_security_ids = set()
            
            # Read from END using XREVRANGE (reverse order - newest first)
            while self._running:
                # Read batch of messages in REVERSE order (newest first)
                messages = self._client.xrevrange(
                    self._stream_name, 
                    max=last_id, 
                    min='-', 
                    count=batch_size
                )
                
                if not messages:
                    break
                
                # Track last message ID for next batch (before the loop)
                batch_last_id = None
                
                for msg_id, data in messages:
                    # Skip the first message if we're continuing from previous batch
                    if last_id != '+' and msg_id == last_id:
                        continue
                    
                    count += 1
                    batch_last_id = msg_id  # Update to this message's ID
                    
                    # Convert string values to proper types
                    try:
                        exchange_segment = int(data.get('exchange_segment', 0))
                        security_id = int(data.get('security_id', 0))
                        
                        # Count segments for debugging (first 10000 only)
                        if count <= 10000:
                            segment_counts[exchange_segment] = segment_counts.get(exchange_segment, 0) + 1
                            if len(sample_security_ids) < 20:
                                sample_security_ids.add(security_id)
                        
                        # Check if this is the NIFTY futures or an option in our map
                        is_futures = (security_id == self.futures_security_id)
                        is_option = (security_id in self.instrument_map)
                        
                        if not is_futures and not is_option:
                            continue
                        
                        # Since we read newest first, only store if not already seen
                        if security_id in latest_quotes:
                            continue
                        
                        quote_data = {
                            'security_id': security_id,
                            'exchange_segment': exchange_segment,
                            'ltp': float(data.get('ltp', 0)),
                            'total_buy_qty': int(float(data.get('total_buy_qty', 0))),
                            'total_sell_qty': int(float(data.get('total_sell_qty', 0))),
                            'volume': int(float(data.get('volume', 0))),
                            'open_interest': int(float(data.get('open_interest', 0))),
                        }
                        
                        latest_quotes[security_id] = quote_data
                        
                    except (ValueError, TypeError) as e:
                        continue
                
                # Update last_id for next batch (go backward from oldest in this batch)
                if batch_last_id:
                    last_id = batch_last_id
                
                # Stop conditions:
                # 1. If we got less than batch_size, we've read everything
                if len(messages) < batch_size:
                    break
                
                # 2. Max iterations to prevent infinite loop
                if count >= stream_len:
                    break
                
                # 3. Early exit if we found enough NIFTY options
                if len(latest_quotes) >= 100 and count > 50000:
                    print(f"Found {len(latest_quotes)} NIFTY options, stopping early")
                    break
                
                # Progress update
                if count % 50000 == 0:
                    print(f"Scanned {count:,} quotes (from end), found {len(latest_quotes)} NIFTY options...")
            
            print(f"Scanned {count:,} total quotes")
            print(f"Exchange segments in sample: {segment_counts}")
            print(f"Sample security_ids from stream: {sorted(list(sample_security_ids))[:10]}")
            print(f"Unique NIFTY instruments with quotes: {len(latest_quotes)}")
            
            # Debug: print first few from instrument_map
            print(f"Sample from instrument_map: {list(self.instrument_map.keys())[:10]}")
            
            # Now emit all the latest quotes
            for quote_data in latest_quotes.values():
                self.quote_received.emit(quote_data)
            
            self.history_loaded.emit(len(latest_quotes))
            
        except Exception as e:
            print(f"Error loading historical data: {e}")
            import traceback
            traceback.print_exc()
            self.history_loaded.emit(0)
    
    def stop(self):
        """Stop the reader thread."""
        self._running = False
        self.wait(2000)


class NiftyOptionsPieVisualizer(QMainWindow):
    """Main visualizer window."""
    
    def __init__(self):
        super().__init__()
        
        # Load NIFTY options map from database at startup (nearest expiry only)
        self.instrument_map, self.expiry_date = load_nifty_options_map()
        
        # Load NIFTY futures security_id for tracking LTP
        self.futures_security_id = load_nifty_futures_security_id(self.expiry_date)
        self.futures_ltp = 0.0  # Will be updated from Redis
        
        # Get initial spot price from NIFTY futures LTP in database
        initial_ltp = get_nifty_futures_ltp(self.futures_security_id)
        if initial_ltp and initial_ltp > 0:
            self.spot_price = round(initial_ltp / 50) * 50  # Round to nearest 50
            self.futures_ltp = initial_ltp
            print(f"Initial spot price from NIFTY Futures LTP: {self.spot_price}")
        else:
            self.spot_price = 24500  # Default fallback
            print(f"Using default spot price: {self.spot_price}")
        
        expiry_str = self.expiry_date.strftime('%d-%b-%Y') if self.expiry_date else 'Unknown'
        self.setWindowTitle(f"NIFTY Options - Buy/Sell Pressure by Strike (Expiry: {expiry_str})")
        self.setGeometry(100, 100, 1200, 900)
        
        # Strikes range configuration
        self.strikes_above = 10
        self.strikes_below = 10
        self.strike_step = 50  # NIFTY strike interval
        self.auto_update_spot = True  # Auto-update spot from futures LTP
        
        # Data storage: strike -> StrikeData
        self.strikes: Dict[int, StrikeData] = defaultdict(StrikeData)
        
        # Pie chart widgets: strike -> (ce_widget, pe_widget, strike_label)
        self.pie_widgets: Dict[int, Tuple[PieChartWidget, PieChartWidget, QLabel]] = {}
        
        # Track displayed strikes for cleanup
        self.displayed_strikes: set = set()
        
        # Stats
        self.quote_count = 0
        self.nifty_quote_count = 0
        self.historical_loaded = 0
        
        # Quote reader - pass instrument map for filtering
        self.quote_reader = RedisQuoteReader()
        self.quote_reader.instrument_map = self.instrument_map  # Share the instrument map
        self.quote_reader.futures_security_id = self.futures_security_id  # Track futures too
        self.quote_reader.quote_received.connect(self.on_quote_received)
        self.quote_reader.connection_status.connect(self.on_connection_status)
        self.quote_reader.history_loaded.connect(self.on_history_loaded)
        
        # Setup UI
        self._setup_ui()
        
        # Start Redis reader
        self.quote_reader.start()
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_charts)
        self.update_timer.start(500)  # Update every 500ms
        
        print(f"Loaded {len(self.instrument_map)} NIFTY options instruments")
        print("Loading historical quotes from Redis stream...")
    
    def _setup_ui(self):
        """Setup the user interface."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Top controls
        controls = QHBoxLayout()
        
        # Expiry info
        expiry_str = self.expiry_date.strftime('%d-%b-%Y') if self.expiry_date else 'Unknown'
        info_label = QLabel(f"NIFTY Options - Expiry: {expiry_str}")
        info_label.setStyleSheet("color: #00d4ff; font-weight: bold; font-size: 14px;")
        controls.addWidget(info_label)
        
        controls.addSpacing(20)
        
        # Futures LTP label (auto-updated)
        if self.futures_ltp > 0:
            self.futures_label = QLabel(f"FUT: {self.futures_ltp:.2f}")
        else:
            self.futures_label = QLabel("FUT: --")
        self.futures_label.setStyleSheet("color: #00ff00; font-weight: bold; font-size: 14px;")
        controls.addWidget(self.futures_label)
        
        controls.addSpacing(10)
        
        # Auto checkbox
        from PyQt5.QtWidgets import QCheckBox
        self.auto_checkbox = QCheckBox("Auto")
        self.auto_checkbox.setChecked(True)
        self.auto_checkbox.setStyleSheet("color: #aaa;")
        self.auto_checkbox.toggled.connect(self.on_auto_toggled)
        controls.addWidget(self.auto_checkbox)
        
        # Spot price input (manual override)
        spot_label = QLabel("Spot:")
        spot_label.setStyleSheet("color: #ffff00; font-weight: bold;")
        controls.addWidget(spot_label)
        
        from PyQt5.QtWidgets import QSpinBox
        self.spot_spinbox = QSpinBox()
        self.spot_spinbox.setRange(10000, 50000)
        self.spot_spinbox.setSingleStep(50)
        self.spot_spinbox.setValue(self.spot_price)
        self.spot_spinbox.setEnabled(False)  # Disabled when auto is on
        self.spot_spinbox.setStyleSheet("""
            QSpinBox {
                background-color: #333;
                color: #ffff00;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #555;
                padding: 3px;
                min-width: 80px;
            }
            QSpinBox:disabled {
                color: #888;
            }
        """)
        self.spot_spinbox.valueChanged.connect(self.on_spot_changed)
        controls.addWidget(self.spot_spinbox)
        
        controls.addStretch()
        
        # Stats
        self.status_label = QLabel("Connecting...")
        self.status_label.setStyleSheet("color: orange; font-weight: bold;")
        controls.addWidget(self.status_label)
        
        self.count_label = QLabel("Quotes: 0 | NIFTY Opts: 0 | Strikes: 0")
        controls.addWidget(self.count_label)
        
        layout.addLayout(controls)
        
        # Legend with layout indicator
        legend = QHBoxLayout()
        
        # Left side - CALLS
        call_label = QLabel("◄ CALLS (CE)")
        call_label.setStyleSheet("color: #00d4ff; font-weight: bold; font-size: 12px;")
        legend.addWidget(call_label)
        
        legend.addStretch()
        
        buy_legend = QLabel("● Buy")
        buy_legend.setStyleSheet("color: #00ff00; font-weight: bold;")
        legend.addWidget(buy_legend)
        
        sell_legend = QLabel("● Sell")
        sell_legend.setStyleSheet("color: #ff4444; font-weight: bold;")
        legend.addWidget(sell_legend)
        
        legend.addStretch()
        
        # Right side - PUTS
        put_label = QLabel("PUTS (PE) ►")
        put_label.setStyleSheet("color: #ffa500; font-weight: bold; font-size: 12px;")
        legend.addWidget(put_label)
        
        layout.addLayout(legend)
        
        # Scrollable grid for pie charts
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(10)
        
        scroll.setWidget(self.grid_widget)
        layout.addWidget(scroll)
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e1e;
                color: white;
            }
            QScrollArea {
                border: 1px solid #333;
            }
            QComboBox {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                padding: 5px;
            }
            QLabel {
                color: white;
            }
        """)
    
    def on_auto_toggled(self, checked: bool):
        """Handle auto-update checkbox toggle."""
        self.auto_update_spot = checked
        self.spot_spinbox.setEnabled(not checked)
        if checked and self.futures_ltp > 0:
            # Update spot from current futures LTP
            new_spot = round(self.futures_ltp / self.strike_step) * self.strike_step
            if new_spot != self.spot_price:
                self.spot_price = new_spot
                self.spot_spinbox.setValue(new_spot)
                self.rebuild_grid()
    
    def on_quote_received(self, data: dict):
        """Handle incoming quote from Redis."""
        self.quote_count += 1
        
        security_id = data.get('security_id')
        if not security_id:
            return
        
        security_id = int(security_id)
        
        # Check if this is the NIFTY futures quote
        if security_id == self.futures_security_id:
            ltp = float(data.get('ltp', 0))
            if ltp > 0:
                self.futures_ltp = ltp
                self.futures_label.setText(f"FUT: {ltp:.2f}")
                
                # Auto-update spot price if enabled
                if self.auto_update_spot:
                    new_spot = round(ltp / self.strike_step) * self.strike_step
                    if new_spot != self.spot_price:
                        self.spot_price = new_spot
                        self.spot_spinbox.setValue(new_spot)
                        self.rebuild_grid()
            return
        
        # Look up instrument from pre-loaded map (already filtered for NIFTY options)
        if security_id not in self.instrument_map:
            return
        
        strike, opt_type = self.instrument_map[security_id]
        
        self.nifty_quote_count += 1
        
        # Get quote data
        buy_qty = int(data.get('total_buy_qty', 0))
        sell_qty = int(data.get('total_sell_qty', 0))
        ltp = float(data.get('ltp', 0))
        
        # Update strike data
        strike_data = self.strikes[strike]
        strike_data.last_update = time.time()
        
        if opt_type == 'CE':
            strike_data.ce_buy_qty = buy_qty
            strike_data.ce_sell_qty = sell_qty
            strike_data.ce_ltp = ltp
            strike_data.ce_security_id = security_id
        else:  # PE
            strike_data.pe_buy_qty = buy_qty
            strike_data.pe_sell_qty = sell_qty
            strike_data.pe_ltp = ltp
            strike_data.pe_security_id = security_id
    
    def on_connection_status(self, connected: bool, message: str):
        """Handle connection status updates."""
        if connected:
            self.status_label.setText("● Connected (loading history...)")
            self.status_label.setStyleSheet("color: orange; font-weight: bold;")
        else:
            self.status_label.setText(f"● {message}")
            self.status_label.setStyleSheet("color: #ff4444; font-weight: bold;")
    
    def on_history_loaded(self, count: int):
        """Handle historical data load completion."""
        self.historical_loaded = count
        self.status_label.setText(f"● Connected (history: {count:,})")
        self.status_label.setStyleSheet("color: #00ff00; font-weight: bold;")
        # Force immediate chart update
        self.update_charts()
    
    def on_spot_changed(self, value: int):
        """Handle spot price change."""
        self.spot_price = value
        self.rebuild_grid()
    
    def get_atm_strike(self) -> int:
        """Get ATM strike based on spot price."""
        # Round to nearest strike step
        return round(self.spot_price / self.strike_step) * self.strike_step
    
    def get_visible_strikes(self) -> list:
        """Get list of strikes to display (10 above and 10 below ATM)."""
        atm = self.get_atm_strike()
        
        # Generate strikes from ATM - 10*step to ATM + 10*step
        strikes = []
        for i in range(-self.strikes_below, self.strikes_above + 1):
            strike = atm + (i * self.strike_step)
            strikes.append(strike)
        
        return strikes
    
    def rebuild_grid(self):
        """Rebuild the entire grid with current visible strikes."""
        # Clear existing widgets
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.pie_widgets.clear()
        self.displayed_strikes.clear()
        
        # Get visible strikes
        visible_strikes = self.get_visible_strikes()
        atm = self.get_atm_strike()
        
        for row_idx, strike in enumerate(visible_strikes):
            # Ensure strike data exists
            if strike not in self.strikes:
                self.strikes[strike] = StrikeData()
            
            strike_data = self.strikes[strike]
            
            ce_widget = PieChartWidget()
            pe_widget = PieChartWidget()
            
            # Strike label in the middle - highlight ATM
            strike_label = QLabel(str(strike))
            is_atm = (strike == atm)
            strike_label.setStyleSheet(f"""
                color: {'#00ff00' if is_atm else '#ffff00'}; 
                font-weight: bold; 
                font-size: {'18px' if is_atm else '14px'};
                background-color: {'#004400' if is_atm else '#333'};
                padding: 5px 10px;
                border-radius: 5px;
                border: {'2px solid #00ff00' if is_atm else 'none'};
            """)
            strike_label.setAlignment(Qt.AlignCenter)
            strike_label.setMinimumWidth(80)
            
            self.pie_widgets[strike] = (ce_widget, pe_widget, strike_label)
            self.displayed_strikes.add(strike)
            
            # Grid layout: CE (col 0) | Strike Label (col 1) | PE (col 2)
            self.grid_layout.addWidget(ce_widget, row_idx, 0)
            self.grid_layout.addWidget(strike_label, row_idx, 1, Qt.AlignCenter)
            self.grid_layout.addWidget(pe_widget, row_idx, 2)
            
            # Update with current data
            ce_widget.set_data(
                strike, "CE",
                strike_data.ce_buy_qty,
                strike_data.ce_sell_qty,
                strike_data.ce_ltp
            )
            pe_widget.set_data(
                strike, "PE",
                strike_data.pe_buy_qty,
                strike_data.pe_sell_qty,
                strike_data.pe_ltp
            )
    
    def update_charts(self):
        """Update all pie charts."""
        # Update stats label
        atm = self.get_atm_strike()
        self.count_label.setText(
            f"ATM: {atm} | Quotes: {self.quote_count:,} | NIFTY Opts: {self.nifty_quote_count:,} | Strikes: {len(self.strikes)}"
        )
        
        if not self.strikes:
            return
        
        # Build grid if not yet built
        if not self.pie_widgets:
            self.rebuild_grid()
            return
        
        # Update only visible strikes
        for strike in self.displayed_strikes:
            if strike not in self.pie_widgets:
                continue
            
            strike_data = self.strikes.get(strike)
            if not strike_data:
                continue
            
            ce_widget, pe_widget, _ = self.pie_widgets[strike]
            
            # Update CE pie (left side)
            ce_widget.set_data(
                strike, "CE",
                strike_data.ce_buy_qty,
                strike_data.ce_sell_qty,
                strike_data.ce_ltp
            )
            
            # Update PE pie (right side)
            pe_widget.set_data(
                strike, "PE",
                strike_data.pe_buy_qty,
                strike_data.pe_sell_qty,
                strike_data.pe_ltp
            )
    
    def closeEvent(self, event):
        """Handle window close."""
        self.quote_reader.stop()
        self.update_timer.stop()
        event.accept()


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = NiftyOptionsPieVisualizer()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
