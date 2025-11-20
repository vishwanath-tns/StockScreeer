#!/usr/bin/env python3
"""
Historical Planetary Data Collector & Browser
Collects planetary positions for every minute from 2024-01-01 to 2026-01-01
Stores in database and provides browsing interface

Features:
1. Historical data collection (every minute for 2 years)
2. Database storage with optimized schema
3. Date/time picker browser interface
4. Progress tracking and resume capability
5. Data validation and error handling
"""

import sys
import os
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import threading
import time
from pathlib import Path

# Add tools to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'tools'))

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    from tkcalendar import DateEntry
    import pandas as pd
    from pyjhora_calculator import ProfessionalAstrologyCalculator
except ImportError as e:
    print(f"Import error: {e}")
    print("Please install: pip install tkcalendar pandas")
    sys.exit(1)

class HistoricalDataCollector:
    """
    Collects historical planetary data for every minute from 2024-01-01 to 2026-01-01
    """
    
    def __init__(self, db_path: str = "historical_planetary_data.db"):
        self.db_path = db_path
        self.calculator = ProfessionalAstrologyCalculator()
        self.start_date = datetime(2024, 1, 1, 0, 0, 0)
        self.end_date = datetime(2026, 1, 1, 0, 0, 0)
        self.total_minutes = int((self.end_date - self.start_date).total_seconds() / 60)
        self.setup_database()
        
    def setup_database(self):
        """Setup SQLite database with optimized schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create main table for planetary positions
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS planetary_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME UNIQUE NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            day INTEGER NOT NULL,
            hour INTEGER NOT NULL,
            minute INTEGER NOT NULL,
            
            -- Sun
            sun_longitude REAL NOT NULL,
            sun_sign TEXT NOT NULL,
            sun_degree_in_sign REAL NOT NULL,
            sun_sign_number INTEGER NOT NULL,
            
            -- Moon
            moon_longitude REAL NOT NULL,
            moon_sign TEXT NOT NULL,
            moon_degree_in_sign REAL NOT NULL,
            moon_sign_number INTEGER NOT NULL,
            
            -- Mars
            mars_longitude REAL NOT NULL,
            mars_sign TEXT NOT NULL,
            mars_degree_in_sign REAL NOT NULL,
            mars_sign_number INTEGER NOT NULL,
            
            -- Mercury
            mercury_longitude REAL NOT NULL,
            mercury_sign TEXT NOT NULL,
            mercury_degree_in_sign REAL NOT NULL,
            mercury_sign_number INTEGER NOT NULL,
            
            -- Jupiter
            jupiter_longitude REAL NOT NULL,
            jupiter_sign TEXT NOT NULL,
            jupiter_degree_in_sign REAL NOT NULL,
            jupiter_sign_number INTEGER NOT NULL,
            
            -- Venus
            venus_longitude REAL NOT NULL,
            venus_sign TEXT NOT NULL,
            venus_degree_in_sign REAL NOT NULL,
            venus_sign_number INTEGER NOT NULL,
            
            -- Saturn
            saturn_longitude REAL NOT NULL,
            saturn_sign TEXT NOT NULL,
            saturn_degree_in_sign REAL NOT NULL,
            saturn_sign_number INTEGER NOT NULL,
            
            -- Rahu
            rahu_longitude REAL NOT NULL,
            rahu_sign TEXT NOT NULL,
            rahu_degree_in_sign REAL NOT NULL,
            rahu_sign_number INTEGER NOT NULL,
            
            -- Ketu
            ketu_longitude REAL NOT NULL,
            ketu_sign TEXT NOT NULL,
            ketu_degree_in_sign REAL NOT NULL,
            ketu_sign_number INTEGER NOT NULL,
            
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create indexes for fast queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON planetary_positions(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_date ON planetary_positions(year, month, day)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_hour ON planetary_positions(year, month, day, hour)')
        
        # Create progress tracking table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS collection_progress (
            id INTEGER PRIMARY KEY,
            last_processed_timestamp DATETIME,
            total_processed INTEGER DEFAULT 0,
            total_minutes INTEGER,
            start_time DATETIME,
            estimated_completion DATETIME,
            status TEXT DEFAULT 'not_started'
        )
        ''')
        
        # Initialize progress if not exists
        cursor.execute('SELECT COUNT(*) FROM collection_progress')
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
            INSERT INTO collection_progress (last_processed_timestamp, total_minutes, start_time, status)
            VALUES (?, ?, ?, ?)
            ''', (self.start_date, self.total_minutes, datetime.now(), 'ready'))
        
        conn.commit()
        conn.close()
        print(f"✅ Database setup complete: {self.db_path}")
        print(f"📊 Total minutes to process: {self.total_minutes:,}")
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current collection progress"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM collection_progress ORDER BY id DESC LIMIT 1')
            progress = cursor.fetchone()
            
            if progress:
                # Convert string timestamps to datetime objects safely
                last_timestamp = progress[1]
                if isinstance(last_timestamp, str):
                    try:
                        last_timestamp = datetime.fromisoformat(last_timestamp)
                    except:
                        last_timestamp = self.start_date
                
                start_time = progress[4]
                if isinstance(start_time, str):
                    try:
                        start_time = datetime.fromisoformat(start_time)
                    except:
                        start_time = datetime.now()
                
                return {
                    'last_timestamp': last_timestamp,
                    'total_processed': progress[2] or 0,
                    'total_minutes': progress[3] or self.total_minutes,
                    'start_time': start_time,
                    'estimated_completion': progress[5],
                    'status': progress[6] or 'not_started'
                }
        except Exception as e:
            print(f"Warning: Error reading progress: {e}")
        finally:
            conn.close()
        
        return {'status': 'not_started', 'last_timestamp': self.start_date, 'total_processed': 0}
    
    def update_progress(self, timestamp: datetime, processed_count: int):
        """Update collection progress"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calculate estimated completion safely
            estimated_completion = None
            if processed_count > 100:  # Wait for some processing before estimating
                try:
                    progress = self.get_progress()
                    start_time = progress.get('start_time')
                    if isinstance(start_time, datetime):
                        elapsed = (datetime.now() - start_time).total_seconds()
                        if elapsed > 0:
                            rate = processed_count / elapsed  # records per second
                            remaining = self.total_minutes - processed_count
                            if rate > 0:
                                estimated_seconds = remaining / rate
                                estimated_completion = datetime.now() + timedelta(seconds=estimated_seconds)
                except Exception as e:
                    print(f"Warning: Could not calculate ETA: {e}")
            
            cursor.execute('''
            UPDATE collection_progress 
            SET last_processed_timestamp = ?, total_processed = ?, estimated_completion = ?, status = ?
            WHERE id = (SELECT MAX(id) FROM collection_progress)
            ''', (timestamp.isoformat(), processed_count, 
                  estimated_completion.isoformat() if estimated_completion else None, 'running'))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Warning: Could not update progress: {e}")
    
    def collect_historical_data(self, progress_callback=None, resume=True):
        """
        Collect historical planetary data for every minute
        """
        print(f"🚀 Starting historical data collection...")
        print(f"📅 Period: {self.start_date} to {self.end_date}")
        
        # Get resume point if requested
        start_point = self.start_date
        processed_count = 0
        
        if resume:
            progress = self.get_progress()
            if progress.get('status') == 'running' and progress.get('last_timestamp'):
                last_ts = progress['last_timestamp']
                if isinstance(last_ts, str):
                    try:
                        last_ts = datetime.fromisoformat(last_ts)
                    except:
                        last_ts = self.start_date
                elif isinstance(last_ts, datetime):
                    pass  # Already datetime
                else:
                    last_ts = self.start_date
                
                start_point = last_ts + timedelta(minutes=1)
                processed_count = progress.get('total_processed', 0)
                print(f"🔄 Resuming from: {start_point}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        current_time = start_point
        batch_size = 100  # Process in batches for better performance
        batch_data = []
        
        try:
            while current_time < self.end_date:
                try:
                    # Get planetary positions for current time
                    positions = self.calculator.get_planetary_positions(current_time)
                    
                    # Prepare data for insertion
                    row_data = [
                        current_time.isoformat(),
                        current_time.year,
                        current_time.month,
                        current_time.day,
                        current_time.hour,
                        current_time.minute
                    ]
                    
                    # Add planetary data
                    planets = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']
                    for planet in planets:
                        if planet in positions:
                            data = positions[planet]
                            row_data.extend([
                                data['longitude'],
                                data['sign'],
                                data['degree_in_sign'],
                                data['sign_number']
                            ])
                        else:
                            # Fallback for missing data
                            row_data.extend([0.0, 'Unknown', 0.0, 0])
                    
                    batch_data.append(tuple(row_data))
                    processed_count += 1
                    
                    # Insert batch when full
                    if len(batch_data) >= batch_size:
                        self.insert_batch(cursor, batch_data)
                        conn.commit()
                        batch_data = []
                        
                        # Update progress
                        self.update_progress(current_time, processed_count)
                        
                        # Progress callback
                        if progress_callback:
                            progress_callback(current_time, processed_count, self.total_minutes)
                        
                        # Print progress every 1000 records
                        if processed_count % 1000 == 0:
                            percentage = (processed_count / self.total_minutes) * 100
                            print(f"📊 Progress: {processed_count:,}/{self.total_minutes:,} ({percentage:.2f}%) - {current_time}")
                    
                    current_time += timedelta(minutes=1)
                    
                except Exception as e:
                    print(f"❌ Error processing {current_time}: {e}")
                    # Continue with next minute even if this one fails
                    current_time += timedelta(minutes=1)
                    
                    # If too many errors in a row, pause briefly
                    if hasattr(self, '_consecutive_errors'):
                        self._consecutive_errors += 1
                        if self._consecutive_errors > 10:
                            print("⚠️  Too many consecutive errors, pausing for 5 seconds...")
                            time.sleep(5)
                            self._consecutive_errors = 0
                    else:
                        self._consecutive_errors = 1
                    continue
                
                # Reset error counter on successful processing
                self._consecutive_errors = 0
            
            # Insert remaining batch
            if batch_data:
                self.insert_batch(cursor, batch_data)
                conn.commit()
            
            # Mark as completed
            cursor.execute('''
            UPDATE collection_progress 
            SET status = 'completed', estimated_completion = ?
            WHERE id = (SELECT MAX(id) FROM collection_progress)
            ''', (datetime.now(),))
            conn.commit()
            
            print(f"✅ Historical data collection completed!")
            print(f"📊 Total records processed: {processed_count:,}")
            
        except KeyboardInterrupt:
            print(f"\n⏹️  Collection paused. Resume with resume=True")
            cursor.execute('''
            UPDATE collection_progress 
            SET status = 'paused'
            WHERE id = (SELECT MAX(id) FROM collection_progress)
            ''')
            conn.commit()
            
        finally:
            conn.close()
    
    def insert_batch(self, cursor, batch_data):
        """Insert batch of data efficiently"""
        cursor.executemany('''
        INSERT OR REPLACE INTO planetary_positions (
            timestamp, year, month, day, hour, minute,
            sun_longitude, sun_sign, sun_degree_in_sign, sun_sign_number,
            moon_longitude, moon_sign, moon_degree_in_sign, moon_sign_number,
            mars_longitude, mars_sign, mars_degree_in_sign, mars_sign_number,
            mercury_longitude, mercury_sign, mercury_degree_in_sign, mercury_sign_number,
            jupiter_longitude, jupiter_sign, jupiter_degree_in_sign, jupiter_sign_number,
            venus_longitude, venus_sign, venus_degree_in_sign, venus_sign_number,
            saturn_longitude, saturn_sign, saturn_degree_in_sign, saturn_sign_number,
            rahu_longitude, rahu_sign, rahu_degree_in_sign, rahu_sign_number,
            ketu_longitude, ketu_sign, ketu_degree_in_sign, ketu_sign_number
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', batch_data)

class PlanetaryDataBrowser:
    """
    GUI browser for historical planetary data
    """
    
    def __init__(self, db_path: str = "historical_planetary_data.db"):
        self.db_path = db_path
        self.setup_gui()
        
    def setup_gui(self):
        """Setup the browser GUI"""
        self.root = tk.Tk()
        self.root.title("Historical Planetary Data Browser v1.0")
        self.root.geometry("1400x900")
        
        # Configure styles
        style = ttk.Style()
        style.theme_use('clam')
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        self.setup_header(main_frame)
        self.setup_controls(main_frame)
        self.setup_data_display(main_frame)
        self.setup_status_bar(main_frame)
        
        # Load initial data
        self.load_current_data()
    
    def setup_header(self, parent):
        """Setup header section"""
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        title_label = ttk.Label(header_frame, text="🌟 Historical Planetary Data Browser", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        # Database status
        self.db_status_label = ttk.Label(header_frame, text="🔄 Checking database...", 
                                        foreground="orange")
        self.db_status_label.grid(row=0, column=1, sticky=tk.E)
        header_frame.columnconfigure(1, weight=1)
    
    def setup_controls(self, parent):
        """Setup control panel"""
        control_frame = ttk.LabelFrame(parent, text="Date & Time Selection", padding="10")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Date picker
        ttk.Label(control_frame, text="Date:").grid(row=0, column=0, padx=(0, 5))
        self.date_entry = DateEntry(control_frame, width=12, background='darkblue',
                                  foreground='white', borderwidth=2, 
                                  mindate=datetime(2024, 1, 1),
                                  maxdate=datetime(2025, 12, 31),
                                  date_pattern='yyyy-mm-dd')
        self.date_entry.set_date(datetime(2024, 1, 1))
        self.date_entry.grid(row=0, column=1, padx=(0, 20))
        
        # Time controls
        ttk.Label(control_frame, text="Time:").grid(row=0, column=2, padx=(0, 5))
        
        time_frame = ttk.Frame(control_frame)
        time_frame.grid(row=0, column=3, padx=(0, 20))
        
        self.hour_var = tk.StringVar(value="00")
        hour_spin = ttk.Spinbox(time_frame, from_=0, to=23, width=3, 
                               textvariable=self.hour_var, format="%02.0f")
        hour_spin.grid(row=0, column=0)
        
        ttk.Label(time_frame, text=":").grid(row=0, column=1, padx=2)
        
        self.minute_var = tk.StringVar(value="00")
        minute_spin = ttk.Spinbox(time_frame, from_=0, to=59, width=3, 
                                 textvariable=self.minute_var, format="%02.0f")
        minute_spin.grid(row=0, column=2)
        
        # Navigation buttons
        nav_frame = ttk.Frame(control_frame)
        nav_frame.grid(row=0, column=4, padx=(20, 0))
        
        ttk.Button(nav_frame, text="◀◀ -1 Day", 
                  command=self.previous_day).grid(row=0, column=0, padx=2)
        ttk.Button(nav_frame, text="◀ -1 Hour", 
                  command=self.previous_hour).grid(row=0, column=1, padx=2)
        ttk.Button(nav_frame, text="🔍 Query", 
                  command=self.query_data).grid(row=0, column=2, padx=2)
        ttk.Button(nav_frame, text="▶ +1 Hour", 
                  command=self.next_hour).grid(row=0, column=3, padx=2)
        ttk.Button(nav_frame, text="▶▶ +1 Day", 
                  command=self.next_day).grid(row=0, column=4, padx=2)
    
    def setup_data_display(self, parent):
        """Setup data display area"""
        # Create notebook for tabs
        notebook = ttk.Notebook(parent)
        notebook.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        parent.rowconfigure(2, weight=1)
        
        # Planetary positions tab
        self.positions_frame = ttk.Frame(notebook)
        notebook.add(self.positions_frame, text="🪐 Planetary Positions")
        self.setup_positions_tab()
        
        # Data range tab
        self.range_frame = ttk.Frame(notebook)
        notebook.add(self.range_frame, text="📊 Data Range View")
        self.setup_range_tab()
    
    def setup_positions_tab(self):
        """Setup planetary positions tab"""
        # Treeview for positions
        columns = ("Planet", "Longitude", "Sign", "Degree", "DMS")
        self.positions_tree = ttk.Treeview(self.positions_frame, columns=columns, 
                                         show='headings', height=12)
        
        for col in columns:
            self.positions_tree.heading(col, text=col)
            self.positions_tree.column(col, width=120, anchor=tk.CENTER)
        
        # Scrollbars
        pos_v_scroll = ttk.Scrollbar(self.positions_frame, orient=tk.VERTICAL, 
                                   command=self.positions_tree.yview)
        pos_h_scroll = ttk.Scrollbar(self.positions_frame, orient=tk.HORIZONTAL, 
                                   command=self.positions_tree.xview)
        self.positions_tree.configure(yscrollcommand=pos_v_scroll.set, 
                                    xscrollcommand=pos_h_scroll.set)
        
        # Grid layout
        self.positions_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        pos_v_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        pos_h_scroll.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        self.positions_frame.columnconfigure(0, weight=1)
        self.positions_frame.rowconfigure(0, weight=1)
        
        # Details panel
        details_frame = ttk.LabelFrame(self.positions_frame, text="Position Details", padding="10")
        details_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.details_text = tk.Text(details_frame, height=8, wrap=tk.WORD)
        details_scroll = ttk.Scrollbar(details_frame, orient=tk.VERTICAL, 
                                     command=self.details_text.yview)
        self.details_text.configure(yscrollcommand=details_scroll.set)
        
        self.details_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        details_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        details_frame.columnconfigure(0, weight=1)
    
    def setup_range_tab(self):
        """Setup data range tab"""
        range_controls = ttk.Frame(self.range_frame, padding="10")
        range_controls.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        ttk.Label(range_controls, text="Show data from:").grid(row=0, column=0, padx=5)
        
        self.range_hours_var = tk.StringVar(value="24")
        hours_combo = ttk.Combobox(range_controls, textvariable=self.range_hours_var,
                                 values=["1", "6", "12", "24", "48", "72", "168"], width=10)
        hours_combo.grid(row=0, column=1, padx=5)
        
        ttk.Label(range_controls, text="hours before selected time").grid(row=0, column=2, padx=5)
        
        ttk.Button(range_controls, text="Load Range", 
                  command=self.load_range_data).grid(row=0, column=3, padx=10)
        
        # Range data display
        range_columns = ("Timestamp", "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")
        self.range_tree = ttk.Treeview(self.range_frame, columns=range_columns, 
                                     show='headings', height=20)
        
        for col in range_columns:
            self.range_tree.heading(col, text=col)
            self.range_tree.column(col, width=100, anchor=tk.CENTER)
        
        range_scroll = ttk.Scrollbar(self.range_frame, orient=tk.VERTICAL, 
                                   command=self.range_tree.yview)
        self.range_tree.configure(yscrollcommand=range_scroll.set)
        
        self.range_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        range_scroll.grid(row=1, column=1, sticky=(tk.N, tk.S), pady=(10, 0))
        
        self.range_frame.columnconfigure(0, weight=1)
        self.range_frame.rowconfigure(1, weight=1)
    
    def setup_status_bar(self, parent):
        """Setup status bar"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))
        
        self.status_label = ttk.Label(status_frame, text="Ready", relief=tk.SUNKEN)
        self.status_label.grid(row=0, column=0, sticky=(tk.W, tk.E))
        status_frame.columnconfigure(0, weight=1)
    
    def load_current_data(self):
        """Load data for current date/time selection"""
        try:
            if not os.path.exists(self.db_path):
                self.db_status_label.config(text="❌ Database not found", foreground="red")
                self.status_label.config(text="Database file not found")
                return
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if data exists
            cursor.execute("SELECT COUNT(*) FROM planetary_positions")
            count = cursor.fetchone()[0]
            
            if count == 0:
                self.db_status_label.config(text="⚠️ Database empty", foreground="orange")
                self.status_label.config(text="No data in database")
            else:
                self.db_status_label.config(text=f"✅ Database ready ({count:,} records)", 
                                          foreground="green")
                self.query_data()
            
            conn.close()
            
        except Exception as e:
            self.db_status_label.config(text="❌ Database error", foreground="red")
            self.status_label.config(text=f"Database error: {e}")
    
    def query_data(self):
        """Query data for selected date/time"""
        try:
            selected_date = self.date_entry.get_date()
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
            
            target_datetime = datetime.combine(selected_date, 
                                             datetime.min.time().replace(hour=hour, minute=minute))
            
            self.status_label.config(text=f"Querying data for {target_datetime}...")
            self.root.update()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT * FROM planetary_positions 
            WHERE timestamp = ?
            """, (target_datetime.isoformat(),))
            
            result = cursor.fetchone()
            
            if result:
                self.display_positions(result)
                self.status_label.config(text=f"✅ Data loaded for {target_datetime}")
            else:
                self.find_nearest_data(target_datetime, cursor)
            
            conn.close()
            
        except Exception as e:
            self.status_label.config(text=f"❌ Query error: {e}")
    
    def find_nearest_data(self, target_datetime, cursor):
        """Find nearest available data"""
        try:
            # Find nearest entry within 1 hour
            cursor.execute("""
            SELECT *, ABS(julianday(timestamp) - julianday(?)) * 24 * 60 as diff_minutes
            FROM planetary_positions 
            WHERE ABS(julianday(timestamp) - julianday(?)) * 24 * 60 <= 60
            ORDER BY diff_minutes ASC LIMIT 1
            """, (target_datetime.isoformat(), target_datetime.isoformat()))
            
            result = cursor.fetchone()
            
            if result:
                diff_minutes = result[-1]  # Last column is diff_minutes
                actual_time = result[1]  # timestamp column
                self.display_positions(result)
                self.status_label.config(text=f"⚠️ Nearest data: {actual_time} ({diff_minutes:.1f} min difference)")
            else:
                self.status_label.config(text="❌ No data found within 1 hour range")
                # Clear display
                for item in self.positions_tree.get_children():
                    self.positions_tree.delete(item)
                
        except Exception as e:
            self.status_label.config(text=f"❌ Search error: {e}")
    
    def display_positions(self, data):
        """Display planetary positions"""
        # Clear existing data
        for item in self.positions_tree.get_children():
            self.positions_tree.delete(item)
        
        # Column indices based on database schema
        planets = [
            ('Sun', 6, 7, 8),       # longitude, sign, degree_in_sign
            ('Moon', 10, 11, 12),
            ('Mars', 14, 15, 16),
            ('Mercury', 18, 19, 20),
            ('Jupiter', 22, 23, 24),
            ('Venus', 26, 27, 28),
            ('Saturn', 30, 31, 32),
            ('Rahu', 34, 35, 36),
            ('Ketu', 38, 39, 40)
        ]
        
        for planet_name, lon_idx, sign_idx, deg_idx in planets:
            longitude = data[lon_idx]
            sign = data[sign_idx]
            degree_in_sign = data[deg_idx]
            
            # Convert to DMS format
            dms = self.decimal_to_dms(degree_in_sign)
            
            self.positions_tree.insert('', 'end', values=(
                planet_name, f"{longitude:.4f}°", sign, 
                f"{degree_in_sign:.4f}°", dms
            ))
        
        # Update details panel
        timestamp = data[1]
        details_text = f"""
📅 Timestamp: {timestamp}
📊 Database ID: {data[0]}
🧮 Calculation Engine: Swiss Ephemeris (Professional Grade)
📍 Location: Delhi, India (28.6139°N, 77.2090°E)

🌟 Planetary Summary:
Sun in {data[7]} at {data[8]:.2f}°
Moon in {data[11]} at {data[12]:.2f}°
Mercury in {data[19]} at {data[20]:.2f}°
Venus in {data[27]} at {data[28]:.2f}°
Mars in {data[15]} at {data[16]:.2f}°
Jupiter in {data[23]} at {data[24]:.2f}°
Saturn in {data[31]} at {data[32]:.2f}°
Rahu in {data[35]} at {data[36]:.2f}°
Ketu in {data[39]} at {data[40]:.2f}°
        """.strip()
        
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(1.0, details_text)
    
    def decimal_to_dms(self, decimal_degrees):
        """Convert decimal degrees to DMS format"""
        try:
            degrees = int(decimal_degrees)
            minutes_float = (decimal_degrees - degrees) * 60
            minutes = int(minutes_float)
            seconds = (minutes_float - minutes) * 60
            return f"{degrees:02d}° {minutes:02d}' {seconds:04.1f}\""
        except:
            return "00° 00' 00.0\""
    
    def previous_day(self):
        """Navigate to previous day"""
        current_date = self.date_entry.get_date()
        new_date = current_date - timedelta(days=1)
        if new_date >= datetime(2024, 1, 1).date():
            self.date_entry.set_date(new_date)
            self.query_data()
    
    def next_day(self):
        """Navigate to next day"""
        current_date = self.date_entry.get_date()
        new_date = current_date + timedelta(days=1)
        if new_date <= datetime(2025, 12, 31).date():
            self.date_entry.set_date(new_date)
            self.query_data()
    
    def previous_hour(self):
        """Navigate to previous hour"""
        current_hour = int(self.hour_var.get())
        if current_hour > 0:
            self.hour_var.set(f"{current_hour-1:02d}")
        else:
            self.hour_var.set("23")
            self.previous_day()
            return
        self.query_data()
    
    def next_hour(self):
        """Navigate to next hour"""
        current_hour = int(self.hour_var.get())
        if current_hour < 23:
            self.hour_var.set(f"{current_hour+1:02d}")
        else:
            self.hour_var.set("00")
            self.next_day()
            return
        self.query_data()
    
    def load_range_data(self):
        """Load data range for analysis"""
        try:
            selected_date = self.date_entry.get_date()
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
            hours_before = int(self.range_hours_var.get())
            
            end_time = datetime.combine(selected_date, 
                                      datetime.min.time().replace(hour=hour, minute=minute))
            start_time = end_time - timedelta(hours=hours_before)
            
            self.status_label.config(text=f"Loading {hours_before}h range data...")
            self.root.update()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT timestamp, sun_longitude, moon_longitude, mercury_longitude, 
                   venus_longitude, mars_longitude, jupiter_longitude, saturn_longitude
            FROM planetary_positions 
            WHERE timestamp BETWEEN ? AND ?
            ORDER BY timestamp ASC
            """, (start_time.isoformat(), end_time.isoformat()))
            
            results = cursor.fetchall()
            
            # Clear existing data
            for item in self.range_tree.get_children():
                self.range_tree.delete(item)
            
            # Display range data
            for row in results:
                self.range_tree.insert('', 'end', values=(
                    row[0], f"{row[1]:.1f}°", f"{row[2]:.1f}°", f"{row[3]:.1f}°",
                    f"{row[4]:.1f}°", f"{row[5]:.1f}°", f"{row[6]:.1f}°", f"{row[7]:.1f}°"
                ))
            
            self.status_label.config(text=f"✅ Loaded {len(results)} records from {hours_before}h range")
            conn.close()
            
        except Exception as e:
            self.status_label.config(text=f"❌ Range load error: {e}")
    
    def run(self):
        """Start the browser application"""
        self.root.mainloop()

class HistoricalPlanetaryApp:
    """
    Main application combining data collection and browsing
    """
    
    def __init__(self):
        self.db_path = "historical_planetary_data.db"
        self.collector = HistoricalDataCollector(self.db_path)
        
    def run_collection(self, progress_callback=None):
        """Run historical data collection"""
        self.collector.collect_historical_data(progress_callback)
    
    def run_browser(self):
        """Run data browser"""
        browser = PlanetaryDataBrowser(self.db_path)
        browser.run()
    
    def run_collection_with_progress(self):
        """Run collection with GUI progress display"""
        progress_window = tk.Tk()
        progress_window.title("Historical Data Collection Progress")
        progress_window.geometry("600x300")
        
        # Progress display
        ttk.Label(progress_window, text="Historical Planetary Data Collection", 
                 font=("Arial", 14, "bold")).pack(pady=10)
        
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_window, variable=progress_var, 
                                     maximum=100, length=400)
        progress_bar.pack(pady=10)
        
        status_label = ttk.Label(progress_window, text="Starting collection...")
        status_label.pack(pady=5)
        
        eta_label = ttk.Label(progress_window, text="")
        eta_label.pack(pady=5)
        
        def progress_callback(current_time, processed, total):
            percentage = (processed / total) * 100
            progress_var.set(percentage)
            status_label.config(text=f"Processing: {current_time} ({processed:,}/{total:,})")
            
            # Estimate time remaining
            if processed > 100:  # After some initial processing
                # This would be calculated based on actual timing
                eta_label.config(text=f"Progress: {percentage:.2f}%")
            
            progress_window.update()
        
        # Start collection in thread
        collection_thread = threading.Thread(
            target=self.collector.collect_historical_data,
            args=(progress_callback, True),
            daemon=True
        )
        collection_thread.start()
        
        # Close button
        def on_close():
            progress_window.quit()
            progress_window.destroy()
        
        ttk.Button(progress_window, text="Close", command=on_close).pack(pady=20)
        progress_window.protocol("WM_DELETE_WINDOW", on_close)
        
        progress_window.mainloop()

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Historical Planetary Data Collection & Browser")
    parser.add_argument('mode', nargs='?', default='browser', 
                       choices=['collect', 'browser', 'progress'],
                       help='Mode: collect data, browse data, or collect with progress GUI')
    
    args = parser.parse_args()
    
    app = HistoricalPlanetaryApp()
    
    if args.mode == 'collect':
        print("🚀 Starting historical data collection...")
        app.run_collection()
    elif args.mode == 'progress':
        print("🚀 Starting collection with progress GUI...")
        app.run_collection_with_progress()
    else:  # browser mode
        print("🖥️  Starting data browser...")
        app.run_browser()

if __name__ == "__main__":
    main()