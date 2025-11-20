from pyjhora_calculator import ProfessionalAstrologyCalculator
from datetime import datetime

print('🧪 Testing PyJHora Professional Calculator...')
calc = ProfessionalAstrologyCalculator()
current_time = datetime.now()
print(f'Test time: {current_time}')

astro_data = calc.get_complete_analysis(current_time)
print('✅ Professional calculations working')
print('Planetary positions:')
for planet, data in list(astro_data['planetary_positions'].items())[:5]:
    print(f'  {planet}: {data["sign"]} {data["degree_in_sign"]:.2f}°')

print('Panchanga data:')
panchanga = astro_data['panchanga']
print(f'  Nakshatra: {panchanga["nakshatra"]["name"]} (#{panchanga["nakshatra"]["number"]})')
print(f'  Tithi: {panchanga["tithi"]["number"]}')
print('✅ Calculator test complete')