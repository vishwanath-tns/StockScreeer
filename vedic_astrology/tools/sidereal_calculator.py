"""
Enhanced Moon Position Calculator with Proper Sidereal Support

This module provides corrected astronomical calculations that properly distinguish
between Tropical and Sidereal (Vedic) systems.
"""

import ephem
import pytz
from datetime import datetime, timezone
import math

class SiderealVedicCalculator:
    """Enhanced calculator with proper sidereal/vedic support"""
    
    def __init__(self):
        """Initialize with Mumbai location and proper sidereal settings"""
        self.observer = ephem.Observer()
        self.observer.lat = '19.0760'  # Mumbai
        self.observer.lon = '72.8777'
        self.observer.elevation = 8
        
        # Zodiac signs
        self.zodiac_signs = [
            'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
            'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
        ]
        
        # Lahiri Ayanamsa for different years (approximate)
        self.lahiri_ayanamsa_base = 23.85  # Base for 2000
        self.ayanamsa_rate = 0.0139  # Degrees per year
    
    def get_current_ayanamsa(self, year=None):
        """Calculate current Lahiri Ayanamsa"""
        if year is None:
            year = datetime.now().year
        
        years_since_2000 = year - 2000
        return self.lahiri_ayanamsa_base + (years_since_2000 * self.ayanamsa_rate)
    
    def get_moon_position_detailed(self, date_time=None):
        """Get detailed moon position in both tropical and sidereal systems"""
        
        if date_time is None:
            date_time = datetime.now(timezone.utc)
        elif date_time.tzinfo is None:
            # Convert to UTC if no timezone
            ist = pytz.timezone('Asia/Kolkata')
            date_time = ist.localize(date_time).astimezone(timezone.utc)
        
        # Set observer time
        self.observer.date = date_time
        
        # Calculate Moon position
        moon = ephem.Moon(self.observer)
        
        # Get ecliptic longitude (proper astronomical coordinate)
        moon_ecliptic_lon = float(moon.hlon) * 180 / math.pi
        
        # Normalize to 0-360
        while moon_ecliptic_lon < 0:
            moon_ecliptic_lon += 360
        while moon_ecliptic_lon >= 360:
            moon_ecliptic_lon -= 360
        
        # Tropical calculation (Western astrology)
        tropical_sign_index = int(moon_ecliptic_lon // 30)
        tropical_degree = moon_ecliptic_lon % 30
        tropical_sign = self.zodiac_signs[tropical_sign_index]
        
        # Sidereal calculation (Vedic astrology)
        current_ayanamsa = self.get_current_ayanamsa(date_time.year)
        sidereal_longitude = moon_ecliptic_lon - current_ayanamsa
        
        # Normalize sidereal longitude
        while sidereal_longitude < 0:
            sidereal_longitude += 360
        while sidereal_longitude >= 360:
            sidereal_longitude -= 360
        
        sidereal_sign_index = int(sidereal_longitude // 30)
        sidereal_degree = sidereal_longitude % 30
        sidereal_sign = self.zodiac_signs[sidereal_sign_index]
        
        return {
            'calculation_time': date_time.isoformat(),
            'ayanamsa_used': round(current_ayanamsa, 2),
            'tropical': {
                'longitude': round(moon_ecliptic_lon, 2),
                'sign': tropical_sign,
                'degree_in_sign': round(tropical_degree, 2),
                'position_string': f"{tropical_degree:.1f}° {tropical_sign}"
            },
            'sidereal_vedic': {
                'longitude': round(sidereal_longitude, 2),
                'sign': sidereal_sign,
                'degree_in_sign': round(sidereal_degree, 2),
                'position_string': f"{sidereal_degree:.1f}° {sidereal_sign}"
            },
            'difference_degrees': round(current_ayanamsa, 2),
            'moon_phase': self._get_moon_phase_info(moon)
        }
    
    def _get_moon_phase_info(self, moon_obj):
        """Get moon phase information"""
        illumination = moon_obj.moon_phase
        
        if illumination < 0.01:
            phase = "New Moon"
        elif illumination < 0.25:
            phase = "Waxing Crescent"
        elif illumination < 0.75:
            phase = "Waxing Gibbous" if illumination < 0.5 else "Waning Gibbous"
        elif illumination < 0.99:
            phase = "Waning Crescent"
        else:
            phase = "Full Moon"
            
        return {
            'phase_name': phase,
            'illumination_percentage': round(illumination * 100, 1)
        }

def test_against_chart():
    """Test our calculations against the attached chart"""
    
    calc = SiderealVedicCalculator()
    
    print("VEDIC vs SIDEREAL SYSTEM EXPLANATION")
    print("=" * 60)
    
    print(f"\nYES, Vedic and Sidereal are essentially THE SAME!")
    print(f"• Vedic astrology uses the Sidereal zodiac")
    print(f"• Western astrology uses the Tropical zodiac")
    print(f"• The difference is the 'Ayanamsa' (precession correction)")
    
    # Test for chart time (Nov 20, 2025, 00:09 IST)
    chart_time_str = "2025-11-20 00:09"
    ist = pytz.timezone('Asia/Kolkata')
    chart_time = datetime.strptime(chart_time_str, '%Y-%m-%d %H:%M')
    chart_time_ist = ist.localize(chart_time)
    
    print(f"\nTESTING FOR YOUR CHART TIME:")
    print(f"Chart time: {chart_time_str} IST")
    
    # Get detailed position
    position_data = calc.get_moon_position_detailed(chart_time_ist)
    
    print(f"\nCURRENT AYANAMSA (2025): {position_data['ayanamsa_used']}°")
    print(f"This is the correction applied to convert Tropical to Sidereal")
    
    print(f"\nCALCULATION RESULTS:")
    print(f"Tropical (Western):  {position_data['tropical']['position_string']}")
    print(f"Sidereal (Vedic):    {position_data['sidereal_vedic']['position_string']}")
    
    print(f"\nYOUR ATTACHED CHART COMPARISON:")
    print(f"Chart shows:      ~27° Scorpio (Sidereal)")
    print(f"Our calculation:   {position_data['sidereal_vedic']['position_string']}")
    
    # Calculate accuracy
    chart_degree = 27.0
    our_degree = position_data['sidereal_vedic']['degree_in_sign']
    chart_sign = 'Scorpio'
    our_sign = position_data['sidereal_vedic']['sign']
    
    if our_sign == chart_sign:
        difference = abs(chart_degree - our_degree)
        print(f"Difference:        {difference:.1f}°")
        
        if difference < 2:
            print("✅ EXCELLENT MATCH!")
        elif difference < 5:
            print("✅ VERY GOOD MATCH!")
        elif difference < 10:
            print("⚠️  Acceptable difference")
        else:
            print("❌ Needs investigation")
    else:
        print(f"❌ Different signs - need to check calculation")
    
    print(f"\nWHY VEDIC = SIDEREAL:")
    print(f"• Both use star-based reference points")
    print(f"• Both apply precession corrections (Ayanamsa)")
    print(f"• Vedic specifically uses Lahiri Ayanamsa (most common)")
    print(f"• Your chart is correctly labeled as 'Sidereal zodiac'")
    
    return position_data

if __name__ == "__main__":
    result = test_against_chart()