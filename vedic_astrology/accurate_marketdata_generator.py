#!/usr/bin/env python3
"""
Accurate Planetary Position Generator for MarketData Database
Generates high-precision planetary positions using ProfessionalAstrologyCalculator
and stores them in the marketdata.planetary_positions table.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import mysql.connector
from dotenv import load_dotenv
import threading
from tools.pyjhora_calculator import ProfessionalAstrologyCalculator

# Load environment variables
load_dotenv()

class AccuratePlanetaryGenerator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Accurate Planetary Position Generator - MarketData")
        self.root.geometry("600x500")
        
        # Calculator instance
        self.calculator = ProfessionalAstrologyCalculator()
        
        # Control variables
        self.is_running = False
        self.generation_thread = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="Accurate Planetary Position Generator", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=10)
        
        subtitle_label = ttk.Label(main_frame, text="MarketData Database - Professional Swiss Ephemeris", 
                                  font=("Arial", 10))
        subtitle_label.grid(row=1, column=0, columnspan=3, pady=5)
        
        # Date range selection
        date_frame = ttk.LabelFrame(main_frame, text="Date Range Selection", padding="10")
        date_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # Start date
        ttk.Label(date_frame, text="Start Date:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.start_year = tk.StringVar(value="2025")
        self.start_month = tk.StringVar(value="1")
        self.start_day = tk.StringVar(value="1")
        
        ttk.Entry(date_frame, textvariable=self.start_year, width=6).grid(row=0, column=1, padx=2)
        ttk.Label(date_frame, text="/").grid(row=0, column=2)
        ttk.Entry(date_frame, textvariable=self.start_month, width=4).grid(row=0, column=3, padx=2)
        ttk.Label(date_frame, text="/").grid(row=0, column=4)
        ttk.Entry(date_frame, textvariable=self.start_day, width=4).grid(row=0, column=5, padx=2)
        
        # End date
        ttk.Label(date_frame, text="End Date:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.end_year = tk.StringVar(value="2025")
        self.end_month = tk.StringVar(value="12")
        self.end_day = tk.StringVar(value="31")
        
        ttk.Entry(date_frame, textvariable=self.end_year, width=6).grid(row=1, column=1, padx=2)
        ttk.Label(date_frame, text="/").grid(row=1, column=2)
        ttk.Entry(date_frame, textvariable=self.end_month, width=4).grid(row=1, column=3, padx=2)
        ttk.Label(date_frame, text="/").grid(row=1, column=4)
        ttk.Entry(date_frame, textvariable=self.end_day, width=4).grid(row=1, column=5, padx=2)
        
        # Database info
        db_frame = ttk.LabelFrame(main_frame, text="Database Information", padding="10")
        db_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        self.db_status_var = tk.StringVar(value="Checking connection...")
        self.db_status_label = ttk.Label(db_frame, textvariable=self.db_status_var)
        self.db_status_label.grid(row=0, column=0, columnspan=2, sticky=tk.W)
        
        self.record_count_var = tk.StringVar(value="Checking existing records...")
        self.record_count_label = ttk.Label(db_frame, textvariable=self.record_count_var)
        self.record_count_label.grid(row=1, column=0, columnspan=2, sticky=tk.W)
        
        # Options
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="10")
        options_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        self.overwrite_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Overwrite existing data", 
                       variable=self.overwrite_var).grid(row=0, column=0, sticky=tk.W)
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=20)
        
        self.start_button = ttk.Button(button_frame, text="Start Generation", 
                                      command=self.start_generation)
        self.start_button.grid(row=0, column=0, padx=10)
        
        self.stop_button = ttk.Button(button_frame, text="Stop Generation", 
                                     command=self.stop_generation, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=10)
        
        # Progress
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
        progress_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                           maximum=100, length=400)
        self.progress_bar.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.progress_text_var = tk.StringVar(value="Ready to start generation")
        self.progress_text = ttk.Label(progress_frame, textvariable=self.progress_text_var)
        self.progress_text.grid(row=1, column=0, columnspan=2)
        
        # Log area
        log_frame = ttk.LabelFrame(main_frame, text="Generation Log", padding="10")
        log_frame.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        # Create text widget with scrollbar
        log_container = tk.Frame(log_frame)
        log_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.log_text = tk.Text(log_container, height=8, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(log_container, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        log_container.columnconfigure(0, weight=1)
        log_container.rowconfigure(0, weight=1)
        
        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(7, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Check database connection on startup
        self.root.after(100, self.check_database_connection)
        
    def log_message(self, message):
        """Add a message to the log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def check_database_connection(self):
        """Check database connection and existing records"""
        try:
            conn = mysql.connector.connect(
                host=os.getenv('MYSQL_HOST', 'localhost'),
                port=int(os.getenv('MYSQL_PORT', 3306)),
                user=os.getenv('MYSQL_USER', 'root'),
                password=os.getenv('MYSQL_PASSWORD', ''),
                database='marketdata'
            )
            
            cursor = conn.cursor()
            
            # Check total records
            cursor.execute('SELECT COUNT(*) FROM planetary_positions')
            total_records = cursor.fetchone()[0]
            
            # Check date range
            if total_records > 0:
                cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM planetary_positions')
                date_range = cursor.fetchone()
                range_text = f"{date_range[0]} to {date_range[1]}"
            else:
                range_text = "No data"
            
            # Check 2025 records
            cursor.execute('SELECT COUNT(*) FROM planetary_positions WHERE YEAR(timestamp) = 2025')
            records_2025 = cursor.fetchone()[0]
            
            self.db_status_var.set(f"✅ Connected to marketdata database")
            self.record_count_var.set(f"📊 Total: {total_records:,} records | 2025: {records_2025:,} | Range: {range_text}")
            
            cursor.close()
            conn.close()
            
            self.log_message(f"Database connection verified. Total records: {total_records:,}")
            
        except Exception as e:
            self.db_status_var.set(f"❌ Database connection failed: {str(e)}")
            self.record_count_var.set("Cannot check records - no connection")
            self.log_message(f"Database connection error: {str(e)}")
    
    def get_database_connection(self):
        """Get database connection"""
        return mysql.connector.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            database='marketdata'
        )
    
    def get_zodiac_sign_info(self, longitude):
        """Convert longitude to sign and degree within sign"""
        signs = [
            "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
            "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
        ]
        
        # Each sign is 30 degrees
        sign_index = int(longitude // 30) % 12
        degree_in_sign = longitude % 30
        
        return signs[sign_index], degree_in_sign
    
    def start_generation(self):
        """Start the planetary position generation"""
        if self.is_running:
            return
            
        try:
            # Validate dates
            start_date = datetime(
                int(self.start_year.get()),
                int(self.start_month.get()),
                int(self.start_day.get())
            )
            end_date = datetime(
                int(self.end_year.get()),
                int(self.end_month.get()),
                int(self.end_day.get())
            )
            
            if start_date >= end_date:
                messagebox.showerror("Error", "End date must be after start date")
                return
                
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid date format: {str(e)}")
            return
        
        # Update UI
        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress_var.set(0)
        
        # Clear log
        self.log_text.delete(1.0, tk.END)
        
        # Start generation in separate thread
        self.generation_thread = threading.Thread(
            target=self.generate_positions,
            args=(start_date, end_date),
            daemon=True
        )
        self.generation_thread.start()
    
    def stop_generation(self):
        """Stop the generation process"""
        self.is_running = False
        self.log_message("Stopping generation... please wait for current batch to complete.")
    
    def generate_positions(self, start_date, end_date):
        """Generate planetary positions for the specified date range"""
        try:
            # Calculate total minutes
            total_minutes = int((end_date - start_date).total_seconds() / 60) + 1
            self.log_message(f"Generating {total_minutes:,} planetary positions from {start_date} to {end_date}")
            self.log_message("Using ProfessionalAstrologyCalculator (Swiss Ephemeris)")
            
            conn = self.get_database_connection()
            cursor = conn.cursor()
            
            # Check for existing data if not overwriting
            if not self.overwrite_var.get():
                cursor.execute(
                    'SELECT COUNT(*) FROM planetary_positions WHERE timestamp BETWEEN %s AND %s',
                    (start_date, end_date)
                )
                existing_count = cursor.fetchone()[0]
                if existing_count > 0:
                    self.log_message(f"Warning: {existing_count} records already exist in this range")
                    self.log_message("Enable 'Overwrite existing data' to replace them")
            
            # Generate positions minute by minute
            current_time = start_date
            processed_count = 0
            batch_size = 1000
            batch_data = []
            
            while current_time <= end_date and self.is_running:
                try:
                    # Get planetary positions
                    positions = self.calculator.get_planetary_positions(current_time)
                    
                    # Prepare data for insertion
                    row_data = [
                        current_time,
                        current_time.year,
                        current_time.month,
                        current_time.day,
                        current_time.hour,
                        current_time.minute
                    ]
                    
                    # Add planetary data
                    for planet in ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Rahu', 'Ketu']:
                        if planet in positions:
                            longitude = positions[planet]['longitude']
                            sign, degree = self.get_zodiac_sign_info(longitude)
                            row_data.extend([longitude, sign, degree])
                        else:
                            row_data.extend([None, None, None])  # Handle missing data
                    
                    batch_data.append(tuple(row_data))
                    processed_count += 1
                    
                    # Insert batch
                    if len(batch_data) >= batch_size or current_time == end_date:
                        if self.overwrite_var.get():
                            # Use INSERT ... ON DUPLICATE KEY UPDATE for overwrite
                            insert_query = """
                            INSERT INTO planetary_positions 
                            (timestamp, year, month, day, hour, minute,
                             sun_longitude, sun_sign, sun_degree,
                             moon_longitude, moon_sign, moon_degree,
                             mercury_longitude, mercury_sign, mercury_degree,
                             venus_longitude, venus_sign, venus_degree,
                             mars_longitude, mars_sign, mars_degree,
                             jupiter_longitude, jupiter_sign, jupiter_degree,
                             saturn_longitude, saturn_sign, saturn_degree,
                             rahu_longitude, rahu_sign, rahu_degree,
                             ketu_longitude, ketu_sign, ketu_degree)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                                   %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                            sun_longitude=VALUES(sun_longitude), sun_sign=VALUES(sun_sign), sun_degree=VALUES(sun_degree),
                            moon_longitude=VALUES(moon_longitude), moon_sign=VALUES(moon_sign), moon_degree=VALUES(moon_degree),
                            mercury_longitude=VALUES(mercury_longitude), mercury_sign=VALUES(mercury_sign), mercury_degree=VALUES(mercury_degree),
                            venus_longitude=VALUES(venus_longitude), venus_sign=VALUES(venus_sign), venus_degree=VALUES(venus_degree),
                            mars_longitude=VALUES(mars_longitude), mars_sign=VALUES(mars_sign), mars_degree=VALUES(mars_degree),
                            jupiter_longitude=VALUES(jupiter_longitude), jupiter_sign=VALUES(jupiter_sign), jupiter_degree=VALUES(jupiter_degree),
                            saturn_longitude=VALUES(saturn_longitude), saturn_sign=VALUES(saturn_sign), saturn_degree=VALUES(saturn_degree),
                            rahu_longitude=VALUES(rahu_longitude), rahu_sign=VALUES(rahu_sign), rahu_degree=VALUES(rahu_degree),
                            ketu_longitude=VALUES(ketu_longitude), ketu_sign=VALUES(ketu_sign), ketu_degree=VALUES(ketu_degree),
                            updated_at=CURRENT_TIMESTAMP
                            """
                        else:
                            # Use INSERT IGNORE for non-overwrite
                            insert_query = """
                            INSERT IGNORE INTO planetary_positions 
                            (timestamp, year, month, day, hour, minute,
                             sun_longitude, sun_sign, sun_degree,
                             moon_longitude, moon_sign, moon_degree,
                             mercury_longitude, mercury_sign, mercury_degree,
                             venus_longitude, venus_sign, venus_degree,
                             mars_longitude, mars_sign, mars_degree,
                             jupiter_longitude, jupiter_sign, jupiter_degree,
                             saturn_longitude, saturn_sign, saturn_degree,
                             rahu_longitude, rahu_sign, rahu_degree,
                             ketu_longitude, ketu_sign, ketu_degree)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                                   %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """
                        
                        cursor.executemany(insert_query, batch_data)
                        conn.commit()
                        batch_data = []
                        
                        # Update progress
                        progress_percent = (processed_count / total_minutes) * 100
                        self.progress_var.set(progress_percent)
                        self.progress_text_var.set(f"Processed {processed_count:,} / {total_minutes:,} positions ({progress_percent:.1f}%)")
                        
                        if processed_count % 10000 == 0:
                            self.log_message(f"Generated {processed_count:,} positions. Current: {current_time}")
                    
                    # Move to next minute
                    current_time += timedelta(minutes=1)
                    
                except Exception as e:
                    self.log_message(f"Error generating position for {current_time}: {str(e)}")
                    current_time += timedelta(minutes=1)
                    continue
            
            cursor.close()
            conn.close()
            
            if self.is_running:
                self.log_message(f"✅ Generation completed! Generated {processed_count:,} planetary positions.")
                self.progress_var.set(100)
                self.progress_text_var.set(f"Completed: {processed_count:,} positions generated")
                
                # Update database info
                self.root.after(1000, self.check_database_connection)
            else:
                self.log_message(f"⏹️ Generation stopped by user. Generated {processed_count:,} positions.")
                
        except Exception as e:
            self.log_message(f"❌ Generation failed: {str(e)}")
            
        finally:
            # Reset UI
            self.is_running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
    
    def run(self):
        """Start the application"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.log_message("Application interrupted by user")
            self.root.quit()

if __name__ == "__main__":
    app = AccuratePlanetaryGenerator()
    app.run()