#!/usr/bin/env python3
"""
MySQL Planetary Data Collector (6 Months Testing)
Collects planetary positions and stores in MySQL database

Key Features:
- Responsive to Ctrl+C interrupts
- Progress display every 100 records
- Auto-save every 1000 records
- Resume capability
- Stores data in MySQL database
- 6 months duration for testing (Jan 1 - July 1, 2024)
"""

import sys
import os
import signal
import pymysql
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MySQLPlanetaryCollector:
    """
    MySQL-based planetary data collector
    """
    
    def __init__(self):
        self.running = True
        self.start_date = datetime(2024, 1, 1, 0, 0, 0)
        self.end_date = datetime(2024, 7, 1, 0, 0, 0)  # 6 months for testing
        self.total_minutes = int((self.end_date - self.start_date).total_seconds() / 60)
        
        # MySQL connection info
        self.mysql_config = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DB', 'stock_screener'),
            'charset': 'utf8mb4',
            'autocommit': False
        }
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.load_calculator()
        self.test_mysql_connection()
    
    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print(f"\n🛑 Received stop signal (Ctrl+C) - stopping gracefully...")
        self.running = False
    
    def load_calculator(self):
        """Load the planetary calculator"""
        try:
            # Use the accurate ProfessionalAstrologyCalculator with Swiss Ephemeris
            from tools.pyjhora_calculator import ProfessionalAstrologyCalculator
            self.calculator = ProfessionalAstrologyCalculator()
            print("✅ Professional Calculator loaded successfully (PyJHora + Swiss Ephemeris)")
            print("🎯 Using high-accuracy calculations matching DrikPanchang")
        except Exception as e:
            print(f"❌ Failed to load professional calculator: {e}")
            print("💡 Falling back to basic calculator...")
            try:
                from calculations.core_calculator import VedicAstrologyCalculator
                self.calculator = VedicAstrologyCalculator()
                print("⚠️  Using basic calculator (lower accuracy)")
            except Exception as e2:
                print(f"❌ Failed to load any calculator: {e2}")
                sys.exit(1)
    
    def test_mysql_connection(self):
        """Test MySQL connection"""
        try:
            conn = pymysql.connect(**self.mysql_config)
            print(f"✅ MySQL connection successful: {self.mysql_config['host']}:{self.mysql_config['port']}")
            
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM planetary_positions")
            count = cursor.fetchone()[0]
            print(f"📊 Current records in MySQL: {count:,}")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ MySQL connection failed: {e}")
            print(f"💡 Check your .env file settings:")
            print(f"   MYSQL_HOST={self.mysql_config['host']}")
            print(f"   MYSQL_PORT={self.mysql_config['port']}")
            print(f"   MYSQL_DB={self.mysql_config['database']}")
            sys.exit(1)
    
    def get_mysql_connection(self):
        """Get MySQL connection"""
        return pymysql.connect(**self.mysql_config)
    
    def get_resume_point(self):
        """Get last processed timestamp for resume capability"""
        try:
            conn = self.get_mysql_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT MAX(timestamp), COUNT(*) FROM planetary_positions WHERE timestamp BETWEEN %s AND %s", 
                          (self.start_date, self.end_date))
            result = cursor.fetchone()
            
            conn.close()
            
            if result and result[0]:
                return result[0], result[1]
            return None, 0
            
        except Exception as e:
            print(f"⚠️  Could not get resume point: {e}")
            return None, 0
    
    def collect_minute_data(self, target_time):
        """Collect data for a specific minute using professional calculator"""
        try:
            # Get planetary positions using professional calculator
            positions = self.calculator.get_planetary_positions(target_time)
            
            # Prepare data
            data = {
                'timestamp': target_time,
                'year': target_time.year,
                'month': target_time.month,
                'day': target_time.day,
                'hour': target_time.hour,
                'minute': target_time.minute
            }
            
            # Add planetary data (professional calculator returns different format)
            planets = ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Rahu', 'Ketu']
            for planet in planets:
                if planet in positions:
                    pos = positions[planet]
                    longitude = pos.get('longitude', 0)
                    sign = pos.get('sign', 'Unknown')
                    degree = pos.get('degree_in_sign', longitude % 30)  # Use provided degree or calculate
                    
                    planet_lower = planet.lower()
                    data[f'{planet_lower}_longitude'] = longitude
                    data[f'{planet_lower}_sign'] = sign
                    data[f'{planet_lower}_degree'] = degree
                else:
                    planet_lower = planet.lower()
                    data[f'{planet_lower}_longitude'] = 0
                    data[f'{planet_lower}_sign'] = 'Unknown'
                    data[f'{planet_lower}_degree'] = 0
            
            return data
            
        except Exception as e:
            print(f"❌ Error collecting data for {target_time}: {e}")
            return None
    
    def save_batch_to_mysql(self, batch_data):
        """Save batch of data to MySQL"""
        if not batch_data:
            return
        
        try:
            conn = self.get_mysql_connection()
            cursor = conn.cursor()
            
            # Prepare INSERT statement
            sql = """
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
            )
            ON DUPLICATE KEY UPDATE
                sun_longitude = VALUES(sun_longitude),
                sun_sign = VALUES(sun_sign),
                sun_degree = VALUES(sun_degree),
                moon_longitude = VALUES(moon_longitude),
                moon_sign = VALUES(moon_sign),
                moon_degree = VALUES(moon_degree),
                mercury_longitude = VALUES(mercury_longitude),
                mercury_sign = VALUES(mercury_sign),
                mercury_degree = VALUES(mercury_degree),
                venus_longitude = VALUES(venus_longitude),
                venus_sign = VALUES(venus_sign),
                venus_degree = VALUES(venus_degree),
                mars_longitude = VALUES(mars_longitude),
                mars_sign = VALUES(mars_sign),
                mars_degree = VALUES(mars_degree),
                jupiter_longitude = VALUES(jupiter_longitude),
                jupiter_sign = VALUES(jupiter_sign),
                jupiter_degree = VALUES(jupiter_degree),
                saturn_longitude = VALUES(saturn_longitude),
                saturn_sign = VALUES(saturn_sign),
                saturn_degree = VALUES(saturn_degree),
                rahu_longitude = VALUES(rahu_longitude),
                rahu_sign = VALUES(rahu_sign),
                rahu_degree = VALUES(rahu_degree),
                ketu_longitude = VALUES(ketu_longitude),
                ketu_sign = VALUES(ketu_sign),
                ketu_degree = VALUES(ketu_degree)
            """
            
            cursor.executemany(sql, batch_data)
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ Error saving batch: {e}")
    
    def show_progress_summary(self):
        """Show progress summary"""
        try:
            conn = self.get_mysql_connection()
            cursor = conn.cursor()
            
            print(f"\n📊 COLLECTION PROGRESS SUMMARY")
            print("="*60)
            
            # Total records
            cursor.execute("SELECT COUNT(*) FROM planetary_positions WHERE timestamp BETWEEN %s AND %s", 
                          (self.start_date, self.end_date))
            total_count = cursor.fetchone()[0]
            
            # Date range
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM planetary_positions WHERE timestamp BETWEEN %s AND %s", 
                          (self.start_date, self.end_date))
            result = cursor.fetchone()
            
            if result[0]:
                min_date, max_date = result
                print(f"📅 Period: {self.start_date} to {self.end_date}")
                print(f"📊 Total target: {self.total_minutes:,} minutes")
                print(f"📈 Collected: {total_count:,} records")
                print(f"📍 Coverage: {(total_count/self.total_minutes)*100:.2f}%")
                print(f"🕐 First record: {min_date}")
                print(f"🕐 Last record: {max_date}")
                
                # Sample records
                cursor.execute("SELECT timestamp, sun_longitude, moon_longitude FROM planetary_positions WHERE timestamp BETWEEN %s AND %s ORDER BY timestamp DESC LIMIT 3", 
                              (self.start_date, self.end_date))
                samples = cursor.fetchall()
                
                print(f"\n📋 Recent records:")
                for sample in samples:
                    timestamp, sun_lon, moon_lon = sample
                    print(f"   {timestamp}: Sun={sun_lon:.2f}°, Moon={moon_lon:.2f}°")
            else:
                print("📈 No records collected yet")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Error showing progress: {e}")
    
    def start_collection(self, resume=True):
        """Start the data collection process"""
        print(f"\n🚀 STARTING MYSQL PLANETARY DATA COLLECTION")
        print(f"📅 Period: {self.start_date} to {self.end_date}")
        print(f"📊 Total minutes: {self.total_minutes:,}")
        print(f"⏹️  Press Ctrl+C to stop gracefully")
        print(f"📈 Progress updates every 100 records")
        print(f"💾 Auto-save every 1000 records")
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
        batch_size = 1000  # Larger batches for MySQL
        report_interval = 100
        
        try:
            while current_time < self.end_date and self.running:
                # Collect data for current minute
                row_data = self.collect_minute_data(current_time)
                
                if row_data:
                    batch_data.append(row_data)
                    processed_count += 1
                    
                    # Progress report
                    if processed_count % report_interval == 0:
                        percentage = (processed_count / self.total_minutes) * 100
                        print(f"📊 {processed_count:,}/{self.total_minutes:,} ({percentage:.2f}%) - {current_time} [Ctrl+C to stop]")
                    
                    # Save batch
                    if len(batch_data) >= batch_size:
                        print(f"💾 Saving batch of {len(batch_data)} records...")
                        self.save_batch_to_mysql(batch_data)
                        batch_data = []
                
                # Move to next minute
                current_time += timedelta(minutes=1)
                
                # Check if stopped
                if not self.running:
                    break
            
            # Save remaining data
            if batch_data:
                print(f"💾 Saving final batch of {len(batch_data)} records...")
                self.save_batch_to_mysql(batch_data)
            
            if self.running:
                print(f"\n🎉 COLLECTION COMPLETE!")
                print(f"📊 Total records processed: {processed_count:,}")
            else:
                print(f"\n⏹️  COLLECTION STOPPED BY USER")
                print(f"📊 Total records processed: {processed_count:,}")
            
        except Exception as e:
            print(f"\n❌ Collection error: {e}")
        
        finally:
            # Save any remaining data
            if batch_data:
                print(f"💾 Saving remaining {len(batch_data)} records...")
                self.save_batch_to_mysql(batch_data)
        
        # Show final summary
        self.show_progress_summary()

def main():
    """Main function"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║           🌟 MySQL Planetary Data Collector v1.0                ║
║                    6 Months Testing Period                      ║
║                  Jan 1 - July 1, 2024                          ║
╚══════════════════════════════════════════════════════════════════╝
""")
    
    collector = MySQLPlanetaryCollector()
    
    # Show initial status
    collector.show_progress_summary()
    
    print(f"\nChoose an action:")
    print(f"1. Start/Resume data collection")
    print(f"2. Show progress summary only")
    print(f"3. Exit")
    
    try:
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == "1":
            print(f"\n🚀 Starting collection...")
            print(f"💡 You can stop anytime with Ctrl+C")
            input("Press Enter to begin or Ctrl+C to cancel...")
            collector.start_collection()
            
        elif choice == "2":
            collector.show_progress_summary()
            
        elif choice == "3":
            print("👋 Goodbye!")
            
        else:
            print("❌ Invalid choice")
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    main()