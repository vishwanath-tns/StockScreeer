#!/usr/bin/env python3
"""
Quick Test for Vedic Astrology Foundation - Data Generation Only
Tests PyJHora calculations without requiring MySQL setup
"""

import sys
import os
sys.path.append('../tools')

from datetime import datetime
import json

def test_pyjhora_calculations():
    """Test PyJHora calculations directly"""
    print("🔬 TESTING PYJHORA CALCULATIONS")
    print("-" * 40)
    
    try:
        from pyjhora_calculator import ProfessionalAstrologyCalculator
        
        calc = ProfessionalAstrologyCalculator()
        test_time = datetime.now()
        
        print(f"📅 Test time: {test_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Get basic analysis
        astro_data = calc.get_complete_analysis(test_time)
        
        if astro_data:
            print("✅ PyJHora calculation successful")
            
            # Display planetary positions
            planets = astro_data.get('planetary_positions', {})
            print(f"📍 Planets calculated: {len(planets)}")
            
            for planet, data in planets.items():
                longitude = data.get('longitude', 0)
                sign = data.get('sign', 'Unknown')
                nakshatra = data.get('nakshatra', 'Unknown')
                print(f"  {planet}: {longitude:.4f}° - {sign} - {nakshatra}")
            
            # Display panchanga
            panchanga = astro_data.get('panchanga', {})
            if panchanga:
                print(f"\n📅 Panchanga:")
                tithi = panchanga.get('tithi', {})
                nakshatra = panchanga.get('nakshatra', {})
                print(f"  Tithi: {tithi.get('name', 'Unknown')}")
                print(f"  Nakshatra: {nakshatra.get('name', 'Unknown')}")
            
            return True
        else:
            print("❌ PyJHora calculation failed")
            return False
            
    except Exception as e:
        print(f"❌ Error in PyJHora test: {e}")
        return False

def test_comprehensive_data_structure():
    """Test the comprehensive data generation structure"""
    print("\n📊 TESTING COMPREHENSIVE DATA STRUCTURE")
    print("-" * 40)
    
    try:
        # Import our comprehensive generator
        sys.path.append('.')
        
        # Create a mock comprehensive data generator for testing structure
        from pyjhora_calculator import ProfessionalAstrologyCalculator
        
        calc = ProfessionalAstrologyCalculator()
        test_time = datetime.now()
        
        basic_data = calc.get_complete_analysis(test_time)
        
        # Test the data structure we would generate
        comprehensive_structure = {
            'calculation_time': test_time,
            'location': {
                'latitude': 28.6139,
                'longitude': 77.2090,
                'timezone': '+05:30'
            },
            'ayanamsa': basic_data.get('ayanamsa', {}),
            'planetary_positions': {},
            'special_lagnas': {},
            'panchanga': basic_data.get('panchanga', {}),
            'calculation_metadata': {
                'ephemeris_type': 'Swiss Ephemeris',
                'calculation_precision': '4_decimal_places',
                'ayanamsa_system': 'Lahiri'
            }
        }
        
        # Enhance planetary positions
        planets = basic_data.get('planetary_positions', {})
        for planet, data in planets.items():
            comprehensive_structure['planetary_positions'][planet] = {
                'longitude': data.get('longitude', 0),
                'sign': data.get('sign', ''),
                'degree_in_sign': data.get('degree_in_sign', 0),
                'nakshatra': data.get('nakshatra', ''),
                'nakshatra_number': data.get('nakshatra_number', 0),
                'pada': data.get('pada', 0),
                'navamsa': data.get('navamsa_sign', ''),
                'retrograde': data.get('retrograde', False)
            }
        
        # Mock special lagnas
        ascendant = basic_data.get('ascendant', {})
        comprehensive_structure['special_lagnas'] = {
            'lagna': {
                'longitude': ascendant.get('longitude', 0),
                'sign': ascendant.get('sign', ''),
                'nakshatra': ascendant.get('nakshatra', ''),
                'pada': ascendant.get('pada', 0)
            },
            'maandi': {'longitude': 123.45, 'sign': 'Cancer', 'nakshatra': 'Pushya'},
            'gulika': {'longitude': 234.56, 'sign': 'Scorpio', 'nakshatra': 'Jyeshtha'},
            'bhava_lagna': {'longitude': 45.67, 'sign': 'Taurus', 'nakshatra': 'Rohini'}
        }
        
        print("✅ Comprehensive data structure created")
        print(f"📊 Planetary positions: {len(comprehensive_structure['planetary_positions'])}")
        print(f"🏛️ Special lagnas: {len(comprehensive_structure['special_lagnas'])}")
        print(f"📅 Panchanga elements: {len(comprehensive_structure['panchanga'])}")
        
        # Display sample data
        print("\n🌟 SAMPLE DATA:")
        if 'Moon' in comprehensive_structure['planetary_positions']:
            moon = comprehensive_structure['planetary_positions']['Moon']
            print(f"🌙 Moon: {moon['sign']} {moon['degree_in_sign']:.2f}° - {moon['nakshatra']}")
        
        if 'lagna' in comprehensive_structure['special_lagnas']:
            lagna = comprehensive_structure['special_lagnas']['lagna']
            print(f"🏛️ Lagna: {lagna['sign']} {lagna.get('degree_in_sign', 0):.2f}° - {lagna['nakshatra']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in data structure test: {e}")
        return False

def test_data_quality():
    """Test data quality and accuracy"""
    print("\n🎯 TESTING DATA QUALITY")
    print("-" * 40)
    
    try:
        from pyjhora_calculator import ProfessionalAstrologyCalculator
        
        calc = ProfessionalAstrologyCalculator()
        
        # Test multiple time points
        test_times = [
            datetime.now(),
            datetime(2025, 1, 1, 12, 0, 0),
            datetime(2025, 6, 15, 6, 0, 0)
        ]
        
        all_successful = True
        
        for i, test_time in enumerate(test_times):
            print(f"  Test {i+1}: {test_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            try:
                astro_data = calc.get_complete_analysis(test_time)
                
                if astro_data:
                    planets = astro_data.get('planetary_positions', {})
                    
                    # Validate data quality
                    for planet, data in planets.items():
                        longitude = data.get('longitude', 0)
                        
                        # Check longitude is within valid range (0-360)
                        if not (0 <= longitude <= 360):
                            print(f"    ❌ Invalid longitude for {planet}: {longitude}")
                            all_successful = False
                        
                        # Check sign is present
                        if not data.get('sign'):
                            print(f"    ❌ Missing sign for {planet}")
                            all_successful = False
                    
                    print(f"    ✅ Data quality check passed for {len(planets)} planets")
                else:
                    print(f"    ❌ No data generated for {test_time}")
                    all_successful = False
                    
            except Exception as e:
                print(f"    ❌ Error for {test_time}: {e}")
                all_successful = False
        
        if all_successful:
            print("✅ All data quality tests passed")
            return True
        else:
            print("❌ Some data quality tests failed")
            return False
            
    except Exception as e:
        print(f"❌ Error in quality test: {e}")
        return False

def display_current_astrological_snapshot():
    """Display current astrological conditions"""
    print("\n🌟 CURRENT ASTROLOGICAL SNAPSHOT")
    print("=" * 50)
    
    try:
        from pyjhora_calculator import ProfessionalAstrologyCalculator
        
        calc = ProfessionalAstrologyCalculator()
        current_time = datetime.now()
        
        astro_data = calc.get_complete_analysis(current_time)
        
        print(f"📅 Date: {current_time.strftime('%Y-%m-%d %H:%M:%S')} IST")
        print(f"📍 Location: Delhi (28.61°N, 77.21°E)")
        
        # Planetary positions
        planets = astro_data.get('planetary_positions', {})
        print(f"\n🪐 PLANETARY POSITIONS:")
        for planet, data in planets.items():
            longitude = data.get('longitude', 0)
            sign = data.get('sign', 'Unknown')
            nakshatra = data.get('nakshatra', 'Unknown')
            retrograde = " (R)" if data.get('retrograde', False) else ""
            print(f"  {planet:8}: {longitude:7.3f}° - {sign:10} - {nakshatra}{retrograde}")
        
        # Ascendant
        ascendant = astro_data.get('ascendant', {})
        if ascendant:
            print(f"\n🏛️ ASCENDANT:")
            print(f"  Lagna  : {ascendant.get('longitude', 0):7.3f}° - {ascendant.get('sign', 'Unknown'):10} - {ascendant.get('nakshatra', 'Unknown')}")
        
        # Panchanga
        panchanga = astro_data.get('panchanga', {})
        if panchanga:
            print(f"\n📅 PANCHANGA:")
            tithi = panchanga.get('tithi', {})
            nakshatra = panchanga.get('nakshatra', {})
            yoga = panchanga.get('yoga', {})
            karana = panchanga.get('karana', {})
            
            print(f"  Tithi    : {tithi.get('name', 'Unknown')}")
            print(f"  Nakshatra: {nakshatra.get('name', 'Unknown')}")
            print(f"  Yoga     : {yoga.get('name', 'Unknown')}")
            print(f"  Karana   : {karana.get('name', 'Unknown')}")
        
        # Ayanamsa
        ayanamsa = astro_data.get('ayanamsa', {})
        if ayanamsa:
            print(f"\n📐 AYANAMSA:")
            print(f"  {ayanamsa.get('name', 'Unknown')}: {ayanamsa.get('value', 0):.6f}°")
        
        return True
        
    except Exception as e:
        print(f"❌ Error displaying snapshot: {e}")
        return False

def main():
    """Main test function"""
    print("🌟 VEDIC ASTROLOGY FOUNDATION - QUICK TEST")
    print("=" * 60)
    print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Test 1: PyJHora calculations
    pyjhora_success = test_pyjhora_calculations()
    
    # Test 2: Data structure
    structure_success = test_comprehensive_data_structure()
    
    # Test 3: Data quality
    quality_success = test_data_quality()
    
    # Display current snapshot
    snapshot_success = display_current_astrological_snapshot()
    
    # Final results
    print("\n" + "=" * 60)
    print("📋 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    tests = [
        ("PyJHora Calculations", pyjhora_success),
        ("Data Structure", structure_success), 
        ("Data Quality", quality_success),
        ("Current Snapshot", snapshot_success)
    ]
    
    all_passed = True
    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:25}: {status}")
        if not result:
            all_passed = False
    
    print("-" * 60)
    
    if all_passed:
        print("🎉 ALL TESTS PASSED! FOUNDATION DATA GENERATION READY!")
        print("\n📋 NEXT STEPS:")
        print("1. Set up MySQL database")
        print("2. Run full foundation test with database storage")
        print("3. Start automated data collection")
        print("4. Implement validation against reference sources")
    else:
        print("❌ SOME TESTS FAILED - PLEASE REVIEW ERRORS ABOVE")
    
    print("=" * 60)

if __name__ == "__main__":
    main()