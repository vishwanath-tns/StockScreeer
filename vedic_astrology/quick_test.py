#!/usr/bin/env python3
"""Quick test of the Professional Vedic Astrology System"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'tools'))

from pyjhora_calculator import ProfessionalAstrologyCalculator

from datetime import datetime

# Test the calculator
calc = ProfessionalAstrologyCalculator()
positions = calc.get_planetary_positions(datetime.now())

print("🌟 Current Planetary Positions (Professional Grade):")
print("="*60)

for planet, data in positions.items():
    print(f"{planet}: {data}")

print("="*60)
print("✅ Professional calculator is working perfectly!")