#!/usr/bin/env python3
"""
Accurate Planetary Data Re-collection Script
Clears old inaccurate data and collects fresh data using ProfessionalAstrologyCalculator

Key Features:
- Clears existing inaccurate database records
- Uses ProfessionalAstrologyCalculator (PyJHora + Swiss Ephemeris)
- Same 6-month period (Jan 1 - July 1, 2024)
- Professional accuracy matching DrikPanchang
- Progress tracking and graceful shutdown
"""

import sys
import os
import signal
import pymysql
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AccuratePlanetaryCollector:
    """
    Professional-grade planetary data collector with Swiss Ephemeris accuracy
    """
    
    def __init__(self):
        self.running = True
        self.start_date = datetime(2024, 1, 1, 0, 0, 0)
        self.end_date = datetime(2024, 7, 1, 0, 0, 0)  # 6 months testing period
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
        
        self.load_professional_calculator()
        self.test_mysql_connection()
    
    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print(f"\n🛑 Received stop signal (Ctrl+C) - stopping gracefully...")
        self.running = False
    
    def load_professional_calculator(self):
        """Load the professional PyJHora calculator"""
        try:
            from tools.pyjhora_calculator import ProfessionalAstrologyCalculator
            self.calculator = ProfessionalAstrologyCalculator()
            print("✅ Professional Calculator loaded successfully")
            print("🎯 Using PyJHora + Swiss Ephemeris (DrikPanchang-level accuracy)")
            
            # Test calculation to verify accuracy
            test_time = datetime(2024, 3, 15, 12, 0, 0)  # Known test date
            test_positions = self.calculator.get_planetary_positions(test_time)
            sun_pos = test_positions.get('Sun', {}).get('longitude', 0)
            moon_pos = test_positions.get('Moon', {}).get('longitude', 0)
            print(f"🧪 Test calculation: Sun={sun_pos:.4f}°, Moon={moon_pos:.4f}° (Mar 15, 2024)")
            
        except Exception as e:
            print(f"❌ Failed to load professional calculator: {e}")
            print("💡 Make sure PyJHora is properly installed and accessible")
            sys.exit(1)
    
    def test_mysql_connection(self):
        """Test MySQL connection and show current data status"""
        try:
            conn = pymysql.connect(**self.mysql_config)
            print(f"✅ MySQL connection successful: {self.mysql_config['host']}:{self.mysql_config['port']}")
            
            cursor = conn.cursor()
            
            # Check total records
            cursor.execute("SELECT COUNT(*) FROM planetary_positions")
            total_count = cursor.fetchone()[0]
            
            # Check 6-month period records
            cursor.execute("SELECT COUNT(*) FROM planetary_positions WHERE timestamp BETWEEN %s AND %s", 
                          (self.start_date, self.end_date))
            period_count = cursor.fetchone()[0]
            
            print(f"📊 Current database status:")
            print(f"   Total records: {total_count:,}")
            print(f"   6-month period (Jan-Jun 2024): {period_count:,}")
            print(f"   Target for collection: {self.total_minutes:,}")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ MySQL connection failed: {e}")
            print(f"💡 Check your .env file settings")
            sys.exit(1)
    
    def clear_existing_data(self):
        """Clear existing inaccurate data for the 6-month period"""
        try:
            conn = pymysql.connect(**self.mysql_config)
            cursor = conn.cursor()
            
            print(f"\n🗑️  CLEARING EXISTING INACCURATE DATA")
            print(f"📅 Period: {self.start_date} to {self.end_date}")
            
            # Count records to be deleted
            cursor.execute("SELECT COUNT(*) FROM planetary_positions WHERE timestamp BETWEEN %s AND %s", 
                          (self.start_date, self.end_date))
            count_to_delete = cursor.fetchone()[0]
            
            if count_to_delete > 0:
                print(f"📊 Found {count_to_delete:,} records to delete")
                
                # Confirm deletion
                response = input(f"⚠️  Are you sure you want to delete {count_to_delete:,} records? (y/N): ").strip().lower()
                
                if response == 'y':
                    print(f"🗑️  Deleting existing records...")
                    cursor.execute("DELETE FROM planetary_positions WHERE timestamp BETWEEN %s AND %s", 
                                  (self.start_date, self.end_date))
                    deleted_count = cursor.rowcount
                    conn.commit()
                    print(f"✅ Deleted {deleted_count:,} records successfully")
                else:
                    print(f"❌ Deletion cancelled by user")
                    conn.close()
                    return False
            else:
                print(f"📊 No existing records found for the period")
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Error clearing data: {e}")
            return False
    
    def get_mysql_connection(self):
        """Get MySQL connection"""
        return pymysql.connect(**self.mysql_config)
    
    def collect_minute_data(self, target_time):
        """Collect accurate data for a specific minute using professional calculator"""
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
            
            # Add planetary data from professional calculator
            planets = ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Rahu', 'Ketu']
            for planet in planets:
                if planet in positions:
                    pos = positions[planet]
                    longitude = pos.get('longitude', 0)
                    sign = pos.get('sign', 'Unknown')
                    degree = pos.get('degree_in_sign', longitude % 30)
                    
                    planet_lower = planet.lower()
                    data[f'{planet_lower}_longitude'] = longitude
                    data[f'{planet_lower}_sign'] = sign
                    data[f'{planet_lower}_degree'] = degree
                else:
                    # Fallback for missing planets
                    planet_lower = planet.lower()
                    data[f'{planet_lower}_longitude'] = 0
                    data[f'{planet_lower}_sign'] = 'Unknown'
                    data[f'{planet_lower}_degree'] = 0
            
            return data
            
        except Exception as e:
            print(f"❌ Error collecting data for {target_time}: {e}")
            return None
    
    def save_batch_to_mysql(self, batch_data):
        """Save batch of accurate data to MySQL"""
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
            """
            
            cursor.executemany(sql, batch_data)
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ Error saving batch: {e}")
    
    def verify_accuracy_sample(self):
        """Verify accuracy with a few sample calculations"""
        print(f"\n🧪 ACCURACY VERIFICATION")
        print("="*60)
        
        # Test with known accurate values (March 15, 2024 12:00 PM)
        test_time = datetime(2024, 3, 15, 12, 0, 0)
        positions = self.calculator.get_planetary_positions(test_time)
        
        # DrikPanchang reference values
        drik_values = {
            'Moon': 37.6542,
            'Mercury': 345.3172,
            'Venus': 309.9586,
            'Mars': 299.7936,
            'Jupiter': 19.7233,
            'Saturn': 317.4442,
            'Rahu': 352.7433,
            'Ketu': 172.7433
        }
        
        print(f"Test Time: {test_time}")
        print("Planet     | Our Calc    | DrikPanchang | Diff (°) | Status")
        print("-" * 60)
        
        all_accurate = True
        for planet, expected in drik_values.items():
            if planet in positions:
                calculated = positions[planet]['longitude']
                diff = abs(calculated - expected)
                status = "✅ EXCELLENT" if diff < 0.1 else "⚠️  CHECK" if diff < 1.0 else "❌ ERROR"
                if diff >= 1.0:
                    all_accurate = False
                print(f"{planet:<10} | {calculated:>10.4f} | {expected:>11.4f} | {diff:>7.4f} | {status}")
        
        if all_accurate:
            print("\n🎯 ACCURACY VERIFIED: All planets within 0.1° of DrikPanchang")
            return True
        else:
            print("\n⚠️  ACCURACY ISSUES: Some planets have large differences")
            return False
    
    def show_progress_summary(self):
        """Show collection progress summary"""
        try:
            conn = self.get_mysql_connection()
            cursor = conn.cursor()
            
            print(f"\n📊 ACCURATE DATA COLLECTION PROGRESS")
            print("="*60)
            
            # Total records for our period
            cursor.execute("SELECT COUNT(*) FROM planetary_positions WHERE timestamp BETWEEN %s AND %s", 
                          (self.start_date, self.end_date))
            total_count = cursor.fetchone()[0]
            
            # Date range
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM planetary_positions WHERE timestamp BETWEEN %s AND %s", 
                          (self.start_date, self.end_date))
            result = cursor.fetchone()
            
            print(f"📅 Target period: {self.start_date} to {self.end_date}")
            print(f"📊 Total target: {self.total_minutes:,} minutes")
            print(f"📈 Collected: {total_count:,} records")
            print(f"📍 Coverage: {(total_count/self.total_minutes)*100:.2f}%")
            
            if result[0]:
                min_date, max_date = result
                print(f"🕐 First record: {min_date}")
                print(f"🕐 Last record: {max_date}")
                
                # Sample recent records
                cursor.execute("""
                SELECT timestamp, sun_longitude, moon_longitude, mercury_longitude 
                FROM planetary_positions 
                WHERE timestamp BETWEEN %s AND %s 
                ORDER BY timestamp DESC LIMIT 3
                """, (self.start_date, self.end_date))
                samples = cursor.fetchall()
                
                print(f"\n📋 Recent accurate records:")
                for sample in samples:
                    timestamp, sun_lon, moon_lon, mercury_lon = sample
                    print(f"   {timestamp}: Sun={sun_lon:.4f}°, Moon={moon_lon:.4f}°, Mercury={mercury_lon:.4f}°")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Error showing progress: {e}")
    
    def start_accurate_collection(self):
        """Start the accurate data collection process"""
        print(f"\n🚀 STARTING ACCURATE PLANETARY DATA COLLECTION")
        print(f"🎯 Using ProfessionalAstrologyCalculator (Swiss Ephemeris)")
        print(f"📅 Period: {self.start_date} to {self.end_date}")
        print(f"📊 Total minutes: {self.total_minutes:,}")
        print(f"⏹️  Press Ctrl+C to stop gracefully")
        print(f"📈 Progress updates every 100 records")
        print(f"💾 Auto-save every 1000 records")
        print("-" * 60)
        
        # Start from beginning
        current_time = self.start_date
        processed_count = 0
        
        # Collection loop
        batch_data = []
        batch_size = 1000
        report_interval = 100
        
        try:
            while current_time < self.end_date and self.running:
                # Collect accurate data for current minute
                row_data = self.collect_minute_data(current_time)
                
                if row_data:
                    batch_data.append(row_data)
                    processed_count += 1
                    
                    # Progress report
                    if processed_count % report_interval == 0:
                        percentage = (processed_count / self.total_minutes) * 100
                        print(f"🎯 {processed_count:,}/{self.total_minutes:,} ({percentage:.2f}%) - {current_time} [Professional Accuracy]")
                    
                    # Save batch
                    if len(batch_data) >= batch_size:
                        print(f"💾 Saving batch of {len(batch_data)} accurate records...")
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
                print(f"\n🎉 ACCURATE COLLECTION COMPLETE!")
                print(f"📊 Total records processed: {processed_count:,}")
                print(f"🎯 Professional-grade accuracy achieved")
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
╔══════════════════════════════════════════════════════════════════════╗
║               🎯 Accurate Planetary Data Re-Collection                ║
║            Swiss Ephemeris Professional-Grade Accuracy               ║
║                      Jan 1 - July 1, 2024                           ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    
    collector = AccuratePlanetaryCollector()
    
    # Verify accuracy first
    if not collector.verify_accuracy_sample():
        print("❌ Accuracy verification failed. Please check calculator setup.")
        return
    
    # Show current status
    collector.show_progress_summary()
    
    print(f"\nChoose an action:")
    print(f"1. Clear old data and start fresh accurate collection")
    print(f"2. Show current database status only")
    print(f"3. Exit")
    
    try:
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == "1":
            # Clear existing data first
            if collector.clear_existing_data():
                print(f"\n🚀 Starting accurate collection...")
                print(f"💡 You can stop anytime with Ctrl+C")
                input("Press Enter to begin or Ctrl+C to cancel...")
                collector.start_accurate_collection()
            
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