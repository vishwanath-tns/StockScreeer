"""
Moon Position Verification Tool

This script helps verify the accuracy of our moon position calculations
by comparing them with multiple astronomical sources and providing detailed
information about the calculation methodology.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'calculations'))

import ephem
from datetime import datetime, timezone
import pytz
from core_calculator import VedicAstrologyCalculator

def verify_moon_position():
    """Verify moon position calculations with detailed breakdown"""
    
    print("=" * 80)
    print("MOON POSITION VERIFICATION TOOL")
    print("=" * 80)
    
    # Get current time in multiple timezones
    utc_now = datetime.now(timezone.utc)
    ist_now = utc_now.astimezone(pytz.timezone('Asia/Kolkata'))
    local_now = datetime.now()
    
    print(f"\nTIME VERIFICATION:")
    print(f"Local time:     {local_now}")
    print(f"UTC time:       {utc_now}")
    print(f"IST time:       {ist_now}")
    
    # Initialize our calculator
    calc = VedicAstrologyCalculator()
    print(f"\nCALCULATOR LOCATION:")
    print(f"Latitude:       {calc.observer.lat} (Mumbai)")
    print(f"Longitude:      {calc.observer.lon} (Mumbai)")
    print(f"Elevation:      {calc.observer.elevation} meters")
    
    # Get our calculations
    summary = calc.get_daily_astro_summary()
    moon_data = summary['planetary_positions']['Moon']
    nakshatra_data = summary['nakshatra']
    
    print(f"\nOUR CALCULATIONS:")
    print(f"Moon Sign:              {moon_data['sign']}")
    print(f"Moon Degree in Sign:    {moon_data['degree_in_sign']:.2f}°")
    print(f"Moon Absolute Longitude: {moon_data['longitude']:.2f}°")
    print(f"Moon Nakshatra:         {nakshatra_data['name']}")
    print(f"Nakshatra Degree:       {nakshatra_data['nakshatra_degree']:.2f}°")
    
    # Direct ephem calculation for comparison
    print(f"\nDIRECT EPHEM CALCULATION:")
    observer = ephem.Observer()
    observer.lat = '19.0760'  # Mumbai
    observer.lon = '72.8777'
    observer.date = utc_now
    
    moon = ephem.Moon(observer)
    moon_lon_deg = float(moon.g_ra) * 180 / ephem.pi  # Convert radians to degrees
    moon_lat_deg = float(moon.g_dec) * 180 / ephem.pi
    
    # Calculate zodiac sign from longitude
    zodiac_signs = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
                   'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
    
    # Ephem longitude calculation
    moon_ecliptic_lon = float(moon.hlon) * 180 / ephem.pi
    while moon_ecliptic_lon < 0:
        moon_ecliptic_lon += 360
    while moon_ecliptic_lon >= 360:
        moon_ecliptic_lon -= 360
        
    sign_index = int(moon_ecliptic_lon // 30)
    degree_in_sign = moon_ecliptic_lon % 30
    
    print(f"Moon Ecliptic Longitude: {moon_ecliptic_lon:.2f}°")
    print(f"Moon Sign (Direct):      {zodiac_signs[sign_index]}")
    print(f"Degree in Sign (Direct): {degree_in_sign:.2f}°")
    print(f"Moon RA:                 {float(moon.ra) * 12 / ephem.pi:.2f}h")
    print(f"Moon Dec:                {float(moon.dec) * 180 / ephem.pi:.2f}°")
    
    # Compare with your attached chart data
    print(f"\nCOMPARISON WITH YOUR CHART:")
    print(f"Your Chart shows:        Moon at 22° Scorpio")
    print(f"Our calculation shows:   Moon at {moon_data['degree_in_sign']:.1f}° {moon_data['sign']}")
    
    # Calculate difference
    if moon_data['sign'] == 'Scorpio':
        degree_diff = abs(22.0 - moon_data['degree_in_sign'])
        print(f"Difference:              {degree_diff:.1f}°")
        
        if degree_diff < 2.0:
            print("✅ EXCELLENT MATCH (within 2°)")
        elif degree_diff < 5.0:
            print("✅ GOOD MATCH (within 5°)")
        elif degree_diff < 10.0:
            print("⚠️  ACCEPTABLE MATCH (within 10°)")
        else:
            print("❌ SIGNIFICANT DIFFERENCE")
    else:
        print("❌ DIFFERENT SIGN - Need to investigate")
    
    # Additional verification methods
    print(f"\nADDITIONAL VERIFICATION:")
    
    # Check for date/time issues
    chart_date = input("\nWhat date/time does your attached chart represent? (YYYY-MM-DD HH:MM or press Enter for current): ").strip()
    
    if chart_date:
        try:
            if len(chart_date) <= 10:  # Just date
                chart_datetime = datetime.strptime(chart_date, '%Y-%m-%d')
            else:  # Date and time
                chart_datetime = datetime.strptime(chart_date, '%Y-%m-%d %H:%M')
            
            # Convert to IST
            ist = pytz.timezone('Asia/Kolkata')
            chart_datetime_ist = ist.localize(chart_datetime)
            
            print(f"\nRECALCULATING FOR YOUR CHART TIME:")
            print(f"Chart time (IST): {chart_datetime_ist}")
            
            # Recalculate for chart time
            chart_summary = calc.get_daily_astro_summary(chart_datetime_ist)
            chart_moon_data = chart_summary['planetary_positions']['Moon']
            
            print(f"Moon at chart time: {chart_moon_data['degree_in_sign']:.1f}° {chart_moon_data['sign']}")
            
            if chart_moon_data['sign'] == 'Scorpio':
                chart_degree_diff = abs(22.0 - chart_moon_data['degree_in_sign'])
                print(f"Difference from 22° Scorpio: {chart_degree_diff:.1f}°")
                
        except ValueError:
            print("Invalid date format. Using current time.")
    
    # Testing methodology explanation
    print(f"\nTESTING METHODOLOGY:")
    print(f"1. Use multiple online ephemeris tools:")
    print(f"   - https://www.astro.com/swisseph/swetest.htm")
    print(f"   - https://astro-seek.com/calculate-moon-position")
    print(f"   - https://theastrologer.com/ephemeris/")
    
    print(f"\n2. Compare with professional software:")
    print(f"   - Jagannatha Hora (free Vedic astrology software)")
    print(f"   - Swiss Ephemeris")
    print(f"   - NASA JPL Horizons")
    
    print(f"\n3. Key factors that affect calculations:")
    print(f"   - Observer location (we use Mumbai: 19.0760°N, 72.8777°E)")
    print(f"   - Time zone (we use IST)")
    print(f"   - Ayanamsa (we use default Lahiri)")
    print(f"   - Coordinate system (tropical vs sidereal)")
    
    print(f"\n4. Expected accuracy:")
    print(f"   - Within 1-2° is excellent for trading purposes")
    print(f"   - Within 5° is acceptable for trend analysis")
    print(f"   - Differences >10° indicate systematic error")

def test_with_online_ephemeris():
    """Provide URLs and instructions for manual verification"""
    
    utc_now = datetime.now(timezone.utc)
    ist_now = utc_now.astimezone(pytz.timezone('Asia/Kolkata'))
    
    print(f"\nONLINE VERIFICATION LINKS:")
    print(f"Current time: {ist_now.strftime('%Y-%m-%d %H:%M')} IST")
    print(f"Mumbai coordinates: 19.0760°N, 72.8777°E")
    print()
    
    # Swiss Ephemeris test URL
    date_str = utc_now.strftime('%d.%m.%Y')
    time_str = utc_now.strftime('%H:%M')
    
    print(f"1. Swiss Ephemeris Test:")
    print(f"   URL: https://www.astro.com/swisseph/swetest.htm")
    print(f"   Parameters:")
    print(f"   - Date: {date_str}")
    print(f"   - Time: {time_str} UT")
    print(f"   - Location: 72.8777E 19.0760N")
    print(f"   - Planet: Moon")
    
    print(f"\n2. AstroSeek Calculator:")
    print(f"   URL: https://astro-seek.com/calculate-moon-position")
    print(f"   Parameters:")
    print(f"   - Date/Time: {ist_now.strftime('%d.%m.%Y %H:%M')}")
    print(f"   - Timezone: Asia/Kolkata (+05:30)")
    print(f"   - Location: Mumbai, India")
    
    print(f"\n3. NASA JPL Horizons:")
    print(f"   URL: https://ssd.jpl.nasa.gov/horizons/app.html")
    print(f"   Parameters:")
    print(f"   - Target Body: Moon [301]")
    print(f"   - Observer Location: Mumbai @72.8777°E,19.0760°N")
    print(f"   - Time Span: {utc_now.strftime('%Y-%m-%d %H:%M')} UTC")

if __name__ == "__main__":
    verify_moon_position()
    print("\n" + "=" * 80)
    test_with_online_ephemeris()
    print("=" * 80)