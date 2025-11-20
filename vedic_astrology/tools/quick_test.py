from pyjhora_calculator import ProfessionalAstrologyCalculator
from datetime import datetime

calc = ProfessionalAstrologyCalculator()
current_time = datetime.now()
print(f"Testing time: {current_time}")

astro_data = calc.get_complete_analysis(current_time)
moon_data = astro_data['planetary_positions']['Moon']

print(f"Fixed Moon: {moon_data['sign']} {moon_data['degree_in_sign']:.2f}°")
print(f"Expected:   Libra ~28.5°")
print(f"Match: {'YES' if abs(moon_data['degree_in_sign'] - 28.5) < 1.0 else 'NO'}")