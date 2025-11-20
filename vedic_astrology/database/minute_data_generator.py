#!/usr/bin/env python3
"""
Minute-Level Planetary Data Generator
Professional-Grade Vedic Astrology Data Collection System
Based on validated PyJHora v1.0-professional-grade

Features:
- Calculates planetary positions every minute
- Stores in MySQL database with optimized schema
- Real-time data collection with error handling
- Professional accuracy (A+ grade validated)
- Comprehensive logging and monitoring
"""

import sys
import os
import logging
from datetime import datetime, timedelta
import time
import threading
import json
from typing import Dict, Any, Optional
import traceback

# Add tools to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'tools'))

try:
    from pyjhora_calculator import ProfessionalAstrologyCalculator
    import mysql.connector
    from mysql.connector import Error
    import schedule
except ImportError as e:
    print(f"Import error: {e}")
    print("Please install required packages: mysql-connector-python schedule")
    sys.exit(1)

class MinuteLevelDataGenerator:
    """
    Professional-grade data generator for minute-level planetary positions
    """
    
    def __init__(self, config_file: str = "database_config.json"):
        """Initialize the data generator"""
        self.config = self.load_config(config_file)
        self.calculator = ProfessionalAstrologyCalculator()
        self.db_connection = None
        self.is_running = False
        self.error_count = 0
        self.last_calculation_time = None
        
        # Setup logging
        self.setup_logging()
        
        # Connect to database
        self.connect_database()
        
        self.logger.info("MinuteLevelDataGenerator initialized successfully")
    
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
            },
            "collection": {
                "interval_seconds": 60,
                "max_errors": 10,
                "retry_delay": 30,
                "batch_size": 100
            },
            "location": {
                "name": "Mumbai",
                "latitude": 19.076,
                "longitude": 72.8777,
                "timezone_hours": 5.5
            }
        }
        
        config_path = os.path.join(os.path.dirname(__file__), config_file)
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults
                    for key in default_config:
                        if key in loaded_config:
                            default_config[key].update(loaded_config[key])
                        
            return default_config
            
        except Exception as e:
            print(f"Error loading config, using defaults: {e}")
            return default_config
    
    def setup_logging(self):
        """Setup comprehensive logging"""
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"data_generator_{datetime.now().strftime('%Y%m%d')}.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger('MinuteLevelGenerator')
    
    def connect_database(self):
        """Connect to MySQL database"""
        try:
            self.db_connection = mysql.connector.connect(
                **self.config['database'],
                autocommit=False,
                use_pure=True
            )
            
            if self.db_connection.is_connected():
                self.logger.info(f"Connected to MySQL database: {self.config['database']['database']}")
                return True
                
        except Error as e:
            self.logger.error(f"Database connection failed: {e}")
            return False
    
    def ensure_database_connection(self):
        """Ensure database connection is active"""
        try:
            if not self.db_connection or not self.db_connection.is_connected():
                self.logger.warning("Database connection lost, reconnecting...")
                self.connect_database()
                
        except Exception as e:
            self.logger.error(f"Database reconnection failed: {e}")
            raise
    
    def calculate_planetary_data(self, target_time: datetime) -> Dict[str, Any]:
        """Calculate complete planetary data for given time"""
        try:
            # Get complete astrological analysis
            astro_data = self.calculator.get_complete_analysis(target_time)
            
            # Extract planetary positions
            planets = astro_data.get('planetary_positions', {})
            
            # Add nakshatra calculations for each planet
            for planet_name, planet_data in planets.items():
                longitude = planet_data.get('longitude', 0)
                nakshatra_info = self.calculate_nakshatra_from_longitude(longitude)
                planet_data.update(nakshatra_info)
            
            # Calculate Julian Day
            julian_day = self.calculator._datetime_to_julian_day(target_time)
            
            # Calculate ayanamsa
            try:
                import swisseph as swe
                swe.set_sid_mode(swe.SIDM_LAHIRI)
                ayanamsa = swe.get_ayanamsa(julian_day)
            except:
                ayanamsa = 24.2  # Approximate value for 2025
            
            return {
                'timestamp': target_time,
                'julian_day': julian_day,
                'planets': planets,
                'panchanga': astro_data.get('panchanga', {}),
                'ayanamsa': ayanamsa,
                'calculation_engine': astro_data.get('calculation_engine', 'PyJHora v4.5.5'),
                'location': astro_data.get('location', 'Unknown')
            }
            
        except Exception as e:
            self.logger.error(f"Calculation failed for {target_time}: {e}")
            raise
    
    def calculate_nakshatra_from_longitude(self, longitude: float) -> Dict:
        """Calculate nakshatra and pada from longitude"""
        try:
            nakshatra_span = 360 / 27  # 13.333... degrees per nakshatra
            longitude = longitude % 360
            
            nakshatra_number = int(longitude / nakshatra_span) + 1
            position_in_nakshatra = (longitude % nakshatra_span)
            pada_span = nakshatra_span / 4
            pada = int(position_in_nakshatra / pada_span) + 1
            
            nakshatra_names = [
                "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu",
                "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta",
                "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha",
                "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
                "Uttara Bhadrapada", "Revati"
            ]
            
            nakshatra_name = nakshatra_names[nakshatra_number - 1] if 1 <= nakshatra_number <= 27 else "Unknown"
            
            return {
                'nakshatra': nakshatra_name,
                'nakshatra_number': nakshatra_number,
                'pada': pada
            }
            
        except Exception as e:
            self.logger.error(f"Nakshatra calculation failed for longitude {longitude}: {e}")
            return {
                'nakshatra': 'Unknown',
                'nakshatra_number': 0,
                'pada': 0
            }
    
    def store_planetary_data(self, data: Dict[str, Any]) -> bool:
        """Store planetary data in MySQL database"""
        try:
            self.ensure_database_connection()
            cursor = self.db_connection.cursor()
            
            # Prepare planetary positions data
            planets = data['planets']
            
            # SQL for planetary positions
            sql = """
            INSERT INTO planetary_positions_minute (
                timestamp, julian_day,
                sun_longitude, sun_sign, sun_degree_in_sign, sun_nakshatra, sun_pada,
                moon_longitude, moon_sign, moon_degree_in_sign, moon_nakshatra, moon_pada,
                mars_longitude, mars_sign, mars_degree_in_sign, mars_nakshatra, mars_pada,
                mercury_longitude, mercury_sign, mercury_degree_in_sign, mercury_nakshatra, mercury_pada,
                jupiter_longitude, jupiter_sign, jupiter_degree_in_sign, jupiter_nakshatra, jupiter_pada,
                venus_longitude, venus_sign, venus_degree_in_sign, venus_nakshatra, venus_pada,
                saturn_longitude, saturn_sign, saturn_degree_in_sign, saturn_nakshatra, saturn_pada,
                rahu_longitude, rahu_sign, rahu_degree_in_sign, rahu_nakshatra, rahu_pada,
                ketu_longitude, ketu_sign, ketu_degree_in_sign, ketu_nakshatra, ketu_pada,
                calculation_engine, location, ayanamsa
            ) VALUES (
                %s, %s,
                %s, %s, %s, %s, %s,  -- Sun
                %s, %s, %s, %s, %s,  -- Moon
                %s, %s, %s, %s, %s,  -- Mars
                %s, %s, %s, %s, %s,  -- Mercury
                %s, %s, %s, %s, %s,  -- Jupiter
                %s, %s, %s, %s, %s,  -- Venus
                %s, %s, %s, %s, %s,  -- Saturn
                %s, %s, %s, %s, %s,  -- Rahu
                %s, %s, %s, %s, %s,  -- Ketu
                %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                julian_day = VALUES(julian_day),
                sun_longitude = VALUES(sun_longitude),
                moon_longitude = VALUES(moon_longitude),
                mars_longitude = VALUES(mars_longitude),
                mercury_longitude = VALUES(mercury_longitude),
                jupiter_longitude = VALUES(jupiter_longitude),
                venus_longitude = VALUES(venus_longitude),
                saturn_longitude = VALUES(saturn_longitude),
                rahu_longitude = VALUES(rahu_longitude),
                ketu_longitude = VALUES(ketu_longitude)
            """
            
            # Prepare values
            values = [
                data['timestamp'], data['julian_day']
            ]
            
            # Add planetary data
            planet_order = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']
            
            for planet in planet_order:
                if planet in planets:
                    p = planets[planet]
                    values.extend([
                        p.get('longitude', 0),
                        p.get('sign', 'Unknown'),
                        p.get('degree_in_sign', 0),
                        p.get('nakshatra', 'Unknown'),
                        p.get('pada', 0)
                    ])
                else:
                    values.extend([0, 'Unknown', 0, 'Unknown', 0])
            
            # Add metadata
            values.extend([
                data.get('calculation_engine', 'PyJHora'),
                data.get('location', 'Unknown'),
                data.get('ayanamsa', 0)
            ])
            
            cursor.execute(sql, values)
            
            # Store panchanga data if available
            if 'panchanga' in data and data['panchanga']:
                self.store_panchanga_data(cursor, data)
            
            self.db_connection.commit()
            cursor.close()
            
            self.logger.info(f"Successfully stored data for {data['timestamp']}")
            return True
            
        except Error as e:
            self.logger.error(f"Database storage failed: {e}")
            if self.db_connection:
                self.db_connection.rollback()
            return False
            
        except Exception as e:
            self.logger.error(f"Unexpected error in storage: {e}")
            return False
    
    def store_panchanga_data(self, cursor, data: Dict[str, Any]):
        """Store panchanga data"""
        try:
            panchanga = data['panchanga']
            
            sql = """
            INSERT INTO panchanga_minute (
                timestamp, tithi_number, tithi_name, nakshatra_number, nakshatra_name,
                yoga_number, yoga_name, karana_number, karana_name
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                tithi_number = VALUES(tithi_number),
                nakshatra_number = VALUES(nakshatra_number),
                yoga_number = VALUES(yoga_number),
                karana_number = VALUES(karana_number)
            """
            
            values = [
                data['timestamp'],
                panchanga.get('tithi', {}).get('number', 0),
                panchanga.get('tithi', {}).get('name', 'Unknown'),
                panchanga.get('nakshatra', {}).get('number', 0),
                panchanga.get('nakshatra', {}).get('name', 'Unknown'),
                panchanga.get('yoga', {}).get('number', 0),
                panchanga.get('yoga', {}).get('name', 'Unknown'),
                panchanga.get('karana', {}).get('number', 0),
                panchanga.get('karana', {}).get('name', 'Unknown')
            ]
            
            cursor.execute(sql, values)
            
        except Exception as e:
            self.logger.warning(f"Panchanga storage failed: {e}")
    
    def collect_minute_data(self):
        """Collect and store data for current minute"""
        try:
            # Get current time rounded to minute
            current_time = datetime.now().replace(second=0, microsecond=0)
            
            self.logger.info(f"Collecting data for {current_time}")
            
            # Calculate planetary data
            data = self.calculate_planetary_data(current_time)
            
            # Store in database
            success = self.store_planetary_data(data)
            
            if success:
                self.last_calculation_time = current_time
                self.error_count = 0
                self.logger.info(f"Data collection successful for {current_time}")
            else:
                self.error_count += 1
                self.logger.error(f"Data collection failed for {current_time}")
            
            return success
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Data collection error: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def start_continuous_collection(self):
        """Start continuous data collection every minute"""
        self.logger.info("Starting continuous data collection...")
        self.is_running = True
        
        # Schedule data collection every minute
        schedule.every().minute.do(self.collect_minute_data)
        
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(1)
                
                # Check error count
                if self.error_count >= self.config['collection']['max_errors']:
                    self.logger.critical(f"Too many errors ({self.error_count}), stopping collection")
                    break
                    
            except KeyboardInterrupt:
                self.logger.info("Received shutdown signal")
                break
            except Exception as e:
                self.logger.error(f"Scheduler error: {e}")
                time.sleep(self.config['collection']['retry_delay'])
        
        self.stop_collection()
    
    def stop_collection(self):
        """Stop data collection"""
        self.is_running = False
        if self.db_connection:
            self.db_connection.close()
        self.logger.info("Data collection stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status"""
        return {
            'is_running': self.is_running,
            'last_calculation_time': self.last_calculation_time,
            'error_count': self.error_count,
            'database_connected': self.db_connection and self.db_connection.is_connected(),
            'config': self.config
        }

def create_config_file():
    """Create default configuration file"""
    config = {
        "database": {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "",
            "database": "vedic_astrology"
        },
        "collection": {
            "interval_seconds": 60,
            "max_errors": 10,
            "retry_delay": 30
        },
        "location": {
            "name": "Mumbai",
            "latitude": 19.076,
            "longitude": 72.8777,
            "timezone_hours": 5.5
        }
    }
    
    config_path = os.path.join(os.path.dirname(__file__), "database_config.json")
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"Configuration file created: {config_path}")
    print("Please update the database credentials before running the generator.")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Minute-Level Planetary Data Generator")
    parser.add_argument("--create-config", action="store_true", help="Create configuration file")
    parser.add_argument("--test", action="store_true", help="Test single calculation")
    parser.add_argument("--config", default="database_config.json", help="Configuration file path")
    
    args = parser.parse_args()
    
    if args.create_config:
        create_config_file()
        return
    
    try:
        generator = MinuteLevelDataGenerator(args.config)
        
        if args.test:
            print("Testing single calculation...")
            success = generator.collect_minute_data()
            print(f"Test {'successful' if success else 'failed'}")
            return
        
        print("Starting minute-level data collection...")
        print("Press Ctrl+C to stop")
        
        generator.start_continuous_collection()
        
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()