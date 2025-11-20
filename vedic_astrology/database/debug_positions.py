#!/usr/bin/env python3
"""
Debug script to check what our calculator is actually computing
vs DrikPanchang reference data
"""

import sys
import os
sys.path.append('../tools')

from pyjhora_calculator import ProfessionalAstrologyCalculator
from datetime import datetime

def debug_planetary_positions():
    """Debug planetary positions to understand the discrepancies"""
    
    print("🔍 DEBUGGING PLANETARY POSITION CALCULATIONS")
    print("=" * 60)
    
    # Initialize calculator
    calc = ProfessionalAstrologyCalculator()
    
    # Test multiple times to see if time affects the results
    test_times = [
        datetime(2025, 11, 20, 0, 0, 0),   # Midnight
        datetime(2025, 11, 20, 5, 30, 0),  # 5:30 AM
        datetime(2025, 11, 20, 12, 0, 0),  # Noon
        datetime(2025, 11, 20, 18, 0, 0),  # 6 PM
    ]
    
    # DrikPanchang reference data (absolute longitudes)
    dp_reference = {
        'Sun': 213.8817,      # 03° Vish 52' 54"
        'Moon': 212.9028,     # 02° Vish 54' 10"  
        'Mars': 227.1061,     # 17° Vish 06' 22"
        'Mercury': 214.3519,  # 04° Vish 21' 07"
        'Jupiter': 90.8061,   # 00° Kark 48' 22"
        'Venus': 202.3903,    # 22° Tula 23' 25"
        'Saturn': 330.9886,   # 00° Meen 59' 19"
        'Rahu': 320.1575,     # 20° Kumb 09' 27"
        'Ketu': 140.1575      # 20° Simh 09' 27"
    }
    
    print("📅 Testing different times to check consistency:")
    print()
    
    for test_time in test_times:
        print(f"⏰ Time: {test_time}")
        
        try:
            # Get our calculations
            positions = calc.get_planetary_positions(test_time)
            
            print(f"{'Planet':<10} {'DrikPanchang':<12} {'PyJHora':<12} {'Difference':<12}")
            print("-" * 50)
            
            for planet in ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']:
                if planet in positions and planet in dp_reference:
                    our_long = positions[planet]['longitude']
                    dp_long = dp_reference[planet]
                    diff = abs(our_long - dp_long)
                    
                    # Handle 360° wraparound
                    if diff > 180:
                        diff = 360 - diff
                    
                    print(f"{planet:<10} {dp_long:>10.4f}° {our_long:>10.4f}° {diff:>10.4f}°")
            
            print()
            
        except Exception as e:
            print(f"❌ Error for {test_time}: {e}")
            print()

def debug_specific_planet_details():
    """Debug specific planet details to understand calculation differences"""
    
    print("🔍 DETAILED PLANET ANALYSIS")
    print("=" * 50)
    
    calc = ProfessionalAstrologyCalculator()
    test_time = datetime(2025, 11, 20, 5, 30, 0)
    
    try:
        # Get complete analysis
        full_data = calc.get_complete_analysis(test_time)
        
        print(f"📅 Analysis for: {test_time}")
        print(f"📍 Location: {full_data['location']}")
        print(f"🧮 Engine: {full_data['calculation_engine']}")
        print()
        
        # Check panchanga data for date verification
        if 'panchanga' in full_data:
            print("📊 Panchanga Elements:")
            for element, data in full_data['panchanga'].items():
                print(f"  {element}: {data.get('number', 'N/A')} - {data.get('name', 'N/A')}")
            print()
        
        # Check planetary details
        if 'planetary_positions' in full_data:
            print("🪐 Detailed Planetary Positions:")
            for planet, data in full_data['planetary_positions'].items():
                print(f"  {planet}:")
                print(f"    Longitude: {data['longitude']:.6f}°")
                print(f"    Sign: {data['sign']} (#{data['sign_number']})")
                print(f"    Degree in sign: {data['degree_in_sign']:.6f}°")
                print()
        
        # Special check for coordinate systems
        print("🌐 Coordinate System Check:")
        print("Checking if our coordinates are tropical vs sidereal...")
        
        # For Nov 20, 2025, approximate ayanamsa should be around 24.2°
        # If our coordinates are tropical, we need to subtract ayanamsa
        
        raw_positions = calc.get_planetary_positions(test_time)
        
        ayanamsa_estimate = 24.2  # Approximate ayanamsa for 2025
        
        print(f"Estimated Ayanamsa: {ayanamsa_estimate}°")
        print()
        print("Checking if subtracting ayanamsa improves accuracy:")
        print(f"{'Planet':<10} {'Current':<12} {'Adjusted':<12} {'DrikPanchang':<12} {'Improvement'}")
        print("-" * 70)
        
        dp_reference = {
            'Sun': 213.8817,
            'Moon': 212.9028,
            'Mars': 227.1061,
            'Mercury': 214.3519,
            'Jupiter': 90.8061,
            'Venus': 202.3903,
            'Saturn': 330.9886,
            'Rahu': 320.1575,
            'Ketu': 140.1575
        }
        
        for planet in ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn']:
            if planet in raw_positions and planet in dp_reference:
                current = raw_positions[planet]['longitude']
                adjusted = (current - ayanamsa_estimate) % 360
                dp_pos = dp_reference[planet]
                
                current_diff = min(abs(current - dp_pos), 360 - abs(current - dp_pos))
                adjusted_diff = min(abs(adjusted - dp_pos), 360 - abs(adjusted - dp_pos))
                
                improvement = "✅" if adjusted_diff < current_diff else "❌"
                
                print(f"{planet:<10} {current:>10.2f}° {adjusted:>10.2f}° {dp_pos:>10.2f}° {improvement}")
        
    except Exception as e:
        print(f"❌ Error in detailed analysis: {e}")

def main():
    """Main debugging function"""
    debug_planetary_positions()
    print("\n" + "=" * 60 + "\n")
    debug_specific_planet_details()

if __name__ == "__main__":
    main()