#!/usr/bin/env python3
"""
MySQL Planetary Data Collector
Collects planetary positions and stores in MySQL database
"""

import sys
import os
import mysql.connector
import signal
import threading
from datetime import datetime, timedelta

class MySQLPlanetaryCollector:
    """
    MySQL-based collector for planetary positions
    """
    
    def __init__(self):
        self.running = True
        self.start_date = datetime(2024, 1, 1, 0, 0, 0)
        self.end_date = datetime(2026, 1, 1, 0, 0, 0)
        self.total_minutes = int((self.end_date - self.start_date).total_seconds() / 60)
        
        # MySQL connection config
        self.config = {
            'host': 'localhost',
            'port': 3306,
            'database': 'marketdata',
            'user': 'root',
            'password': 'Ganesh@@2283@@'
        }
        
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
            sys.path.append('vedic_astrology')
            from calculations.core_calculator import VedicAstrologyCalculator
            self.calculator = VedicAstrologyCalculator()
            print("✅ Calculator loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load calculator: {e}")
            sys.exit(1)
    
    def setup_database(self):
        """Test database connection and show table info"""
        print(f"🔗 Connecting to MySQL database...")
        
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor()
            
            print(f"✅ Connected to MySQL: {self.config['database']}")
            
            # Check if table exists
            cursor.execute("SHOW TABLES LIKE 'planetary_positions'")
            if not cursor.fetchone():
                print("❌ Table 'planetary_positions' not found!")
                print("💡 Run: python create_mysql_planetary_table.py")
                sys.exit(1)
            
            # Show table info
            self.show_database_info()
            
            conn.close()
            
        except mysql.connector.Error as e:
            print(f"❌ MySQL Error: {e}")
            sys.exit(1)
    
    def show_database_info(self):
        """Show current database status"""
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor()
            
            print(f"\n📊 DATABASE INFORMATION")
            print("=" * 60)
            print(f"🗄️  Host: {self.config['host']}")
            print(f"🗄️  Database: {self.config['database']}")
            print(f"🗄️  Table: planetary_positions")
            
            # Show table structure
            cursor.execute("DESCRIBE planetary_positions")
            columns = cursor.fetchall()
            
            print(f"\n🏗️  Columns ({len(columns)} total):")
            for col in columns:
                field, type_info, null, key, default, extra = col
                key_info = f" ({key})" if key else ""
                print(f"   - {field:<25} {type_info}{key_info}")
            
            # Show current data
            cursor.execute("SELECT COUNT(*) FROM planetary_positions")
            count = cursor.fetchone()[0]
            
            print(f"\n📈 Current Records: {count:,}")
            
            if count > 0:
                cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM planetary_positions")
                result = cursor.fetchone()
                if result[0]:
                    print(f"📅 Date Range: {result[0]} to {result[1]}")
                
                # Show sample records
                cursor.execute("""
                    SELECT timestamp, sun_longitude, moon_longitude 
                    FROM planetary_positions 
                    ORDER BY timestamp DESC 
                    LIMIT 3
                """)
                recent = cursor.fetchall()
                
                print(f"\n📋 Recent Records:")
                for record in recent:
                    ts, sun_lon, moon_lon = record
                    print(f"   {ts}: Sun={sun_lon:.2f}°, Moon={moon_lon:.2f}°")
            
            conn.close()
            
        except mysql.connector.Error as e:
            print(f"❌ Database info error: {e}")
    
    def get_resume_point(self):
        """Get the last processed timestamp for resume capability"""
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT last_timestamp, processed_count 
                FROM planetary_collection_progress 
                ORDER BY id DESC LIMIT 1
            """)
            result = cursor.fetchone()
            
            conn.close()
            
            if result and result[0]:
                return result[0], result[1]
            return None, 0
            
        except mysql.connector.Error:
            return None, 0
    
    def update_progress(self, timestamp, count):
        """Update collection progress"""
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO planetary_collection_progress (last_timestamp, processed_count)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE 
                last_timestamp = VALUES(last_timestamp),
                processed_count = VALUES(processed_count)
            """, (timestamp, count))
            
            conn.commit()
            conn.close()
            
        except mysql.connector.Error as e:
            print(f"⚠️  Progress update error: {e}")
    
    def collect_minute_data(self, target_time):
        """Collect data for a specific minute"""
        try:
            # Get planetary positions
            positions = self.calculator.get_planetary_positions(target_time)
            
            # Prepare data - match the MySQL table structure
            data = {
                'timestamp': target_time,
                'year': target_time.year,
                'month': target_time.month,
                'day': target_time.day,
                'hour': target_time.hour,
                'minute': target_time.minute
            }
            
            # Add planetary data 
            planets = ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn']
            for planet in planets:
                if planet in positions:
                    planet_data = positions[planet]
                    prefix = planet.lower()
                    
                    # Extract longitude, sign, and degree from the position data
                    longitude = planet_data.get('longitude', 0.0)
                    sign = planet_data.get('sign', 'Unknown')
                    
                    # Calculate degree within sign (0-30)
                    degree_in_sign = longitude % 30
                    
                    data[f'{prefix}_longitude'] = longitude
                    data[f'{prefix}_sign'] = sign
                    data[f'{prefix}_degree'] = degree_in_sign
                else:
                    # Default values if planet not found
                    prefix = planet.lower()
                    data[f'{prefix}_longitude'] = None
                    data[f'{prefix}_sign'] = 'Unknown'
                    data[f'{prefix}_degree'] = None
            
            # Add Rahu/Ketu with default values for now
            for node in ['rahu', 'ketu']:
                data[f'{node}_longitude'] = None
                data[f'{node}_sign'] = 'Unknown'
                data[f'{node}_degree'] = None
            
            return data
            
        except Exception as e:
            print(f"❌ Error collecting data for {target_time}: {e}")
            return None
    
    def save_batch_data(self, batch_data):
        """Save a batch of records to MySQL"""
        if not batch_data:
            return
        
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor()
            
            # Prepare INSERT statement
            insert_sql = """
            INSERT INTO planetary_positions (
                timestamp, year, month, day, hour, minute,
                sun_longitude, sun_sign, sun_degree,
                moon_longitude, moon_sign, moon_degree,
                mercury_longitude, mercury_sign, mercury_degree,
                venus_longitude, venus_sign, venus_degree,
                mars_longitude, mars_sign, mars_degree,
                jupiter_longitude, jupiter_sign, jupiter_degree,
                saturn_longitude, saturn_sign, saturn_degree,
                rahu_longitude, rahu_sign, rahu_degree,
                ketu_longitude, ketu_sign, ketu_degree
            ) VALUES (
                %(timestamp)s, %(year)s, %(month)s, %(day)s, %(hour)s, %(minute)s,
                %(sun_longitude)s, %(sun_sign)s, %(sun_degree)s,
                %(moon_longitude)s, %(moon_sign)s, %(moon_degree)s,
                %(mercury_longitude)s, %(mercury_sign)s, %(mercury_degree)s,
                %(venus_longitude)s, %(venus_sign)s, %(venus_degree)s,
                %(mars_longitude)s, %(mars_sign)s, %(mars_degree)s,
                %(jupiter_longitude)s, %(jupiter_sign)s, %(jupiter_degree)s,
                %(saturn_longitude)s, %(saturn_sign)s, %(saturn_degree)s,
                %(rahu_longitude)s, %(rahu_sign)s, %(rahu_degree)s,
                %(ketu_longitude)s, %(ketu_sign)s, %(ketu_degree)s
            ) ON DUPLICATE KEY UPDATE
                sun_longitude = VALUES(sun_longitude),
                sun_sign = VALUES(sun_sign),
                sun_degree = VALUES(sun_degree),
                moon_longitude = VALUES(moon_longitude),
                moon_sign = VALUES(moon_sign),
                moon_degree = VALUES(moon_degree)
            """
            
            cursor.executemany(insert_sql, batch_data)
            conn.commit()
            
            print(f"✅ Saved batch of {len(batch_data)} records to MySQL")
            
            conn.close()
            
        except mysql.connector.Error as e:
            print(f"❌ Error saving batch: {e}")
    
    def start_collection(self, resume=True):
        """Start the data collection process"""
        print(f"\n🚀 STARTING MYSQL PLANETARY DATA COLLECTION")
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
                    current_time = last_timestamp + timedelta(minutes=1)
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
                    
                    # Progress report
                    if processed_count % report_interval == 0:
                        progress = (processed_count / self.total_minutes) * 100
                        print(f"📊 {processed_count:,}/{self.total_minutes:,} ({progress:.2f}%) - {current_time} [Ctrl+C to stop]")
                    
                    # Save batch
                    if len(batch_data) >= batch_size:
                        print(f"💾 Saving batch of {len(batch_data)} records...")
                        self.save_batch_data(batch_data)
                        self.update_progress(current_time, processed_count)
                        batch_data = []
                
                # Move to next minute
                current_time += timedelta(minutes=1)
                
                # Small delay to prevent overwhelming the system
                if not self.running:
                    break
            
            # Save remaining data
            if batch_data and self.running:
                print(f"💾 Saving final batch of {len(batch_data)} records...")
                self.save_batch_data(batch_data)
                self.update_progress(current_time, processed_count)
            
            if not self.running:
                print(f"\n⏹️  COLLECTION STOPPED BY USER")
            else:
                print(f"\n🎉 COLLECTION COMPLETED!")
            
            print(f"📊 Total records processed: {processed_count:,}")
            print(f"💾 Data saved to: MySQL {self.config['database']}.planetary_positions")
            
            # Show final status
            self.show_database_info()
            
        except Exception as e:
            print(f"\n❌ Collection error: {e}")
            # Save any remaining data
            if batch_data:
                print(f"💾 Emergency save: {len(batch_data)} records...")
                self.save_batch_data(batch_data)

def main():
    """Main function"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║           🌟 MySQL Planetary Data Collector v1.0                ║
║                    Stores in MySQL Database                     ║
╚══════════════════════════════════════════════════════════════════╝
""")
    
    collector = MySQLPlanetaryCollector()
    
    while True:
        print(f"\nChoose an action:")
        print("1. Start/Resume data collection")
        print("2. Show database information only")
        print("3. Exit")
        
        try:
            choice = input("\nEnter choice (1-3): ").strip()
            
            if choice == "1":
                print(f"\n🚀 Starting collection...")
                print(f"💡 You can stop anytime with Ctrl+C")
                input("Press Enter to begin or Ctrl+C to cancel...")
                collector.start_collection()
                break
            
            elif choice == "2":
                collector.show_database_info()
            
            elif choice == "3":
                print("👋 Goodbye!")
                break
            
            else:
                print("❌ Invalid choice. Please enter 1-3.")
        
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()