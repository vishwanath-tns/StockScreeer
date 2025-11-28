"""
Simple Vedic Astrology Demo (No Unicode)

Basic demonstration of Vedic astrology calculations without Unicode characters
to avoid encoding issues.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'vedic_astrology', 'calculations'))

import datetime
from core_calculator import VedicAstrologyCalculator
from moon_cycle_analyzer import MoonCycleAnalyzer


def simple_demo():
    """Simple demo without Unicode characters"""
    print("=== VEDIC ASTROLOGY STOCK MARKET INTEGRATION DEMO ===")
    print(f"Date: {datetime.date.today()}")
    print()
    
    # Basic calculations
    calc = VedicAstrologyCalculator()
    
    print("CURRENT LUNAR INFORMATION:")
    moon_info = calc.get_moon_phase()
    print(f"Phase: {moon_info['phase_name']}")
    print(f"Illumination: {moon_info['illumination_percentage']}%")
    print(f"Market Trend: {moon_info['market_influence']['trend']}")
    print()
    
    print("CURRENT NAKSHATRA:")
    nakshatra_info = calc.get_current_nakshatra()
    print(f"Name: {nakshatra_info['name']}")
    print(f"Characteristics: {nakshatra_info['characteristics']}")
    print(f"Market Influence: {nakshatra_info['market_influence']}")
    print()
    
    print("TIMING ANALYSIS:")
    timing_info = calc.is_auspicious_time()
    print(f"Currently Auspicious: {timing_info['is_auspicious']}")
    print(f"Recommendation: {timing_info['recommendation']}")
    print()
    
    # Moon cycle analysis
    analyzer = MoonCycleAnalyzer()
    guidance = analyzer.get_current_moon_guidance()
    
    print("MARKET GUIDANCE:")
    market_guidance = guidance['market_guidance']
    print(f"Volatility Level: {market_guidance['volatility_level']}")
    print(f"Suggested Strategy: {market_guidance['suggested_strategy']}")
    print(f"Overall: {guidance['overall_recommendation']}")
    print()
    
    # Next few days
    print("NEXT 5 DAYS LUNAR CALENDAR:")
    start_date = datetime.date.today()
    end_date = start_date + datetime.timedelta(days=5)
    
    lunar_calendar = analyzer.generate_lunar_calendar(start_date, end_date)
    
    for data in lunar_calendar:
        print(f"{data.date}: {data.phase} | Vol: {data.volatility_score} | Strategy: {data.suggested_strategy}")
    
    print()
    print("=== DEMO COMPLETED SUCCESSFULLY ===")
    print("Vedic astrology integration is working correctly!")


if __name__ == "__main__":
    simple_demo()