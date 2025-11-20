#!/usr/bin/env python3
"""
Test Historical Planetary Data System
Quick test to verify all components work before full collection
"""

import sys
import os
from datetime import datetime, timedelta

# Add tools to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'tools'))

def test_calculator():
    """Test the planetary calculator"""
    print("🧮 TESTING PLANETARY CALCULATOR")
    print("="*50)
    
    try:
        from pyjhora_calculator import ProfessionalAstrologyCalculator
        
        calc = ProfessionalAstrologyCalculator()
        
        # Test with a few different dates
        test_dates = [
            datetime(2024, 1, 1, 0, 0, 0),
            datetime(2024, 6, 15, 12, 30, 0),
            datetime(2025, 12, 31, 23, 59, 0)
        ]
        
        for test_date in test_dates:
            print(f"\n📅 Testing: {test_date}")
            positions = calc.get_planetary_positions(test_date)
            
            for planet, data in positions.items():
                print(f"  {planet}: {data['longitude']:.4f}° in {data['sign']}")
        
        print("\n✅ Calculator test: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Calculator test failed: {e}")
        return False

def test_database_setup():
    """Test database setup"""
    print("\n🗄️  TESTING DATABASE SETUP")
    print("="*50)
    
    try:
        from historical_planetary_app import HistoricalDataCollector
        
        # Use test database
        test_db = "test_historical.db"
        
        # Clean up old test db
        if os.path.exists(test_db):
            os.remove(test_db)
        
        collector = HistoricalDataCollector(test_db)
        
        print(f"✅ Database created: {test_db}")
        
        # Test collecting a few minutes of data
        print("📊 Testing small data collection...")
        
        import sqlite3
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        
        # Collect just 5 minutes of test data
        test_start = datetime(2024, 1, 1, 0, 0, 0)
        for i in range(5):
            test_time = test_start + timedelta(minutes=i)
            positions = collector.calculator.get_planetary_positions(test_time)
            
            # Insert test data
            row_data = [
                test_time.isoformat(),
                test_time.year, test_time.month, test_time.day,
                test_time.hour, test_time.minute
            ]
            
            planets = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']
            for planet in planets:
                if planet in positions:
                    data = positions[planet]
                    row_data.extend([
                        data['longitude'], data['sign'], 
                        data['degree_in_sign'], data['sign_number']
                    ])
                else:
                    row_data.extend([0.0, 'Unknown', 0.0, 0])
            
            cursor.execute('''
            INSERT INTO planetary_positions (
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
            ''', tuple(row_data))
        
        conn.commit()
        
        # Test querying
        cursor.execute("SELECT COUNT(*) FROM planetary_positions")
        count = cursor.fetchone()[0]
        
        print(f"✅ Test data inserted: {count} records")
        
        # Test query
        cursor.execute("SELECT * FROM planetary_positions WHERE timestamp = ?", 
                      (test_start.isoformat(),))
        result = cursor.fetchone()
        
        if result:
            print("✅ Database query successful")
            print(f"   Sample: {result[1]} - Sun at {result[6]:.4f}° in {result[7]}")
        
        conn.close()
        
        # Clean up test database
        os.remove(test_db)
        
        print("✅ Database test: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_gui_components():
    """Test GUI components (without actually opening windows)"""
    print("\n🖥️  TESTING GUI COMPONENTS")
    print("="*50)
    
    try:
        import tkinter as tk
        from tkcalendar import DateEntry
        
        # Test basic tkinter
        root = tk.Tk()
        root.withdraw()  # Hide window
        
        # Test DateEntry
        date_entry = DateEntry(root)
        
        root.destroy()
        
        print("✅ GUI components available")
        return True
        
    except Exception as e:
        print(f"❌ GUI test failed: {e}")
        return False

def show_system_summary():
    """Show system summary"""
    print("\n🎯 HISTORICAL PLANETARY DATA SYSTEM SUMMARY")
    print("="*60)
    
    print("""
📊 Collection Specifications:
   • Period: 2024-01-01 00:00:00 to 2026-01-01 00:00:00
   • Frequency: Every minute (1,051,200 total records)
   • Planets: Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu
   • Data: Longitude, sign, degree in sign, sign number for each planet
   • Storage: SQLite database with optimized indexing

🚀 Performance Estimates:
   • Collection Rate: ~100-500 records per second
   • Total Time: 30 minutes to 3 hours (depending on system)
   • Database Size: ~300-500 MB final size
   • Resume Support: Can pause and resume at any time

🔍 Browser Features:
   • Date/time picker for any moment in the 2-year period
   • Instant planetary position lookup
   • Navigation controls (day/hour forward/backward)
   • Range view showing multiple hours
   • Professional DMS notation display

💡 Usage Instructions:
   1. Run: python launch_historical_system.py
   2. Click "Start Collection" to begin data gathering
   3. Use "Open Data Browser" to explore collected data
   4. Collection can run in background while browsing partial data
    """)

def main():
    """Main test function"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║              🌟 Historical Planetary Data System Test                ║
║                        System Verification                          ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    
    success_count = 0
    total_tests = 3
    
    if test_calculator():
        success_count += 1
    
    if test_database_setup():
        success_count += 1
        
    if test_gui_components():
        success_count += 1
    
    show_system_summary()
    
    print(f"\n🎉 TEST SUMMARY")
    print("="*50)
    print(f"✅ Tests Passed: {success_count}/{total_tests}")
    print(f"🎯 System Status: {'READY' if success_count == total_tests else 'PARTIAL'}")
    
    if success_count == total_tests:
        print(f"\n🚀 System is ready! Launch with:")
        print(f"   python launch_historical_system.py")
    else:
        print(f"\n⚠️  Some components need attention. Check error messages above.")
        
    print(f"\n💡 What happens next:")
    print(f"   1. Launch the system to start data collection")
    print(f"   2. Collection will run for 2 years of minute-by-minute data")
    print(f"   3. Browser becomes available immediately as data is collected")
    print(f"   4. You can pause/resume collection at any time")

if __name__ == "__main__":
    main()