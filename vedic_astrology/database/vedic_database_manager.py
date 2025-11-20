#!/usr/bin/env python3
"""
Database Management System for Vedic Astrology Data
Professional-grade storage and retrieval of planetary positions
"""

import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, List, Optional, Tuple
import json
import logging

class VedicAstrologyDatabase:
    """
    Professional database manager for Vedic astrology calculations
    Handles all planetary positions, lagnas, panchanga elements
    """
    
    def __init__(self, config_file: str = None):
        self.config = self.load_config(config_file)
        self.connection = None
        self.setup_logging()
        
    def load_config(self, config_file: str = None) -> Dict:
        """Load database configuration"""
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)
        
        # Default configuration from environment
        return {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'database': os.getenv('MYSQL_DB', 'vedic_astrology'),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'charset': 'utf8mb4',
            'autocommit': True,
            'pool_size': 5
        }
    
    def setup_logging(self):
        """Setup logging for database operations"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('VedicAstrologyDB')
    
    def connect(self) -> bool:
        """Establish database connection"""
        try:
            self.connection = mysql.connector.connect(**self.config)
            if self.connection.is_connected():
                self.logger.info("Successfully connected to MySQL database")
                return True
        except Error as e:
            self.logger.error(f"Error connecting to MySQL: {e}")
            return False
        return False
    
    def disconnect(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            self.logger.info("MySQL connection closed")
    
    def execute_schema(self, schema_file: str = 'comprehensive_vedic_schema.sql') -> bool:
        """Execute the database schema creation"""
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()
            
            schema_path = os.path.join(os.path.dirname(__file__), schema_file)
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            # Split by delimiter and execute each statement
            statements = schema_sql.split(';')
            cursor = self.connection.cursor()
            
            for statement in statements:
                statement = statement.strip()
                if statement:
                    try:
                        cursor.execute(statement)
                        self.connection.commit()
                    except Error as e:
                        if "already exists" not in str(e):
                            self.logger.warning(f"Schema execution warning: {e}")
            
            cursor.close()
            self.logger.info("Database schema executed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing schema: {e}")
            return False
    
    def store_planetary_positions(self, calc_time: datetime, positions: Dict, 
                                location: Tuple[float, float] = (28.6139, 77.2090)) -> bool:
        """
        Store planetary positions in database
        
        Args:
            calc_time: Calculation timestamp
            positions: Dict with planetary position data
            location: (latitude, longitude) tuple
            
        Returns:
            bool: Success status
        """
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()
            
            cursor = self.connection.cursor()
            
            # Prepare planetary positions data
            insert_query = """
            INSERT INTO planetary_positions (
                calculation_time, location_lat, location_lon, ayanamsa_type, ayanamsa_value,
                sun_longitude, sun_nakshatra, sun_pada, sun_rasi, sun_navamsa,
                moon_longitude, moon_nakshatra, moon_pada, moon_rasi, moon_navamsa,
                mars_longitude, mars_nakshatra, mars_pada, mars_rasi, mars_navamsa, mars_retrograde,
                mercury_longitude, mercury_nakshatra, mercury_pada, mercury_rasi, mercury_navamsa, mercury_retrograde,
                jupiter_longitude, jupiter_nakshatra, jupiter_pada, jupiter_rasi, jupiter_navamsa, jupiter_retrograde,
                venus_longitude, venus_nakshatra, venus_pada, venus_rasi, venus_navamsa, venus_retrograde,
                saturn_longitude, saturn_nakshatra, saturn_pada, saturn_rasi, saturn_navamsa, saturn_retrograde,
                rahu_longitude, rahu_nakshatra, rahu_pada, rahu_rasi, rahu_navamsa,
                ketu_longitude, ketu_nakshatra, ketu_pada, ketu_rasi, ketu_navamsa
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                ayanamsa_value = VALUES(ayanamsa_value),
                sun_longitude = VALUES(sun_longitude),
                moon_longitude = VALUES(moon_longitude)
            """
            
            # Extract data from positions dict
            sun = positions.get('planetary_positions', {}).get('Sun', {})
            moon = positions.get('planetary_positions', {}).get('Moon', {})
            mars = positions.get('planetary_positions', {}).get('Mars', {})
            mercury = positions.get('planetary_positions', {}).get('Mercury', {})
            jupiter = positions.get('planetary_positions', {}).get('Jupiter', {})
            venus = positions.get('planetary_positions', {}).get('Venus', {})
            saturn = positions.get('planetary_positions', {}).get('Saturn', {})
            rahu = positions.get('planetary_positions', {}).get('Rahu', {})
            ketu = positions.get('planetary_positions', {}).get('Ketu', {})
            
            ayanamsa = positions.get('ayanamsa', {})
            
            data = (
                calc_time, location[0], location[1], 
                ayanamsa.get('name', 'Lahiri'), ayanamsa.get('value', 0),
                
                # Sun
                sun.get('longitude', 0), sun.get('nakshatra', ''), 
                sun.get('pada', 0), sun.get('sign', ''), sun.get('navamsa', ''),
                
                # Moon
                moon.get('longitude', 0), moon.get('nakshatra', ''), 
                moon.get('pada', 0), moon.get('sign', ''), moon.get('navamsa', ''),
                
                # Mars
                mars.get('longitude', 0), mars.get('nakshatra', ''), 
                mars.get('pada', 0), mars.get('sign', ''), mars.get('navamsa', ''), 
                mars.get('retrograde', False),
                
                # Mercury
                mercury.get('longitude', 0), mercury.get('nakshatra', ''), 
                mercury.get('pada', 0), mercury.get('sign', ''), mercury.get('navamsa', ''), 
                mercury.get('retrograde', False),
                
                # Jupiter
                jupiter.get('longitude', 0), jupiter.get('nakshatra', ''), 
                jupiter.get('pada', 0), jupiter.get('sign', ''), jupiter.get('navamsa', ''), 
                jupiter.get('retrograde', False),
                
                # Venus
                venus.get('longitude', 0), venus.get('nakshatra', ''), 
                venus.get('pada', 0), venus.get('sign', ''), venus.get('navamsa', ''), 
                venus.get('retrograde', False),
                
                # Saturn
                saturn.get('longitude', 0), saturn.get('nakshatra', ''), 
                saturn.get('pada', 0), saturn.get('sign', ''), saturn.get('navamsa', ''), 
                saturn.get('retrograde', False),
                
                # Rahu
                rahu.get('longitude', 0), rahu.get('nakshatra', ''), 
                rahu.get('pada', 0), rahu.get('sign', ''), rahu.get('navamsa', ''),
                
                # Ketu
                ketu.get('longitude', 0), ketu.get('nakshatra', ''), 
                ketu.get('pada', 0), ketu.get('sign', ''), ketu.get('navamsa', '')
            )
            
            cursor.execute(insert_query, data)
            self.connection.commit()
            cursor.close()
            
            self.logger.info(f"Stored planetary positions for {calc_time}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing planetary positions: {e}")
            return False
    
    def store_special_lagnas(self, calc_time: datetime, lagnas: Dict,
                           location: Tuple[float, float] = (28.6139, 77.2090)) -> bool:
        """Store special lagnas data"""
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()
            
            cursor = self.connection.cursor()
            
            insert_query = """
            INSERT INTO special_lagnas (
                calculation_time, location_lat, location_lon,
                lagna_longitude, lagna_nakshatra, lagna_pada, lagna_rasi, lagna_navamsa,
                maandi_longitude, maandi_nakshatra, maandi_pada, maandi_rasi,
                gulika_longitude, gulika_nakshatra, gulika_pada, gulika_rasi,
                bhava_lagna_longitude, bhava_lagna_nakshatra, bhava_lagna_pada, bhava_lagna_rasi,
                hora_lagna_longitude, hora_lagna_nakshatra, hora_lagna_pada, hora_lagna_rasi,
                ghati_lagna_longitude, ghati_lagna_nakshatra, ghati_lagna_pada, ghati_lagna_rasi,
                vighati_lagna_longitude, vighati_lagna_nakshatra, vighati_lagna_pada, vighati_lagna_rasi,
                varnada_lagna_longitude, varnada_lagna_nakshatra, varnada_lagna_pada, varnada_lagna_rasi,
                sree_lagna_longitude, sree_lagna_nakshatra, sree_lagna_pada, sree_lagna_rasi,
                pranapada_lagna_longitude, pranapada_lagna_nakshatra, pranapada_lagna_pada, pranapada_lagna_rasi,
                indu_lagna_longitude, indu_lagna_nakshatra, indu_lagna_pada, indu_lagna_rasi,
                bhrigu_bindu_longitude, bhrigu_bindu_nakshatra, bhrigu_bindu_pada, bhrigu_bindu_rasi
            ) VALUES (
                %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                lagna_longitude = VALUES(lagna_longitude)
            """
            
            # Extract lagna data
            lagna = lagnas.get('lagna', {})
            maandi = lagnas.get('maandi', {})
            gulika = lagnas.get('gulika', {})
            # ... extract other lagnas
            
            data = (
                calc_time, location[0], location[1],
                # Main lagna
                lagna.get('longitude', 0), lagna.get('nakshatra', ''),
                lagna.get('pada', 0), lagna.get('sign', ''), lagna.get('navamsa', ''),
                # Maandi
                maandi.get('longitude', 0), maandi.get('nakshatra', ''),
                maandi.get('pada', 0), maandi.get('sign', ''),
                # Gulika
                gulika.get('longitude', 0), gulika.get('nakshatra', ''),
                gulika.get('pada', 0), gulika.get('sign', ''),
                # ... add other lagnas with default values
                0, '', 0, '',  # bhava_lagna
                0, '', 0, '',  # hora_lagna  
                0, '', 0, '',  # ghati_lagna
                0, '', 0, '',  # vighati_lagna
                0, '', 0, '',  # varnada_lagna
                0, '', 0, '',  # sree_lagna
                0, '', 0, '',  # pranapada_lagna
                0, '', 0, '',  # indu_lagna
                0, '', 0, ''   # bhrigu_bindu
            )
            
            cursor.execute(insert_query, data)
            self.connection.commit()
            cursor.close()
            
            self.logger.info(f"Stored special lagnas for {calc_time}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing special lagnas: {e}")
            return False
    
    def store_panchanga(self, calc_time: datetime, panchanga: Dict,
                       location: Tuple[float, float] = (28.6139, 77.2090)) -> bool:
        """Store panchanga elements"""
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()
            
            cursor = self.connection.cursor()
            
            insert_query = """
            INSERT INTO panchanga_elements (
                calculation_time, location_lat, location_lon,
                tithi_number, tithi_name, tithi_percentage, tithi_remaining_hours,
                nakshatra_number, nakshatra_name, nakshatra_percentage, 
                nakshatra_remaining_hours, nakshatra_lord,
                yoga_number, yoga_name, yoga_percentage, yoga_remaining_hours,
                karana_number, karana_name, karana_percentage, karana_remaining_hours,
                var_number, var_name, var_lord
            ) VALUES (
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                tithi_percentage = VALUES(tithi_percentage),
                nakshatra_percentage = VALUES(nakshatra_percentage)
            """
            
            tithi = panchanga.get('tithi', {})
            nakshatra = panchanga.get('nakshatra', {})
            yoga = panchanga.get('yoga', {})
            karana = panchanga.get('karana', {})
            var = panchanga.get('var', {})
            
            data = (
                calc_time, location[0], location[1],
                # Tithi
                tithi.get('number', 0), tithi.get('name', ''),
                tithi.get('percentage', 0), tithi.get('remaining_hours', 0),
                # Nakshatra
                nakshatra.get('number', 0), nakshatra.get('name', ''),
                nakshatra.get('percentage', 0), nakshatra.get('remaining_hours', 0),
                nakshatra.get('lord', ''),
                # Yoga
                yoga.get('number', 0), yoga.get('name', ''),
                yoga.get('percentage', 0), yoga.get('remaining_hours', 0),
                # Karana
                karana.get('number', 0), karana.get('name', ''),
                karana.get('percentage', 0), karana.get('remaining_hours', 0),
                # Var
                var.get('number', 0), var.get('name', ''), var.get('lord', '')
            )
            
            cursor.execute(insert_query, data)
            self.connection.commit()
            cursor.close()
            
            self.logger.info(f"Stored panchanga for {calc_time}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing panchanga: {e}")
            return False
    
    def get_planetary_positions(self, query_time: datetime = None,
                              location: Tuple[float, float] = None) -> Optional[Dict]:
        """Retrieve planetary positions for a given time"""
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()
            
            if query_time is None:
                query_time = datetime.now()
            
            cursor = self.connection.cursor(dictionary=True)
            
            if location:
                cursor.callproc('GetPlanetaryPositionsForTime', 
                              [query_time, location[0], location[1]])
            else:
                query = """
                SELECT * FROM current_planetary_positions 
                WHERE calculation_time <= %s
                ORDER BY calculation_time DESC LIMIT 1
                """
                cursor.execute(query, (query_time,))
            
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                self.logger.info(f"Retrieved planetary positions for {query_time}")
                return result
            else:
                self.logger.warning(f"No planetary positions found for {query_time}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error retrieving planetary positions: {e}")
            return None
    
    def store_validation_result(self, calc_time: datetime, source: str,
                              validation_type: str, object_name: str,
                              our_value: float, reference_value: float,
                              notes: str = None) -> bool:
        """Store validation results for accuracy tracking"""
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()
            
            # Calculate differences
            difference_arcseconds = abs(our_value - reference_value) * 3600
            difference_percentage = abs(our_value - reference_value) / reference_value * 100 if reference_value != 0 else 0
            
            # Determine validation status and grade
            if difference_arcseconds <= 3.6:  # Within 0.01 degrees
                status = 'PASS'
                grade = 'A+' if difference_arcseconds <= 1.8 else 'A'
            elif difference_arcseconds <= 18:  # Within 0.05 degrees
                status = 'WARNING'
                grade = 'B+' if difference_arcseconds <= 9 else 'B'
            elif difference_arcseconds <= 36:  # Within 0.1 degrees
                status = 'FAIL'
                grade = 'C'
            else:
                status = 'FAIL'
                grade = 'F'
            
            cursor = self.connection.cursor()
            
            insert_query = """
            INSERT INTO validation_logs (
                calculation_time, data_source, validation_type, object_name,
                our_value, reference_value, difference_arcseconds, difference_percentage,
                validation_status, accuracy_grade, notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            data = (
                calc_time, source, validation_type, object_name,
                our_value, reference_value, difference_arcseconds, difference_percentage,
                status, grade, notes
            )
            
            cursor.execute(insert_query, data)
            self.connection.commit()
            cursor.close()
            
            self.logger.info(f"Stored validation result: {object_name} - {status} ({grade})")
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing validation result: {e}")
            return False
    
    def get_validation_summary(self, start_time: datetime = None, 
                             end_time: datetime = None) -> pd.DataFrame:
        """Get validation summary statistics"""
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()
            
            if start_time is None:
                start_time = datetime.now() - timedelta(days=7)
            if end_time is None:
                end_time = datetime.now()
            
            cursor = self.connection.cursor()
            cursor.callproc('GetValidationSummary', [start_time, end_time])
            
            results = cursor.fetchall()
            cursor.close()
            
            if results:
                columns = ['data_source', 'validation_type', 'object_name', 
                          'total_validations', 'passed', 'failed',
                          'avg_difference_arcseconds', 'max_difference_arcseconds',
                          'min_difference_arcseconds']
                
                df = pd.DataFrame(results, columns=columns)
                self.logger.info(f"Retrieved validation summary: {len(results)} records")
                return df
            else:
                self.logger.warning("No validation data found")
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"Error retrieving validation summary: {e}")
            return pd.DataFrame()

# Example usage and testing
if __name__ == "__main__":
    # Initialize database
    db = VedicAstrologyDatabase()
    
    if db.connect():
        print("✅ Database connection successful")
        
        # Create schema
        if db.execute_schema():
            print("✅ Database schema created/updated")
        
        # Test data storage (you would replace this with actual PyJHora data)
        test_time = datetime.now()
        test_positions = {
            'planetary_positions': {
                'Sun': {'longitude': 237.45, 'nakshatra': 'Jyeshtha', 'pada': 2, 'sign': 'Scorpio'},
                'Moon': {'longitude': 32.15, 'nakshatra': 'Mool', 'pada': 2, 'sign': 'Scorpio'},
                # ... other planets
            },
            'ayanamsa': {'name': 'Lahiri', 'value': 24.15}
        }
        
        if db.store_planetary_positions(test_time, test_positions):
            print("✅ Test planetary positions stored")
        
        # Test retrieval
        retrieved = db.get_planetary_positions(test_time)
        if retrieved:
            print("✅ Planetary positions retrieved successfully")
            print(f"Sun longitude: {retrieved.get('sun_longitude')}")
        
        db.disconnect()
    else:
        print("❌ Database connection failed")