#!/usr/bin/env python3
"""
Focused analysis of Mars and Jupiter coordinate discrepancies
"""

import sys
import os
sys.path.append('../tools')

from pyjhora_calculator import ProfessionalAstrologyCalculator
from datetime import datetime

def analyze_mars_jupiter_issue():
    """Analyze the Mars and Jupiter position discrepancy"""
    
    print("🔍 MARS & JUPITER POSITION ANALYSIS")
    print("=" * 50)
    
    calc = ProfessionalAstrologyCalculator()
    test_date = datetime(2025, 11, 20, 5, 30, 0)
    
    # Get our calculations
    positions = calc.get_planetary_positions(test_date)
    
    # DrikPanchang reference data
    dp_reference = {
        'Mars': {
            'longitude': 210 + 17 + 6/60 + 22/3600,  # 17° Vish 06' 22" = 227.1061°
            'sign': 'Vrishchika',  # Scorpio
            'expected_sign_number': 7  # Scorpio is 8th sign, but 0-indexed = 7
        },
        'Jupiter': {
            'longitude': 90 + 0 + 48/60 + 22/3600,   # 00° Kark 48' 22" = 90.8061°
            'sign': 'Karkata',  # Cancer  
            'expected_sign_number': 3  # Cancer is 4th sign, but 0-indexed = 3
        }
    }
    
    print(f"📅 Test Date: {test_date}")
    print()
    
    # Analyze Mars
    if 'Mars' in positions:
        mars_data = positions['Mars']
        dp_mars = dp_reference['Mars']
        
        print("♂️ MARS ANALYSIS:")
        print(f"  DrikPanchang: {dp_mars['longitude']:.4f}° in {dp_mars['sign']} (sign #{dp_mars['expected_sign_number']})")
        print(f"  Our calculation: {mars_data['longitude']:.4f}° in {mars_data['sign']} (sign #{mars_data['sign_number']})")
        print(f"  Raw degree in sign: {mars_data['degree_in_sign']:.4f}°")
        print(f"  Difference: {abs(mars_data['longitude'] - dp_mars['longitude']):.4f}°")
        print()
        
        # Check if signs are swapped or off by some amount
        if mars_data['sign_number'] != dp_mars['expected_sign_number']:
            sign_difference = (mars_data['sign_number'] - dp_mars['expected_sign_number']) % 12
            print(f"  🔍 Sign discrepancy: Our sign {mars_data['sign_number']} vs expected {dp_mars['expected_sign_number']}")
            print(f"      Sign difference: {sign_difference} signs")
            print(f"      This could indicate a {sign_difference * 30}° offset issue")
        
        print()
    
    # Analyze Jupiter  
    if 'Jupiter' in positions:
        jupiter_data = positions['Jupiter']
        dp_jupiter = dp_reference['Jupiter']
        
        print("♃ JUPITER ANALYSIS:")
        print(f"  DrikPanchang: {dp_jupiter['longitude']:.4f}° in {dp_jupiter['sign']} (sign #{dp_jupiter['expected_sign_number']})")
        print(f"  Our calculation: {jupiter_data['longitude']:.4f}° in {jupiter_data['sign']} (sign #{jupiter_data['sign_number']})")
        print(f"  Raw degree in sign: {jupiter_data['degree_in_sign']:.4f}°")
        print(f"  Difference: {abs(jupiter_data['longitude'] - dp_jupiter['longitude']):.4f}°")
        print()
        
        # Check if signs are swapped or off by some amount
        if jupiter_data['sign_number'] != dp_jupiter['expected_sign_number']:
            sign_difference = (jupiter_data['sign_number'] - dp_jupiter['expected_sign_number']) % 12
            print(f"  🔍 Sign discrepancy: Our sign {jupiter_data['sign_number']} vs expected {dp_jupiter['expected_sign_number']}")
            print(f"      Sign difference: {sign_difference} signs")
            print(f"      This could indicate a {sign_difference * 30}° offset issue")
        
        print()
    
    # Look for patterns
    print("🔍 PATTERN ANALYSIS:")
    print()
    
    # Check all planets for consistent offset patterns
    all_planets = {
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
    
    print(f"{'Planet':<10} {'DrikPanchang':<12} {'Our Calc':<12} {'Difference':<12} {'Analysis'}")
    print("-" * 70)
    
    for planet, dp_long in all_planets.items():
        if planet in positions:
            our_long = positions[planet]['longitude']
            diff = abs(our_long - dp_long)
            
            # Handle 360° wraparound  
            if diff > 180:
                diff = 360 - diff
                
            # Categorize the difference
            if diff < 1:
                analysis = "✅ Accurate"
            elif diff < 5:
                analysis = "⚠️ Minor offset"
            elif diff > 100:
                analysis = "❌ Major error"
            else:
                analysis = "🔍 Moderate diff"
            
            print(f"{planet:<10} {dp_long:>10.4f}° {our_long:>10.4f}° {diff:>10.4f}° {analysis}")
    
    print()
    
    # Check for systematic coordinate system differences
    print("🌐 COORDINATE SYSTEM HYPOTHESIS:")
    print()
    
    # Test various coordinate transformations
    test_transformations = [
        ("No change", lambda x: x),
        ("Add 180°", lambda x: (x + 180) % 360),
        ("Subtract 180°", lambda x: (x - 180) % 360),
        ("Negate longitude", lambda x: (-x) % 360),
        ("360° - longitude", lambda x: (360 - x) % 360),
    ]
    
    # Focus on Mars since it has the biggest discrepancy
    if 'Mars' in positions:
        mars_our = positions['Mars']['longitude']
        mars_dp = dp_reference['Mars']['longitude']
        
        print(f"Testing transformations on Mars (DP target: {mars_dp:.2f}°):")
        print(f"{'Transformation':<15} {'Result':<10} {'Difference':<10} {'Improvement'}")
        print("-" * 50)
        
        for name, transform in test_transformations:
            transformed = transform(mars_our)
            diff = min(abs(transformed - mars_dp), 360 - abs(transformed - mars_dp))
            original_diff = min(abs(mars_our - mars_dp), 360 - abs(mars_our - mars_dp))
            improvement = "✅" if diff < original_diff else "❌"
            
            print(f"{name:<15} {transformed:>8.2f}° {diff:>8.2f}° {improvement}")

def main():
    """Main analysis function"""
    analyze_mars_jupiter_issue()

if __name__ == "__main__":
    main()