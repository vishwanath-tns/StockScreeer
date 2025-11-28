"""
Vedic Astrology Demo Script

This script demonstrates the comprehensive Vedic astrology integration
with stock market analysis, showcasing moon cycles, nakshatra analysis,
planetary positions, and auspicious timing calculations.

Author: Stock Screener with Vedic Astrology Integration
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'vedic_astrology', 'calculations'))

import datetime
from core_calculator import VedicAstrologyCalculator
from moon_cycle_analyzer import MoonCycleAnalyzer


def print_separator(title: str):
    """Print a formatted section separator"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def demo_basic_calculations():
    """Demonstrate basic Vedic astrology calculations"""
    print_separator("BASIC VEDIC ASTROLOGY CALCULATIONS")
    
    calc = VedicAstrologyCalculator()
    
    # Current astronomical state
    print("CURRENT LUNAR INFORMATION:")
    moon_info = calc.get_moon_phase()
    print(f"Phase: {moon_info['phase_name']}")
    print(f"Illumination: {moon_info['illumination_percentage']}%")
    print(f"Age: {moon_info['age_days']} days")
    print(f"Market Trend: {moon_info['market_influence']['trend']}")
    print(f"Strategy: {moon_info['market_influence']['strategy']}")
    
    print("\nCURRENT NAKSHATRA:")
    nakshatra_info = calc.get_current_nakshatra()
    print(f"Name: {nakshatra_info['name']}")
    print(f"Deity: {nakshatra_info['deity']}")
    print(f"Characteristics: {nakshatra_info['characteristics']}")
    print(f"Market Influence: {nakshatra_info['market_influence']}")
    
    print("\nPLANETARY POSITIONS:")
    planetary_positions = calc.get_planetary_positions()
    for planet, position in planetary_positions.items():
        sectors = position['market_influence']['sectors']
        print(f"{planet:8}: {position['sign']:12} {position['degree_in_sign']:6.1f}° | Sectors: {', '.join(sectors[:3])}")
    
    print("\nTIMING ANALYSIS:")
    timing_info = calc.is_auspicious_time()
    print(f"Currently Auspicious: {timing_info['is_auspicious']}")
    print(f"Recommendation: {timing_info['recommendation']}")
    print(f"Rahu Kaal Today: {timing_info['rahu_kaal_period']}")
    print(f"Abhijit Muhurat: {timing_info['abhijit_period']}")


def demo_moon_cycle_analysis():
    """Demonstrate moon cycle analysis capabilities"""
    print_separator("MOON CYCLE ANALYSIS ENGINE")
    
    analyzer = MoonCycleAnalyzer()
    
    # Current moon guidance
    print("CURRENT MOON GUIDANCE:")
    guidance = analyzer.get_current_moon_guidance()
    
    moon_phase = guidance['moon_phase']
    market_guidance = guidance['market_guidance']
    
    print(f"Date: {guidance['current_date']}")
    print(f"Moon Phase: {moon_phase['name']} ({moon_phase['illumination']}%)")
    print(f"Lunar Age: {moon_phase['age_days']} days")
    print(f"Nakshatra: {guidance['nakshatra']['name']}")
    print(f"Market Bias: {market_guidance['trend_bias']}")
    print(f"Volatility Level: {market_guidance['volatility_level']}")
    print(f"Suggested Strategy: {market_guidance['suggested_strategy']}")
    print(f"Volume Expectation: {market_guidance['volume_expectation']}")
    
    print(f"\nOVERALL RECOMMENDATION:")
    print(f"{guidance['overall_recommendation']}")
    
    # Upcoming transitions
    if guidance['upcoming_transitions']:
        print(f"\nUPCOMING LUNAR TRANSITIONS:")
        for i, transition in enumerate(guidance['upcoming_transitions'], 1):
            print(f"{i}. {transition['date']} ({transition['days_from_now']} days): {transition['from_phase']} -> {transition['to_phase']}")
            print(f"   Impact: {transition['market_impact']}")
            print(f"   Strategy: {transition['suggested_strategy']}")


def demo_lunar_calendar():
    """Demonstrate lunar calendar generation"""
    print_separator("LUNAR CALENDAR GENERATION")
    
    analyzer = MoonCycleAnalyzer()
    
    # Generate 14-day lunar calendar
    start_date = datetime.date.today()
    end_date = start_date + datetime.timedelta(days=14)
    
    lunar_calendar = analyzer.generate_lunar_calendar(start_date, end_date)
    
    print(f"📆 14-DAY LUNAR CALENDAR (From {start_date}):")
    print(f"{'Date':<12} | {'Phase':<15} | {'Vol':<4} | {'Nakshatra':<15} | {'Strategy':<20}")
    print('-' * 85)
    
    for data in lunar_calendar:
        date_str = data.date.strftime('%Y-%m-%d')
        print(f"{date_str:<12} | {data.phase:<15} | {data.volatility_score:<4.1f} | {data.nakshatra:<15} | {data.suggested_strategy:<20}")
    
    # Phase transition analysis
    print(f"\n🔄 PHASE TRANSITION ANALYSIS:")
    transitions = analyzer.analyze_phase_transitions(days_back=30)
    
    if transitions['recent_transitions']:
        print(f"\nRecent Transitions (Last 5):")
        for trans in transitions['recent_transitions']:
            print(f"  {trans['date'].strftime('%Y-%m-%d')}: {trans['from_phase']} → {trans['to_phase']}")
            print(f"    Market Impact: {trans['market_impact']}")
            print(f"    Volatility Change: {trans['volatility_change']:+.2f}")
    
    if transitions['phase_statistics']:
        print(f"\nPhase Statistics:")
        for phase, stats in transitions['phase_statistics'].items():
            print(f"  {phase}: {stats['days_count']} days, Avg Vol: {stats['avg_volatility']}")


def demo_auspicious_timing():
    """Demonstrate auspicious timing calculations for different days"""
    print_separator("AUSPICIOUS TIMING ANALYSIS")
    
    calc = VedicAstrologyCalculator()
    
    print("⏰ WEEKLY RAHU KAAL SCHEDULE:")
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    base_date = datetime.date.today()
    # Find the most recent Monday
    days_since_monday = base_date.weekday()
    monday = base_date - datetime.timedelta(days=days_since_monday)
    
    print(f"{'Day':<10} | {'Date':<12} | {'Rahu Kaal':<17} | {'Recommendation':<30}")
    print('-' * 75)
    
    for i, day in enumerate(days):
        check_date = monday + datetime.timedelta(days=i)
        check_datetime = datetime.datetime.combine(check_date, datetime.time(10, 0))  # 10 AM
        
        timing_info = calc.is_auspicious_time(check_datetime)
        
        print(f"{day:<10} | {check_date:<12} | {timing_info['rahu_kaal_period']:<17} | {timing_info['recommendation']:<30}")
    
    print(f"\n🕐 DAILY AUSPICIOUS PERIODS:")
    print(f"Brahma Muhurat: 4:00 AM - 6:00 AM (Best for long-term investments)")
    print(f"Abhijit Muhurat: 11:45 AM - 12:30 PM (Auspicious for all activities)")
    print(f"Godhuli Muhurat: Sunset time (Good for strategy planning)")


def demo_market_correlation_patterns():
    """Demonstrate market correlation patterns with lunar phases"""
    print_separator("MARKET CORRELATION PATTERNS")
    
    print("📈 LUNAR PHASE MARKET CORRELATIONS:")
    
    phase_patterns = {
        'New Moon': {
            'market_behavior': 'Bottom formation, Fresh starts',
            'volatility': 'Low (0.7x)',
            'volume': 'Low',
            'sectors': 'Growth stocks, New IPOs, Emerging sectors',
            'strategy': 'Accumulation, Value picking',
            'historical_pattern': 'Market bottoms often coincide with new moons'
        },
        'Waxing Crescent': {
            'market_behavior': 'Early upward momentum',
            'volatility': 'Low-Medium (0.8x)',
            'volume': 'Increasing',
            'sectors': 'Small & Mid-cap, Growth stories',
            'strategy': 'Momentum building, Early entries',
            'historical_pattern': 'Gradual buying interest builds up'
        },
        'First Quarter': {
            'market_behavior': 'Moderate bullish momentum',
            'volatility': 'Normal (1.0x)',
            'volume': 'Normal',
            'sectors': 'Balanced portfolio, Diversified',
            'strategy': 'Trend following, Balanced allocation',
            'historical_pattern': 'Trend confirmation phase'
        },
        'Waxing Gibbous': {
            'market_behavior': 'Strong bullish momentum',
            'volatility': 'High (1.2x)',
            'volume': 'High',
            'sectors': 'Large cap, Momentum favorites',
            'strategy': 'Momentum trading, Profit booking prep',
            'historical_pattern': 'FOMO phase, Peak buying interest'
        },
        'Full Moon': {
            'market_behavior': 'Market peaks, High volatility',
            'volatility': 'Very High (1.5x)',
            'volume': 'Very High',
            'sectors': 'Volatile sectors, High beta stocks',
            'strategy': 'Profit booking, Risk management',
            'historical_pattern': 'Market tops often occur near full moons'
        },
        'Waning Gibbous': {
            'market_behavior': 'Early correction signals',
            'volatility': 'High (1.3x)',
            'volume': 'High',
            'sectors': 'Defensive stocks, Safe havens',
            'strategy': 'Defensive positioning, Cash building',
            'historical_pattern': 'Smart money starts exiting'
        },
        'Last Quarter': {
            'market_behavior': 'Moderate correction phase',
            'volatility': 'Medium (1.1x)',
            'volume': 'Normal',
            'sectors': 'Quality at discount, Value picks',
            'strategy': 'Value hunting, Selective buying',
            'historical_pattern': 'Selling pressure, Trend reversal'
        },
        'Waning Crescent': {
            'market_behavior': 'Final correction phase',
            'volatility': 'Low-Medium (0.9x)',
            'volume': 'Decreasing',
            'sectors': 'Oversold quality, Contrarian plays',
            'strategy': 'Contrarian investing, Cycle preparation',
            'historical_pattern': 'Capitulation, Bottom formation begins'
        }
    }
    
    for phase, pattern in phase_patterns.items():
        print(f"\n{phase}:")
        print(f"  Market Behavior: {pattern['market_behavior']}")
        print(f"  Volatility: {pattern['volatility']}")
        print(f"  Volume: {pattern['volume']}")
        print(f"  Favored Sectors: {pattern['sectors']}")
        print(f"  Strategy: {pattern['strategy']}")
        print(f"  Pattern: {pattern['historical_pattern']}")


def demo_planetary_sector_influence():
    """Demonstrate planetary influence on market sectors"""
    print_separator("PLANETARY SECTOR INFLUENCE")
    
    calc = VedicAstrologyCalculator()
    planetary_positions = calc.get_planetary_positions()
    
    print("🪐 CURRENT PLANETARY INFLUENCES ON SECTORS:")
    print(f"{'Planet':<8} | {'Sign':<12} | {'Degree':<8} | {'Influenced Sectors':<50}")
    print('-' * 85)
    
    for planet, position in planetary_positions.items():
        sectors = ', '.join(position['market_influence']['sectors'][:4])  # Show first 4 sectors
        print(f"{planet:<8} | {position['sign']:<12} | {position['degree_in_sign']:6.1f}° | {sectors:<50}")
    
    print(f"\n📊 SECTOR INFLUENCE ANALYSIS:")
    print(f"Based on current planetary positions, here's today's sector guidance:")
    
    for planet, position in planetary_positions.items():
        influence = position['market_influence']
        print(f"\n{planet} in {position['sign']}:")
        print(f"  Primary Sectors: {', '.join(influence['sectors'][:3])}")
        print(f"  Characteristics: {influence['characteristics']}")
        print(f"  Trading Impact: {influence['trading_impact']}")


def demo_comprehensive_daily_analysis():
    """Demonstrate comprehensive daily astrological analysis"""
    print_separator("COMPREHENSIVE DAILY ANALYSIS")
    
    calc = VedicAstrologyCalculator()
    analyzer = MoonCycleAnalyzer()
    
    # Get comprehensive analysis
    daily_summary = calc.get_daily_astro_summary()
    moon_guidance = analyzer.get_current_moon_guidance()
    
    print(f"📅 DAILY ASTROLOGICAL MARKET ANALYSIS")
    print(f"Date: {daily_summary['date']}")
    
    print(f"\n🌙 LUNAR ANALYSIS:")
    moon_phase = daily_summary['moon_phase']
    print(f"Phase: {moon_phase['phase_name']} ({moon_phase['illumination_percentage']}%)")
    print(f"Age: {moon_phase['age_days']} days")
    print(f"Market Influence: {moon_phase['market_influence']['trend']}")
    
    print(f"\n⭐ NAKSHATRA INFLUENCE:")
    nakshatra = daily_summary['nakshatra']
    print(f"Current: {nakshatra['name']}")
    print(f"Deity: {nakshatra['deity']}")
    print(f"Market Impact: {nakshatra['market_influence']}")
    
    print(f"\n⏰ TIMING GUIDANCE:")
    timing = daily_summary['timing_analysis']
    print(f"Overall Auspiciousness: {timing['is_auspicious']}")
    print(f"Recommendation: {timing['recommendation']}")
    print(f"Avoid Period: {timing['rahu_kaal_period']}")
    
    print(f"\n📈 MARKET STRATEGY:")
    market_guidance = moon_guidance['market_guidance']
    print(f"Trend Bias: {market_guidance['trend_bias']}")
    print(f"Volatility Level: {market_guidance['volatility_level']}x")
    print(f"Suggested Strategy: {market_guidance['suggested_strategy']}")
    print(f"Volume Expectation: {market_guidance['volume_expectation']}")
    
    print(f"\n💡 OVERALL RECOMMENDATION:")
    overall = daily_summary['overall_market_influence']
    print(f"{overall['overall_recommendation']}")


def main():
    """Run the complete Vedic astrology demo"""
    print("VEDIC ASTROLOGY STOCK MARKET INTEGRATION DEMO")
    print(f"Demonstration Date: {datetime.date.today().strftime('%Y-%m-%d')}")
    
    try:
        # Run all demo sections
        demo_basic_calculations()
        demo_moon_cycle_analysis()
        demo_lunar_calendar()
        demo_auspicious_timing()
        demo_market_correlation_patterns()
        demo_planetary_sector_influence()
        demo_comprehensive_daily_analysis()
        
        print_separator("DEMO COMPLETION")
        print("✅ Vedic Astrology integration demo completed successfully!")
        print("\n🌟 KEY FEATURES DEMONSTRATED:")
        print("• Real-time lunar phase tracking and market correlation")
        print("• Nakshatra analysis with sector implications")
        print("• Planetary position calculations and sector influence")
        print("• Auspicious timing analysis for trading decisions")
        print("• 14-day lunar calendar with volatility predictions")
        print("• Phase transition analysis and upcoming events")
        print("• Comprehensive daily astrological market guidance")
        
        print("\n🚀 READY FOR INTEGRATION:")
        print("This Vedic astrology module is ready to be integrated with")
        print("your stock screener for enhanced market timing and analysis.")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    if success:
        print(f"\n🎯 Next steps: Create GUI integration and market correlation backtesting")
    sys.exit(0 if success else 1)