"""
Moon Zodiac House Analysis for Stock Market Correlation

This module analyzes how the Moon's transit through different zodiac signs
affects market movements, sector performance, and price patterns according
to Vedic astrology principles.

Author: Stock Screener with Vedic Astrology Integration
"""

import sys
import os
import datetime
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import matplotlib.pyplot as plt
import seaborn as sns

# Add the path to import vedic astrology modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'calculations'))

from core_calculator import VedicAstrologyCalculator
from moon_cycle_analyzer import MoonCycleAnalyzer


@dataclass
class ZodiacMarketInfluence:
    """Data class for zodiac sign market influence"""
    sign: str
    element: str
    quality: str
    ruling_planet: str
    market_tendency: str
    volatility_factor: float
    favored_sectors: List[str]
    price_direction: str
    volume_pattern: str
    risk_level: str
    trading_strategy: str


class MoonZodiacAnalyzer:
    """Analyzer for Moon's zodiac position effects on market"""
    
    def __init__(self):
        self.calculator = VedicAstrologyCalculator()
        self.moon_analyzer = MoonCycleAnalyzer()
        
        # Zodiac signs with their market characteristics
        self.zodiac_influences = {
            "Aries": ZodiacMarketInfluence(
                sign="Aries",
                element="Fire",
                quality="Cardinal",
                ruling_planet="Mars",
                market_tendency="Aggressive Bull Runs",
                volatility_factor=1.4,
                favored_sectors=["Defense", "Steel", "Auto", "Energy", "Sports"],
                price_direction="Sharp Upward",
                volume_pattern="High with Spikes",
                risk_level="High",
                trading_strategy="Momentum Trading"
            ),
            "Taurus": ZodiacMarketInfluence(
                sign="Taurus",
                element="Earth",
                quality="Fixed",
                ruling_planet="Venus",
                market_tendency="Steady Accumulation",
                volatility_factor=0.7,
                favored_sectors=["Banking", "FMCG", "Real Estate", "Agriculture", "Luxury"],
                price_direction="Steady Upward",
                volume_pattern="Consistent",
                risk_level="Low",
                trading_strategy="Value Investing"
            ),
            "Gemini": ZodiacMarketInfluence(
                sign="Gemini",
                element="Air",
                quality="Mutable",
                ruling_planet="Mercury",
                market_tendency="Quick Reversals",
                volatility_factor=1.2,
                favored_sectors=["IT", "Telecom", "Media", "Airlines", "Trading"],
                price_direction="Sideways with Swings",
                volume_pattern="Erratic",
                risk_level="Medium-High",
                trading_strategy="Swing Trading"
            ),
            "Cancer": ZodiacMarketInfluence(
                sign="Cancer",
                element="Water",
                quality="Cardinal",
                ruling_planet="Moon",
                market_tendency="Emotional Extremes",
                volatility_factor=1.3,
                favored_sectors=["FMCG", "Healthcare", "Hospitality", "Water", "Housing"],
                price_direction="Emotional Swings",
                volume_pattern="Sentiment Driven",
                risk_level="High",
                trading_strategy="Contrarian"
            ),
            "Leo": ZodiacMarketInfluence(
                sign="Leo",
                element="Fire",
                quality="Fixed",
                ruling_planet="Sun",
                market_tendency="Strong Leadership",
                volatility_factor=1.1,
                favored_sectors=["Banking", "Government", "Gold", "Entertainment", "Leadership"],
                price_direction="Confident Upward",
                volume_pattern="Strong and Sustained",
                risk_level="Medium",
                trading_strategy="Blue Chip Focus"
            ),
            "Virgo": ZodiacMarketInfluence(
                sign="Virgo",
                element="Earth",
                quality="Mutable",
                ruling_planet="Mercury",
                market_tendency="Analytical Corrections",
                volatility_factor=0.9,
                favored_sectors=["Healthcare", "IT Services", "Analytics", "Pharma", "Quality"],
                price_direction="Corrective Moves",
                volume_pattern="Measured",
                risk_level="Low-Medium",
                trading_strategy="Technical Analysis"
            ),
            "Libra": ZodiacMarketInfluence(
                sign="Libra",
                element="Air",
                quality="Cardinal",
                ruling_planet="Venus",
                market_tendency="Balanced Trading",
                volatility_factor=0.8,
                favored_sectors=["Luxury", "Fashion", "Legal", "Partnerships", "Beauty"],
                price_direction="Balanced Range",
                volume_pattern="Balanced",
                risk_level="Low",
                trading_strategy="Range Trading"
            ),
            "Scorpio": ZodiacMarketInfluence(
                sign="Scorpio",
                element="Water",
                quality="Fixed",
                ruling_planet="Mars",
                market_tendency="Deep Transformations",
                volatility_factor=1.5,
                favored_sectors=["Mining", "Oil", "Investigation", "Transformation", "Hidden"],
                price_direction="Intense Moves",
                volume_pattern="Concentrated Bursts",
                risk_level="Very High",
                trading_strategy="Deep Value"
            ),
            "Sagittarius": ZodiacMarketInfluence(
                sign="Sagittarius",
                element="Fire",
                quality="Mutable",
                ruling_planet="Jupiter",
                market_tendency="Expansive Growth",
                volatility_factor=1.0,
                favored_sectors=["Export", "Education", "Travel", "Foreign", "Philosophy"],
                price_direction="Expansive Upward",
                volume_pattern="Growing",
                risk_level="Medium",
                trading_strategy="Growth Investing"
            ),
            "Capricorn": ZodiacMarketInfluence(
                sign="Capricorn",
                element="Earth",
                quality="Cardinal",
                ruling_planet="Saturn",
                market_tendency="Disciplined Climb",
                volatility_factor=0.6,
                favored_sectors=["Infrastructure", "Cement", "Long-term", "Government", "Authority"],
                price_direction="Slow and Steady",
                volume_pattern="Disciplined",
                risk_level="Very Low",
                trading_strategy="Long-term Holdings"
            ),
            "Aquarius": ZodiacMarketInfluence(
                sign="Aquarius",
                element="Air",
                quality="Fixed",
                ruling_planet="Saturn",
                market_tendency="Innovation Spurts",
                volatility_factor=1.1,
                favored_sectors=["Technology", "Innovation", "Social", "Humanitarian", "Future"],
                price_direction="Innovative Jumps",
                volume_pattern="Tech-driven",
                risk_level="Medium",
                trading_strategy="Innovation Focus"
            ),
            "Pisces": ZodiacMarketInfluence(
                sign="Pisces",
                element="Water",
                quality="Mutable",
                ruling_planet="Jupiter",
                market_tendency="Intuitive Flows",
                volatility_factor=1.2,
                favored_sectors=["Chemicals", "Liquids", "Spirituality", "Arts", "Intuition"],
                price_direction="Flowing Trends",
                volume_pattern="Intuitive",
                risk_level="Medium-High",
                trading_strategy="Intuitive Trading"
            )
        }
    
    def get_moon_zodiac_influence(self, date_time: datetime.datetime = None) -> Dict[str, Any]:
        """Get current Moon's zodiac position and market influence"""
        if date_time is None:
            date_time = datetime.datetime.now()
        
        # Get planetary positions to find Moon's zodiac sign
        positions = self.calculator.get_planetary_positions(date_time)
        moon_position = positions['Moon']
        moon_sign = moon_position['sign']
        
        # Get zodiac influence
        influence = self.zodiac_influences.get(moon_sign)
        
        if influence is None:
            return {"error": f"No influence data for sign: {moon_sign}"}
        
        return {
            "date": date_time.strftime("%Y-%m-%d"),
            "moon_sign": moon_sign,
            "moon_degree": moon_position['degree_in_sign'],
            "influence": influence.__dict__,
            "market_prediction": self._generate_market_prediction(influence),
            "sector_recommendations": self._get_sector_recommendations(influence),
            "risk_assessment": self._assess_risk_level(influence)
        }
    
    def _generate_market_prediction(self, influence: ZodiacMarketInfluence) -> Dict[str, str]:
        """Generate market prediction based on zodiac influence"""
        return {
            "overall_trend": influence.market_tendency,
            "price_expectation": influence.price_direction,
            "volatility_forecast": f"{influence.volatility_factor}x normal",
            "volume_prediction": influence.volume_pattern,
            "recommended_strategy": influence.trading_strategy
        }
    
    def _get_sector_recommendations(self, influence: ZodiacMarketInfluence) -> Dict[str, Any]:
        """Get sector recommendations based on zodiac influence"""
        return {
            "favored_sectors": influence.favored_sectors,
            "element_focus": influence.element,
            "quality_approach": influence.quality,
            "planetary_ruler": influence.ruling_planet
        }
    
    def _assess_risk_level(self, influence: ZodiacMarketInfluence) -> Dict[str, Any]:
        """Assess risk level for trading"""
        risk_strategies = {
            "Very Low": "Aggressive position sizing allowed",
            "Low": "Normal position sizing",
            "Medium": "Moderate position sizing with stops",
            "Medium-High": "Reduced position sizing",
            "High": "Small positions only",
            "Very High": "Avoid or hedge positions"
        }
        
        return {
            "risk_level": influence.risk_level,
            "volatility_factor": influence.volatility_factor,
            "position_sizing": risk_strategies.get(influence.risk_level, "Caution advised")
        }
    
    def analyze_zodiac_price_correlation(self, start_date: datetime.date, 
                                       end_date: datetime.date) -> pd.DataFrame:
        """Analyze correlation between Moon zodiac positions and price patterns"""
        
        # Generate date range
        date_range = pd.date_range(start_date, end_date, freq='D')
        
        analysis_data = []
        
        for date in date_range:
            date_time = datetime.datetime.combine(date.date(), datetime.time(12, 0))
            
            # Get Moon's zodiac position
            zodiac_analysis = self.get_moon_zodiac_influence(date_time)
            
            if "error" not in zodiac_analysis:
                influence = self.zodiac_influences[zodiac_analysis['moon_sign']]
                
                analysis_data.append({
                    'date': date.date(),
                    'moon_sign': zodiac_analysis['moon_sign'],
                    'moon_degree': zodiac_analysis['moon_degree'],
                    'element': influence.element,
                    'quality': influence.quality,
                    'ruling_planet': influence.ruling_planet,
                    'volatility_factor': influence.volatility_factor,
                    'risk_level': influence.risk_level,
                    'market_tendency': influence.market_tendency,
                    'price_direction': influence.price_direction,
                    'favored_sectors': ', '.join(influence.favored_sectors[:3])
                })
        
        return pd.DataFrame(analysis_data)
    
    def create_zodiac_correlation_report(self, start_date: datetime.date, 
                                       end_date: datetime.date) -> Dict[str, Any]:
        """Create comprehensive zodiac correlation report"""
        
        df = self.analyze_zodiac_price_correlation(start_date, end_date)
        
        if df.empty:
            return {"error": "No data available for analysis"}
        
        # Statistical analysis
        sign_stats = df.groupby('moon_sign').agg({
            'volatility_factor': ['mean', 'std', 'count'],
            'date': ['min', 'max']
        }).round(3)
        
        # Element analysis
        element_stats = df.groupby('element').agg({
            'volatility_factor': 'mean',
            'moon_sign': 'count'
        }).round(3)
        
        # Risk level distribution
        risk_distribution = df['risk_level'].value_counts()
        
        # Most/Least volatile signs
        volatility_ranking = df.groupby('moon_sign')['volatility_factor'].mean().sort_values(ascending=False)
        
        return {
            "analysis_period": f"{start_date} to {end_date}",
            "total_days_analyzed": len(df),
            "zodiac_sign_statistics": sign_stats.to_dict(),
            "element_analysis": element_stats.to_dict(),
            "risk_level_distribution": risk_distribution.to_dict(),
            "volatility_ranking": volatility_ranking.to_dict(),
            "most_volatile_sign": volatility_ranking.index[0],
            "least_volatile_sign": volatility_ranking.index[-1],
            "average_volatility": df['volatility_factor'].mean(),
            "recommendations": self._generate_correlation_recommendations(df)
        }
    
    def _generate_correlation_recommendations(self, df: pd.DataFrame) -> Dict[str, str]:
        """Generate trading recommendations based on correlation analysis"""
        
        high_volatility_signs = df[df['volatility_factor'] > 1.2]['moon_sign'].unique()
        low_volatility_signs = df[df['volatility_factor'] < 0.9]['moon_sign'].unique()
        
        return {
            "high_volatility_periods": f"Expect increased volatility when Moon is in: {', '.join(high_volatility_signs)}",
            "low_volatility_periods": f"Safer trading when Moon is in: {', '.join(low_volatility_signs)}",
            "fire_signs_strategy": "Aries, Leo, Sagittarius - Focus on momentum and energy sectors",
            "earth_signs_strategy": "Taurus, Virgo, Capricorn - Value investing and stable sectors",
            "air_signs_strategy": "Gemini, Libra, Aquarius - Technology and communication sectors",
            "water_signs_strategy": "Cancer, Scorpio, Pisces - Emotional sectors and contrarian plays"
        }
    
    def visualize_zodiac_price_correlation(self, start_date: datetime.date, 
                                         end_date: datetime.date, save_path: str = None):
        """Create visualizations for zodiac-price correlations"""
        
        df = self.analyze_zodiac_price_correlation(start_date, end_date)
        
        if df.empty:
            print("No data available for visualization")
            return
        
        # Create figure with subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(20, 12))
        fig.suptitle('Moon Zodiac Signs - Market Correlation Analysis', fontsize=16, fontweight='bold')
        
        # 1. Volatility by Zodiac Sign
        sign_volatility = df.groupby('moon_sign')['volatility_factor'].mean().sort_values(ascending=False)
        colors = ['red' if x > 1.1 else 'orange' if x > 0.9 else 'green' for x in sign_volatility.values]
        
        ax1.bar(sign_volatility.index, sign_volatility.values, color=colors, alpha=0.7)
        ax1.set_title('Average Volatility by Moon Sign', fontweight='bold')
        ax1.set_ylabel('Volatility Factor')
        ax1.axhline(y=1.0, color='black', linestyle='--', alpha=0.5, label='Normal (1.0x)')
        ax1.legend()
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # 2. Element-wise Analysis
        element_data = df.groupby('element')['volatility_factor'].mean()
        colors_element = ['red', 'brown', 'lightblue', 'blue']
        
        ax2.pie(element_data.values, labels=element_data.index, autopct='%1.1f%%', 
               colors=colors_element, startangle=90)
        ax2.set_title('Volatility Distribution by Element', fontweight='bold')
        
        # 3. Time Series of Volatility
        df['date'] = pd.to_datetime(df['date'])
        ax3.plot(df['date'], df['volatility_factor'], 'purple', linewidth=2, alpha=0.8)
        ax3.fill_between(df['date'], 0.5, df['volatility_factor'], alpha=0.3, color='purple')
        ax3.set_title('Volatility Factor Over Time', fontweight='bold')
        ax3.set_ylabel('Volatility Factor')
        ax3.grid(True, alpha=0.3)
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)
        
        # 4. Risk Level Distribution
        risk_counts = df['risk_level'].value_counts()
        risk_colors = ['green', 'yellow', 'orange', 'red', 'darkred'][:len(risk_counts)]
        
        ax4.pie(risk_counts.values, labels=risk_counts.index, autopct='%1.1f%%',
               colors=risk_colors, startangle=90)
        ax4.set_title('Risk Level Distribution', fontweight='bold')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Zodiac correlation visualization saved to: {save_path}")
        
        plt.show()
        return fig


def test_zodiac_analysis():
    """Test function for zodiac analysis"""
    print("=== Moon Zodiac Market Correlation Analysis ===")
    
    analyzer = MoonZodiacAnalyzer()
    
    # Current zodiac influence
    print("\nCURRENT MOON ZODIAC INFLUENCE:")
    current_influence = analyzer.get_moon_zodiac_influence()
    
    if "error" not in current_influence:
        print(f"Date: {current_influence['date']}")
        print(f"Moon Sign: {current_influence['moon_sign']}")
        print(f"Moon Degree: {current_influence['moon_degree']:.1f}°")
        print(f"Market Tendency: {current_influence['influence']['market_tendency']}")
        print(f"Volatility Factor: {current_influence['influence']['volatility_factor']}x")
        print(f"Favored Sectors: {', '.join(current_influence['influence']['favored_sectors'][:3])}")
        print(f"Trading Strategy: {current_influence['influence']['trading_strategy']}")
        print(f"Risk Level: {current_influence['influence']['risk_level']}")
    
    # Correlation analysis for 2025
    print(f"\nZODIAC CORRELATION ANALYSIS (2025):")
    start_date = datetime.date(2025, 1, 1)
    end_date = datetime.date(2025, 12, 31)
    
    report = analyzer.create_zodiac_correlation_report(start_date, end_date)
    
    if "error" not in report:
        print(f"Analysis Period: {report['analysis_period']}")
        print(f"Total Days: {report['total_days_analyzed']}")
        print(f"Most Volatile Sign: {report['most_volatile_sign']}")
        print(f"Least Volatile Sign: {report['least_volatile_sign']}")
        print(f"Average Volatility: {report['average_volatility']:.2f}x")
        
        print(f"\nRECOMMENDATIONS:")
        for key, value in report['recommendations'].items():
            print(f"• {key.replace('_', ' ').title()}: {value}")
        
        # Create visualization
        save_path = os.path.join(os.path.dirname(__file__), 'zodiac_correlation_2025.png')
        analyzer.visualize_zodiac_price_correlation(start_date, end_date, save_path)
    
    print("\nZodiac analysis completed!")


if __name__ == "__main__":
    test_zodiac_analysis()