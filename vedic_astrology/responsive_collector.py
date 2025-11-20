#!/usr/bin/env python3
"""
Responsive Historical Planetary Data Collector
Can be stopped with Ctrl+C and shows database tables

Key Features:
- Responsive to Ctrl+C interrupts
- Progress display every 50 records
- Graceful shutdown with data saving
- Database table information display
- Resume capability
"""

import sys
import os
import sqlite3
import signal
import threading
from datetime import datetime, timedelta

# Add tools to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'tools'))

class ResponsiveCollector:
    """
    Responsive collector that can be stopped gracefully
    """
    
    def __init__(self, db_path="planetary_positions.db"):
        self.db_path = db_path
        self.running = True
        self.start_date = datetime(2024, 1, 1, 0, 0, 0)
        self.end_date = datetime(2026, 1, 1, 0, 0, 0)
        self.total_minutes = int((self.end_date - self.start_date).total_seconds() / 60)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.setup_database()
        self.load_calculator()
    
    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print(f"\n🛑 Received stop signal (Ctrl+C) - stopping gracefully...")
        self.running = False
    
    def load_calculator(self):
        """Load the planetary calculator"""
        try:
            from calculations.core_calculator import VedicAstrologyCalculator
            self.calculator = VedicAstrologyCalculator()
            print("✅ Calculator loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load calculator: {e}")
            sys.exit(1)
    
    def setup_database(self):
        """Setup database with clear table structure"""
        print(f"🗄️  Setting up database: {self.db_path}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main planetary positions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS planetary_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT UNIQUE NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL, 
            day INTEGER NOT NULL,
            hour INTEGER NOT NULL,
            minute INTEGER NOT NULL,
            
            -- Planetary data (longitude, sign, degree in sign)
            sun_longitude REAL,
            sun_sign TEXT,
            sun_degree REAL,
            
            moon_longitude REAL,
            moon_sign TEXT,
            moon_degree REAL,
            
            mercury_longitude REAL,
            mercury_sign TEXT, 
            mercury_degree REAL,
            
            venus_longitude REAL,
            venus_sign TEXT,
            venus_degree REAL,
            
            mars_longitude REAL,
            mars_sign TEXT,
            mars_degree REAL,
            
            jupiter_longitude REAL,
            jupiter_sign TEXT,
            jupiter_degree REAL,
            
            saturn_longitude REAL,
            saturn_sign TEXT,
            saturn_degree REAL,
            
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Progress tracking table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS collection_progress (
            id INTEGER PRIMARY KEY,
            last_timestamp TEXT,
            processed_count INTEGER DEFAULT 0,
            start_time TEXT,
            last_update TEXT
        )
        ''')
        
        # Create indexes for fast queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON planetary_positions(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_date ON planetary_positions(year, month, day)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_hour ON planetary_positions(year, month, day, hour)')
        
        conn.commit()
        conn.close()
        
        print("✅ Database setup complete")
        self.show_database_info()
    
    def show_database_info(self):
        """Show database table structure and current data"""
        print("\n📊 DATABASE INFORMATION")
        print("="*60)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Show table structure
        print("🗄️  Table: planetary_positions")
        print("   Columns:")
        cursor.execute("PRAGMA table_info(planetary_positions)")
        for row in cursor.fetchall():
            col_id, name, col_type, not_null, default, pk = row
            print(f"   - {name} ({col_type})")
        
        # Show current data count
        cursor.execute("SELECT COUNT(*) FROM planetary_positions")
        count = cursor.fetchone()[0]
        print(f"\n📈 Current Records: {count:,}")
        
        if count > 0:
            # Show date range
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM planetary_positions")
            min_date, max_date = cursor.fetchone()
            print(f"📅 Date Range: {min_date} to {max_date}")
            
            # Show sample data
            cursor.execute("SELECT timestamp, sun_longitude, moon_longitude FROM planetary_positions ORDER BY timestamp DESC LIMIT 3")
            print("\n📋 Recent Records:")
            for row in cursor.fetchall():
                print(f"   {row[0]}: Sun={row[1]:.2f}°, Moon={row[2]:.2f}°")
        
        # Show progress info
        cursor.execute("SELECT * FROM collection_progress ORDER BY id DESC LIMIT 1")
        progress = cursor.fetchone()
        if progress:
            print(f"\n⏯️  Collection Progress:")
            print(f"   Last processed: {progress[1]}")
            print(f"   Records processed: {progress[2]:,}")
        
        conn.close()
        print("="*60)
    
    def get_resume_point(self):
        """Get the last processed timestamp for resume"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT last_timestamp, processed_count FROM collection_progress ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        
        conn.close()
        
        if result and result[0]:
            return result[0], result[1]
        return None, 0
    
    def update_progress(self, timestamp, count):
        """Update collection progress"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO collection_progress (id, last_timestamp, processed_count, last_update)
        VALUES (1, ?, ?, ?)
        ''', (timestamp.isoformat(), count, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def collect_minute_data(self, target_time):
        """Collect data for a specific minute"""
        try:
            # Get planetary positions
            positions = self.calculator.get_planetary_positions(target_time)
            
            # Prepare data row
            row_data = [
                target_time.isoformat(),
                target_time.year,
                target_time.month,
                target_time.day,
                target_time.hour,
                target_time.minute
            ]
            
            # Add planetary data
            planets = ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn']
            for planet in planets:
                if planet in positions:
                    data = positions[planet]
                    row_data.extend([
                        data.get('longitude', 0.0),
                        data.get('sign', 'Unknown'),
                        data.get('degree_in_sign', 0.0)
                    ])
                else:
                    row_data.extend([0.0, 'Unknown', 0.0])
            
            return row_data
            
        except Exception as e:
            print(f"❌ Error calculating positions for {target_time}: {e}")
            return None
    
    def save_batch(self, batch_data):
        """Save a batch of data to database"""
        if not batch_data:
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.executemany('''
            INSERT OR REPLACE INTO planetary_positions (
                timestamp, year, month, day, hour, minute,
                sun_longitude, sun_sign, sun_degree,
                moon_longitude, moon_sign, moon_degree,
                mercury_longitude, mercury_sign, mercury_degree,
                venus_longitude, venus_sign, venus_degree,
                mars_longitude, mars_sign, mars_degree,
                jupiter_longitude, jupiter_sign, jupiter_degree,
                saturn_longitude, saturn_sign, saturn_degree
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', batch_data)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ Error saving batch: {e}")
    
    def start_collection(self, resume=True):
        """Start the data collection process"""
        print(f"\n🚀 STARTING PLANETARY DATA COLLECTION")
        print(f"📅 Period: {self.start_date} to {self.end_date}")
        print(f"📊 Total minutes: {self.total_minutes:,}")
        print(f"⏹️  Press Ctrl+C to stop gracefully")
        print(f"📈 Progress updates every 50 records")
        print(f"💾 Auto-save every 100 records")
        print("-" * 60)
        
        # Determine starting point
        current_time = self.start_date
        processed_count = 0
        
        if resume:
            last_timestamp, count = self.get_resume_point()
            if last_timestamp:
                try:
                    current_time = datetime.fromisoformat(last_timestamp) + timedelta(minutes=1)
                    processed_count = count
                    print(f"🔄 Resuming from: {current_time}")
                    print(f"📊 Already processed: {processed_count:,} records")
                except Exception as e:
                    print(f"⚠️  Resume failed, starting fresh: {e}")
        
        # Collection loop
        batch_data = []
        batch_size = 100
        report_interval = 50
        
        try:
            while current_time < self.end_date and self.running:
                # Collect data for current minute
                row_data = self.collect_minute_data(current_time)
                
                if row_data:
                    batch_data.append(row_data)
                    processed_count += 1
                    
                    # Show progress
                    if processed_count % report_interval == 0:
                        percentage = (processed_count / self.total_minutes) * 100
                        print(f"📊 {processed_count:,}/{self.total_minutes:,} ({percentage:.2f}%) - {current_time} [Ctrl+C to stop]")
                    
                    # Save batch when full
                    if len(batch_data) >= batch_size:
                        print(f"💾 Saving batch of {len(batch_data)} records...")
                        self.save_batch(batch_data)
                        self.update_progress(current_time, processed_count)
                        batch_data = []
                        
                        # Check if still running
                        if not self.running:
                            break
                
                # Move to next minute
                current_time += timedelta(minutes=1)
                
                # Small delay to make it more responsive to Ctrl+C
                if processed_count % 10 == 0:
                    import time
                    time.sleep(0.001)  # 1ms pause every 10 records
            
            # Save final batch
            if batch_data and self.running:
                print(f"💾 Saving final batch of {len(batch_data)} records...")
                self.save_batch(batch_data)
                self.update_progress(current_time, processed_count)
            
            # Final status
            if self.running:
                print("\n✅ COLLECTION COMPLETED SUCCESSFULLY!")
            else:
                print("\n⏹️  COLLECTION STOPPED BY USER")
            
            print(f"📊 Total records processed: {processed_count:,}")
            print(f"💾 Data saved to: {self.db_path}")
            
        except Exception as e:
            print(f"\n❌ Collection failed: {e}")
            if batch_data:
                print("💾 Attempting to save current batch...")
                self.save_batch(batch_data)
                self.update_progress(current_time, processed_count)
        
        finally:
            print(f"\n📊 FINAL DATABASE STATUS:")
            self.show_database_info()

def main():
    """Main function"""
    print("""
╔════════════════════════════════════════════════════════════════════╗
║           🌟 Responsive Planetary Data Collector v2.0             ║
║                    Easy Stop with Ctrl+C                          ║
╚════════════════════════════════════════════════════════════════════╝
""")
    
    collector = ResponsiveCollector()
    
    # Ask user what to do
    print("\nChoose an action:")
    print("1. Start/Resume data collection")
    print("2. Show database information only")
    print("3. Exit")
    
    try:
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == "1":
            print(f"\n🚀 Starting collection...")
            print(f"💡 You can stop anytime with Ctrl+C")
            input("Press Enter to begin or Ctrl+C to cancel...")
            collector.start_collection(resume=True)
            
        elif choice == "2":
            print(f"\n📊 Database Information:")
            collector.show_database_info()
            
        else:
            print(f"👋 Goodbye!")
    
    except KeyboardInterrupt:
        print(f"\n👋 Cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()