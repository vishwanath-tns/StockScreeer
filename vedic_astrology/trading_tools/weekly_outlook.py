"""
Weekly Market Outlook Generator

This tool creates comprehensive weekly reports with specific trading recommendations
for the upcoming week based on Vedic astrology analysis.
"""

import sys
import os
import datetime
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
import matplotlib.pyplot as plt
import json

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'calculations'))

from market_forecast import MarketForecastEngine
from trading_strategy import TradingStrategyGenerator


class WeeklyOutlookGenerator:
    """Generate comprehensive weekly market outlook reports"""
    
    def __init__(self):
        self.forecast_engine = MarketForecastEngine()
        self.strategy_generator = TradingStrategyGenerator()
        
        # Define market sectors with NSE symbols
        self.nse_sectors = {
            'NIFTY_BANK': ['HDFCBANK', 'ICICIBANK', 'SBIN', 'KOTAKBANK', 'AXISBANK', 'INDUSIND', 'BANDHANBNK'],
            'NIFTY_IT': ['TCS', 'INFY', 'HCLTECH', 'WIPRO', 'TECHM', 'LTI', 'MINDTREE'],
            'NIFTY_PHARMA': ['SUNPHARMA', 'DRREDDY', 'CIPLA', 'LUPIN', 'BIOCON', 'DIVISLAB'],
            'NIFTY_FMCG': ['HINDUUNILVR', 'ITC', 'NESTLEIND', 'BRITANNIA', 'DABUR', 'GODREJCP'],
            'NIFTY_AUTO': ['MARUTI', 'TATAMOTORS', 'M&M', 'BAJAJ-AUTO', 'HEROMOTOCO', 'EICHERMOT'],
            'NIFTY_ENERGY': ['RELIANCE', 'ONGC', 'IOC', 'BPCL', 'HPCL', 'GAIL'],
            'NIFTY_METAL': ['TATASTEEL', 'JSWSTEEL', 'HINDALCO', 'VEDL', 'COALINDIA', 'HINDZINC'],
            'NIFTY_REALTY': ['DLF', 'GODREJPROP', 'BRIGADE', 'PRESTIGE', 'SOBHA']
        }
        
    def generate_weekly_outlook(self, target_week: datetime.date = None) -> Dict[str, Any]:
        """Generate comprehensive weekly outlook"""
        
        if target_week is None:
            target_week = datetime.date.today()
        
        # Get the start of the target week (Monday)
        week_start = target_week - datetime.timedelta(days=target_week.weekday())
        week_end = week_start + datetime.timedelta(days=4)  # Friday
        
        # Generate 1-week forecast
        forecast = self.forecast_engine.generate_weekly_forecast(1)
        
        if not forecast['weekly_forecasts']:
            return {"error": "Could not generate forecast"}
        
        week_forecast = forecast['weekly_forecasts'][0]
        
        # Get daily strategies for the week
        daily_strategies = []
        for day in range(5):  # Monday to Friday
            current_date = week_start + datetime.timedelta(days=day)
            daily_strategy = self.strategy_generator.generate_daily_strategy(current_date)
            if "error" not in daily_strategy:
                daily_strategies.append(daily_strategy)
        
        # Generate comprehensive outlook
        outlook = {
            'report_date': datetime.date.today().strftime('%Y-%m-%d'),
            'target_week': f"{week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}",
            'week_number': week_start.isocalendar()[1],
            'executive_summary': self._create_executive_summary(week_forecast, daily_strategies),
            'weekly_forecast': week_forecast,
            'daily_breakdown': daily_strategies,
            'sector_outlook': self._generate_sector_outlook(daily_strategies),
            'stock_watchlist': self._create_stock_watchlist(daily_strategies),
            'risk_calendar': self._create_risk_calendar(daily_strategies),
            'trading_plan': self._create_weekly_trading_plan(week_forecast, daily_strategies),
            'key_dates': self._identify_key_dates(daily_strategies),
            'portfolio_allocation': self._recommend_portfolio_allocation(week_forecast)
        }
        
        return outlook
    
    def _create_executive_summary(self, week_forecast: Dict, daily_strategies: List[Dict]) -> Dict[str, Any]:
        """Create executive summary of the week"""
        
        # Extract key metrics
        avg_volatility = week_forecast['volatility_analysis']['average']
        dominant_element = week_forecast['dominant_element']
        confidence = week_forecast['confidence_level']
        
        # Count high-risk days
        high_risk_days = sum(1 for day in daily_strategies 
                           if day['risk_management']['risk_level'] in ['High', 'Very High'])
        
        # Identify best day
        volatilities = [float(day['market_outlook']['volatility_expectation'].replace('x normal', ''))
                       for day in daily_strategies 
                       if 'x normal' in day['market_outlook']['volatility_expectation']]
        
        if volatilities:
            best_day_index = np.argmin(volatilities)
            best_day = daily_strategies[best_day_index]['day_name']
        else:
            best_day = "To be determined"
        
        # Market sentiment
        if avg_volatility >= 1.3:
            sentiment = "Bearish/Cautious"
            recommendation = "Focus on capital preservation and defensive strategies"
        elif avg_volatility <= 0.8:
            sentiment = "Bullish/Optimistic"
            recommendation = "Good week for accumulation and growth strategies"
        else:
            sentiment = "Neutral/Mixed"
            recommendation = "Balanced approach with selective opportunities"
        
        return {
            'week_theme': f"{dominant_element} Element Dominance",
            'market_sentiment': sentiment,
            'volatility_level': week_forecast['volatility_analysis']['classification'],
            'confidence_level': confidence,
            'high_risk_days': high_risk_days,
            'best_trading_day': best_day,
            'overall_recommendation': recommendation,
            'key_insight': f"Week {week_forecast['week_number']} shows {dominant_element.lower()} characteristics with {avg_volatility}x normal volatility"
        }
    
    def _generate_sector_outlook(self, daily_strategies: List[Dict]) -> Dict[str, Any]:
        """Generate sector-wise outlook for the week"""
        
        sector_rankings = {}
        
        # Aggregate sector preferences across the week
        all_sectors = []
        for day in daily_strategies:
            primary_sectors = day['sector_strategy']['primary_sectors']
            all_sectors.extend(primary_sectors)
        
        # Count sector mentions
        sector_counts = pd.Series(all_sectors).value_counts()
        
        # Map to NSE sector indices and create rankings
        sector_outlook = {}
        for sector, count in sector_counts.head(8).items():
            # Map sector to NSE equivalent
            nse_sector = self._map_to_nse_sector(sector)
            
            if count >= 4:  # Mentioned in most days
                outlook = "Very Bullish"
                action = "Accumulate on dips"
            elif count >= 3:
                outlook = "Bullish"
                action = "Buy on weakness"
            elif count >= 2:
                outlook = "Neutral to Positive"
                action = "Selective buying"
            else:
                outlook = "Neutral"
                action = "Hold current positions"
            
            sector_outlook[nse_sector or sector] = {
                'outlook': outlook,
                'frequency': count,
                'action': action,
                'stocks': self.nse_sectors.get(nse_sector, [sector])[:5]
            }
        
        return {
            'top_sectors': list(sector_outlook.keys())[:5],
            'detailed_outlook': sector_outlook,
            'rotation_strategy': self._get_rotation_strategy(daily_strategies)
        }
    
    def _map_to_nse_sector(self, sector: str) -> Optional[str]:
        """Map generic sector to NSE sector index"""
        mapping = {
            'BANKING': 'NIFTY_BANK',
            'IT': 'NIFTY_IT',
            'HEALTHCARE': 'NIFTY_PHARMA',
            'FMCG': 'NIFTY_FMCG',
            'AUTO': 'NIFTY_AUTO',
            'ENERGY': 'NIFTY_ENERGY',
            'STEEL': 'NIFTY_METAL',
            'REALESTATE': 'NIFTY_REALTY'
        }
        return mapping.get(sector.upper())
    
    def _get_rotation_strategy(self, daily_strategies: List[Dict]) -> str:
        """Get sector rotation strategy for the week"""
        
        elements = [day['moon_position']['element'] for day in daily_strategies]
        element_counts = pd.Series(elements).value_counts()
        
        if len(element_counts) >= 3:
            return "Active rotation - Multiple elements suggest frequent sector shifts"
        elif element_counts.iloc[0] >= 4:
            dominant = element_counts.index[0]
            return f"Stable focus - {dominant} element dominance suggests sector concentration"
        else:
            return "Moderate rotation - Some sector switching expected"
    
    def _create_stock_watchlist(self, daily_strategies: List[Dict]) -> Dict[str, List[str]]:
        """Create categorized stock watchlist for the week"""
        
        all_top_picks = []
        all_accumulation = []
        all_momentum = []
        
        for day in daily_strategies:
            recommendations = day['stock_recommendations']
            all_top_picks.extend(recommendations.get('top_picks', []))
            all_accumulation.extend(recommendations.get('accumulation_candidates', []))
            all_momentum.extend(recommendations.get('momentum_plays', []))
        
        # Count mentions and create final lists
        top_picks_counts = pd.Series(all_top_picks).value_counts()
        accumulation_counts = pd.Series(all_accumulation).value_counts()
        momentum_counts = pd.Series(all_momentum).value_counts()
        
        return {
            'high_conviction': top_picks_counts.head(8).index.tolist(),
            'accumulation_targets': accumulation_counts.head(10).index.tolist(),
            'momentum_candidates': momentum_counts.head(8).index.tolist(),
            'mention_frequency': {
                'top_picks': top_picks_counts.head(5).to_dict(),
                'accumulation': accumulation_counts.head(5).to_dict(),
                'momentum': momentum_counts.head(5).to_dict()
            }
        }
    
    def _create_risk_calendar(self, daily_strategies: List[Dict]) -> Dict[str, Any]:
        """Create risk calendar for the week"""
        
        risk_calendar = []
        
        for day in daily_strategies:
            date = day['date']
            day_name = day['day_name']
            risk_level = day['risk_management']['risk_level']
            volatility = day['market_outlook']['volatility_expectation']
            moon_sign = day['moon_position']['sign']
            
            # Risk score (1-5, where 5 is highest risk)
            risk_scores = {'Very Low': 1, 'Low': 2, 'Medium': 3, 'High': 4, 'Very High': 5}
            risk_score = risk_scores.get(risk_level, 3)
            
            risk_calendar.append({
                'date': date,
                'day': day_name,
                'risk_level': risk_level,
                'risk_score': risk_score,
                'volatility': volatility,
                'moon_sign': moon_sign,
                'alerts': day['alerts_and_warnings'][:2]  # Top 2 alerts
            })
        
        # Identify highest and lowest risk days
        risk_scores = [day['risk_score'] for day in risk_calendar]
        highest_risk_day = risk_calendar[np.argmax(risk_scores)]['day']
        lowest_risk_day = risk_calendar[np.argmin(risk_scores)]['day']
        
        return {
            'daily_risk': risk_calendar,
            'highest_risk_day': highest_risk_day,
            'lowest_risk_day': lowest_risk_day,
            'average_risk_score': round(np.mean(risk_scores), 1),
            'risk_distribution': pd.Series([day['risk_level'] for day in risk_calendar]).value_counts().to_dict()
        }
    
    def _create_weekly_trading_plan(self, week_forecast: Dict, daily_strategies: List[Dict]) -> Dict[str, Any]:
        """Create comprehensive weekly trading plan"""
        
        # Aggregate position sizing recommendations
        position_sizes = []
        for day in daily_strategies:
            size_text = day['risk_management']['max_position_size']
            if '%' in size_text:
                size_pct = float(size_text.split('%')[0])
                position_sizes.append(size_pct)
        
        avg_position_size = np.mean(position_sizes) if position_sizes else 5.0
        
        # Trading approach based on week characteristics
        volatility = week_forecast['volatility_analysis']['average']
        confidence = week_forecast['confidence_level']
        
        if volatility >= 1.3:
            approach = "Defensive"
            cash_allocation = "40-60%"
            max_positions = "3-5 stocks maximum"
        elif volatility <= 0.8:
            approach = "Aggressive"
            cash_allocation = "10-20%"
            max_positions = "8-12 stocks"
        else:
            approach = "Balanced"
            cash_allocation = "20-30%"
            max_positions = "5-8 stocks"
        
        return {
            'weekly_approach': approach,
            'recommended_cash_allocation': cash_allocation,
            'max_concurrent_positions': max_positions,
            'average_position_size': f"{avg_position_size:.1f}%",
            'preferred_strategies': week_forecast['trading_strategy']['primary_strategy'],
            'entry_criteria': self._get_weekly_entry_criteria(daily_strategies),
            'exit_criteria': self._get_weekly_exit_criteria(daily_strategies),
            'risk_management_rules': self._get_weekly_risk_rules(week_forecast, daily_strategies)
        }
    
    def _get_weekly_entry_criteria(self, daily_strategies: List[Dict]) -> List[str]:
        """Get entry criteria for the week"""
        criteria = []
        
        # Analyze common entry methods
        entry_methods = [day['trading_tactics']['entry_method'] for day in daily_strategies]
        
        if any('breakout' in method.lower() for method in entry_methods):
            criteria.append("Wait for volume-confirmed breakouts")
        if any('dip' in method.lower() for method in entry_methods):
            criteria.append("Buy on support level dips")
        if any('pattern' in method.lower() for method in entry_methods):
            criteria.append("Follow technical chart patterns")
        
        # Add volatility-based criteria
        high_vol_days = sum(1 for day in daily_strategies 
                           if 'High' in day['risk_management']['risk_level'])
        
        if high_vol_days >= 3:
            criteria.append("Wait for volatility to settle before entry")
        else:
            criteria.append("Normal entry timing acceptable")
        
        return criteria[:4]  # Limit to top 4 criteria
    
    def _get_weekly_exit_criteria(self, daily_strategies: List[Dict]) -> List[str]:
        """Get exit criteria for the week"""
        criteria = []
        
        # Analyze exit strategies
        exit_strategies = [day['trading_tactics']['exit_strategy'] for day in daily_strategies]
        
        if any('quick' in strategy.lower() for strategy in exit_strategies):
            criteria.append("Take quick profits, don't be greedy")
        if any('trail' in strategy.lower() for strategy in exit_strategies):
            criteria.append("Use trailing stops aggressively")
        if any('target' in strategy.lower() for strategy in exit_strategies):
            criteria.append("Stick to predetermined profit targets")
        
        # Add holding period guidance
        holding_periods = [day['trading_tactics']['ideal_holding_period'] for day in daily_strategies]
        if any('intraday' in period.lower() for period in holding_periods):
            criteria.append("Prefer intraday to short-term holds")
        elif any('week' in period.lower() for period in holding_periods):
            criteria.append("Suitable for swing trading holds")
        
        return criteria[:4]
    
    def _get_weekly_risk_rules(self, week_forecast: Dict, daily_strategies: List[Dict]) -> List[str]:
        """Get risk management rules for the week"""
        rules = []
        
        volatility = week_forecast['volatility_analysis']['average']
        high_risk_days = week_forecast['risk_assessment']['high_risk_days']
        
        # Position sizing rule
        if volatility >= 1.3:
            rules.append("Maximum 2% position size per stock")
        elif volatility <= 0.8:
            rules.append("Can increase to 8-10% position size per stock")
        else:
            rules.append("Standard 5% position size per stock")
        
        # Stop loss rules
        if high_risk_days >= 3:
            rules.append("Use very tight stops (2-3%)")
        else:
            rules.append("Standard stop losses (4-5%)")
        
        # Exposure rules
        if volatility >= 1.2:
            rules.append("Maximum 50% portfolio exposure")
            rules.append("Avoid overnight positions on high volatility days")
        else:
            rules.append("Can maintain 70-80% exposure")
        
        return rules[:5]
    
    def _identify_key_dates(self, daily_strategies: List[Dict]) -> Dict[str, Any]:
        """Identify key dates and events for the week"""
        
        key_dates = []
        
        for day in daily_strategies:
            date = day['date']
            day_name = day['day_name']
            moon_sign = day['moon_position']['sign']
            alerts = day['alerts_and_warnings']
            
            # Identify significant days
            if 'Scorpio' in moon_sign:
                key_dates.append({
                    'date': date,
                    'day': day_name,
                    'significance': 'Scorpio Moon - Highest volatility expected',
                    'action': 'Extreme caution required'
                })
            elif any('EXTREME' in alert for alert in alerts):
                key_dates.append({
                    'date': date,
                    'day': day_name,
                    'significance': 'Extreme volatility warning',
                    'action': 'Consider staying in cash'
                })
            elif day['risk_management']['risk_level'] == 'Very Low':
                key_dates.append({
                    'date': date,
                    'day': day_name,
                    'significance': 'Low risk accumulation opportunity',
                    'action': 'Good day for buying'
                })
        
        return {
            'significant_dates': key_dates,
            'total_key_dates': len(key_dates),
            'recommendation': 'Plan trades around these key dates'
        }
    
    def _recommend_portfolio_allocation(self, week_forecast: Dict) -> Dict[str, Any]:
        """Recommend portfolio allocation for the week"""
        
        volatility = week_forecast['volatility_analysis']['average']
        risk_percentage = week_forecast['risk_assessment']['risk_percentage']
        dominant_element = week_forecast['dominant_element']
        
        # Base allocation
        if volatility >= 1.3 or risk_percentage >= 60:
            allocation = {
                'Cash': '50-70%',
                'Large Cap': '20-30%',
                'Mid Cap': '5-10%',
                'Small Cap': '0-5%',
                'Derivatives': '0%'
            }
        elif volatility <= 0.8 and risk_percentage <= 20:
            allocation = {
                'Cash': '10-20%',
                'Large Cap': '40-50%',
                'Mid Cap': '20-30%',
                'Small Cap': '10-15%',
                'Derivatives': '5-10%'
            }
        else:
            allocation = {
                'Cash': '20-30%',
                'Large Cap': '35-45%',
                'Mid Cap': '15-25%',
                'Small Cap': '5-10%',
                'Derivatives': '0-5%'
            }
        
        # Element-based sector allocation
        if dominant_element == 'Fire':
            sector_focus = {'Energy': '25%', 'Auto': '20%', 'Steel': '15%', 'Others': '40%'}
        elif dominant_element == 'Earth':
            sector_focus = {'Banking': '30%', 'FMCG': '20%', 'Infrastructure': '15%', 'Others': '35%'}
        elif dominant_element == 'Air':
            sector_focus = {'IT': '30%', 'Telecom': '15%', 'Media': '10%', 'Others': '45%'}
        else:  # Water
            sector_focus = {'Healthcare': '25%', 'Chemicals': '20%', 'Hospitality': '10%', 'Others': '45%'}
        
        return {
            'asset_allocation': allocation,
            'sector_allocation': sector_focus,
            'risk_budget': f"{100 - risk_percentage:.0f}% of portfolio",
            'rebalancing_frequency': 'Daily monitoring, weekly rebalancing',
            'special_considerations': self._get_allocation_considerations(week_forecast)
        }
    
    def _get_allocation_considerations(self, week_forecast: Dict) -> List[str]:
        """Get special considerations for allocation"""
        considerations = []
        
        if week_forecast['confidence_level'] in ['Low', 'Very Low']:
            considerations.append("Low confidence week - maintain higher cash levels")
        
        if week_forecast['volatility_analysis']['average'] >= 1.2:
            considerations.append("High volatility expected - focus on liquid assets")
        
        if len(week_forecast['key_alerts']) >= 3:
            considerations.append("Multiple alerts - exercise extra caution")
        
        considerations.append(f"Element focus: {week_forecast['dominant_element']} - adjust sector weights accordingly")
        
        return considerations


def create_weekly_outlook_report():
    """Create comprehensive weekly outlook report"""
    print("=== GENERATING WEEKLY MARKET OUTLOOK REPORT ===")
    
    generator = WeeklyOutlookGenerator()
    
    # Generate next week's outlook
    next_monday = datetime.date.today() + datetime.timedelta(days=(7 - datetime.date.today().weekday()))
    outlook = generator.generate_weekly_outlook(next_monday)
    
    if "error" in outlook:
        print(f"Error generating outlook: {outlook['error']}")
        return
    
    # Create reports directory
    reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    # Save detailed outlook as JSON
    outlook_file = os.path.join(reports_dir, f"weekly_outlook_W{outlook['week_number']}_{datetime.date.today().strftime('%Y%m%d')}.json")
    with open(outlook_file, 'w') as f:
        json.dump(outlook, f, indent=2, default=str)
    
    # Create human-readable report
    report_file = os.path.join(reports_dir, f"Weekly_Market_Outlook_W{outlook['week_number']}.txt")
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("═" * 80 + "\n")
        f.write("               WEEKLY MARKET OUTLOOK REPORT\n")
        f.write("                   Vedic Astrology Analysis\n")
        f.write("═" * 80 + "\n\n")
        
        f.write(f"Report Generated: {outlook['report_date']}\n")
        f.write(f"Target Week: {outlook['target_week']} (Week {outlook['week_number']})\n\n")
        
        # Executive Summary
        summary = outlook['executive_summary']
        f.write("🎯 EXECUTIVE SUMMARY\n")
        f.write("-" * 40 + "\n")
        f.write(f"Week Theme: {summary['week_theme']}\n")
        f.write(f"Market Sentiment: {summary['market_sentiment']}\n")
        f.write(f"Volatility Level: {summary['volatility_level']}\n")
        f.write(f"Confidence Level: {summary['confidence_level']}\n")
        f.write(f"High Risk Days: {summary['high_risk_days']}/5\n")
        f.write(f"Best Trading Day: {summary['best_trading_day']}\n")
        f.write(f"Recommendation: {summary['overall_recommendation']}\n")
        f.write(f"Key Insight: {summary['key_insight']}\n\n")
        
        # Sector Outlook
        sector_outlook = outlook['sector_outlook']
        f.write("📊 SECTOR OUTLOOK\n")
        f.write("-" * 40 + "\n")
        f.write(f"Top Sectors: {', '.join(sector_outlook['top_sectors'])}\n")
        f.write(f"Rotation Strategy: {sector_outlook['rotation_strategy']}\n\n")
        
        for sector, details in list(sector_outlook['detailed_outlook'].items())[:5]:
            f.write(f"{sector}: {details['outlook']} - {details['action']}\n")
        f.write("\n")
        
        # Stock Watchlist
        watchlist = outlook['stock_watchlist']
        f.write("📋 STOCK WATCHLIST\n")
        f.write("-" * 40 + "\n")
        f.write(f"High Conviction: {', '.join(watchlist['high_conviction'][:8])}\n")
        f.write(f"Accumulation: {', '.join(watchlist['accumulation_targets'][:8])}\n")
        f.write(f"Momentum: {', '.join(watchlist['momentum_candidates'][:6])}\n\n")
        
        # Risk Calendar
        risk_cal = outlook['risk_calendar']
        f.write("⚠️ RISK CALENDAR\n")
        f.write("-" * 40 + "\n")
        f.write(f"Highest Risk Day: {risk_cal['highest_risk_day']}\n")
        f.write(f"Lowest Risk Day: {risk_cal['lowest_risk_day']}\n")
        f.write(f"Average Risk Score: {risk_cal['average_risk_score']}/5\n\n")
        
        for day_risk in risk_cal['daily_risk']:
            f.write(f"{day_risk['day']} ({day_risk['date']}): {day_risk['risk_level']} Risk - {day_risk['moon_sign']} Moon\n")
        f.write("\n")
        
        # Trading Plan
        trading_plan = outlook['trading_plan']
        f.write("📈 WEEKLY TRADING PLAN\n")
        f.write("-" * 40 + "\n")
        f.write(f"Approach: {trading_plan['weekly_approach']}\n")
        f.write(f"Cash Allocation: {trading_plan['recommended_cash_allocation']}\n")
        f.write(f"Max Positions: {trading_plan['max_concurrent_positions']}\n")
        f.write(f"Position Size: {trading_plan['average_position_size']}\n")
        f.write(f"Strategy: {trading_plan['preferred_strategies']}\n\n")
        
        f.write("Entry Criteria:\n")
        for criteria in trading_plan['entry_criteria']:
            f.write(f"  • {criteria}\n")
        f.write("\nExit Criteria:\n")
        for criteria in trading_plan['exit_criteria']:
            f.write(f"  • {criteria}\n")
        f.write("\nRisk Rules:\n")
        for rule in trading_plan['risk_management_rules']:
            f.write(f"  • {rule}\n")
        f.write("\n")
        
        # Portfolio Allocation
        allocation = outlook['portfolio_allocation']
        f.write("💼 RECOMMENDED PORTFOLIO ALLOCATION\n")
        f.write("-" * 40 + "\n")
        f.write("Asset Allocation:\n")
        for asset, percent in allocation['asset_allocation'].items():
            f.write(f"  {asset}: {percent}\n")
        f.write("\nSector Allocation:\n")
        for sector, percent in allocation['sector_allocation'].items():
            f.write(f"  {sector}: {percent}\n")
        f.write(f"\nRisk Budget: {allocation['risk_budget']}\n")
        f.write(f"Rebalancing: {allocation['rebalancing_frequency']}\n\n")
        
        # Key Dates
        key_dates = outlook['key_dates']
        if key_dates['significant_dates']:
            f.write("📅 KEY DATES TO WATCH\n")
            f.write("-" * 40 + "\n")
            for date_info in key_dates['significant_dates']:
                f.write(f"{date_info['day']} ({date_info['date']}): {date_info['significance']}\n")
                f.write(f"  Action: {date_info['action']}\n\n")
        
        f.write("═" * 80 + "\n")
        f.write("Report generated by Vedic Astrology Market Analysis System\n")
        f.write("For educational purposes - Not investment advice\n")
        f.write("═" * 80 + "\n")
    
    print(f"📄 Weekly outlook reports generated:")
    print(f"  • Detailed JSON: {outlook_file}")
    print(f"  • Summary Report: {report_file}")
    
    # Display key highlights
    print(f"\n🎯 WEEK {outlook['week_number']} HIGHLIGHTS:")
    summary = outlook['executive_summary']
    print(f"Theme: {summary['week_theme']}")
    print(f"Sentiment: {summary['market_sentiment']}")
    print(f"Best Day: {summary['best_trading_day']}")
    print(f"Risk Days: {summary['high_risk_days']}/5")
    
    print(f"\n📊 Top Sectors: {', '.join(outlook['sector_outlook']['top_sectors'][:3])}")
    print(f"💎 High Conviction: {', '.join(outlook['stock_watchlist']['high_conviction'][:5])}")
    
    return {
        'outlook_file': outlook_file,
        'report_file': report_file,
        'outlook_data': outlook
    }


if __name__ == "__main__":
    create_weekly_outlook_report()