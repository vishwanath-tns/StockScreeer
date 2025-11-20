#!/usr/bin/env python3
"""
Test and Setup Script for Comprehensive Vedic Astrology Foundation
"""

import os
import sys
sys.path.append('.')

from comprehensive_data_generator import ComprehensiveVedicDataGenerator
from vedic_database_manager import VedicAstrologyDatabase
from datetime import datetime
import json

def test_database_setup():
    """Test database setup and schema creation"""
    print("🗄️ TESTING DATABASE SETUP")
    print("-" * 40)
    
    db = VedicAstrologyDatabase('config.json')
    
    if db.connect():
        print("✅ Database connection successful")
        
        if db.execute_schema():
            print("✅ Database schema created/updated successfully")
            
            # Test basic operations
            test_config = db.connection.cursor()
            test_config.execute("SELECT COUNT(*) FROM system_config")
            config_count = test_config.fetchone()[0]
            print(f"✅ System configuration entries: {config_count}")
            test_config.close()
            
            db.disconnect()
            return True
        else:
            print("❌ Failed to create database schema")
            return False
    else:
        print("❌ Database connection failed")
        print("💡 Make sure MySQL is running and credentials are correct")
        return False

def test_data_generation():
    """Test comprehensive data generation"""
    print("\n📊 TESTING DATA GENERATION")
    print("-" * 40)
    
    generator = ComprehensiveVedicDataGenerator()
    
    # Test single calculation
    test_data = generator.calculate_comprehensive_data()
    
    if test_data:
        print("✅ Data generation successful")
        
        # Display key data points
        planets = test_data.get('planetary_positions', {})
        print(f"📍 Planetary positions calculated: {len(planets)} planets")
        
        lagnas = test_data.get('special_lagnas', {})
        print(f"🏛️ Special lagnas calculated: {len(lagnas)} lagnas")
        
        panchanga = test_data.get('panchanga', {})
        print(f"📅 Panchanga elements: {len(panchanga)} elements")
        
        # Show sample data
        if 'Moon' in planets:
            moon = planets['Moon']
            print(f"🌙 Moon: {moon.get('sign', 'Unknown')} {moon.get('degree_in_sign', 0):.2f}° - {moon.get('nakshatra', 'Unknown')}")
        
        if 'lagna' in lagnas:
            lagna = lagnas['lagna']
            print(f"🏛️ Lagna: {lagna.get('sign', 'Unknown')} {lagna.get('degree_in_sign', 0):.2f}° - {lagna.get('nakshatra', 'Unknown')}")
        
        return True
    else:
        print("❌ Data generation failed")
        return False

def test_database_storage():
    """Test storing data in database"""
    print("\n💾 TESTING DATABASE STORAGE")
    print("-" * 40)
    
    generator = ComprehensiveVedicDataGenerator()
    
    if generator.generate_and_store_data():
        print("✅ Data storage successful")
        
        # Verify stored data
        db = VedicAstrologyDatabase()
        if db.connect():
            cursor = db.connection.cursor()
            
            # Check planetary positions
            cursor.execute("SELECT COUNT(*) FROM planetary_positions WHERE calculation_time >= NOW() - INTERVAL 1 HOUR")
            recent_positions = cursor.fetchone()[0]
            print(f"✅ Recent planetary positions in DB: {recent_positions}")
            
            # Check special lagnas
            cursor.execute("SELECT COUNT(*) FROM special_lagnas WHERE calculation_time >= NOW() - INTERVAL 1 HOUR")
            recent_lagnas = cursor.fetchone()[0]
            print(f"✅ Recent special lagnas in DB: {recent_lagnas}")
            
            # Check panchanga
            cursor.execute("SELECT COUNT(*) FROM panchanga_elements WHERE calculation_time >= NOW() - INTERVAL 1 HOUR")
            recent_panchanga = cursor.fetchone()[0]
            print(f"✅ Recent panchanga elements in DB: {recent_panchanga}")
            
            cursor.close()
            db.disconnect()
        
        return True
    else:
        print("❌ Database storage failed")
        return False

def display_current_data():
    """Display current astrological data"""
    print("\n🌟 CURRENT ASTROLOGICAL DATA")
    print("-" * 40)
    
    db = VedicAstrologyDatabase()
    if db.connect():
        current_data = db.get_planetary_positions()
        if current_data:
            print(f"⏰ Calculation time: {current_data.get('calculation_time', 'Unknown')}")
            print(f"🌞 Sun: {current_data.get('sun_longitude', 0):.4f}° - {current_data.get('sun_nakshatra', 'Unknown')}")
            print(f"🌙 Moon: {current_data.get('moon_longitude', 0):.4f}° - {current_data.get('moon_nakshatra', 'Unknown')}")
            print(f"🔴 Mars: {current_data.get('mars_longitude', 0):.4f}° - {current_data.get('mars_nakshatra', 'Unknown')}")
            print(f"💫 Mercury: {current_data.get('mercury_longitude', 0):.4f}° - {current_data.get('mercury_nakshatra', 'Unknown')}")
            print(f"🟡 Jupiter: {current_data.get('jupiter_longitude', 0):.4f}° - {current_data.get('jupiter_nakshatra', 'Unknown')}")
            print(f"💎 Venus: {current_data.get('venus_longitude', 0):.4f}° - {current_data.get('venus_nakshatra', 'Unknown')}")
            print(f"🔵 Saturn: {current_data.get('saturn_longitude', 0):.4f}° - {current_data.get('saturn_nakshatra', 'Unknown')}")
            print(f"🌑 Rahu: {current_data.get('rahu_longitude', 0):.4f}° - {current_data.get('rahu_nakshatra', 'Unknown')}")
            print(f"🌑 Ketu: {current_data.get('ketu_longitude', 0):.4f}° - {current_data.get('ketu_nakshatra', 'Unknown')}")
        else:
            print("❌ No current data found in database")
        
        db.disconnect()

def main():
    """Main test function"""
    print("🌟 COMPREHENSIVE VEDIC ASTROLOGY FOUNDATION SETUP")
    print("=" * 60)
    print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Test 1: Database Setup
    db_success = test_database_setup()
    
    if not db_success:
        print("\n❌ Database setup failed. Please check your MySQL configuration.")
        return
    
    # Test 2: Data Generation
    gen_success = test_data_generation()
    
    if not gen_success:
        print("\n❌ Data generation failed. Please check PyJHora installation.")
        return
    
    # Test 3: Database Storage
    storage_success = test_database_storage()
    
    if storage_success:
        # Display current data
        display_current_data()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! FOUNDATION IS READY!")
        print("=" * 60)
        print("✅ Database schema created")
        print("✅ Data generation working")
        print("✅ Database storage functional")
        print("✅ All planetary positions captured")
        print("✅ Special lagnas calculated")
        print("✅ Panchanga elements stored")
        
        print("\n📋 NEXT STEPS:")
        print("1. Set up automated 5-minute data generation")
        print("2. Implement Jagannatha Hora validation")
        print("3. Add DrikPanchang cross-verification")
        print("4. Build accuracy testing framework")
        print("5. Create API layer for trading applications")
        
        # Option to start automated generation
        print("\n🤖 Would you like to start automated data generation?")
        choice = input("Enter 'yes' to start 5-minute automated collection: ")
        
        if choice.lower() in ['yes', 'y']:
            print("\n🚀 Starting automated data generation...")
            generator = ComprehensiveVedicDataGenerator()
            generator.start_automated_generation(5)
            
            try:
                print("✅ Automated generation running. Press Ctrl+C to stop.")
                while True:
                    import time
                    time.sleep(30)
                    print(f"⏰ System active: {datetime.now().strftime('%H:%M:%S')}")
            except KeyboardInterrupt:
                generator.stop_automated_generation()
                print("\n✋ Automated generation stopped.")
        
    else:
        print("\n❌ FOUNDATION SETUP INCOMPLETE")
        print("Please review the errors above and retry.")

if __name__ == "__main__":
    main()