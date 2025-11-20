"""
Core Vedic Astrology Calculations Module

This module provides fundamental astronomical calculations required for Vedic astrology
including lunar phases, planetary positions, nakshatra calculations, and muhurat timings.

Author: Stock Screener with Vedic Astrology Integration
"""

import ephem
import pytz
import datetime
from typing import Dict, List, Tuple, Optional, Any
import math
from enum import Enum

# Indian Standard Time
IST = pytz.timezone('Asia/Kolkata')

class LunarPhase(Enum):
    """Lunar phase enumeration"""
    NEW_MOON = "New Moon"
    WAXING_CRESCENT = "Waxing Crescent"
    FIRST_QUARTER = "First Quarter"
    WAXING_GIBBOUS = "Waxing Gibbous"
    FULL_MOON = "Full Moon"
    WANING_GIBBOUS = "Waning Gibbous"
    LAST_QUARTER = "Last Quarter"
    WANING_CRESCENT = "Waning Crescent"

class VedicAstrologyCalculator:
    """Core astronomical calculator for Vedic astrology principles"""
    
    def __init__(self):
        """Initialize the calculator with observer location (Mumbai, India as default)"""
        self.observer = ephem.Observer()
        # Mumbai coordinates (financial capital of India)
        self.observer.lat = '19.0760'
        self.observer.lon = '72.8777'
        self.observer.elevation = 8  # meters above sea level
        
        # Vedic planets (Navagraha)
        self.planets = {
            'Sun': ephem.Sun(),
            'Moon': ephem.Moon(),
            'Mars': ephem.Mars(),
            'Mercury': ephem.Mercury(),
            'Jupiter': ephem.Jupiter(),
            'Venus': ephem.Venus(),
            'Saturn': ephem.Saturn()
        }
        
        # 27 Nakshatras with their starting degrees and characteristics
        self.nakshatras = [
            {"name": "Ashwini", "start_degree": 0.0, "end_degree": 13.33, 
             "deity": "Ashwini Kumaras", "characteristics": "Swift, Healing, Beginnings",
             "market_influence": "Sudden movements, healthcare sector, new launches"},
            {"name": "Bharani", "start_degree": 13.33, "end_degree": 26.67, 
             "deity": "Yama", "characteristics": "Transformation, Death & Rebirth",
             "market_influence": "Volatile periods, transformation sectors, restructuring"},
            {"name": "Krittika", "start_degree": 26.67, "end_degree": 40.0, 
             "deity": "Agni", "characteristics": "Sharp, Cutting, Purification",
             "market_influence": "Sharp movements, energy sector, decisive trends"},
            {"name": "Rohini", "start_degree": 40.0, "end_degree": 53.33, 
             "deity": "Brahma", "characteristics": "Growth, Beauty, Nourishment",
             "market_influence": "Steady growth, FMCG sector, agricultural stocks"},
            {"name": "Mrigashira", "start_degree": 53.33, "end_degree": 66.67, 
             "deity": "Soma", "characteristics": "Searching, Gentle, Creative",
             "market_influence": "Research phases, pharma sector, exploration companies"},
            {"name": "Ardra", "start_degree": 66.67, "end_degree": 80.0, 
             "deity": "Rudra", "characteristics": "Storm, Destruction, Renewal",
             "market_influence": "Market disruptions, correction phases, restructuring"},
            {"name": "Punarvasu", "start_degree": 80.0, "end_degree": 93.33, 
             "deity": "Aditi", "characteristics": "Return, Renewal, Recovery",
             "market_influence": "Market recovery, comeback stories, revival sectors"},
            {"name": "Pushya", "start_degree": 93.33, "end_degree": 106.67, 
             "deity": "Brihaspati", "characteristics": "Nourishment, Protection, Growth",
             "market_influence": "Steady growth, banking sector, protective stocks"},
            {"name": "Ashlesha", "start_degree": 106.67, "end_degree": 120.0, 
             "deity": "Nagas", "characteristics": "Serpent, Hidden, Mysterious",
             "market_influence": "Hidden factors, insider trading, mysterious movements"},
            {"name": "Magha", "start_degree": 120.0, "end_degree": 133.33, 
             "deity": "Pitrs", "characteristics": "Royal, Ancestral, Authority",
             "market_influence": "Blue chip stocks, established companies, leadership"},
            {"name": "Purva Phalguni", "start_degree": 133.33, "end_degree": 146.67, 
             "deity": "Bhaga", "characteristics": "Pleasure, Luxury, Enjoyment",
             "market_influence": "Luxury goods, entertainment, consumption stocks"},
            {"name": "Uttara Phalguni", "start_degree": 146.67, "end_degree": 160.0, 
             "deity": "Aryaman", "characteristics": "Partnership, Union, Support",
             "market_influence": "Merger activities, partnership news, alliance stocks"},
            {"name": "Hasta", "start_degree": 160.0, "end_degree": 173.33, 
             "deity": "Savitar", "characteristics": "Hand, Skill, Craftsmanship",
             "market_influence": "Manufacturing, skilled sectors, handicraft exports"},
            {"name": "Chitra", "start_degree": 173.33, "end_degree": 186.67, 
             "deity": "Vishvakarma", "characteristics": "Bright, Beautiful, Creative",
             "market_influence": "Design sectors, architecture, creative industries"},
            {"name": "Swati", "start_degree": 186.67, "end_degree": 200.0, 
             "deity": "Vayu", "characteristics": "Independent, Flexible, Movement",
             "market_influence": "Independent stocks, flexible sectors, travel industry"},
            {"name": "Vishakha", "start_degree": 200.0, "end_degree": 213.33, 
             "deity": "Indra-Agni", "characteristics": "Forked, Achievement, Goal",
             "market_influence": "Dual sectors, achievement stories, goal-oriented stocks"},
            {"name": "Anuradha", "start_degree": 213.33, "end_degree": 226.67, 
             "deity": "Mitra", "characteristics": "Friendship, Devotion, Success",
             "market_influence": "Cooperative sectors, devotional success, team stocks"},
            {"name": "Jyeshtha", "start_degree": 226.67, "end_degree": 240.0, 
             "deity": "Indra", "characteristics": "Elder, Authority, Protection",
             "market_influence": "Senior companies, protective stocks, authority sectors"},
            {"name": "Mula", "start_degree": 240.0, "end_degree": 253.33, 
             "deity": "Nirriti", "characteristics": "Root, Foundation, Investigation",
             "market_influence": "Foundation sectors, root cause analysis, investigation"},
            {"name": "Purva Ashadha", "start_degree": 253.33, "end_degree": 266.67, 
             "deity": "Apas", "characteristics": "Invincible, Water, Purification",
             "market_influence": "Water sector, purification industries, invincible stocks"},
            {"name": "Uttara Ashadha", "start_degree": 266.67, "end_degree": 280.0, 
             "deity": "Vishve Devah", "characteristics": "Victory, Universal, Final",
             "market_influence": "Victory stocks, universal sectors, final settlements"},
            {"name": "Shravana", "start_degree": 280.0, "end_degree": 293.33, 
             "deity": "Vishnu", "characteristics": "Listening, Learning, Fame",
             "market_influence": "Media sector, education stocks, famous companies"},
            {"name": "Dhanishtha", "start_degree": 293.33, "end_degree": 306.67, 
             "deity": "Vasus", "characteristics": "Wealth, Music, Rhythm",
             "market_influence": "Wealth creation, music industry, rhythmic patterns"},
            {"name": "Shatabhisha", "start_degree": 306.67, "end_degree": 320.0, 
             "deity": "Indra", "characteristics": "Hundred Healers, Medicine, Mystical",
             "market_influence": "Healthcare, pharmaceutical, mystical sectors"},
            {"name": "Purva Bhadrapada", "start_degree": 320.0, "end_degree": 333.33, 
             "deity": "Aja Ekapada", "characteristics": "Transformation, Fire, Passion",
             "market_influence": "Transformation sectors, energy stocks, passionate movements"},
            {"name": "Uttara Bhadrapada", "start_degree": 333.33, "end_degree": 346.67, 
             "deity": "Ahir Budhnya", "characteristics": "Foundation, Deep, Mystical",
             "market_influence": "Foundation stocks, deep value, mystical sectors"},
            {"name": "Revati", "start_degree": 346.67, "end_degree": 360.0, 
             "deity": "Pushan", "characteristics": "Wealthy, Journey, Completion",
             "market_influence": "Wealth management, travel sector, completion cycles"}
        ]
        
        # Zodiac signs for planetary position calculations
        self.zodiac_signs = [
            "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
            "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
        ]
        
    def set_date_time(self, date_time: datetime.datetime):
        """Set the date and time for calculations"""
        if date_time.tzinfo is None:
            date_time = IST.localize(date_time)
        self.observer.date = date_time.astimezone(pytz.UTC)
    
    def get_moon_phase(self, date_time: Optional[datetime.datetime] = None) -> Dict[str, Any]:
        """
        Calculate current lunar phase and related information
        
        Returns:
            Dictionary with phase name, illumination percentage, age in days, and market influence
        """
        if date_time:
            self.set_date_time(date_time)
        else:
            self.set_date_time(datetime.datetime.now())
        
        moon = ephem.Moon()
        moon.compute(self.observer)
        
        # Calculate phase information
        phase = moon.phase  # Illumination percentage
        
        # Find the previous and next new moon to calculate lunar age
        previous_new = ephem.previous_new_moon(self.observer.date)
        next_new = ephem.next_new_moon(self.observer.date)
        
        # Lunar age in days
        age = self.observer.date - previous_new
        
        # Determine phase name based on age and illumination
        phase_name = self._determine_phase_name(age, phase)
        
        # Market influence based on lunar phase
        market_influence = self._get_market_influence_by_phase(phase_name)
        
        return {
            'phase_name': phase_name.value,
            'illumination_percentage': round(phase, 2),
            'age_days': round(float(age), 2),
            'previous_new_moon': previous_new,
            'next_new_moon': next_new,
            'market_influence': market_influence
        }
    
    def _determine_phase_name(self, age: float, illumination: float) -> LunarPhase:
        """Determine lunar phase name based on age and illumination"""
        age_days = float(age)
        
        if age_days < 1:
            return LunarPhase.NEW_MOON
        elif age_days < 6.38:
            return LunarPhase.WAXING_CRESCENT
        elif age_days < 8.38:
            return LunarPhase.FIRST_QUARTER
        elif age_days < 13.76:
            return LunarPhase.WAXING_GIBBOUS
        elif age_days < 15.76:
            return LunarPhase.FULL_MOON
        elif age_days < 21.14:
            return LunarPhase.WANING_GIBBOUS
        elif age_days < 23.14:
            return LunarPhase.LAST_QUARTER
        else:
            return LunarPhase.WANING_CRESCENT
    
    def _get_market_influence_by_phase(self, phase: LunarPhase) -> Dict[str, str]:
        """Get market influence characteristics for each lunar phase"""
        influences = {
            LunarPhase.NEW_MOON: {
                "trend": "Bottom formation, fresh starts",
                "activity": "Accumulation phase, new position building",
                "sectors": "Growth stocks, new IPOs, emerging sectors",
                "strategy": "Long-term investment, value picking"
            },
            LunarPhase.WAXING_CRESCENT: {
                "trend": "Early upward momentum",
                "activity": "Growing confidence, gradual buying",
                "sectors": "Small and mid-cap stocks, growth stories",
                "strategy": "Momentum building, early entry points"
            },
            LunarPhase.FIRST_QUARTER: {
                "trend": "Moderate bullish momentum",
                "activity": "Increased trading volume, trend confirmation",
                "sectors": "Balanced sectors, diversified portfolio",
                "strategy": "Trend following, balanced allocation"
            },
            LunarPhase.WAXING_GIBBOUS: {
                "trend": "Strong bullish momentum",
                "activity": "Peak buying interest, FOMO phase",
                "sectors": "Large cap stocks, momentum favorites",
                "strategy": "Momentum trading, profit booking preparation"
            },
            LunarPhase.FULL_MOON: {
                "trend": "Market peaks, high volatility",
                "activity": "Profit booking, emotional trading",
                "sectors": "Volatile sectors, high beta stocks",
                "strategy": "Profit booking, risk management"
            },
            LunarPhase.WANING_GIBBOUS: {
                "trend": "Early correction signals",
                "activity": "Smart money exits, distribution phase",
                "sectors": "Defensive stocks, safe havens",
                "strategy": "Defensive positioning, cash accumulation"
            },
            LunarPhase.LAST_QUARTER: {
                "trend": "Moderate correction phase",
                "activity": "Selling pressure, trend reversal",
                "sectors": "Quality stocks at discount, value picks",
                "strategy": "Value hunting, selective buying"
            },
            LunarPhase.WANING_CRESCENT: {
                "trend": "Final correction phase",
                "activity": "Capitulation, bottom formation",
                "sectors": "Oversold quality stocks, contrarian plays",
                "strategy": "Contrarian investing, preparation for cycle"
            }
        }
        return influences.get(phase, {})
    
    def get_current_nakshatra(self, date_time: Optional[datetime.datetime] = None) -> Dict[str, Any]:
        """
        Calculate current nakshatra based on Moon's position
        
        Returns:
            Dictionary with nakshatra information and market implications
        """
        if date_time:
            self.set_date_time(date_time)
        else:
            self.set_date_time(datetime.datetime.now())
        
        moon = ephem.Moon()
        moon.compute(self.observer)
        
        # Moon's longitude in degrees
        moon_longitude = math.degrees(moon.ra)
        
        # Normalize to 0-360 range
        while moon_longitude < 0:
            moon_longitude += 360
        while moon_longitude >= 360:
            moon_longitude -= 360
        
        # Find the nakshatra (each nakshatra spans 13.33 degrees)
        nakshatra_index = int(moon_longitude / 13.333333)
        if nakshatra_index >= 27:
            nakshatra_index = 26
        
        nakshatra_info = self.nakshatras[nakshatra_index].copy()
        nakshatra_info['moon_longitude'] = round(moon_longitude, 2)
        nakshatra_info['nakshatra_degree'] = round(moon_longitude % 13.333333, 2)
        
        return nakshatra_info
    
    def get_planetary_positions(self, date_time: Optional[datetime.datetime] = None) -> Dict[str, Dict[str, Any]]:
        """
        Calculate positions of all major planets
        
        Returns:
            Dictionary with each planet's position and characteristics
        """
        if date_time:
            self.set_date_time(date_time)
        else:
            self.set_date_time(datetime.datetime.now())
        
        positions = {}
        
        for planet_name, planet_obj in self.planets.items():
            planet_obj.compute(self.observer)
            
            # Convert to degrees
            longitude = math.degrees(planet_obj.ra)
            while longitude < 0:
                longitude += 360
            while longitude >= 360:
                longitude -= 360
            
            # Determine zodiac sign
            sign_index = int(longitude / 30)
            sign = self.zodiac_signs[sign_index]
            degree_in_sign = longitude % 30
            
            # Market influence for each planet
            market_influence = self._get_planet_market_influence(planet_name, sign)
            
            positions[planet_name] = {
                'longitude': round(longitude, 2),
                'sign': sign,
                'degree_in_sign': round(degree_in_sign, 2),
                'market_influence': market_influence
            }
        
        return positions
    
    def _get_planet_market_influence(self, planet: str, sign: str) -> Dict[str, Any]:
        """Get market influence for planet in specific sign"""
        
        planet_influences = {
            'Sun': {
                'sectors': ['Banking', 'Government', 'Gold', 'PSUs', 'Leadership stocks'],
                'characteristics': 'Authority, Government policies, Leadership changes',
                'trading_impact': 'Government stock performance, policy announcements'
            },
            'Moon': {
                'sectors': ['FMCG', 'Dairy', 'Water', 'Healthcare', 'Consumer goods'],
                'characteristics': 'Public sentiment, emotional trading, consumer behavior',
                'trading_impact': 'Sentiment-driven moves, consumer stock performance'
            },
            'Mars': {
                'sectors': ['Defense', 'Steel', 'Real Estate', 'Energy', 'Infrastructure'],
                'characteristics': 'Aggressive moves, war/conflict, energy sectors',
                'trading_impact': 'Volatile movements, energy stock performance'
            },
            'Mercury': {
                'sectors': ['IT', 'Communication', 'Media', 'Trading', 'Transport'],
                'characteristics': 'Communication, technology, quick movements',
                'trading_impact': 'Tech stock performance, communication sector'
            },
            'Jupiter': {
                'sectors': ['Finance', 'Education', 'Banking', 'Wisdom sectors', 'Large caps'],
                'characteristics': 'Expansion, growth, wisdom, large institutions',
                'trading_impact': 'Financial sector performance, institutional moves'
            },
            'Venus': {
                'sectors': ['Luxury', 'Entertainment', 'Beauty', 'Arts', 'Fashion'],
                'characteristics': 'Luxury goods, entertainment, artistic sectors',
                'trading_impact': 'Luxury stock performance, entertainment sector'
            },
            'Saturn': {
                'sectors': ['Infrastructure', 'Oil', 'Mining', 'Real Estate', 'Long-term assets'],
                'characteristics': 'Slow movements, long-term trends, restrictions',
                'trading_impact': 'Infrastructure performance, long-term value'
            }
        }
        
        return planet_influences.get(planet, {})
    
    def is_auspicious_time(self, date_time: Optional[datetime.datetime] = None) -> Dict[str, Any]:
        """
        Determine if current time is auspicious for trading according to Vedic principles
        
        Returns:
            Dictionary with auspicious timing information
        """
        if date_time:
            current_time = date_time
        else:
            current_time = datetime.datetime.now(IST)
        
        # Calculate Rahu Kaal (inauspicious period)
        rahu_kaal = self._calculate_rahu_kaal(current_time.date())
        
        # Check if current time is in Rahu Kaal
        in_rahu_kaal = (rahu_kaal['start'] <= current_time.time() <= rahu_kaal['end'])
        
        # Abhijit Muhurat (most auspicious time)
        abhijit_start = datetime.time(11, 45)
        abhijit_end = datetime.time(12, 30)
        in_abhijit = (abhijit_start <= current_time.time() <= abhijit_end)
        
        # Brahma Muhurat (early morning auspicious time)
        brahma_start = datetime.time(4, 0)
        brahma_end = datetime.time(6, 0)
        in_brahma = (brahma_start <= current_time.time() <= brahma_end)
        
        # Overall auspiciousness
        is_auspicious = not in_rahu_kaal and (in_abhijit or in_brahma)
        
        return {
            'is_auspicious': is_auspicious,
            'in_rahu_kaal': in_rahu_kaal,
            'rahu_kaal_period': f"{rahu_kaal['start']} - {rahu_kaal['end']}",
            'in_abhijit_muhurat': in_abhijit,
            'abhijit_period': "11:45 AM - 12:30 PM",
            'in_brahma_muhurat': in_brahma,
            'brahma_period': "4:00 AM - 6:00 AM",
            'recommendation': self._get_timing_recommendation(is_auspicious, in_rahu_kaal, in_abhijit, in_brahma)
        }
    
    def _calculate_rahu_kaal(self, date: datetime.date) -> Dict[str, datetime.time]:
        """Calculate Rahu Kaal timings for a given date"""
        # Rahu Kaal varies by day of the week
        weekday = date.weekday()  # 0=Monday, 6=Sunday
        
        rahu_kaal_timings = {
            0: (datetime.time(7, 30), datetime.time(9, 0)),   # Monday
            1: (datetime.time(15, 0), datetime.time(16, 30)), # Tuesday
            2: (datetime.time(12, 0), datetime.time(13, 30)), # Wednesday
            3: (datetime.time(13, 30), datetime.time(15, 0)), # Thursday
            4: (datetime.time(10, 30), datetime.time(12, 0)), # Friday
            5: (datetime.time(9, 0), datetime.time(10, 30)),  # Saturday
            6: (datetime.time(16, 30), datetime.time(18, 0))  # Sunday
        }
        
        start_time, end_time = rahu_kaal_timings[weekday]
        return {'start': start_time, 'end': end_time}
    
    def _get_timing_recommendation(self, is_auspicious: bool, in_rahu_kaal: bool, 
                                 in_abhijit: bool, in_brahma: bool) -> str:
        """Get trading recommendation based on timing"""
        if in_rahu_kaal:
            return "Avoid major trading decisions during Rahu Kaal"
        elif in_abhijit:
            return "Excellent time for all trading activities (Abhijit Muhurat)"
        elif in_brahma:
            return "Good time for long-term investment decisions (Brahma Muhurat)"
        elif is_auspicious:
            return "Favorable time for trading activities"
        else:
            return "Neutral timing - proceed with normal caution"
    
    def get_daily_astro_summary(self, date_time: Optional[datetime.datetime] = None) -> Dict[str, Any]:
        """
        Get comprehensive daily astrological summary
        
        Returns:
            Complete summary with moon phase, nakshatra, planetary positions, and timing
        """
        if date_time:
            target_date = date_time
        else:
            target_date = datetime.datetime.now(IST)
        
        return {
            'date': target_date.strftime('%Y-%m-%d'),
            'moon_phase': self.get_moon_phase(target_date),
            'nakshatra': self.get_current_nakshatra(target_date),
            'planetary_positions': self.get_planetary_positions(target_date),
            'timing_analysis': self.is_auspicious_time(target_date),
            'overall_market_influence': self._get_overall_market_influence(target_date)
        }
    
    def _get_overall_market_influence(self, date_time: datetime.datetime) -> Dict[str, str]:
        """Calculate overall market influence combining all factors"""
        moon_phase = self.get_moon_phase(date_time)
        nakshatra = self.get_current_nakshatra(date_time)
        timing = self.is_auspicious_time(date_time)
        
        # Combine influences to create overall assessment
        phase_influence = moon_phase['market_influence']['trend']
        nakshatra_influence = nakshatra['market_influence']
        timing_influence = timing['recommendation']
        
        return {
            'primary_influence': phase_influence,
            'secondary_influence': nakshatra_influence,
            'timing_influence': timing_influence,
            'overall_recommendation': f"Luna: {phase_influence}, Nakshatra: {nakshatra['name']}, Timing: {timing_influence}"
        }


def test_calculator():
    """Test function to demonstrate the calculator capabilities"""
    calc = VedicAstrologyCalculator()
    
    print("=== Vedic Astrology Calculator Test ===")
    print()
    
    # Test current astro summary
    summary = calc.get_daily_astro_summary()
    
    print(f"Date: {summary['date']}")
    print()
    
    print("LUNAR PHASE:")
    moon = summary['moon_phase']
    print(f"Phase: {moon['phase_name']}")
    print(f"Illumination: {moon['illumination_percentage']}%")
    print(f"Age: {moon['age_days']} days")
    print(f"Market Trend: {moon['market_influence']['trend']}")
    print()
    
    print("CURRENT NAKSHATRA:")
    nakshatra = summary['nakshatra']
    print(f"Name: {nakshatra['name']}")
    print(f"Deity: {nakshatra['deity']}")
    print(f"Characteristics: {nakshatra['characteristics']}")
    print(f"Market Influence: {nakshatra['market_influence']}")
    print()
    
    print("PLANETARY POSITIONS:")
    for planet, position in summary['planetary_positions'].items():
        print(f"{planet}: {position['sign']} {position['degree_in_sign']:.1f}° - {position['market_influence']['sectors']}")
    print()
    
    print("TIMING ANALYSIS:")
    timing = summary['timing_analysis']
    print(f"Auspicious: {timing['is_auspicious']}")
    print(f"Recommendation: {timing['recommendation']}")
    print(f"Rahu Kaal: {timing['rahu_kaal_period']}")
    print()
    
    print("OVERALL MARKET INFLUENCE:")
    influence = summary['overall_market_influence']
    print(f"Recommendation: {influence['overall_recommendation']}")
    
    return summary


if __name__ == "__main__":
    test_calculator()