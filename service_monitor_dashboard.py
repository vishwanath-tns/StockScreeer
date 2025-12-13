#!/usr/bin/env python
"""
Real-time Service Monitor Dashboard
====================================
Shows live stats for Feed Launcher and Database Writer services
"""

import sys
import os
import threading
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment
load_dotenv()

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QGroupBox, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QFont

# Database
from sqlalchemy import create_engine, text

def get_db_engine():
    """Create database engine"""
    host = os.getenv('MYSQL_HOST', 'localhost')
    port = os.getenv('MYSQL_PORT', '3306')
    user = os.getenv('MYSQL_USER', 'root')
    password = os.getenv('MYSQL_PASSWORD', '')
    db = os.getenv('MYSQL_DB', 'dhan_trading')
    
    connection_string = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}"
    return create_engine(connection_string, echo=False, pool_pre_ping=True)

class MonitorStats(QObject):
    """Background stats collector"""
    stats_updated = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.stats = {}
        
    def collect_stats(self):
        """Collect stats in background"""
        try:
            # Try to import redis
            try:
                import redis
                r = redis.Redis(host='localhost', port=6379, decode_responses=True, socket_connect_timeout=2)
                r.ping()  # Test connection
                redis_available = True
            except:
                redis_available = False
                r = None
            
            # Connect to DB
            engine = get_db_engine()
            
            while self.running:
                try:
                    stats = {
                        'feed': self.get_feed_stats(r) if redis_available else self.get_feed_stats_fallback(),
                        'db': self.get_db_stats(engine),
                        'timestamp': datetime.now().strftime("%H:%M:%S")
                    }
                    
                    self.stats_updated.emit(stats)
                except Exception as e:
                    pass  # Continue even if one update fails
                
                time.sleep(2)  # Update every 2 seconds
                
        except Exception as e:
            print(f"Error in collect_stats: {e}")
    
    def get_feed_stats_fallback(self):
        """Fallback when Redis not available"""
        return {
            'status': 'CHECKING',
            'total_quotes': 'N/A',
            'last_update': 'N/A',
            'redis_stream': 'dhan:quotes'
        }
    
    def get_feed_stats(self, redis_conn):
        """Get Feed Launcher stats"""
        try:
            if redis_conn is None:
                return self.get_feed_stats_fallback()
            
            # Get info from Redis streams
            stream_info = redis_conn.xinfo_stream('dhan:quotes')
            quote_count = stream_info['last-generated-id']
            
            # Try to get last quote
            last_quote = redis_conn.xrevrange('dhan:quotes', count=1)
            last_quote_time = "NOW"
            if last_quote:
                last_quote_time = datetime.now().strftime("%H:%M:%S")
            
            return {
                'status': 'PUBLISHING',
                'total_quotes': quote_count if quote_count else 0,
                'last_update': last_quote_time,
                'redis_stream': 'dhan:quotes'
            }
        except Exception as e:
            return {
                'status': 'DISCONNECTED',
                'total_quotes': 'N/A',
                'last_update': 'N/A',
                'redis_stream': 'dhan:quotes'
            }
    
    def get_db_stats(self, engine):
        """Get Database Writer stats"""
        try:
            with engine.connect() as conn:
                # Total quotes
                result = conn.execute(text("SELECT COUNT(*) as count FROM dhan_fno_quotes"))
                total = result.fetchone()[0] if result.fetchone() else 0
                
                # Requery to get actual result
                result = conn.execute(text("SELECT COUNT(*) as count FROM dhan_fno_quotes"))
                row = result.fetchone()
                total = row[0] if row else 0
                
                # Last 1 minute
                one_min_ago = datetime.now() - timedelta(minutes=1)
                result = conn.execute(text("""
                    SELECT COUNT(*) as count FROM dhan_fno_quotes 
                    WHERE created_at > :time
                """), {"time": one_min_ago})
                row = result.fetchone()
                last_1min = row[0] if row else 0
                
                # Last 5 minutes
                five_min_ago = datetime.now() - timedelta(minutes=5)
                result = conn.execute(text("""
                    SELECT COUNT(*) as count FROM dhan_fno_quotes 
                    WHERE created_at > :time
                """), {"time": five_min_ago})
                row = result.fetchone()
                last_5min = row[0] if row else 0
                
                # Latest record
                result = conn.execute(text("""
                    SELECT created_at FROM dhan_fno_quotes 
                    ORDER BY created_at DESC LIMIT 1
                """))
                last_record = result.fetchone()
                last_write = last_record[0].strftime("%H:%M:%S") if last_record else "N/A"
                
                return {
                    'status': 'WRITING' if last_1min > 0 else 'IDLE',
                    'total_quotes': total,
                    'last_1min': last_1min,
                    'last_5min': last_5min,
                    'write_rate': last_1min,
                    'last_write': last_write
                }
        except Exception as e:
            return {
                'status': 'ERROR',
                'total_quotes': 0,
                'last_1min': 0,
                'last_5min': 0,
                'write_rate': 0,
                'last_write': 'N/A',
                'error': str(e)
            }
    
    def stop(self):
        """Stop collecting stats"""
        self.running = False


class ServiceMonitorDashboard(QMainWindow):
    """Real-time service monitor"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dhan Services - Real-time Monitor")
        self.setGeometry(100, 100, 1000, 500)
        
        # Stats collector
        self.monitor = MonitorStats()
        self.monitor.stats_updated.connect(self.update_dashboard)
        
        # Start stats collection in background
        stats_thread = threading.Thread(target=self.monitor.collect_stats, daemon=True)
        stats_thread.start()
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI"""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Real-time Service Monitor Dashboard")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Feed Launcher panel
        feed_panel = self.create_feed_panel()
        
        # DB Writer panel
        db_panel = self.create_db_panel()
        
        # Panels side by side
        panels_layout = QHBoxLayout()
        panels_layout.addWidget(feed_panel)
        panels_layout.addWidget(db_panel)
        layout.addLayout(panels_layout, 1)
        
        main_widget.setLayout(layout)
        
        # Store labels for updates
        self.feed_labels = {}
        self.db_labels = {}
    
    def create_feed_panel(self):
        """Create Feed Launcher panel"""
        group = QGroupBox("FNO Feed Launcher (Redis Publisher)")
        group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 12px; }")
        layout = QGridLayout()
        
        # Status
        layout.addWidget(QLabel("Status:"), 0, 0)
        self.feed_labels['status'] = QLabel("CHECKING")
        self.feed_labels['status'].setStyleSheet("color: orange; font-weight: bold; font-size: 11px;")
        layout.addWidget(self.feed_labels['status'], 0, 1)
        
        # Total quotes in Redis
        layout.addWidget(QLabel("Quotes in Redis:"), 1, 0)
        self.feed_labels['total'] = QLabel("0")
        self.feed_labels['total'].setFont(QFont("Arial", 12, QFont.Bold))
        self.feed_labels['total'].setStyleSheet("color: #4CAF50;")
        layout.addWidget(self.feed_labels['total'], 1, 1)
        
        # Last update
        layout.addWidget(QLabel("Last Update:"), 2, 0)
        self.feed_labels['last_update'] = QLabel("N/A")
        self.feed_labels['last_update'].setFont(QFont("Arial", 10))
        layout.addWidget(self.feed_labels['last_update'], 2, 1)
        
        layout.setRowStretch(3, 1)
        
        group.setLayout(layout)
        return group
    
    def create_db_panel(self):
        """Create DB Writer panel"""
        group = QGroupBox("FNO Database Writer (Redis Subscriber)")
        group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 12px; }")
        layout = QGridLayout()
        
        # Status
        layout.addWidget(QLabel("Status:"), 0, 0)
        self.db_labels['status'] = QLabel("IDLE")
        self.db_labels['status'].setStyleSheet("color: orange; font-weight: bold; font-size: 11px;")
        layout.addWidget(self.db_labels['status'], 0, 1)
        
        # Total quotes in DB
        layout.addWidget(QLabel("Total in Database:"), 1, 0)
        self.db_labels['total'] = QLabel("0")
        self.db_labels['total'].setFont(QFont("Arial", 12, QFont.Bold))
        self.db_labels['total'].setStyleSheet("color: #2196F3;")
        layout.addWidget(self.db_labels['total'], 1, 1)
        
        # Last 1 minute
        layout.addWidget(QLabel("Written (1 min):"), 2, 0)
        self.db_labels['last_1min'] = QLabel("0")
        self.db_labels['last_1min'].setFont(QFont("Arial", 11, QFont.Bold))
        self.db_labels['last_1min'].setStyleSheet("color: green;")
        layout.addWidget(self.db_labels['last_1min'], 2, 1)
        
        # Last 5 minutes
        layout.addWidget(QLabel("Written (5 min):"), 3, 0)
        self.db_labels['last_5min'] = QLabel("0")
        layout.addWidget(self.db_labels['last_5min'], 3, 1)
        
        # Last write time
        layout.addWidget(QLabel("Last Write:"), 4, 0)
        self.db_labels['last_write'] = QLabel("N/A")
        layout.addWidget(self.db_labels['last_write'], 4, 1)
        
        layout.setRowStretch(5, 1)
        
        group.setLayout(layout)
        return group
    
    def update_dashboard(self, stats):
        """Update dashboard with new stats"""
        try:
            # Update feed panel
            feed = stats['feed']
            self.feed_labels['status'].setText(feed['status'])
            if feed['status'] == 'PUBLISHING':
                self.feed_labels['status'].setStyleSheet("color: green; font-weight: bold; font-size: 11px;")
            else:
                self.feed_labels['status'].setStyleSheet("color: red; font-weight: bold; font-size: 11px;")
            
            total = feed['total_quotes']
            self.feed_labels['total'].setText(f"{total:,}" if isinstance(total, int) else str(total))
            self.feed_labels['last_update'].setText(feed['last_update'])
            
            # Update DB panel
            db = stats['db']
            self.db_labels['status'].setText(db['status'])
            if db['status'] == 'WRITING':
                self.db_labels['status'].setStyleSheet("color: green; font-weight: bold; font-size: 11px;")
            elif db['status'] == 'IDLE':
                self.db_labels['status'].setStyleSheet("color: orange; font-weight: bold; font-size: 11px;")
            else:
                self.db_labels['status'].setStyleSheet("color: red; font-weight: bold; font-size: 11px;")
            
            self.db_labels['total'].setText(f"{db['total_quotes']:,}" if isinstance(db['total_quotes'], int) else str(db['total_quotes']))
            self.db_labels['last_1min'].setText(f"{db['last_1min']} quotes" if isinstance(db['last_1min'], int) else str(db['last_1min']))
            self.db_labels['last_5min'].setText(f"{db['last_5min']} quotes" if isinstance(db['last_5min'], int) else str(db['last_5min']))
            self.db_labels['last_write'].setText(db['last_write'])
        except Exception as e:
            pass  # Silently ignore update errors
    
    def closeEvent(self, event):
        """Clean up on close"""
        self.monitor.stop()
        event.accept()


if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        dashboard = ServiceMonitorDashboard()
        dashboard.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Error starting dashboard: {e}")
        import traceback
        traceback.print_exc()

