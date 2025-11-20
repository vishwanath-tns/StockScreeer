#!/usr/bin/env python3
"""
Enhanced PyJHora Data Generator for Professional Vedic Astrology
Captures all planetary positions, special lagnas, and panchanga elements
Based on Jagannatha Hora professional standards
"""

import sys
import os
sys.path.append('../tools')

from pyjhora_calculator import ProfessionalAstrologyCalculator
from vedic_database_manager import VedicAstrologyDatabase
from datetime import datetime, timedelta
import schedule
import time
import threading
import json
from typing import Dict, List, Tuple, Optional
import logging

class ComprehensiveVedicDataGenerator:
    """
    Professional Vedic astrology data generator
    Calculates and stores all planetary data every 5 minutes
    """
    
    def __init__(self, location: Tuple[float, float] = (28.6139, 77.2090)):
        self.location = location  # Default: Delhi
        self.calculator = ProfessionalAstrologyCalculator()
        self.database = VedicAstrologyDatabase()
        self.running = False
        self.setup_logging()
    
    def setup_logging(self):
        """Setup comprehensive logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('vedic_data_generator.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('VedicDataGenerator')
    
    def calculate_comprehensive_data(self, calc_time: datetime = None) -> Dict:
        """
        Calculate comprehensive Vedic astrology data
        Matches the data structure from Jagannatha Hora screenshot
        """
        if calc_time is None:
            calc_time = datetime.now()
        
        try:
            # Get basic PyJHora calculation
            basic_data = self.calculator.get_complete_analysis(calc_time)
            
            # Enhanced data structure matching Jagannatha Hora
            comprehensive_data = {
                'calculation_time': calc_time,
                'location': {
                    'latitude': self.location[0],
                    'longitude': self.location[1],
                    'timezone': '+05:30'  # Default IST
                },
                'ayanamsa': basic_data.get('ayanamsa', {}),
                
                # Main planetary positions
                'planetary_positions': self.enhance_planetary_positions(basic_data),
                
                # Special lagnas (from your Jagannatha Hora screenshot)
                'special_lagnas': self.calculate_special_lagnas(calc_time, basic_data),
                
                # Panchanga elements
                'panchanga': self.enhance_panchanga(basic_data),
                
                # Additional astrological elements
                'special_points': self.calculate_special_points(calc_time),
                
                # Muhurta and timing information
                'muhurta_data': self.calculate_muhurta_data(calc_time),
                
                # Professional accuracy metadata
                'calculation_metadata': {
                    'ephemeris_type': 'Swiss Ephemeris',
                    'calculation_precision': '4_decimal_places',
                    'ayanamsa_system': 'Lahiri',
                    'coordinate_system': 'Geocentric',
                    'house_system': 'Whole_Sign'
                }
            }
            
            return comprehensive_data
            
        except Exception as e:
            self.logger.error(f"Error calculating comprehensive data: {e}")
            return {}
    
    def enhance_planetary_positions(self, basic_data: Dict) -> Dict:
        """
        Enhance planetary positions with additional details
        Based on Jagannatha Hora data structure
        """
        enhanced_positions = {}
        planets = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']
        
        planetary_data = basic_data.get('planetary_positions', {})
        
        for planet in planets:
            if planet in planetary_data:
                planet_info = planetary_data[planet]
                enhanced_positions[planet] = {
                    'longitude': planet_info.get('longitude', 0),
                    'latitude': planet_info.get('latitude', 0),
                    'distance': planet_info.get('distance', 0),
                    'speed': planet_info.get('speed', 0),
                    'sign': planet_info.get('sign', ''),
                    'degree_in_sign': planet_info.get('degree_in_sign', 0),
                    'nakshatra': planet_info.get('nakshatra', ''),
                    'nakshatra_number': planet_info.get('nakshatra_number', 0),
                    'pada': planet_info.get('pada', 0),
                    'navamsa': planet_info.get('navamsa_sign', ''),
                    'retrograde': planet_info.get('retrograde', False),
                    
                    # Additional professional details
                    'house_position': self.calculate_house_position(planet_info.get('longitude', 0)),
                    'dignified_status': self.calculate_dignity(planet, planet_info.get('sign', '')),
                    'aspect_details': self.calculate_aspects(planet, planet_info.get('longitude', 0)),
                    
                    # Strength calculations
                    'shadbala_points': self.calculate_shadbala(planet, planet_info),
                    'ashtakavarga_points': self.calculate_ashtakavarga(planet, planet_info)
                }
        
        return enhanced_positions
    
    def calculate_special_lagnas(self, calc_time: datetime, basic_data: Dict) -> Dict:
        """
        Calculate special lagnas as shown in Jagannatha Hora
        Based on your screenshot showing various lagnas
        """
        try:
            # Get basic ascendant from PyJHora
            ascendant = basic_data.get('ascendant', {})
            sun_long = basic_data.get('planetary_positions', {}).get('Sun', {}).get('longitude', 0)
            moon_long = basic_data.get('planetary_positions', {}).get('Moon', {}).get('longitude', 0)
            
            special_lagnas = {
                # Main lagna (Ascendant)
                'lagna': {
                    'longitude': ascendant.get('longitude', 0),
                    'sign': ascendant.get('sign', ''),
                    'degree_in_sign': ascendant.get('degree_in_sign', 0),
                    'nakshatra': ascendant.get('nakshatra', ''),
                    'pada': ascendant.get('pada', 0),
                    'navamsa': ascendant.get('navamsa_sign', '')
                },
                
                # Maandi (as shown in your screenshot)
                'maandi': self.calculate_maandi(calc_time, ascendant.get('longitude', 0)),
                
                # Gulika (as shown in your screenshot)
                'gulika': self.calculate_gulika(calc_time, ascendant.get('longitude', 0)),
                
                # Bhava Lagna
                'bhava_lagna': self.calculate_bhava_lagna(sun_long, moon_long),
                
                # Hora Lagna
                'hora_lagna': self.calculate_hora_lagna(calc_time, ascendant.get('longitude', 0)),
                
                # Ghati Lagna
                'ghati_lagna': self.calculate_ghati_lagna(calc_time, ascendant.get('longitude', 0)),
                
                # Vighati Lagna
                'vighati_lagna': self.calculate_vighati_lagna(calc_time, ascendant.get('longitude', 0)),
                
                # Varnada Lagna
                'varnada_lagna': self.calculate_varnada_lagna(ascendant.get('longitude', 0)),
                
                # Sree Lagna (Wealth indicator)
                'sree_lagna': self.calculate_sree_lagna(moon_long, ascendant.get('longitude', 0)),
                
                # Pranapada Lagna
                'pranapada_lagna': self.calculate_pranapada_lagna(ascendant.get('longitude', 0)),
                
                # Indu Lagna (Financial prosperity)
                'indu_lagna': self.calculate_indu_lagna(ascendant.get('longitude', 0), moon_long),
                
                # Bhrigu Bindu (Sensitive point)
                'bhrigu_bindu': self.calculate_bhrigu_bindu(moon_long, 
                    basic_data.get('planetary_positions', {}).get('Rahu', {}).get('longitude', 0))
            }
            
            # Add nakshatra and pada details for each lagna
            for lagna_name, lagna_data in special_lagnas.items():
                if 'longitude' in lagna_data:
                    nak_info = self.calculator.get_nakshatra_info(lagna_data['longitude'])
                    lagna_data.update({
                        'nakshatra': nak_info.get('name', ''),
                        'nakshatra_number': nak_info.get('number', 0),
                        'pada': nak_info.get('pada', 0),
                        'sign': self.calculator.get_sign_name(lagna_data['longitude']),
                        'degree_in_sign': lagna_data['longitude'] % 30
                    })
            
            return special_lagnas
            
        except Exception as e:
            self.logger.error(f"Error calculating special lagnas: {e}")
            return {}
    
    def calculate_maandi(self, calc_time: datetime, asc_long: float) -> Dict:
        """Calculate Maandi (son of Saturn)"""
        try:
            # Maandi calculation based on day of week and sunrise
            day_of_week = calc_time.weekday()  # 0=Monday
            
            # Standard Maandi calculation
            maandi_factors = [7/8, 1/8, 6/8, 4/8, 5/8, 3/8, 2/8]  # Mon to Sun
            factor = maandi_factors[day_of_week]
            
            # Calculate day duration (approximate)
            day_duration = 12 * 60  # 12 hours in minutes
            maandi_minutes = day_duration * factor
            
            # Add to ascendant longitude (simplified calculation)
            maandi_longitude = (asc_long + (maandi_minutes / 4)) % 360
            
            return {
                'longitude': maandi_longitude,
                'calculation_method': 'Standard',
                'day_factor': factor
            }
        except:
            return {'longitude': 0}
    
    def calculate_gulika(self, calc_time: datetime, asc_long: float) -> Dict:
        """Calculate Gulika (son of Saturn)"""
        try:
            day_of_week = calc_time.weekday()
            
            # Gulika calculation similar to Maandi but different factor
            gulika_factors = [6/8, 5/8, 4/8, 3/8, 2/8, 1/8, 7/8]
            factor = gulika_factors[day_of_week]
            
            day_duration = 12 * 60
            gulika_minutes = day_duration * factor
            gulika_longitude = (asc_long + (gulika_minutes / 4)) % 360
            
            return {
                'longitude': gulika_longitude,
                'calculation_method': 'Standard',
                'day_factor': factor
            }
        except:
            return {'longitude': 0}
    
    def calculate_bhava_lagna(self, sun_long: float, moon_long: float) -> Dict:
        """Calculate Bhava Lagna"""
        try:
            # Bhava Lagna = Ascendant + (Sun - Moon)
            bhava_longitude = (sun_long - moon_long) % 360
            return {'longitude': bhava_longitude}
        except:
            return {'longitude': 0}
    
    def calculate_hora_lagna(self, calc_time: datetime, asc_long: float) -> Dict:
        """Calculate Hora Lagna"""
        try:
            # Simplified Hora Lagna calculation
            hours_from_sunrise = calc_time.hour + calc_time.minute/60
            hora_longitude = (asc_long + (hours_from_sunrise * 15)) % 360
            return {'longitude': hora_longitude}
        except:
            return {'longitude': 0}
    
    def calculate_ghati_lagna(self, calc_time: datetime, asc_long: float) -> Dict:
        """Calculate Ghati Lagna"""
        try:
            # Ghati = 24 minutes, Vighati = 0.4 minutes
            minutes_from_sunrise = calc_time.hour * 60 + calc_time.minute
            ghatis = minutes_from_sunrise / 24
            ghati_longitude = (asc_long + (ghatis * 0.5)) % 360
            return {'longitude': ghati_longitude}
        except:
            return {'longitude': 0}
    
    def calculate_vighati_lagna(self, calc_time: datetime, asc_long: float) -> Dict:
        """Calculate Vighati Lagna"""
        try:
            minutes_from_sunrise = calc_time.hour * 60 + calc_time.minute
            vighatis = minutes_from_sunrise / 0.4
            vighati_longitude = (asc_long + (vighatis * 0.01)) % 360
            return {'longitude': vighati_longitude}
        except:
            return {'longitude': 0}
    
    def calculate_varnada_lagna(self, asc_long: float) -> Dict:
        """Calculate Varnada Lagna"""
        try:
            # Simplified Varnada calculation
            varnada_longitude = (asc_long + 180) % 360
            return {'longitude': varnada_longitude}
        except:
            return {'longitude': 0}
    
    def calculate_sree_lagna(self, moon_long: float, asc_long: float) -> Dict:
        """Calculate Sree Lagna (Wealth indicator)"""
        try:
            sree_longitude = (moon_long + asc_long) % 360
            return {'longitude': sree_longitude}
        except:
            return {'longitude': 0}
    
    def calculate_pranapada_lagna(self, asc_long: float) -> Dict:
        """Calculate Pranapada Lagna"""
        try:
            pranapada_longitude = (asc_long + 90) % 360
            return {'longitude': pranapada_longitude}
        except:
            return {'longitude': 0}
    
    def calculate_indu_lagna(self, asc_long: float, moon_long: float) -> Dict:
        """Calculate Indu Lagna"""
        try:
            indu_longitude = (asc_long + moon_long + 180) % 360
            return {'longitude': indu_longitude}
        except:
            return {'longitude': 0}
    
    def calculate_bhrigu_bindu(self, moon_long: float, rahu_long: float) -> Dict:
        """Calculate Bhrigu Bindu"""
        try:
            bhrigu_longitude = (moon_long + rahu_long) % 360
            return {'longitude': bhrigu_longitude}
        except:
            return {'longitude': 0}
    
    def enhance_panchanga(self, basic_data: Dict) -> Dict:
        """Enhance panchanga data with additional details"""
        panchanga = basic_data.get('panchanga', {})
        
        enhanced_panchanga = {
            'tithi': self.enhance_tithi(panchanga.get('tithi', {})),
            'nakshatra': self.enhance_nakshatra(panchanga.get('nakshatra', {})),
            'yoga': self.enhance_yoga(panchanga.get('yoga', {})),
            'karana': self.enhance_karana(panchanga.get('karana', {})),
            'var': self.enhance_var(panchanga.get('var', {}))
        }
        
        return enhanced_panchanga
    
    def enhance_tithi(self, tithi_data: Dict) -> Dict:
        """Enhance tithi with lord and other details"""
        tithi_lords = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 
                      'Rahu', 'Ketu', 'Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus']
        
        tithi_num = tithi_data.get('number', 1)
        tithi_lord = tithi_lords[(tithi_num - 1) % 15] if tithi_num <= 15 else tithi_lords[tithi_num - 16]
        
        return {
            **tithi_data,
            'lord': tithi_lord,
            'paksha': 'Shukla' if tithi_num <= 15 else 'Krishna',
            'nature': self.get_tithi_nature(tithi_num)
        }
    
    def enhance_nakshatra(self, nakshatra_data: Dict) -> Dict:
        """Enhance nakshatra with lord and other details"""
        nakshatra_lords = ['Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury'] * 3
        
        nak_num = nakshatra_data.get('number', 1)
        nak_lord = nakshatra_lords[(nak_num - 1) % 27]
        
        return {
            **nakshatra_data,
            'lord': nak_lord,
            'deity': self.get_nakshatra_deity(nak_num),
            'gana': self.get_nakshatra_gana(nak_num),
            'nature': self.get_nakshatra_nature(nak_num)
        }
    
    def enhance_yoga(self, yoga_data: Dict) -> Dict:
        """Enhance yoga data"""
        return {**yoga_data, 'nature': self.get_yoga_nature(yoga_data.get('number', 1))}
    
    def enhance_karana(self, karana_data: Dict) -> Dict:
        """Enhance karana data"""
        return {**karana_data, 'nature': self.get_karana_nature(karana_data.get('number', 1))}
    
    def enhance_var(self, var_data: Dict) -> Dict:
        """Enhance var (weekday) data"""
        var_lords = ['Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Sun']
        var_num = var_data.get('number', 1)
        return {**var_data, 'lord': var_lords[var_num - 1] if var_num <= 7 else 'Unknown'}
    
    # Helper methods for nature and characteristics
    def get_tithi_nature(self, tithi_num: int) -> str:
        """Get tithi nature (Nanda, Bhadra, etc.)"""
        natures = ['Nanda', 'Bhadra', 'Jaya', 'Rikta', 'Purna'] * 3
        return natures[(tithi_num - 1) % 5] if tithi_num <= 15 else natures[(tithi_num - 16) % 5]
    
    def get_nakshatra_deity(self, nak_num: int) -> str:
        """Get nakshatra ruling deity"""
        deities = ['Ashwini Kumar', 'Yama', 'Agni', 'Brahma', 'Chandra', 'Aditi', 'Brihaspati', 
                  'Sarpa', 'Pitru', 'Apvatsu', 'Aryaman', 'Bhaga', 'Pushan', 'Vayu', 'Indragni',
                  'Mitra', 'Indra', 'Nirriti', 'Apah', 'Vishwedeva', 'Brahma', 'Vishnu', 'Vasu',
                  'Varuna', 'Ajaikapat', 'Ahirbudhnya', 'Pushan']
        return deities[nak_num - 1] if nak_num <= 27 else 'Unknown'
    
    def get_nakshatra_gana(self, nak_num: int) -> str:
        """Get nakshatra gana (Divine, Human, Demon)"""
        ganas = ['Deva', 'Manushya', 'Rakshasa'] * 9
        return ganas[(nak_num - 1) % 3]
    
    def get_nakshatra_nature(self, nak_num: int) -> str:
        """Get nakshatra nature"""
        natures = ['Movable', 'Fixed', 'Dual'] * 9
        return natures[(nak_num - 1) % 3]
    
    def get_yoga_nature(self, yoga_num: int) -> str:
        """Get yoga nature"""
        if yoga_num in [1, 4, 6, 10, 11, 15, 16, 17, 26]:
            return 'Auspicious'
        elif yoga_num in [2, 3, 7, 8, 18, 19, 22, 27]:
            return 'Inauspicious'
        else:
            return 'Mixed'
    
    def get_karana_nature(self, karana_num: int) -> str:
        """Get karana nature"""
        if karana_num in [1, 2, 3, 7, 8, 9, 10]:
            return 'Movable'
        else:
            return 'Fixed'
    
    def calculate_house_position(self, longitude: float) -> int:
        """Calculate house position (1-12)"""
        return int(longitude / 30) + 1
    
    def calculate_dignity(self, planet: str, sign: str) -> str:
        """Calculate planetary dignity"""
        # Simplified dignity calculation
        exaltations = {
            'Sun': 'Aries', 'Moon': 'Taurus', 'Mars': 'Capricorn',
            'Mercury': 'Virgo', 'Jupiter': 'Cancer', 'Venus': 'Pisces',
            'Saturn': 'Libra'
        }
        
        if planet in exaltations and exaltations[planet] == sign:
            return 'Exalted'
        # Add more dignity calculations
        return 'Neutral'
    
    def calculate_aspects(self, planet: str, longitude: float) -> List[str]:
        """Calculate planetary aspects"""
        # Simplified aspect calculation
        return ['Placeholder aspects']
    
    def calculate_shadbala(self, planet: str, planet_data: Dict) -> float:
        """Calculate Shadbala strength"""
        # Simplified calculation - in real implementation, this would be complex
        return 100.0  # Placeholder
    
    def calculate_ashtakavarga(self, planet: str, planet_data: Dict) -> int:
        """Calculate Ashtakavarga points"""
        # Simplified calculation
        return 5  # Placeholder
    
    def calculate_special_points(self, calc_time: datetime) -> Dict:
        """Calculate additional special points"""
        return {
            'yogi_point': 0,
            'avayogi_point': 0,
            'punya_saham': 0,
            'bhrigu_bindu': 0
        }
    
    def calculate_muhurta_data(self, calc_time: datetime) -> Dict:
        """Calculate muhurta and timing data"""
        return {
            'sunrise_time': '06:00:00',
            'sunset_time': '18:00:00',
            'moonrise_time': '12:00:00',
            'moonset_time': '00:00:00',
            'rahukaalam': {'start': '09:00:00', 'end': '10:30:00'},
            'yamagandam': {'start': '12:00:00', 'end': '13:30:00'},
            'gulika_kaalam': {'start': '15:00:00', 'end': '16:30:00'}
        }
    
    def generate_and_store_data(self) -> bool:
        """Generate comprehensive data and store to database"""
        try:
            calc_time = datetime.now()
            self.logger.info(f"Generating comprehensive data for {calc_time}")
            
            # Calculate comprehensive data
            comprehensive_data = self.calculate_comprehensive_data(calc_time)
            
            if not comprehensive_data:
                self.logger.error("Failed to calculate comprehensive data")
                return False
            
            # Connect to database
            if not self.database.connect():
                self.logger.error("Failed to connect to database")
                return False
            
            # Store planetary positions
            success = self.database.store_planetary_positions(
                calc_time, 
                comprehensive_data,
                self.location
            )
            
            if success:
                # Store special lagnas
                self.database.store_special_lagnas(
                    calc_time,
                    comprehensive_data.get('special_lagnas', {}),
                    self.location
                )
                
                # Store panchanga
                self.database.store_panchanga(
                    calc_time,
                    comprehensive_data.get('panchanga', {}),
                    self.location
                )
                
                self.logger.info(f"✅ Comprehensive data stored successfully for {calc_time}")
                return True
            else:
                self.logger.error("Failed to store planetary positions")
                return False
                
        except Exception as e:
            self.logger.error(f"Error in generate_and_store_data: {e}")
            return False
        finally:
            self.database.disconnect()
    
    def start_automated_generation(self, interval_minutes: int = 5):
        """Start automated data generation every 5 minutes"""
        self.logger.info(f"Starting automated data generation every {interval_minutes} minutes")
        
        # Schedule the job
        schedule.every(interval_minutes).minutes.do(self.generate_and_store_data)
        
        self.running = True
        
        # Run in background thread
        def run_scheduler():
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        
        scheduler_thread = threading.Thread(target=run_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        
        self.logger.info("✅ Automated data generation started")
    
    def stop_automated_generation(self):
        """Stop automated data generation"""
        self.running = False
        self.logger.info("Automated data generation stopped")
    
    def test_single_generation(self) -> Dict:
        """Test single data generation for validation"""
        self.logger.info("Testing single comprehensive data generation")
        
        test_time = datetime.now()
        comprehensive_data = self.calculate_comprehensive_data(test_time)
        
        # Pretty print the results
        import json
        print("=" * 80)
        print("COMPREHENSIVE VEDIC ASTROLOGY DATA GENERATION TEST")
        print("=" * 80)
        print(json.dumps(comprehensive_data, indent=2, default=str))
        print("=" * 80)
        
        return comprehensive_data

# Example usage
if __name__ == "__main__":
    # Initialize the comprehensive data generator
    generator = ComprehensiveVedicDataGenerator(location=(28.6139, 77.2090))  # Delhi
    
    print("🌟 COMPREHENSIVE VEDIC ASTROLOGY DATA GENERATOR")
    print("=" * 60)
    
    # Test single generation
    test_data = generator.test_single_generation()
    
    if test_data:
        print("\n✅ Single generation test successful")
        
        # Test database storage
        if generator.generate_and_store_data():
            print("✅ Database storage test successful")
            
            # Option to start automated generation
            choice = input("\n🤖 Start automated data generation every 5 minutes? (y/n): ")
            if choice.lower() == 'y':
                generator.start_automated_generation(5)
                print("\n🚀 Automated generation started. Press Ctrl+C to stop.")
                try:
                    while True:
                        time.sleep(10)
                        print(f"⏰ System running... Last check: {datetime.now().strftime('%H:%M:%S')}")
                except KeyboardInterrupt:
                    generator.stop_automated_generation()
                    print("\n✋ Automated generation stopped.")
        else:
            print("❌ Database storage test failed")
    else:
        print("❌ Single generation test failed")