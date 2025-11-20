#!/usr/bin/env python3
"""
SQLite Version of Vedic Database for Easy Testing
No MySQL setup required - uses local SQLite file
"""

import sqlite3
import os
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, List, Optional, Tuple
import json
import logging

class VedicAstrologyDatabaseSQLite:
    """
    SQLite version of the Vedic astrology database
    Perfect for testing and development
    """
    
    def __init__(self, db_file: str = "vedic_astrology.db"):
        self.db_file = db_file
        self.connection = None
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging for database operations"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('VedicAstrologyDBSQLite')
    
    def connect(self) -> bool:
        """Establish database connection"""
        try:
            self.connection = sqlite3.connect(self.db_file)
            self.connection.row_factory = sqlite3.Row  # Enable dict-like access
            self.logger.info(f"Successfully connected to SQLite database: {self.db_file}")
            return True
        except Exception as e:
            self.logger.error(f"Error connecting to SQLite: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.logger.info("SQLite connection closed")
    
    def create_schema(self) -> bool:
        """Create database schema"""
        try:
            if not self.connection:
                self.connect()
            
            cursor = self.connection.cursor()
            
            # Main planetary positions table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS planetary_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                calculation_time DATETIME NOT NULL,
                location_lat REAL DEFAULT 28.6139,
                location_lon REAL DEFAULT 77.2090,
                ayanamsa_type TEXT DEFAULT 'Lahiri',
                ayanamsa_value REAL NOT NULL,
                
                -- Main Planets
                sun_longitude REAL NOT NULL,
                sun_nakshatra TEXT,
                sun_pada INTEGER,
                sun_rasi TEXT,
                sun_navamsa TEXT,
                
                moon_longitude REAL NOT NULL,
                moon_nakshatra TEXT,
                moon_pada INTEGER,
                moon_rasi TEXT,
                moon_navamsa TEXT,
                
                mars_longitude REAL NOT NULL,
                mars_nakshatra TEXT,
                mars_pada INTEGER,
                mars_rasi TEXT,
                mars_navamsa TEXT,
                mars_retrograde BOOLEAN DEFAULT 0,
                
                mercury_longitude REAL NOT NULL,
                mercury_nakshatra TEXT,
                mercury_pada INTEGER,
                mercury_rasi TEXT,
                mercury_navamsa TEXT,
                mercury_retrograde BOOLEAN DEFAULT 0,
                
                jupiter_longitude REAL NOT NULL,
                jupiter_nakshatra TEXT,
                jupiter_pada INTEGER,
                jupiter_rasi TEXT,
                jupiter_navamsa TEXT,
                jupiter_retrograde BOOLEAN DEFAULT 0,
                
                venus_longitude REAL NOT NULL,
                venus_nakshatra TEXT,
                venus_pada INTEGER,
                venus_rasi TEXT,
                venus_navamsa TEXT,
                venus_retrograde BOOLEAN DEFAULT 0,
                
                saturn_longitude REAL NOT NULL,
                saturn_nakshatra TEXT,
                saturn_pada INTEGER,
                saturn_rasi TEXT,
                saturn_navamsa TEXT,
                saturn_retrograde BOOLEAN DEFAULT 0,
                
                rahu_longitude REAL NOT NULL,
                rahu_nakshatra TEXT,
                rahu_pada INTEGER,
                rahu_rasi TEXT,
                rahu_navamsa TEXT,
                
                ketu_longitude REAL NOT NULL,
                ketu_nakshatra TEXT,
                ketu_pada INTEGER,
                ketu_rasi TEXT,
                ketu_navamsa TEXT
            )''')
            
            # Special lagnas table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS special_lagnas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                calculation_time DATETIME NOT NULL,
                location_lat REAL NOT NULL,
                location_lon REAL NOT NULL,
                
                lagna_longitude REAL NOT NULL,
                lagna_nakshatra TEXT,
                lagna_pada INTEGER,
                lagna_rasi TEXT,
                
                maandi_longitude REAL,
                maandi_nakshatra TEXT,
                maandi_pada INTEGER,
                maandi_rasi TEXT,
                
                gulika_longitude REAL,
                gulika_nakshatra TEXT,
                gulika_pada INTEGER,
                gulika_rasi TEXT
            )''')
            
            # Panchanga elements table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS panchanga_elements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                calculation_time DATETIME NOT NULL,
                location_lat REAL NOT NULL,
                location_lon REAL NOT NULL,
                
                tithi_number INTEGER,
                tithi_name TEXT,
                tithi_percentage REAL,
                
                nakshatra_number INTEGER,
                nakshatra_name TEXT,
                nakshatra_percentage REAL,
                nakshatra_lord TEXT,
                
                yoga_number INTEGER,
                yoga_name TEXT,
                yoga_percentage REAL,
                
                karana_number INTEGER,
                karana_name TEXT,
                karana_percentage REAL,
                
                var_number INTEGER,
                var_name TEXT,
                var_lord TEXT
            )''')
            
            # Validation logs
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS validation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                calculation_time DATETIME NOT NULL,
                data_source TEXT NOT NULL,
                validation_type TEXT NOT NULL,
                object_name TEXT NOT NULL,
                our_value REAL,
                reference_value REAL,
                difference_arcseconds REAL,
                validation_status TEXT NOT NULL,
                accuracy_grade TEXT,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_planetary_time ON planetary_positions(calculation_time)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_lagnas_time ON special_lagnas(calculation_time)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_panchanga_time ON panchanga_elements(calculation_time)')
            
            self.connection.commit()
            cursor.close()
            
            self.logger.info("Database schema created successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating schema: {e}")
            return False
    
    def store_planetary_positions(self, calc_time: datetime, positions: Dict, 
                                location: Tuple[float, float] = (28.6139, 77.2090)) -> bool:
        """Store planetary positions in database"""
        try:
            if not self.connection:
                self.connect()
            
            cursor = self.connection.cursor()
            
            # Extract planetary data
            planets = positions.get('planetary_positions', {})
            ayanamsa = positions.get('ayanamsa', {})
            
            # Prepare data
            data = {
                'calculation_time': calc_time.isoformat(),
                'location_lat': location[0],
                'location_lon': location[1],
                'ayanamsa_type': ayanamsa.get('name', 'Lahiri'),
                'ayanamsa_value': ayanamsa.get('value', 0),
            }
            
            # Add planetary positions
            for planet in ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']:
                if planet in planets:
                    planet_data = planets[planet]
                    prefix = planet.lower()
                    
                    data[f'{prefix}_longitude'] = planet_data.get('longitude', 0)
                    data[f'{prefix}_nakshatra'] = planet_data.get('nakshatra', '')
                    data[f'{prefix}_pada'] = planet_data.get('pada', 0)
                    data[f'{prefix}_rasi'] = planet_data.get('sign', '')
                    data[f'{prefix}_navamsa'] = planet_data.get('navamsa_sign', '')
                    
                    if planet not in ['Rahu', 'Ketu']:  # Only physical planets can be retrograde
                        data[f'{prefix}_retrograde'] = planet_data.get('retrograde', False)
            
            # Insert data
            columns = ', '.join(data.keys())
            placeholders = ', '.join('?' * len(data))
            values = list(data.values())
            
            insert_query = f'''
            INSERT OR REPLACE INTO planetary_positions ({columns})
            VALUES ({placeholders})
            '''
            
            cursor.execute(insert_query, values)
            self.connection.commit()
            cursor.close()
            
            self.logger.info(f"Stored planetary positions for {calc_time}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing planetary positions: {e}")
            return False
    
    def get_latest_planetary_positions(self) -> Optional[Dict]:
        """Get the latest planetary positions"""
        try:
            if not self.connection:
                self.connect()
            
            cursor = self.connection.cursor()
            
            cursor.execute('''
            SELECT * FROM planetary_positions 
            ORDER BY calculation_time DESC 
            LIMIT 1
            ''')
            
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                result = dict(row)
                self.logger.info(f"Retrieved latest planetary positions for {result['calculation_time']}")
                return result
            else:
                self.logger.warning("No planetary positions found")
                return None
                
        except Exception as e:
            self.logger.error(f"Error retrieving planetary positions: {e}")
            return None
    
    def get_record_count(self, table_name: str) -> int:
        """Get count of records in a table"""
        try:
            if not self.connection:
                self.connect()
            
            cursor = self.connection.cursor()
            cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
            count = cursor.fetchone()[0]
            cursor.close()
            
            return count
            
        except Exception as e:
            self.logger.error(f"Error getting record count for {table_name}: {e}")
            return 0
    
    def get_database_stats(self) -> Dict:
        """Get comprehensive database statistics"""
        try:
            stats = {
                'planetary_positions': self.get_record_count('planetary_positions'),
                'special_lagnas': self.get_record_count('special_lagnas'),
                'panchanga_elements': self.get_record_count('panchanga_elements'),
                'validation_logs': self.get_record_count('validation_logs'),
                'database_file_size': os.path.getsize(self.db_file) if os.path.exists(self.db_file) else 0
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting database stats: {e}")
            return {}

# Test the SQLite database
if __name__ == "__main__":
    print("🗄️ TESTING SQLITE VEDIC DATABASE")
    print("=" * 40)
    
    # Initialize database
    db = VedicAstrologyDatabaseSQLite("test_vedic.db")
    
    if db.connect():
        print("✅ SQLite connection successful")
        
        # Create schema
        if db.create_schema():
            print("✅ Database schema created")
            
            # Test data storage
            from datetime import datetime
            import sys
            sys.path.append('../tools')
            
            try:
                from pyjhora_calculator import ProfessionalAstrologyCalculator
                
                calc = ProfessionalAstrologyCalculator()
                test_time = datetime.now()
                astro_data = calc.get_complete_analysis(test_time)
                
                if db.store_planetary_positions(test_time, astro_data):
                    print("✅ Test data stored successfully")
                    
                    # Retrieve data
                    latest = db.get_latest_planetary_positions()
                    if latest:
                        print("✅ Data retrieval successful")
                        print(f"   Time: {latest['calculation_time']}")
                        print(f"   Sun:  {latest['sun_longitude']:.3f}° {latest['sun_rasi']}")
                        print(f"   Moon: {latest['moon_longitude']:.3f}° {latest['moon_rasi']}")
                    
                    # Database stats
                    stats = db.get_database_stats()
                    print("✅ Database statistics:")
                    for table, count in stats.items():
                        if table != 'database_file_size':
                            print(f"   {table}: {count} records")
                        else:
                            print(f"   Database size: {count} bytes")
                
            except ImportError:
                print("⚠️  PyJHora not available for this test")
        
        db.disconnect()
        
        print("\n🎉 SQLite database test completed!")
    else:
        print("❌ SQLite connection failed")