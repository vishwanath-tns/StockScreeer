#!/usr/bin/env python3
"""
Deep dive into PyJHora raw data to understand the coordinate issues
"""

import sys
import os
sys.path.append('../tools')
sys.path.append('D:/MyProjects/StockScreeer')

# Direct PyJHora imports to check raw data
from jhora.panchanga import drik
from jhora.horoscope.chart.chart import Chart
from jhora.horoscope.chart.charts import mixed_chart
from datetime import datetime

def raw_pyjhora_test():
    """Test PyJHora directly without our wrapper to see raw data"""
    
    print("🔬 RAW PYJHORA DATA ANALYSIS")
    print("=" * 50)
    
    # Set up location (Mumbai)
    place = drik.Place('Mumbai', 19.076, 72.8777, 5.5)  # Mumbai coordinates with IST offset
    
    # Test date: November 20, 2025, 5:30 AM
    test_date = datetime(2025, 11, 20, 5, 30, 0)
    
    print(f"📅 Test Date: {test_date}")
    print(f"📍 Location: {place}")
    print()
    
    # Convert to Julian Day
    jd = drik.sidereal_time.julian_day(test_date.year, test_date.month, test_date.day, 
                                       test_date.hour + test_date.minute/60.0 + test_date.second/3600.0)
    
    print(f"🌌 Julian Day: {jd}")
    print()
    
    # Get raw planetary positions
    print("🪐 RAW PLANETARY POSITIONS FROM PYJHORA:")
    raw_positions = drik.planetary_positions(jd, place)
    
    planet_names = ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Rahu', 'Ketu']
    
    print("Raw data structure:")
    for i, planet_data in enumerate(raw_positions):
        if i < len(planet_names):
            print(f"  {planet_names[i]}: {planet_data}")
    
    print()
    print("Interpreted positions:")
    print(f"{'Planet':<10} {'Raw Data':<20} {'Calculated Longitude':<20}")
    print("-" * 55)
    
    for i, planet_data in enumerate(raw_positions):
        if i < len(planet_names):
            planet_name = planet_names[i]
            
            # PyJHora returns [planet_index, degree_in_sign, sign_number]
            if isinstance(planet_data, (list, tuple)) and len(planet_data) >= 3:
                planet_index = planet_data[0]
                degree_in_sign = planet_data[1] 
                sign_number = planet_data[2]
                
                # Calculate absolute longitude
                longitude = (sign_number * 30 + degree_in_sign) % 360
                
                print(f"{planet_name:<10} {str(planet_data):<20} {longitude:<20.6f}")
            else:
                print(f"{planet_name:<10} {str(planet_data):<20} {'Error parsing':<20}")
    
    print()
    
    # Test individual planet calculation
    print("🧪 INDIVIDUAL PLANET TESTS:")
    print()
    
    # Test Sun position specifically
    print("☀️ Testing Sun position:")
    try:
        sun_long = drik.lunar_longitude(jd, place, as_string=False)  # This might be wrong function
        print(f"  Using lunar_longitude: {sun_long}")
    except:
        pass
    
    try:
        sun_long = drik.sun_longitude(jd, as_string=False)
        print(f"  Using sun_longitude: {sun_long}")
    except:
        pass
    
    # Test Mars position specifically  
    print("♂️ Testing Mars position:")
    try:
        mars_long = drik.mars_longitude(jd, as_string=False)
        print(f"  Using mars_longitude: {mars_long}")
    except:
        pass
    
    # Test Jupiter position specifically
    print("♃ Testing Jupiter position:")
    try:
        jupiter_long = drik.jupiter_longitude(jd, as_string=False)
        print(f"  Using jupiter_longitude: {jupiter_long}")
    except:
        pass
    
    print()
    
    # Check ayanamsa
    print("🌐 AYANAMSA CHECK:")
    try:
        ayanamsa = drik.ayanamsa(jd)
        print(f"  Current Ayanamsa: {ayanamsa}°")
        
        # Apply ayanamsa correction to see if it helps
        print(f"\n🔧 APPLYING AYANAMSA CORRECTION:")
        print(f"{'Planet':<10} {'Sidereal':<12} {'Tropical':<12} {'DrikPanchang':<12} {'Sidereal Match':<12}")
        print("-" * 70)
        
        dp_reference = {
            'Sun': 213.8817,
            'Moon': 212.9028,
            'Mars': 227.1061,
            'Mercury': 214.3519,
            'Jupiter': 90.8061,
            'Venus': 202.3903,
            'Saturn': 330.9886,
        }
        
        for i, planet_data in enumerate(raw_positions[:7]):  # First 7 planets
            if i < len(planet_names):
                planet_name = planet_names[i]
                
                if isinstance(planet_data, (list, tuple)) and len(planet_data) >= 3:
                    degree_in_sign = planet_data[1] 
                    sign_number = planet_data[2]
                    
                    # Sidereal longitude (what we calculated)
                    sidereal_long = (sign_number * 30 + degree_in_sign) % 360
                    
                    # Tropical longitude (add ayanamsa)
                    tropical_long = (sidereal_long + ayanamsa) % 360
                    
                    dp_pos = dp_reference.get(planet_name, 0)
                    
                    # Check which is closer
                    sidereal_diff = min(abs(sidereal_long - dp_pos), 360 - abs(sidereal_long - dp_pos))
                    tropical_diff = min(abs(tropical_long - dp_pos), 360 - abs(tropical_long - dp_pos))
                    
                    better_match = "Sidereal" if sidereal_diff < tropical_diff else "Tropical"
                    
                    print(f"{planet_name:<10} {sidereal_long:<12.2f} {tropical_long:<12.2f} {dp_pos:<12.2f} {better_match:<12}")
    
    except Exception as e:
        print(f"  Error checking ayanamsa: {e}")

def main():
    """Main function for raw PyJHora testing"""
    raw_pyjhora_test()

if __name__ == "__main__":
    main()