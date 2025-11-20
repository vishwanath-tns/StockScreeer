"""
Trading Dashboard - View All Vedic Astrology Reports

This creates an easy-to-view dashboard of all generated trading reports
"""

import os
import json
import datetime
from typing import Dict, List, Any


class TradingDashboard:
    """Dashboard to view all trading reports"""
    
    def __init__(self):
        self.reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
        
    def create_dashboard_summary(self):
        """Create a comprehensive dashboard summary"""
        
        print("=" * 80)
        print("               VEDIC ASTROLOGY TRADING DASHBOARD")
        print("                     " + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        print("=" * 80)
        
        # Check what reports are available
        available_reports = self._scan_available_reports()
        
        print(f"\n📁 AVAILABLE REPORTS ({len(available_reports)} files):")
        print("-" * 50)
        for report in available_reports:
            print(f"  • {report}")
        
        # Display today's key insights
        print(f"\n🎯 TODAY'S KEY INSIGHTS ({datetime.date.today().strftime('%A, %B %d, %Y')}):")
        print("-" * 50)
        
        self._display_daily_insights()
        
        # Display weekly outlook
        print(f"\n📅 WEEKLY OUTLOOK:")
        print("-" * 50)
        
        self._display_weekly_insights()
        
        # Display trading calendar
        print(f"\n📊 UPCOMING TRADING CALENDAR:")
        print("-" * 50)
        
        self._display_trading_calendar()
        
        # Display practical recommendations
        print(f"\n💡 PRACTICAL TRADING RECOMMENDATIONS:")
        print("-" * 50)
        
        self._display_practical_recommendations()
        
        print("\n" + "=" * 80)
        print("Reports Location: " + os.path.abspath(self.reports_dir))
        print("Update Frequency: Daily (Run tools to refresh)")
        print("=" * 80)
    
    def _scan_available_reports(self) -> List[str]:
        """Scan for available report files"""
        reports = []
        
        if not os.path.exists(self.reports_dir):
            return reports
        
        for file in os.listdir(self.reports_dir):
            if file.endswith(('.json', '.txt', '.csv', '.png')):
                reports.append(file)
        
        return sorted(reports)
    
    def _display_daily_insights(self):
        """Display today's key insights"""
        
        today_str = datetime.date.today().strftime('%Y%m%d')
        daily_strategy_file = os.path.join(self.reports_dir, f"daily_strategy_{today_str}.json")
        
        if os.path.exists(daily_strategy_file):
            try:
                with open(daily_strategy_file, 'r') as f:
                    daily_data = json.load(f)
                
                moon_pos = daily_data['moon_position']
                market_outlook = daily_data['market_outlook']
                risk_mgmt = daily_data['risk_management']
                stocks = daily_data['stock_recommendations']
                
                print(f"🌙 Moon Position: {moon_pos['sign']} ({moon_pos['element']} element)")
                print(f"📈 Market Outlook: {market_outlook['overall_outlook']}")
                print(f"⚠️ Risk Level: {risk_mgmt['risk_level']} - {risk_mgmt['max_position_size']}")
                print(f"🎯 Top Stocks: {', '.join(stocks.get('top_picks', [])[:5])}")
                print(f"💰 Strategy: {daily_data['trading_tactics']['primary_strategy']}")
                
                # Show alerts
                alerts = daily_data.get('alerts_and_warnings', [])
                if alerts:
                    print(f"🚨 Key Alerts:")
                    for alert in alerts[:3]:
                        print(f"    {alert}")
                
            except Exception as e:
                print(f"Could not load daily strategy: {e}")
        else:
            print("⚠️ No daily strategy available - Run trading_strategy.py to generate")
    
    def _display_weekly_insights(self):
        """Display weekly insights"""
        
        # Find the most recent weekly outlook
        weekly_files = [f for f in os.listdir(self.reports_dir) if f.startswith('weekly_outlook_') and f.endswith('.json')]
        
        if weekly_files:
            latest_weekly = sorted(weekly_files)[-1]
            weekly_file = os.path.join(self.reports_dir, latest_weekly)
            
            try:
                with open(weekly_file, 'r') as f:
                    weekly_data = json.load(f)
                
                summary = weekly_data['executive_summary']
                sector_outlook = weekly_data['sector_outlook']
                risk_cal = weekly_data['risk_calendar']
                
                print(f"📊 Week {weekly_data['week_number']}: {summary['week_theme']}")
                print(f"🎭 Sentiment: {summary['market_sentiment']}")
                print(f"📈 Volatility: {summary['volatility_level']}")
                print(f"🌟 Best Day: {summary['best_trading_day']}")
                print(f"⚠️ Risk Days: {summary['high_risk_days']}/5")
                print(f"🏭 Top Sectors: {', '.join(sector_outlook['top_sectors'][:3])}")
                print(f"💡 Recommendation: {summary['overall_recommendation']}")
                
            except Exception as e:
                print(f"Could not load weekly outlook: {e}")
        else:
            print("⚠️ No weekly outlook available - Run weekly_outlook.py to generate")
    
    def _display_trading_calendar(self):
        """Display upcoming trading calendar"""
        
        today_str = datetime.date.today().strftime('%Y%m%d')
        calendar_file = os.path.join(self.reports_dir, f"trading_calendar_{today_str}.csv")
        
        if os.path.exists(calendar_file):
            try:
                import pandas as pd
                df = pd.read_csv(calendar_file)
                
                # Show next 7 days
                next_7_days = df.head(7)
                
                print("📅 Next 7 Trading Days:")
                for _, row in next_7_days.iterrows():
                    date = pd.to_datetime(row['Date']).strftime('%m/%d')
                    day = row['Day'][:3]  # Short day name
                    moon_sign = row['Moon_Sign']
                    volatility = row['Volatility_Factor']
                    action = row['Action']
                    
                    # Color coding
                    if 'CAUTION' in action:
                        indicator = "🔴"
                    elif 'ACCUMULATE' in action:
                        indicator = "🟢"
                    elif 'CAREFUL' in action:
                        indicator = "🟡"
                    else:
                        indicator = "⚪"
                    
                    print(f"  {indicator} {date} {day}: {moon_sign} Moon ({volatility}x) - {action}")
                
            except Exception as e:
                print(f"Could not load trading calendar: {e}")
        else:
            print("⚠️ No trading calendar available - Run market_forecast.py to generate")
    
    def _display_practical_recommendations(self):
        """Display practical recommendations for traders"""
        
        today_str = datetime.date.today().strftime('%Y%m%d')
        summary_file = os.path.join(self.reports_dir, f"trading_summary_{today_str}.txt")
        
        print("📋 HOW TO USE THIS DATA FOR TRADING:")
        print()
        print("1. 🌙 DAILY MOON TRACKING:")
        print("   • Check Moon sign each morning before market open")
        print("   • Adjust position sizes based on volatility factor")
        print("   • Focus on favored sectors for the day")
        print()
        print("2. ⚠️ RISK MANAGEMENT:")
        print("   • Scorpio Moon: Reduce positions to 25% normal size")
        print("   • High volatility (1.2x+): Use tight 2-3% stop losses")
        print("   • Low volatility (0.8x-): Opportunity for accumulation")
        print()
        print("3. 🎯 SECTOR ROTATION:")
        print("   • Fire Signs: Energy, Auto, Steel, Defense stocks")
        print("   • Earth Signs: Banking, FMCG, Infrastructure")
        print("   • Air Signs: IT, Telecom, Media stocks")
        print("   • Water Signs: Healthcare, Chemicals, Hospitality")
        print()
        print("4. 📊 TIMING YOUR TRADES:")
        print("   • High volatility days: Wait for clear patterns")
        print("   • Low volatility days: Good for swing trades")
        print("   • Check weekly outlook for best/worst days")
        print()
        print("5. 💼 PORTFOLIO ALLOCATION:")
        print("   • High risk weeks: 50-70% cash allocation")
        print("   • Low risk weeks: Can increase exposure to 80%")
        print("   • Always maintain 20% cash for opportunities")
        
        if os.path.exists(summary_file):
            print(f"\n📄 Detailed summary available in: {summary_file}")
        
        print(f"\n🔄 UPDATE SCHEDULE:")
        print("   • Run daily_strategy.py every morning before 9:15 AM")
        print("   • Run weekly_outlook.py every Sunday evening")
        print("   • Run market_forecast.py for 4-week ahead planning")
        print("   • Monitor alerts throughout the trading day")


def create_quick_reference():
    """Create a quick reference guide"""
    
    reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    quick_ref_file = os.path.join(reports_dir, "Quick_Reference_Guide.txt")
    
    with open(quick_ref_file, 'w', encoding='utf-8') as f:
        f.write("VEDIC ASTROLOGY TRADING QUICK REFERENCE GUIDE\n")
        f.write("=" * 60 + "\n\n")
        
        f.write("MOON SIGN VOLATILITY REFERENCE:\n")
        f.write("-" * 40 + "\n")
        f.write("🔴 VERY HIGH RISK (1.4x+ volatility):\n")
        f.write("   • Scorpio Moon: 1.5x - Intense transformations\n")
        f.write("   • Action: Minimize exposure, 25% normal position size\n\n")
        
        f.write("🟡 HIGH RISK (1.2x+ volatility):\n")
        f.write("   • Aries Moon: 1.4x - Aggressive movements\n")
        f.write("   • Cancer Moon: 1.3x - Emotional extremes\n")
        f.write("   • Gemini Moon: 1.2x - Quick reversals\n")
        f.write("   • Action: Reduced positions (50-70% normal)\n\n")
        
        f.write("🟢 LOW RISK (0.8x- volatility):\n")
        f.write("   • Capricorn Moon: 0.6x - Disciplined climb\n")
        f.write("   • Taurus Moon: 0.7x - Steady accumulation\n")
        f.write("   • Libra Moon: 0.8x - Balanced trading\n")
        f.write("   • Action: Good for accumulation (120-150% normal)\n\n")
        
        f.write("SECTOR ROTATION BY ELEMENT:\n")
        f.write("-" * 40 + "\n")
        f.write("🔥 FIRE (Aries, Leo, Sagittarius):\n")
        f.write("   Primary: RELIANCE, TATAMOTORS, TATASTEEL, HAL\n")
        f.write("   Strategy: Momentum trading, quick profits\n\n")
        
        f.write("🌍 EARTH (Taurus, Virgo, Capricorn):\n")
        f.write("   Primary: HDFCBANK, ICICIBANK, ITC, ULTRACEMCO\n")
        f.write("   Strategy: Value accumulation, patient holding\n\n")
        
        f.write("💨 AIR (Gemini, Libra, Aquarius):\n")
        f.write("   Primary: TCS, INFY, BHARTIARTL, LT\n")
        f.write("   Strategy: Swing trading, tech focus\n\n")
        
        f.write("💧 WATER (Cancer, Scorpio, Pisces):\n")
        f.write("   Primary: DRREDDY, CIPLA, UPL, COALINDIA\n")
        f.write("   Strategy: Contrarian plays, emotional sectors\n\n")
        
        f.write("DAILY TRADING CHECKLIST:\n")
        f.write("-" * 40 + "\n")
        f.write("☐ Check today's Moon sign and element\n")
        f.write("☐ Review volatility factor for position sizing\n")
        f.write("☐ Identify favored sectors for the day\n")
        f.write("☐ Set appropriate stop losses based on risk level\n")
        f.write("☐ Check weekly outlook for context\n")
        f.write("☐ Monitor alerts throughout the day\n")
        f.write("☐ Adjust positions before market close if needed\n\n")
        
        f.write("POSITION SIZING RULES:\n")
        f.write("-" * 40 + "\n")
        f.write("Very High Risk: 1-2% per stock, 10% total exposure\n")
        f.write("High Risk: 2-3% per stock, 15% total exposure\n")
        f.write("Medium Risk: 3-5% per stock, 25% total exposure\n")
        f.write("Low Risk: 5-8% per stock, 40% total exposure\n")
        f.write("Very Low Risk: 8-10% per stock, 50% total exposure\n\n")
        
        f.write("STOP LOSS GUIDELINES:\n")
        f.write("-" * 40 + "\n")
        f.write("Extreme Volatility (1.4x+): 2-3% stops\n")
        f.write("High Volatility (1.2x+): 3-4% stops\n")
        f.write("Normal Volatility (0.8-1.2x): 4-5% stops\n")
        f.write("Low Volatility (0.8x-): 5-7% stops\n\n")
        
        f.write("Generated: " + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n")
    
    print(f"📖 Quick reference guide created: {quick_ref_file}")
    return quick_ref_file


if __name__ == "__main__":
    print("🚀 Initializing Trading Dashboard...")
    
    dashboard = TradingDashboard()
    dashboard.create_dashboard_summary()
    
    print("\n" + "=" * 80)
    create_quick_reference()
    print("=" * 80)