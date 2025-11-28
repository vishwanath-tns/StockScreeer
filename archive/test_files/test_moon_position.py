import sys
sys.path.append('./vedic_astrology/tools')
from pyjhora_calculator import ProfessionalAstrologyCalculator
from datetime import datetime, time

print("Testing Moon Position for Stock Recommendations")
print("=" * 50)

calc = ProfessionalAstrologyCalculator()
trading_time = datetime.combine(datetime.now().date(), time(9, 15))
astro_data = calc.get_complete_analysis(trading_time)
moon_data = astro_data['planetary_positions'].get('Moon', {})
moon_sign = moon_data.get('sign', 'Unknown')
moon_degree = moon_data.get('degree', 'Unknown')

print(f"Moon Sign: {moon_sign}")
print(f"Moon Degree: {moon_degree}")

sign_elements = {
    'Aries': 'Fire', 'Taurus': 'Earth', 'Gemini': 'Air', 'Cancer': 'Water',
    'Leo': 'Fire', 'Virgo': 'Earth', 'Libra': 'Air', 'Scorpio': 'Water',
    'Sagittarius': 'Fire', 'Capricorn': 'Earth', 'Aquarius': 'Air', 'Pisces': 'Water'
}
element = sign_elements.get(moon_sign, 'Unknown')

print(f"Element: {element}")
print(f"Expected Stock Recommendations: {element} element stocks should appear in GUI")