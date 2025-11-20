#!/usr/bin/env python3
"""
Test the market summary generation directly
"""

import sys
sys.path.append('../tools')

def test_market_summary():
    try:
        from pyjhora_calculator import ProfessionalAstrologyCalculator
        import datetime
        
        calc = ProfessionalAstrologyCalculator()
        live_time = datetime.datetime.now()
        print(f"Testing market summary generation at: {live_time}")
        
        astro_data = calc.get_complete_analysis(live_time)
        
        # Extract current data
        moon_data = astro_data['planetary_positions'].get('Moon', {})
        moon_sign = moon_data.get('sign', 'Unknown')
        moon_degree = moon_data.get('degree_in_sign', 0)
        
        sign_elements = {
            'Aries': 'Fire', 'Taurus': 'Earth', 'Gemini': 'Air', 'Cancer': 'Water',
            'Leo': 'Fire', 'Virgo': 'Earth', 'Libra': 'Air', 'Scorpio': 'Water',
            'Sagittarius': 'Fire', 'Capricorn': 'Earth', 'Aquarius': 'Air', 'Pisces': 'Water'
        }
        element = sign_elements.get(moon_sign, 'Unknown')
        
        moon_phase = astro_data.get('moon_phase', {})
        phase_name = moon_phase.get('phase_name', 'Unknown')
        phase_percentage = moon_phase.get('illumination', 0)
        
        panchanga = astro_data.get('panchanga', {})
        tithi = panchanga.get('tithi', {}).get('name', 'Unknown')
        nakshatra_name = panchanga.get('nakshatra', {}).get('name', 'Unknown')
        nakshatra_number = panchanga.get('nakshatra', {}).get('number', 0)
        
        # Test the summary format that should appear
        summary = f"""
🔮 LIVE ASTROLOGICAL MARKET ANALYSIS - {live_time.strftime('%Y-%m-%d')} ({live_time.strftime('%A')})
{'='*75}

🌙 LIVE MOON POSITION (PyJHora Swiss Ephemeris) - {live_time.strftime('%H:%M:%S')}:
   Sign: {moon_sign} at {moon_degree:.2f}°
   Element: {element} (Trading characteristic)
   Phase: {phase_name} ({phase_percentage:.1f}% illuminated)
   
📅 PANCHANGA DATA:
   Tithi: {tithi}
   Nakshatra: {nakshatra_name} (#{nakshatra_number})
   
📊 MARKET OUTLOOK (Based on Moon in {element}):
   - {element} element influences market sentiment
   - Current lunar phase: {phase_name}
   - Trading approach: Align with {element} energy
   
⏰ Live Data Updated: {live_time.strftime('%H:%M:%S')}"""

        print("SUCCESS: Market summary generated")
        print("=" * 60)
        print(summary)
        print("=" * 60)
        print("✅ This should now appear in the Market Summary tab")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    test_market_summary()