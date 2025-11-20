#!/usr/bin/env python3
"""
Test PyJHora accuracy against Drik Panchang data
Comparing moon position for November 20, 2025
"""

from datetime import datetime, timezone
import pytz
from pyjhora_calculator import ProfessionalAstrologyCalculator

def test_moon_position_accuracy():
    """Test moon position against Drik Panchang reference data"""
    
    # Reference data from Drik Panchang (November 20, 2025)
    # Time shown in your screenshot: 01:13:58
    reference_time = datetime(2025, 11, 20, 1, 13, 58)
    
    print("🔍 ACCURACY TEST: PyJHora vs Drik Panchang")
    print("="*50)
    print(f"Reference Time: {reference_time}")
    print()
    
    # Create calculator
    calc = ProfessionalAstrologyCalculator()
    
    # Test different time interpretations
    test_times = [
        ("Local Time (as entered)", reference_time),
        ("IST Timezone", reference_time.replace(tzinfo=pytz.timezone('Asia/Kolkata'))),
        ("UTC Interpretation", reference_time.replace(tzinfo=timezone.utc)),
        ("Current Live Time", datetime.now()),
        ("9:15 AM Trading Time", datetime(2025, 11, 20, 9, 15, 0))
    ]
    
    print("Expected from Drik Panchang:")
    print("🌙 Moon: 28° Tula 31' 11\" (Libra 28.52°)")
    print("🌞 Sun: 03° Vrish 30' 31\" (Scorpio 3.51°)")
    print()
    
    for description, test_time in test_times:
        print(f"🧪 Testing: {description}")
        try:
            # Get positions
            astro_data = calc.get_complete_analysis(test_time)
            positions = astro_data.get('planetary_positions', {})
            
            # Extract moon position
            moon_data = positions.get('Moon', {})
            moon_sign = moon_data.get('sign', 'Unknown')
            moon_degree = moon_data.get('degree_in_sign', 0)
            moon_longitude = moon_data.get('longitude', 0)
            
            # Extract sun position
            sun_data = positions.get('Sun', {})
            sun_sign = sun_data.get('sign', 'Unknown')
            sun_degree = sun_data.get('degree_in_sign', 0)
            
            print(f"   🌙 Moon: {moon_sign} {moon_degree:.2f}° (Absolute: {moon_longitude:.2f}°)")
            print(f"   🌞 Sun:  {sun_sign} {sun_degree:.2f}°")
            
            # Calculate difference from expected
            expected_moon_degree = 28.52  # 28°31'11"
            moon_difference = abs(moon_degree - expected_moon_degree)
            
            if moon_difference < 1.0:
                print(f"   ✅ EXCELLENT: Difference {moon_difference:.2f}°")
            elif moon_difference < 3.0:
                print(f"   ⚠️  GOOD: Difference {moon_difference:.2f}°") 
            else:
                print(f"   ❌ NEEDS ADJUSTMENT: Difference {moon_difference:.2f}°")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
    
    # Test ayanamsa settings
    print("🔧 Testing different Ayanamsa settings...")
    print("(This might help match Drik Panchang exactly)")
    

if __name__ == "__main__":
    test_moon_position_accuracy()