#!/usr/bin/env python3
"""
Simple Historical Planetary Data Collector
Stable command-line version without GUI
"""

import os
import sys
import sqlite3
import signal
import time
from datetime import datetime, timedelta

# Add the vedic_astrology directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from calculations.core_calculator import VedicAstrologyCalculator

class SimpleHistoricalCollector:
    def __init__(self):
        self.calculator = VedicAstrologyCalculator()
        self.db_path = os.path.join(os.path.dirname(__file__), 'planetary_positions.db')
        self.start_date = datetime(2024, 1, 1, 0, 0, 0)
        self.end_date = datetime(2026, 1, 1, 0, 0, 0)
        self.total_minutes = int((self.end_date - self.start_date).total_seconds() / 60)
        self.running = True
        
        # Signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Setup database
        self.setup_database()
    
    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print(f"\n⏹️  Graceful shutdown initiated...")
        self.running = False
    
    def setup_database(self):
        """Create database and tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Main table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS planetary_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL UNIQUE,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                day INTEGER NOT NULL,
                hour INTEGER NOT NULL,
                minute INTEGER NOT NULL,
                
                sun_longitude REAL NOT NULL,
                sun_sign TEXT NOT NULL,
                moon_longitude REAL NOT NULL,
                moon_sign TEXT NOT NULL,
                mars_longitude REAL NOT NULL,
                mars_sign TEXT NOT NULL,
                mercury_longitude REAL NOT NULL,
                mercury_sign TEXT NOT NULL,
                jupiter_longitude REAL NOT NULL,
                jupiter_sign TEXT NOT NULL,
                venus_longitude REAL NOT NULL,
                venus_sign TEXT NOT NULL,
                saturn_longitude REAL NOT NULL,
                saturn_sign TEXT NOT NULL,
                rahu_longitude REAL NOT NULL,
                rahu_sign TEXT NOT NULL,
                ketu_longitude REAL NOT NULL,
                ketu_sign TEXT NOT NULL,
                
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON planetary_positions(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_date ON planetary_positions(year, month, day)')
            
            # Progress table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS progress (
                id INTEGER PRIMARY KEY,
                last_timestamp TEXT,
                processed_count INTEGER DEFAULT 0
            )
            ''')
            
            conn.commit()
            conn.close()
            print(f"✅ Database setup: {self.db_path}")
            
        except Exception as e:
            print(f"❌ Database setup failed: {e}")
            sys.exit(1)
    
    def get_last_processed(self):
        """Get last processed timestamp"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Try to get from progress table
            cursor.execute('SELECT last_timestamp, processed_count FROM progress ORDER BY id DESC LIMIT 1')
            result = cursor.fetchone()
            
            if result and result[0]:
                return result[0], result[1]
            
            # Fallback: check actual data
            cursor.execute('SELECT MAX(timestamp) FROM planetary_positions')
            last_ts = cursor.fetchone()[0]
            
            if last_ts:
                cursor.execute('SELECT COUNT(*) FROM planetary_positions')
                count = cursor.fetchone()[0]
                return last_ts, count
            
            conn.close()
            return None, 0
            
        except Exception as e:
            print(f"Warning: Could not get progress: {e}")
            return None, 0
    
    def update_progress(self, timestamp_str: str, count: int):
        """Update progress in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM progress')  # Keep only latest
            cursor.execute('INSERT INTO progress (last_timestamp, processed_count) VALUES (?, ?)',
                         (timestamp_str, count))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Warning: Could not update progress: {e}")
    
    def collect_data(self, resume=True):
        """Collect historical data"""
        print(f"🚀 Starting collection from {self.start_date} to {self.end_date}")
        print(f"📊 Total minutes to process: {self.total_minutes:,}")
        
        # Determine start point
        current_time = self.start_date
        processed_count = 0
        
        if resume:
            last_ts, count = self.get_last_processed()
            if last_ts:
                try:
                    current_time = datetime.fromisoformat(last_ts) + timedelta(minutes=1)
                    processed_count = count
                    print(f"🔄 Resuming from: {current_time} (processed: {processed_count:,})")
                except:
                    print("⚠️  Could not parse last timestamp, starting fresh")
        
        start_time = time.time()
        last_report = start_time
        batch_data = []
        batch_size = 100
        consecutive_errors = 0
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            while current_time < self.end_date and self.running:
                try:
                    # Get planetary positions
                    positions = self.calculator.get_planetary_positions(current_time)
                    
                    # Prepare data
                    row_data = [
                        current_time.isoformat(),
                        current_time.year,
                        current_time.month,
                        current_time.day,
                        current_time.hour,
                        current_time.minute
                    ]
                    
                    # Add planetary data (simplified) 
                    planets = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn']
                    for planet in planets:
                        if planet in positions:
                            data = positions[planet]
                            longitude = data.get('longitude', 0.0)
                            sign = data.get('sign', 'Unknown')
                            row_data.extend([longitude, sign])
                        else:
                            row_data.extend([0.0, 'Unknown'])
                    
                    # Add placeholders for Rahu and Ketu (not available in core calculator)
                    row_data.extend([0.0, 'Unknown'])  # Rahu
                    row_data.extend([0.0, 'Unknown'])  # Ketu
                    
                    batch_data.append(tuple(row_data))
                    processed_count += 1
                    consecutive_errors = 0
                    
                    # Insert batch
                    if len(batch_data) >= batch_size:
                        cursor.executemany('''
                        INSERT OR REPLACE INTO planetary_positions (
                            timestamp, year, month, day, hour, minute,
                            sun_longitude, sun_sign, moon_longitude, moon_sign,
                            mars_longitude, mars_sign, mercury_longitude, mercury_sign,
                            jupiter_longitude, jupiter_sign, venus_longitude, venus_sign,
                            saturn_longitude, saturn_sign, rahu_longitude, rahu_sign,
                            ketu_longitude, ketu_sign
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', batch_data)
                        
                        conn.commit()
                        batch_data = []
                        
                        # Update progress
                        self.update_progress(current_time.isoformat(), processed_count)
                    
                    # Progress report every 1000 records or 30 seconds
                    now = time.time()
                    if processed_count % 1000 == 0 or (now - last_report) > 30:
                        elapsed = now - start_time
                        rate = processed_count / elapsed if elapsed > 0 else 0
                        percentage = (processed_count / self.total_minutes) * 100
                        remaining = (self.total_minutes - processed_count) / rate if rate > 0 else 0
                        eta_hours = remaining / 3600
                        
                        print(f"📊 {processed_count:,}/{self.total_minutes:,} ({percentage:.2f}%) | "
                              f"{rate:.1f} rec/s | ETA: {eta_hours:.1f}h | {current_time}")
                        last_report = now
                    
                    current_time += timedelta(minutes=1)
                    
                except Exception as e:
                    consecutive_errors += 1
                    print(f"❌ Error at {current_time}: {e}")
                    
                    if consecutive_errors > 10:
                        print("⚠️  Too many errors, pausing 10 seconds...")
                        time.sleep(10)
                        consecutive_errors = 0
                    
                    current_time += timedelta(minutes=1)
                    continue
            
            # Insert final batch
            if batch_data:
                cursor.executemany('''
                INSERT OR REPLACE INTO planetary_positions (
                    timestamp, year, month, day, hour, minute,
                    sun_longitude, sun_sign, moon_longitude, moon_sign,
                    mars_longitude, mars_sign, mercury_longitude, mercury_sign,
                    jupiter_longitude, jupiter_sign, venus_longitude, venus_sign,
                    saturn_longitude, saturn_sign, rahu_longitude, rahu_sign,
                    ketu_longitude, ketu_sign
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', batch_data)
                conn.commit()
            
            conn.close()
            
            if self.running:
                print(f"\n✅ Collection completed! Processed {processed_count:,} records")
            else:
                print(f"\n⏹️  Collection stopped. Processed {processed_count:,} records")
                print(f"💡 Resume with: python simple_collector.py")
                
        except Exception as e:
            print(f"❌ Collection failed: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

def main():
    """Main function"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║         🌟 Simple Historical Planetary Data Collector                ║
║              Stable Command Line Version                            ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    
    collector = SimpleHistoricalCollector()
    
    print(f"\n📋 Collection Details:")
    print(f"   Period: 2024-01-01 to 2026-01-01")
    print(f"   Total: {collector.total_minutes:,} minutes")
    print(f"   Database: {collector.db_path}")
    
    # Check existing data
    last_ts, count = collector.get_last_processed()
    if count > 0:
        percentage = (count / collector.total_minutes) * 100
        print(f"   Existing: {count:,} records ({percentage:.1f}%)")
        print(f"   Last: {last_ts}")
    
    print(f"\n💡 Press Ctrl+C to stop safely at any time")
    print(f"🚀 Starting collection...\n")
    
    try:
        collector.collect_data(resume=True)
    except KeyboardInterrupt:
        print(f"\n🛑 Collection stopped by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()