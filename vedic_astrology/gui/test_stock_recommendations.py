from pyjhora_calculator import ProfessionalAstrologyCalculator
from datetime import datetime
import sys
sys.path.append('.')

print("🔍 TESTING STOCK RECOMMENDATION LOGIC")
print("=" * 50)

# Test the PyJHora calculation
calc = ProfessionalAstrologyCalculator()
trading_time = datetime.combine(datetime.now().date(), datetime.time(9, 15))
print(f"Trading time: {trading_time}")

astro_data = calc.get_complete_analysis(trading_time)
moon_data = astro_data['planetary_positions'].get('Moon', {})
moon_sign = moon_data.get('sign', 'Unknown')

sign_elements = {
    'Aries': 'Fire', 'Taurus': 'Earth', 'Gemini': 'Air', 'Cancer': 'Water',
    'Leo': 'Fire', 'Virgo': 'Earth', 'Libra': 'Air', 'Scorpio': 'Water',
    'Sagittarius': 'Fire', 'Capricorn': 'Earth', 'Aquarius': 'Air', 'Pisces': 'Water'
}
element = sign_elements.get(moon_sign, 'Unknown')

print(f"Moon Sign: {moon_sign}")
print(f"Element: {element}")
print()

# Test the stock recommendation logic
print("STOCK RECOMMENDATIONS THAT SHOULD BE GENERATED:")
print("-" * 55)

if element == 'Fire':
    print("🔥 FIRE ELEMENT STOCKS:")
    print("  High Conviction: Energy Focus, RELIANCE, TCS, INFY, L&T")
    print("  Momentum: High Energy Momentum, ADANIGREEN, TATASTEEL, BAJFINANCE")
elif element == 'Earth':
    print("🌱 EARTH ELEMENT STOCKS:")
    print("  Accumulation: Stable Growth, HDFC, ICICIBANK, ITC, HINDUNILVR, NTPC")
    print("  High Conviction: Blue Chip Banking, SBI, KOTAKBANK")
elif element == 'Water':
    print("💧 WATER ELEMENT STOCKS:")
    print("  High Conviction: Healthcare Focus, SUNPHARMA, DRREDDY, CIPLA")
    print("  Accumulation: Chemical & Process, ASIANPAINT, PIDILITIND, NESTLEIND")
elif element == 'Air':
    print("💨 AIR ELEMENT STOCKS:")
    print("  Momentum: Communication & Media, BHARTIARTL, JIOFINTECH, ZOMATO")
    print("  High Conviction: Digital & Platforms, WIPRO, TECHM")

print()
print("✅ Logic test complete - these recommendations should appear in the GUI")