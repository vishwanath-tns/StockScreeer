#!/usr/bin/env python3
"""
Planetary Position Query GUI
Professional-Grade Vedic Astrology Position Viewer
Displays stored planetary positions from MySQL database with DrikPanchang validation

Features:
- Date/time picker for precise position lookup
- Real-time position display with professional formatting
- DrikPanchang validation comparison interface
- Nakshatra and pada information
- Export functionality for validation testing
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import json
from typing import Dict, Any, Optional, List
import threading

# Add tools to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'tools'))

try:
    import mysql.connector
    from mysql.connector import Error
    from tkcalendar import DateEntry
    import pandas as pd
except ImportError as e:
    print(f"Import error: {e}")
    print("Please install required packages: mysql-connector-python tkcalendar pandas")
    sys.exit(1)

class PlanetaryPositionViewer:
    """
    GUI application for viewing stored planetary positions
    """
    
    def __init__(self, config_file: str = "database_config.json"):
        """Initialize the viewer application"""
        self.config = self.load_config(config_file)
        self.db_connection = None
        
        # Setup main window
        self.setup_main_window()
        
        # Connect to database
        self.connect_database()
        
        # Current position data
        self.current_data = None
        
    def load_config(self, config_file: str) -> Dict:
        """Load database configuration"""
        default_config = {
            "database": {
                "host": "localhost",
                "port": 3306,
                "user": "root",
                "password": "",
                "database": "vedic_astrology",
                "charset": "utf8mb4"
            }
        }
        
        config_path = os.path.join(os.path.dirname(__file__), config_file)
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                    if 'database' in loaded_config:
                        default_config['database'].update(loaded_config['database'])
                        
            return default_config
            
        except Exception as e:
            print(f"Error loading config, using defaults: {e}")
            return default_config
    
    def connect_database(self):
        """Connect to MySQL database"""
        try:
            self.db_connection = mysql.connector.connect(
                **self.config['database'],
                autocommit=True,
                use_pure=True
            )
            
            if self.db_connection.is_connected():
                self.status_label.config(text="✅ Database Connected", foreground="green")
                self.load_latest_data()
            else:
                self.status_label.config(text="❌ Database Connection Failed", foreground="red")
                
        except Error as e:
            self.status_label.config(text=f"❌ Database Error: {e}", foreground="red")
            messagebox.showerror("Database Error", f"Failed to connect to database:\n{e}")
    
    def setup_main_window(self):
        """Setup the main window and widgets"""
        self.root = tk.Tk()
        self.root.title("Professional Planetary Position Viewer - v1.0")
        self.root.geometry("1200x800")
        
        # Configure styles
        style = ttk.Style()
        style.theme_use('clam')
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        title_label = ttk.Label(header_frame, text="🌟 Professional Planetary Position Viewer", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        self.status_label = ttk.Label(header_frame, text="🔄 Connecting to database...", 
                                     foreground="orange")
        self.status_label.grid(row=0, column=1, sticky=tk.E)
        header_frame.columnconfigure(1, weight=1)
        
        # Control panel
        control_frame = ttk.LabelFrame(main_frame, text="Date & Time Selection", padding="10")
        control_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        control_frame.columnconfigure(4, weight=1)
        
        # Date selection
        ttk.Label(control_frame, text="Date:").grid(row=0, column=0, padx=(0, 5))
        self.date_entry = DateEntry(control_frame, width=12, background='darkblue',
                                  foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.date_entry.grid(row=0, column=1, padx=(0, 20))
        
        # Time selection
        ttk.Label(control_frame, text="Time:").grid(row=0, column=2, padx=(0, 5))
        
        time_frame = ttk.Frame(control_frame)
        time_frame.grid(row=0, column=3, padx=(0, 20))
        
        self.hour_var = tk.StringVar(value=str(datetime.now().hour).zfill(2))
        hour_spin = ttk.Spinbox(time_frame, from_=0, to=23, width=3, textvariable=self.hour_var,
                               format="%02.0f")
        hour_spin.grid(row=0, column=0)
        
        ttk.Label(time_frame, text=":").grid(row=0, column=1, padx=2)
        
        self.minute_var = tk.StringVar(value=str(datetime.now().minute).zfill(2))
        minute_spin = ttk.Spinbox(time_frame, from_=0, to=59, width=3, textvariable=self.minute_var,
                                 format="%02.0f")
        minute_spin.grid(row=0, column=2)
        
        # Buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=0, column=4, sticky=tk.E, padx=(20, 0))
        
        ttk.Button(button_frame, text="🔍 Query Position", 
                  command=self.query_position).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(button_frame, text="📅 Latest Data", 
                  command=self.load_latest_data).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(button_frame, text="🔄 Refresh DB", 
                  command=self.connect_database).grid(row=0, column=2)
        
        # Main content area with notebook
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        main_frame.rowconfigure(2, weight=1)
        
        # Planetary positions tab
        self.positions_frame = ttk.Frame(notebook)
        notebook.add(self.positions_frame, text="🪐 Planetary Positions")
        self.setup_positions_tab()
        
        # Validation tab
        self.validation_frame = ttk.Frame(notebook)
        notebook.add(self.validation_frame, text="✅ DrikPanchang Validation")
        self.setup_validation_tab()
        
        # Database info tab
        self.info_frame = ttk.Frame(notebook)
        notebook.add(self.info_frame, text="📊 Database Info")
        self.setup_info_tab()
        
        # Status bar
        self.setup_status_bar(main_frame)
    
    def setup_positions_tab(self):
        """Setup planetary positions display tab"""
        # Create treeview for planetary data
        columns = ("Planet", "Longitude", "Sign", "Degree", "Nakshatra", "Pada", "DMS")
        self.positions_tree = ttk.Treeview(self.positions_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        for col in columns:
            self.positions_tree.heading(col, text=col)
            self.positions_tree.column(col, width=100, anchor=tk.CENTER)
        
        # Scrollbar
        positions_scrollbar = ttk.Scrollbar(self.positions_frame, orient=tk.VERTICAL, command=self.positions_tree.yview)
        self.positions_tree.configure(yscrollcommand=positions_scrollbar.set)
        
        # Grid layout
        self.positions_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        positions_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.positions_frame.columnconfigure(0, weight=1)
        self.positions_frame.rowconfigure(0, weight=1)
        
        # Info panel
        info_panel = ttk.LabelFrame(self.positions_frame, text="Position Details", padding="10")
        info_panel.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.position_info = tk.Text(info_panel, height=6, wrap=tk.WORD)
        info_scrollbar = ttk.Scrollbar(info_panel, orient=tk.VERTICAL, command=self.position_info.yview)
        self.position_info.configure(yscrollcommand=info_scrollbar.set)
        
        self.position_info.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        info_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        info_panel.columnconfigure(0, weight=1)
    
    def setup_validation_tab(self):
        """Setup DrikPanchang validation tab"""
        # Instructions
        instructions = ttk.Label(self.validation_frame, 
                                text="🎯 DrikPanchang Validation Tool\n\n"
                                     "1. Select date/time and query position\n"
                                     "2. Enter DrikPanchang reference data below\n"
                                     "3. Click 'Validate' to compare accuracy",
                                font=("Arial", 10))
        instructions.grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=10, pady=10)
        
        # Reference data entry
        ref_frame = ttk.LabelFrame(self.validation_frame, text="DrikPanchang Reference Data", padding="10")
        ref_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=10, pady=(0, 10))
        
        ttk.Label(ref_frame, text="Paste DrikPanchang planetary data:").grid(row=0, column=0, sticky=tk.W)
        
        self.reference_text = tk.Text(ref_frame, height=8, width=80)
        ref_scrollbar = ttk.Scrollbar(ref_frame, orient=tk.VERTICAL, command=self.reference_text.yview)
        self.reference_text.configure(yscrollcommand=ref_scrollbar.set)
        
        self.reference_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        ref_scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S), pady=(5, 0))
        ref_frame.columnconfigure(0, weight=1)
        
        # Validation buttons
        val_buttons = ttk.Frame(self.validation_frame)
        val_buttons.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(val_buttons, text="✅ Validate Against DrikPanchang", 
                  command=self.validate_against_drikpanchang).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(val_buttons, text="📤 Export for External Validation", 
                  command=self.export_for_validation).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(val_buttons, text="🔍 Show Validation History", 
                  command=self.show_validation_history).grid(row=0, column=2)
        
        # Validation results
        results_frame = ttk.LabelFrame(self.validation_frame, text="Validation Results", padding="10")
        results_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)
        
        self.validation_results = tk.Text(results_frame, height=12)
        val_results_scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.validation_results.yview)
        self.validation_results.configure(yscrollcommand=val_results_scrollbar.set)
        
        self.validation_results.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        val_results_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.validation_frame.columnconfigure(0, weight=1)
        self.validation_frame.rowconfigure(3, weight=1)
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
    
    def setup_info_tab(self):
        """Setup database info tab"""
        # Database statistics
        stats_frame = ttk.LabelFrame(self.info_frame, text="Database Statistics", padding="10")
        stats_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        self.stats_text = tk.Text(stats_frame, height=8, width=60)
        stats_scrollbar = ttk.Scrollbar(stats_frame, orient=tk.VERTICAL, command=self.stats_text.yview)
        self.stats_text.configure(yscrollcommand=stats_scrollbar.set)
        
        self.stats_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        stats_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        stats_frame.columnconfigure(0, weight=1)
        
        # Recent entries
        recent_frame = ttk.LabelFrame(self.info_frame, text="Recent Entries", padding="10")
        recent_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)
        
        recent_columns = ("Timestamp", "Sun", "Moon", "Mars", "Mercury", "Jupiter")
        self.recent_tree = ttk.Treeview(recent_frame, columns=recent_columns, show='headings', height=10)
        
        for col in recent_columns:
            self.recent_tree.heading(col, text=col)
            self.recent_tree.column(col, width=120, anchor=tk.CENTER)
        
        recent_scrollbar = ttk.Scrollbar(recent_frame, orient=tk.VERTICAL, command=self.recent_tree.yview)
        self.recent_tree.configure(yscrollcommand=recent_scrollbar.set)
        
        self.recent_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        recent_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.info_frame.columnconfigure(0, weight=1)
        self.info_frame.rowconfigure(1, weight=1)
        recent_frame.columnconfigure(0, weight=1)
        recent_frame.rowconfigure(0, weight=1)
        
        # Refresh button
        ttk.Button(self.info_frame, text="🔄 Refresh Statistics", 
                  command=self.update_database_stats).grid(row=2, column=0, pady=10)
    
    def setup_status_bar(self, parent):
        """Setup status bar"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        self.query_status = ttk.Label(status_frame, text="Ready", relief=tk.SUNKEN)
        self.query_status.grid(row=0, column=0, sticky=(tk.W, tk.E))
        status_frame.columnconfigure(0, weight=1)
    
    def query_position(self):
        """Query planetary position for selected date/time"""
        try:
            # Get selected date and time
            selected_date = self.date_entry.get_date()
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
            
            target_datetime = datetime.combine(selected_date, datetime.min.time().replace(hour=hour, minute=minute))
            
            self.query_status.config(text=f"Querying position for {target_datetime}...")
            self.root.update()
            
            # Query database
            cursor = self.db_connection.cursor(dictionary=True)
            
            sql = """
            SELECT * FROM planetary_positions_minute 
            WHERE timestamp = %s
            """
            
            cursor.execute(sql, (target_datetime,))
            result = cursor.fetchone()
            
            if result:
                self.current_data = result
                self.display_planetary_positions(result, target_datetime)
                self.query_status.config(text=f"✅ Data found for {target_datetime}")
            else:
                # Try to find nearest time
                self.find_nearest_data(target_datetime, cursor)
            
            cursor.close()
            
        except Exception as e:
            messagebox.showerror("Query Error", f"Failed to query position:\n{e}")
            self.query_status.config(text=f"❌ Query failed: {e}")
    
    def find_nearest_data(self, target_datetime, cursor):
        """Find nearest available data"""
        try:
            # Find nearest entry
            sql = """
            (SELECT *, ABS(TIMESTAMPDIFF(MINUTE, timestamp, %s)) as time_diff
             FROM planetary_positions_minute 
             WHERE timestamp <= %s
             ORDER BY timestamp DESC LIMIT 1)
            UNION
            (SELECT *, ABS(TIMESTAMPDIFF(MINUTE, timestamp, %s)) as time_diff
             FROM planetary_positions_minute 
             WHERE timestamp > %s
             ORDER BY timestamp ASC LIMIT 1)
            ORDER BY time_diff ASC LIMIT 1
            """
            
            cursor.execute(sql, (target_datetime, target_datetime, target_datetime, target_datetime))
            result = cursor.fetchone()
            
            if result:
                self.current_data = result
                time_diff = result['time_diff']
                actual_time = result['timestamp']
                self.display_planetary_positions(result, actual_time)
                self.query_status.config(text=f"⚠️ Nearest data: {actual_time} ({time_diff} min difference)")
            else:
                self.query_status.config(text="❌ No data found in database")
                messagebox.showwarning("No Data", "No planetary position data found in database")
                
        except Exception as e:
            self.query_status.config(text=f"❌ Search failed: {e}")
    
    def display_planetary_positions(self, data, timestamp):
        """Display planetary positions in the treeview"""
        # Clear existing data
        for item in self.positions_tree.get_children():
            self.positions_tree.delete(item)
        
        planets = [
            ('Sun', 'sun'), ('Moon', 'moon'), ('Mars', 'mars'), ('Mercury', 'mercury'),
            ('Jupiter', 'jupiter'), ('Venus', 'venus'), ('Saturn', 'saturn'),
            ('Rahu', 'rahu'), ('Ketu', 'ketu')
        ]
        
        for planet_name, planet_key in planets:
            longitude = data.get(f'{planet_key}_longitude', 0)
            sign = data.get(f'{planet_key}_sign', 'Unknown')
            degree_in_sign = data.get(f'{planet_key}_degree_in_sign', 0)
            nakshatra = data.get(f'{planet_key}_nakshatra', 'Unknown')
            pada = data.get(f'{planet_key}_pada', 0)
            
            # Convert to DMS format
            dms = self.decimal_to_dms(degree_in_sign)
            
            self.positions_tree.insert('', 'end', values=(
                planet_name, f"{longitude:.4f}°", sign, f"{degree_in_sign:.4f}°", 
                nakshatra, pada, dms
            ))
        
        # Update info panel
        info_text = f"""
📅 Timestamp: {timestamp}
🧮 Calculation Engine: {data.get('calculation_engine', 'Unknown')}
📍 Location: {data.get('location', 'Unknown')}
🌌 Julian Day: {data.get('julian_day', 'Unknown')}
🔢 Ayanamsa: {data.get('ayanamsa', 'Unknown'):.4f}°
📊 Database ID: {data.get('id', 'Unknown')}
        """.strip()
        
        self.position_info.delete(1.0, tk.END)
        self.position_info.insert(1.0, info_text)
    
    def decimal_to_dms(self, decimal_degrees):
        """Convert decimal degrees to degrees, minutes, seconds format"""
        try:
            degrees = int(decimal_degrees)
            minutes_float = (decimal_degrees - degrees) * 60
            minutes = int(minutes_float)
            seconds = (minutes_float - minutes) * 60
            return f"{degrees:02d}° {minutes:02d}' {seconds:04.1f}\""
        except:
            return "00° 00' 00.0\""
    
    def load_latest_data(self):
        """Load the latest available data"""
        try:
            if not self.db_connection or not self.db_connection.is_connected():
                self.connect_database()
                return
            
            cursor = self.db_connection.cursor(dictionary=True)
            
            sql = """
            SELECT * FROM planetary_positions_minute 
            ORDER BY timestamp DESC LIMIT 1
            """
            
            cursor.execute(sql)
            result = cursor.fetchone()
            
            if result:
                self.current_data = result
                timestamp = result['timestamp']
                self.display_planetary_positions(result, timestamp)
                
                # Update date/time selectors
                self.date_entry.set_date(timestamp.date())
                self.hour_var.set(str(timestamp.hour).zfill(2))
                self.minute_var.set(str(timestamp.minute).zfill(2))
                
                self.query_status.config(text=f"✅ Latest data: {timestamp}")
                
            else:
                self.query_status.config(text="❌ No data found in database")
                messagebox.showinfo("No Data", "No data found in database. Please run the data generator first.")
            
            cursor.close()
            
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to load latest data:\n{e}")
            self.query_status.config(text=f"❌ Failed to load data: {e}")
    
    def validate_against_drikpanchang(self):
        """Validate current positions against DrikPanchang data"""
        if not self.current_data:
            messagebox.showwarning("No Data", "Please query a position first")
            return
        
        # This would integrate with the existing validation tools
        self.validation_results.delete(1.0, tk.END)
        self.validation_results.insert(tk.END, "🔍 DrikPanchang validation feature coming soon...\n\n")
        self.validation_results.insert(tk.END, "Current data loaded:\n")
        
        if self.current_data:
            timestamp = self.current_data['timestamp']
            self.validation_results.insert(tk.END, f"Timestamp: {timestamp}\n")
            
            planets = ['sun', 'moon', 'mars', 'mercury', 'jupiter', 'venus', 'saturn', 'rahu', 'ketu']
            for planet in planets:
                longitude = self.current_data.get(f'{planet}_longitude', 0)
                nakshatra = self.current_data.get(f'{planet}_nakshatra', 'Unknown')
                self.validation_results.insert(tk.END, f"{planet.title()}: {longitude:.4f}° in {nakshatra}\n")
    
    def export_for_validation(self):
        """Export current position data for external validation"""
        if not self.current_data:
            messagebox.showwarning("No Data", "Please query a position first")
            return
        
        try:
            # Create export data
            export_data = {
                'timestamp': str(self.current_data['timestamp']),
                'julian_day': float(self.current_data['julian_day']),
                'planets': {}
            }
            
            planets = ['sun', 'moon', 'mars', 'mercury', 'jupiter', 'venus', 'saturn', 'rahu', 'ketu']
            for planet in planets:
                export_data['planets'][planet] = {
                    'longitude': float(self.current_data.get(f'{planet}_longitude', 0)),
                    'sign': self.current_data.get(f'{planet}_sign', 'Unknown'),
                    'degree_in_sign': float(self.current_data.get(f'{planet}_degree_in_sign', 0)),
                    'nakshatra': self.current_data.get(f'{planet}_nakshatra', 'Unknown'),
                    'pada': int(self.current_data.get(f'{planet}_pada', 0))
                }
            
            # Save to file
            timestamp_str = str(self.current_data['timestamp']).replace(':', '-').replace(' ', '_')
            filename = f"planetary_export_{timestamp_str}.json"
            
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            messagebox.showinfo("Export Complete", f"Data exported to: {filename}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export data:\n{e}")
    
    def show_validation_history(self):
        """Show validation history from database"""
        # This would query the validation_logs table
        self.validation_results.delete(1.0, tk.END)
        self.validation_results.insert(tk.END, "📊 Validation history feature coming soon...\n")
        self.validation_results.insert(tk.END, "Will show accuracy trends and validation results over time.\n")
    
    def update_database_stats(self):
        """Update database statistics"""
        try:
            if not self.db_connection or not self.db_connection.is_connected():
                self.connect_database()
                return
            
            cursor = self.db_connection.cursor(dictionary=True)
            
            # Get basic statistics
            stats_queries = {
                'total_entries': "SELECT COUNT(*) as count FROM planetary_positions_minute",
                'date_range': "SELECT MIN(timestamp) as min_date, MAX(timestamp) as max_date FROM planetary_positions_minute",
                'latest_entry': "SELECT timestamp FROM planetary_positions_minute ORDER BY timestamp DESC LIMIT 1",
                'today_entries': "SELECT COUNT(*) as count FROM planetary_positions_minute WHERE DATE(timestamp) = CURDATE()"
            }
            
            stats_data = {}
            for key, query in stats_queries.items():
                cursor.execute(query)
                result = cursor.fetchone()
                stats_data[key] = result
            
            # Display statistics
            self.stats_text.delete(1.0, tk.END)
            
            stats_text = f"""
📊 Database Statistics:

Total Entries: {stats_data['total_entries']['count']:,}
Today's Entries: {stats_data['today_entries']['count']}

Date Range:
  From: {stats_data['date_range']['min_date']}
  To: {stats_data['date_range']['max_date']}

Latest Entry: {stats_data['latest_entry']['timestamp']}

Database: {self.config['database']['database']}
Host: {self.config['database']['host']}
            """.strip()
            
            self.stats_text.insert(1.0, stats_text)
            
            # Load recent entries
            self.load_recent_entries(cursor)
            
            cursor.close()
            
        except Exception as e:
            messagebox.showerror("Statistics Error", f"Failed to update statistics:\n{e}")
    
    def load_recent_entries(self, cursor):
        """Load recent entries for display"""
        try:
            # Clear existing entries
            for item in self.recent_tree.get_children():
                self.recent_tree.delete(item)
            
            sql = """
            SELECT timestamp, sun_longitude, moon_longitude, mars_longitude, 
                   mercury_longitude, jupiter_longitude
            FROM planetary_positions_minute 
            ORDER BY timestamp DESC LIMIT 20
            """
            
            cursor.execute(sql)
            results = cursor.fetchall()
            
            for row in results:
                self.recent_tree.insert('', 'end', values=(
                    row['timestamp'],
                    f"{row['sun_longitude']:.2f}°",
                    f"{row['moon_longitude']:.2f}°",
                    f"{row['mars_longitude']:.2f}°",
                    f"{row['mercury_longitude']:.2f}°",
                    f"{row['jupiter_longitude']:.2f}°"
                ))
                
        except Exception as e:
            print(f"Error loading recent entries: {e}")
    
    def run(self):
        """Run the application"""
        # Load initial data
        self.update_database_stats()
        
        # Start main loop
        self.root.mainloop()

def main():
    """Main function"""
    try:
        app = PlanetaryPositionViewer()
        app.run()
    except Exception as e:
        messagebox.showerror("Application Error", f"Failed to start application:\n{e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()