from pyjhora_calculator import ProfessionalAstrologyCalculator
from datetime import datetime

print("🌟 NAKSHATRA IDENTIFICATION TEST")
print("="*40)

calc = ProfessionalAstrologyCalculator()
current_time = datetime.now()

# Test current nakshatra
astro_data = calc.get_complete_analysis(current_time)
panchanga = astro_data['panchanga']

nakshatra_number = panchanga['nakshatra']['number']
nakshatra_name = panchanga['nakshatra']['name']

print(f"Current Time: {current_time}")
print(f"Nakshatra Number: {nakshatra_number}")
print(f"Nakshatra Name: {nakshatra_name}")
print()

if nakshatra_number == 16:
    print("✅ CONFIRMED: Nakshatra 16 = Vishakha")
    print("This matches your Drik Panchang data showing 'Vishakha' nakshatra")
else:
    print(f"Current nakshatra is #{nakshatra_number} = {nakshatra_name}")
    
print()
print("📋 All 27 Nakshatras:")
for i, name in enumerate(calc.nakshatra_names, 1):
    marker = " 👑" if i == 16 else ""
    print(f"{i:2d}. {name}{marker}")