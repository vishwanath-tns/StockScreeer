"""
Trading Strategy Generator based on Vedic Astrology

This tool generates specific trading strategies and actionable recommendations
based on current and upcoming lunar positions.
"""

import sys
import os
import datetime
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
import json

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'calculations'))

from moon_zodiac_analyzer import MoonZodiacAnalyzer
from market_forecast import MarketForecastEngine


class TradingStrategyGenerator:
    """Generate specific trading strategies based on astrological analysis"""
    
    def __init__(self):
        self.zodiac_analyzer = MoonZodiacAnalyzer()
        self.forecast_engine = MarketForecastEngine()
        
        # Stock recommendations by sector and zodiac element
        self.sector_stocks = {
            'ENERGY': ['RELIANCE', 'ONGC', 'IOC', 'BPCL', 'HPCL', 'GAIL', 'NTPC'],
            'DEFENSE': ['BEL', 'HAL', 'BEML', 'COCHINSHIP', 'GRSE'],
            'AUTO': ['MARUTI', 'TATAMOTORS', 'M&M', 'BAJAJ-AUTO', 'HEROMOTOCO', 'TVSMOTOR'],
            'STEEL': ['TATASTEEL', 'JSWSTEEL', 'SAILRED', 'JINDALSTEL', 'NMDC'],
            'BANKING': ['HDFCBANK', 'ICICIBANK', 'SBIN', 'KOTAKBANK', 'AXISBANK', 'INDUSIND'],
            'FMCG': ['HINDUUNILVR', 'ITC', 'NESTLEIND', 'BRITANNIA', 'DABUR', 'GODREJCP'],
            'IT': ['TCS', 'INFY', 'WIPRO', 'HCLTECH', 'TECHM', 'LTI', 'MPHASIS'],
            'HEALTHCARE': ['DRREDDY', 'CIPLA', 'LUPIN', 'BIOCON', 'CADILAHC', 'TORNTPHARM'],
            'TELECOM': ['BHARTIARTL', 'IDEA', 'RCOM'],
            'INFRASTRUCTURE': ['LT', 'ULTRACEMCO', 'ACC', 'AMBUJACEMENT', 'GRASIM'],
            'CHEMICALS': ['UPL', 'PIDILITIND', 'ATUL', 'DEEPAKNI', 'BALRAMCHIN'],
            'REALESTATE': ['DLF', 'GODREJPROP', 'BRIGADE', 'PRESTIGE', 'SOBHA'],
            'MINING': ['COALINDIA', 'HINDZINC', 'VEDL', 'NMDC', 'MOIL']
        }
        
        # Risk-based position sizing rules
        self.position_sizing_rules = {
            'Very High': {'max_position': 0.02, 'max_total_exposure': 0.10},  # 2% per stock, 10% total
            'High': {'max_position': 0.03, 'max_total_exposure': 0.15},      # 3% per stock, 15% total
            'Medium': {'max_position': 0.05, 'max_total_exposure': 0.25},    # 5% per stock, 25% total
            'Low': {'max_position': 0.08, 'max_total_exposure': 0.40},       # 8% per stock, 40% total
            'Very Low': {'max_position': 0.10, 'max_total_exposure': 0.50}   # 10% per stock, 50% total
        }
    
    def generate_daily_strategy(self, date: datetime.date = None) -> Dict[str, Any]:
        """Generate complete trading strategy for a specific day"""
        
        if date is None:
            date = datetime.date.today()
        
        date_time = datetime.datetime.combine(date, datetime.time(12, 0))
        
        # Get zodiac analysis
        zodiac_analysis = self.zodiac_analyzer.get_moon_zodiac_influence(date_time)
        
        if "error" in zodiac_analysis:
            return {"error": f"Could not analyze date {date}"}
        
        influence = zodiac_analysis['influence']
        
        # Generate comprehensive strategy
        strategy = {
            'date': date.strftime('%Y-%m-%d'),
            'day_name': date.strftime('%A'),
            'moon_position': {
                'sign': zodiac_analysis['moon_sign'],
                'degree': round(zodiac_analysis['moon_degree'], 1),
                'element': influence['element'],
                'quality': influence['quality']
            },
            'market_outlook': self._generate_market_outlook(influence),
            'risk_management': self._generate_risk_rules(influence),
            'sector_strategy': self._generate_sector_strategy(influence),
            'stock_recommendations': self._get_stock_recommendations(influence),
            'trading_tactics': self._generate_trading_tactics(influence),
            'timing_strategy': self._generate_timing_strategy(influence),
            'alerts_and_warnings': self._generate_alerts(influence, zodiac_analysis['moon_sign'])
        }
        
        return strategy
    
    def _generate_market_outlook(self, influence: Dict) -> Dict[str, Any]:
        """Generate market outlook for the day"""
        
        volatility = influence['volatility_factor']
        element = influence['element']
        tendency = influence['market_tendency']
        
        if volatility >= 1.4:
            outlook = "Highly Volatile - Extreme caution required"
            expectation = "Large price swings, gaps, emotional trading"
        elif volatility >= 1.2:
            outlook = "Elevated Volatility - Increased attention needed"
            expectation = "Above-normal price movements, active trading"
        elif volatility <= 0.8:
            outlook = "Low Volatility - Good for accumulation"
            expectation = "Stable price action, good for value buying"
        else:
            outlook = "Normal Volatility - Standard trading conditions"
            expectation = "Regular price patterns, balanced opportunities"
        
        return {
            'overall_outlook': outlook,
            'volatility_expectation': f"{volatility}x normal",
            'price_expectation': expectation,
            'market_tendency': tendency,
            'dominant_element': element,
            'recommended_approach': self._get_element_approach(element)
        }
    
    def _get_element_approach(self, element: str) -> str:
        """Get trading approach based on element"""
        approaches = {
            'Fire': 'Aggressive momentum trading, quick decisions',
            'Earth': 'Conservative value investing, patient accumulation',
            'Air': 'Flexible swing trading, technology focus',
            'Water': 'Intuitive contrarian trading, emotional sectors'
        }
        return approaches.get(element, 'Balanced approach')
    
    def _generate_risk_rules(self, influence: Dict) -> Dict[str, Any]:
        """Generate risk management rules for the day"""
        
        risk_level = influence['risk_level']
        volatility = influence['volatility_factor']
        
        sizing_rules = self.position_sizing_rules.get(risk_level, self.position_sizing_rules['Medium'])
        
        # Stop loss recommendations
        if volatility >= 1.4:
            stop_loss = "2-3% (Very tight)"
            profit_target = "4-6% (Quick profits)"
        elif volatility >= 1.2:
            stop_loss = "3-4% (Tight)"
            profit_target = "6-8% (Moderate targets)"
        elif volatility <= 0.8:
            stop_loss = "5-7% (Wide)"
            profit_target = "10-15% (Patient targets)"
        else:
            stop_loss = "4-5% (Standard)"
            profit_target = "8-12% (Normal targets)"
        
        return {
            'risk_level': risk_level,
            'max_position_size': f"{sizing_rules['max_position']*100:.0f}% of portfolio per stock",
            'max_total_exposure': f"{sizing_rules['max_total_exposure']*100:.0f}% of total portfolio",
            'stop_loss_recommendation': stop_loss,
            'profit_target': profit_target,
            'leverage_advice': 'Avoid leverage' if volatility >= 1.3 else 'Use moderate leverage',
            'overnight_holdings': 'Avoid' if volatility >= 1.4 else 'Allowed with stops'
        }
    
    def _generate_sector_strategy(self, influence: Dict) -> Dict[str, Any]:
        """Generate sector-specific strategy"""
        
        element = influence['element']
        favored_sectors = influence['favored_sectors']
        
        # Primary and secondary sector focus
        if element == 'Fire':
            primary_focus = ['ENERGY', 'DEFENSE', 'AUTO', 'STEEL']
            avoid_sectors = ['FMCG', 'UTILITIES']
            approach = 'Momentum-based sector rotation'
        elif element == 'Earth':
            primary_focus = ['BANKING', 'FMCG', 'INFRASTRUCTURE', 'REALESTATE']
            avoid_sectors = ['TECHNOLOGY', 'SPECULATION']
            approach = 'Value-based sector accumulation'
        elif element == 'Air':
            primary_focus = ['IT', 'TELECOM', 'AVIATION', 'MEDIA']
            avoid_sectors = ['HEAVY_INDUSTRY', 'MINING']
            approach = 'Technology and communication focus'
        else:  # Water
            primary_focus = ['HEALTHCARE', 'CHEMICALS', 'HOSPITALITY']
            avoid_sectors = ['MECHANICAL', 'CONSTRUCTION']
            approach = 'Emotional and intuitive sectors'
        
        return {
            'element_focus': element,
            'primary_sectors': primary_focus,
            'secondary_sectors': favored_sectors,
            'sectors_to_avoid': avoid_sectors,
            'rotation_strategy': approach,
            'sector_allocation': self._get_sector_allocation(primary_focus)
        }
    
    def _get_sector_allocation(self, sectors: List[str]) -> Dict[str, str]:
        """Get recommended allocation across sectors"""
        allocation = {}
        equal_weight = round(100 / len(sectors), 1)
        
        for sector in sectors:
            allocation[sector] = f"{equal_weight}%"
        
        return allocation
    
    def _get_stock_recommendations(self, influence: Dict) -> Dict[str, List[str]]:
        """Get specific stock recommendations"""
        
        element = influence['element']
        volatility = influence['volatility_factor']
        
        recommendations = {
            'top_picks': [],
            'accumulation_candidates': [],
            'momentum_plays': [],
            'avoid_list': []
        }
        
        # Get stocks from favored sectors
        favored_sectors = influence['favored_sectors'][:3]  # Top 3 sectors
        
        for sector in favored_sectors:
            sector_key = sector.upper().replace(' ', '_')
            stocks = self.sector_stocks.get(sector_key, [])
            
            if stocks:
                if volatility >= 1.2:  # High volatility
                    recommendations['momentum_plays'].extend(stocks[:2])
                else:  # Low volatility
                    recommendations['accumulation_candidates'].extend(stocks[:3])
                
                recommendations['top_picks'].extend(stocks[:2])
        
        # Remove duplicates and limit lists
        recommendations['top_picks'] = list(set(recommendations['top_picks']))[:5]
        recommendations['accumulation_candidates'] = list(set(recommendations['accumulation_candidates']))[:8]
        recommendations['momentum_plays'] = list(set(recommendations['momentum_plays']))[:5]
        
        # Add stocks to avoid in high volatility
        if volatility >= 1.3:
            # Avoid small-cap and volatile stocks
            recommendations['avoid_list'] = ['Small-cap stocks', 'Penny stocks', 'Highly leveraged companies']
        
        return recommendations
    
    def _generate_trading_tactics(self, influence: Dict) -> Dict[str, Any]:
        """Generate specific trading tactics"""
        
        element = influence['element']
        volatility = influence['volatility_factor']
        strategy = influence['trading_strategy']
        
        # Entry tactics
        if volatility >= 1.3:
            entry_method = "Wait for clear breakouts with volume confirmation"
            scaling_approach = "Scale in with small positions"
        elif volatility <= 0.8:
            entry_method = "Buy on dips and support levels"
            scaling_approach = "Scale in on weakness"
        else:
            entry_method = "Follow technical patterns"
            scaling_approach = "Normal position building"
        
        # Exit tactics
        if element == 'Fire':
            exit_strategy = "Quick profit taking, trail stops aggressively"
        elif element == 'Water':
            exit_strategy = "Contrarian exits, sell strength, buy weakness"
        else:
            exit_strategy = "Target-based exits with standard trailing stops"
        
        return {
            'primary_strategy': strategy,
            'entry_method': entry_method,
            'exit_strategy': exit_strategy,
            'scaling_approach': scaling_approach,
            'ideal_holding_period': self._get_holding_period(element, volatility),
            'technical_indicators': self._get_recommended_indicators(element),
            'market_timing': self._get_market_timing_advice(volatility)
        }
    
    def _get_holding_period(self, element: str, volatility: float) -> str:
        """Get recommended holding period"""
        if volatility >= 1.3:
            return "Intraday to 1-2 days (Very short)"
        elif element == 'Fire':
            return "2-5 days (Short momentum)"
        elif element == 'Earth':
            return "2-4 weeks (Medium term)"
        else:
            return "1-2 weeks (Swing trading)"
    
    def _get_recommended_indicators(self, element: str) -> List[str]:
        """Get recommended technical indicators by element"""
        indicators = {
            'Fire': ['RSI', 'MACD', 'Volume', 'Momentum oscillators'],
            'Earth': ['Moving averages', 'Support/Resistance', 'Value metrics'],
            'Air': ['Bollinger Bands', 'Volatility indicators', 'Trend lines'],
            'Water': ['Stochastic', 'Williams %R', 'Sentiment indicators']
        }
        return indicators.get(element, ['RSI', 'Moving averages'])
    
    def _get_market_timing_advice(self, volatility: float) -> str:
        """Get market timing advice"""
        if volatility >= 1.4:
            return "Trade only during market hours, avoid pre/post market"
        elif volatility >= 1.2:
            return "Focus on first hour and last hour of trading"
        else:
            return "Normal trading hours, any time suitable"
    
    def _generate_timing_strategy(self, influence: Dict) -> Dict[str, str]:
        """Generate intraday timing strategy"""
        
        element = influence['element']
        volatility = influence['volatility_factor']
        
        if element == 'Fire' and volatility >= 1.2:
            return {
                'best_entry_time': '9:15-10:00 AM (Opening momentum)',
                'best_exit_time': '2:30-3:30 PM (Before close)',
                'avoid_periods': '11:00 AM - 1:00 PM (Lunch doldrums)',
                'overnight_strategy': 'Avoid - too risky'
            }
        elif element == 'Earth':
            return {
                'best_entry_time': '10:00-11:00 AM (After opening volatility)',
                'best_exit_time': 'End of day for profits',
                'avoid_periods': 'First 15 minutes (Gap volatility)',
                'overnight_strategy': 'Suitable for swing trades'
            }
        elif volatility >= 1.3:
            return {
                'best_entry_time': 'Wait for clear patterns',
                'best_exit_time': 'Quick profit taking',
                'avoid_periods': 'High volatility spikes',
                'overnight_strategy': 'Strictly avoid'
            }
        else:
            return {
                'best_entry_time': 'Any time with good setups',
                'best_exit_time': 'Target-based exits',
                'avoid_periods': 'None specifically',
                'overnight_strategy': 'Allowed with stops'
            }
    
    def _generate_alerts(self, influence: Dict, moon_sign: str) -> List[str]:
        """Generate specific alerts for the day"""
        alerts = []
        
        volatility = influence['volatility_factor']
        risk_level = influence['risk_level']
        
        if moon_sign == 'Scorpio':
            alerts.append("[SCORPIO] SCORPIO MOON: Expect intense, transformative movements. Trade very carefully!")
        
        if volatility >= 1.4:
            alerts.append("[EXTREME] EXTREME VOLATILITY: Consider staying in cash or very small positions")
        elif volatility >= 1.2:
            alerts.append("[HIGH VOL] HIGH VOLATILITY: Use tight stops and take quick profits")
        
        if risk_level == 'Very High':
            alerts.append("🛑 VERY HIGH RISK: Maximum position size 2% per stock")
        
        if influence['element'] == 'Water':
            alerts.append("💧 WATER ELEMENT: Market may be driven by emotions and sentiment")
        elif influence['element'] == 'Fire':
            alerts.append("🔥 FIRE ELEMENT: Momentum and energy sectors favored")
        
        # Add sector-specific alerts
        favored = influence['favored_sectors'][0] if influence['favored_sectors'] else 'None'
        alerts.append(f"[SECTOR] SECTOR FOCUS: {favored} expected to outperform")
        
        return alerts
    
    def generate_weekly_strategies(self, weeks_ahead: int = 2) -> Dict[str, Any]:
        """Generate strategies for multiple weeks"""
        
        weekly_strategies = []
        today = datetime.date.today()
        
        for week in range(weeks_ahead):
            week_start = today + datetime.timedelta(days=(7 * week))
            week_start = week_start - datetime.timedelta(days=week_start.weekday())
            
            daily_strategies = []
            for day in range(7):
                current_date = week_start + datetime.timedelta(days=day)
                
                # Only generate for weekdays
                if current_date.weekday() < 5:
                    daily_strategy = self.generate_daily_strategy(current_date)
                    if "error" not in daily_strategy:
                        daily_strategies.append(daily_strategy)
            
            if daily_strategies:
                week_summary = self._summarize_weekly_strategy(daily_strategies, week + 1)
                weekly_strategies.append({
                    'week_number': week + 1,
                    'week_start': week_start.strftime('%Y-%m-%d'),
                    'summary': week_summary,
                    'daily_strategies': daily_strategies
                })
        
        return {
            'generation_date': today.strftime('%Y-%m-%d'),
            'weeks_ahead': weeks_ahead,
            'weekly_strategies': weekly_strategies
        }
    
    def _summarize_weekly_strategy(self, daily_strategies: List[Dict], week_num: int) -> Dict[str, Any]:
        """Summarize strategy for a week"""
        
        # Aggregate weekly data
        volatilities = []
        for s in daily_strategies:
            vol_str = s['market_outlook']['volatility_expectation']
            if 'x normal' in vol_str:
                try:
                    vol_num = float(vol_str.replace('x normal', '').strip())
                    volatilities.append(vol_num)
                except ValueError:
                    volatilities.append(1.0)  # Default if parsing fails
        
        avg_volatility = np.mean(volatilities) if volatilities else 1.0
        
        dominant_elements = [s['moon_position']['element'] for s in daily_strategies]
        dominant_element = max(set(dominant_elements), key=dominant_elements.count)
        
        high_risk_days = sum(1 for s in daily_strategies if 'High' in s['risk_management']['risk_level'])
        
        return {
            'week_theme': f"Week {week_num} - {dominant_element} Dominant",
            'average_volatility': f"{avg_volatility:.1f}x normal",
            'high_risk_days': high_risk_days,
            'recommended_approach': self._get_element_approach(dominant_element),
            'key_focus': f"{dominant_element} element strategies"
        }


def generate_trading_reports():
    """Generate comprehensive trading reports"""
    print("=== GENERATING VEDIC TRADING STRATEGY REPORTS ===")
    
    generator = TradingStrategyGenerator()
    
    # Generate today's strategy
    today_strategy = generator.generate_daily_strategy()
    
    # Generate 2-week strategies
    weekly_strategies = generator.generate_weekly_strategies(2)
    
    # Create reports directory
    reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    # Save today's detailed strategy
    today_file = os.path.join(reports_dir, f"daily_strategy_{datetime.date.today().strftime('%Y%m%d')}.json")
    with open(today_file, 'w') as f:
        json.dump(today_strategy, f, indent=2, default=str)
    
    # Save weekly strategies
    weekly_file = os.path.join(reports_dir, f"weekly_strategies_{datetime.date.today().strftime('%Y%m%d')}.json")
    with open(weekly_file, 'w') as f:
        json.dump(weekly_strategies, f, indent=2, default=str)
    
    # Create human-readable summary
    summary_file = os.path.join(reports_dir, f"trading_summary_{datetime.date.today().strftime('%Y%m%d')}.txt")
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("=== VEDIC ASTROLOGY TRADING STRATEGY REPORT ===\n\n")
        f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Today's strategy summary
        f.write("📅 TODAY'S TRADING STRATEGY\n")
        f.write("=" * 50 + "\n")
        f.write(f"Date: {today_strategy['date']} ({today_strategy['day_name']})\n")
        f.write(f"Moon Position: {today_strategy['moon_position']['sign']} ({today_strategy['moon_position']['element']} element)\n")
        f.write(f"Market Outlook: {today_strategy['market_outlook']['overall_outlook']}\n")
        f.write(f"Volatility: {today_strategy['market_outlook']['volatility_expectation']}\n")
        f.write(f"Risk Level: {today_strategy['risk_management']['risk_level']}\n")
        f.write(f"Max Position Size: {today_strategy['risk_management']['max_position_size']}\n")
        f.write(f"Stop Loss: {today_strategy['risk_management']['stop_loss_recommendation']}\n\n")
        
        # Alerts
        f.write("🚨 KEY ALERTS:\n")
        for alert in today_strategy['alerts_and_warnings']:
            f.write(f"  • {alert}\n")
        f.write("\n")
        
        # Stock recommendations
        f.write("📊 STOCK RECOMMENDATIONS:\n")
        f.write(f"Top Picks: {', '.join(today_strategy['stock_recommendations']['top_picks'])}\n")
        f.write(f"Accumulation: {', '.join(today_strategy['stock_recommendations']['accumulation_candidates'][:5])}\n")
        f.write(f"Momentum: {', '.join(today_strategy['stock_recommendations']['momentum_plays'])}\n\n")
        
        # Sector strategy
        f.write("🎯 SECTOR STRATEGY:\n")
        f.write(f"Primary Focus: {', '.join(today_strategy['sector_strategy']['primary_sectors'])}\n")
        f.write(f"Approach: {today_strategy['sector_strategy']['rotation_strategy']}\n\n")
        
        # Trading tactics
        f.write("⚡ TRADING TACTICS:\n")
        f.write(f"Strategy: {today_strategy['trading_tactics']['primary_strategy']}\n")
        f.write(f"Entry: {today_strategy['trading_tactics']['entry_method']}\n")
        f.write(f"Exit: {today_strategy['trading_tactics']['exit_strategy']}\n")
        f.write(f"Holding Period: {today_strategy['trading_tactics']['ideal_holding_period']}\n\n")
    
    print(f"📄 Reports generated:")
    print(f"  • Today's Strategy: {today_file}")
    print(f"  • Weekly Strategies: {weekly_file}")
    print(f"  • Summary Report: {summary_file}")
    
    # Display key information
    print(f"\n🎯 TODAY'S KEY INFORMATION:")
    print(f"Moon Sign: {today_strategy['moon_position']['sign']} ({today_strategy['moon_position']['element']})")
    print(f"Volatility: {today_strategy['market_outlook']['volatility_expectation']}")
    print(f"Risk Level: {today_strategy['risk_management']['risk_level']}")
    print(f"Top Stocks: {', '.join(today_strategy['stock_recommendations']['top_picks'][:3])}")
    print(f"Strategy: {today_strategy['trading_tactics']['primary_strategy']}")
    
    print(f"\n🚨 Key Alerts:")
    for alert in today_strategy['alerts_and_warnings'][:3]:
        print(f"  • {alert}")
    
    return {
        'daily_strategy_file': today_file,
        'weekly_strategies_file': weekly_file,
        'summary_file': summary_file
    }


if __name__ == "__main__":
    generate_trading_reports()