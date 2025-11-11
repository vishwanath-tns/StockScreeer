"""
Dashboard tab for Stock Screener GUI with organized subsections.

Provides:
1. Database Status - Database tables monitoring 
2. RSI Divergences - RSI divergence analysis
3. Trend Ratings Status - Trend rating distribution and analysis
4. SMA Trends Status - Moving average trend analysis
"""

import tkinter as tk
from tkinter import ttk
import os
from datetime import datetime, date
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DashboardTab:
    """Enhanced Dashboard tab with organized subsections."""
    
    def __init__(self, parent):
        """Initialize the dashboard tab."""
        self.parent = parent
        self.main_frame = ttk.Frame(parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Initialize components
        self.create_dashboard()
        
        # Auto-refresh every 30 seconds
        self.auto_refresh()
    
    def create_dashboard(self):
        """Create the dashboard UI with subsections."""
        # Title
        title_frame = ttk.Frame(self.main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(title_frame, text="📊 Database Dashboard", 
                 font=('Arial', 18, 'bold')).pack(side=tk.LEFT)
        
        # Refresh button
        ttk.Button(title_frame, text="🔄 Refresh All", 
                  command=self.refresh_dashboard).pack(side=tk.RIGHT)
        
        # Last updated label
        self.last_updated_label = ttk.Label(title_frame, text="", foreground="gray")
        self.last_updated_label.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Create notebook for subsections
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create all subsections
        self.create_database_status_section()
        self.create_rsi_divergences_section()
        self.create_trend_ratings_section()  
        self.create_sma_trends_section()
        
        # Initial refresh
        self.refresh_dashboard()
    
    def create_database_status_section(self):
        """Create Database Status subsection - monitors database tables."""
        db_frame = ttk.Frame(self.notebook)
        self.notebook.add(db_frame, text="🗄️ Database Status")
        
        # Status cards for database tables
        cards_frame = ttk.Frame(db_frame)
        cards_frame.pack(fill=tk.X, pady=10, padx=10)
        
        # Configure grid columns
        for i in range(4):
            cards_frame.grid_columnconfigure(i, weight=1)
        
        # Create status cards
        self.bhav_card = self.create_status_card(cards_frame, "📈 BHAV Data", "Loading...", "gray", 0, 0)
        self.sma_card = self.create_status_card(cards_frame, "📊 SMAs", "Loading...", "gray", 0, 1)
        self.rsi_card = self.create_status_card(cards_frame, "📉 RSI", "Loading...", "gray", 0, 2)
        self.trend_card = self.create_status_card(cards_frame, "🎯 Trends", "Loading...", "gray", 0, 3)
        
        # Database details section
        details_frame = ttk.LabelFrame(db_frame, text="📋 Database Details", padding=10)
        details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_frame = ttk.Frame(details_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.db_details_text = tk.Text(text_frame, height=12, wrap=tk.WORD, font=('Consolas', 10))
        self.db_details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.db_details_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.db_details_text.configure(yscrollcommand=scrollbar.set)
    
    def create_rsi_divergences_section(self):
        """Create RSI Divergences subsection."""
        rsi_frame = ttk.Frame(self.notebook)
        self.notebook.add(rsi_frame, text="📈 RSI Divergences")
        
        # Header
        header_frame = ttk.Frame(rsi_frame)
        header_frame.pack(fill=tk.X, pady=10, padx=10)
        
        ttk.Label(header_frame, text="📈 RSI Divergence Analysis", 
                 font=('Arial', 14, 'bold')).pack(side=tk.LEFT)
        
        ttk.Button(header_frame, text="🔄 Refresh RSI", 
                  command=self.refresh_rsi_divergences).pack(side=tk.RIGHT)
        
        # Content area
        content_frame = ttk.LabelFrame(rsi_frame, text="RSI Divergence Status", padding=10)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_frame = ttk.Frame(content_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.rsi_content_text = tk.Text(text_frame, wrap=tk.WORD, font=('Consolas', 10))
        self.rsi_content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        rsi_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.rsi_content_text.yview)
        rsi_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.rsi_content_text.configure(yscrollcommand=rsi_scrollbar.set)
    
    def create_trend_ratings_section(self):
        """Create Trend Ratings Status subsection.""" 
        trend_frame = ttk.Frame(self.notebook)
        self.notebook.add(trend_frame, text="🎯 Trend Ratings")
        
        # Header
        header_frame = ttk.Frame(trend_frame)
        header_frame.pack(fill=tk.X, pady=10, padx=10)
        
        ttk.Label(header_frame, text="🎯 Trend Ratings Analysis", 
                 font=('Arial', 14, 'bold')).pack(side=tk.LEFT)
        
        ttk.Button(header_frame, text="🔄 Refresh Trends", 
                  command=self.refresh_trend_ratings).pack(side=tk.RIGHT)
        
        # Content area
        content_frame = ttk.LabelFrame(trend_frame, text="Trend Ratings Distribution", padding=10)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_frame = ttk.Frame(content_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.trend_content_text = tk.Text(text_frame, wrap=tk.WORD, font=('Consolas', 10))
        self.trend_content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        trend_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.trend_content_text.yview)
        trend_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.trend_content_text.configure(yscrollcommand=trend_scrollbar.set)
    
    def create_sma_trends_section(self):
        """Create SMA Trends Status subsection."""
        sma_frame = ttk.Frame(self.notebook)
        self.notebook.add(sma_frame, text="📊 SMA Trends")
        
        # Header
        header_frame = ttk.Frame(sma_frame)
        header_frame.pack(fill=tk.X, pady=10, padx=10)
        
        ttk.Label(header_frame, text="📊 SMA Trends Analysis", 
                 font=('Arial', 14, 'bold')).pack(side=tk.LEFT)
        
        ttk.Button(header_frame, text="🔄 Refresh SMA", 
                  command=self.refresh_sma_trends).pack(side=tk.RIGHT)
        
        # Content area
        content_frame = ttk.LabelFrame(sma_frame, text="SMA Trend Analysis", padding=10)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_frame = ttk.Frame(content_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.sma_content_text = tk.Text(text_frame, wrap=tk.WORD, font=('Consolas', 10))
        self.sma_content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        sma_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.sma_content_text.yview)
        sma_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.sma_content_text.configure(yscrollcommand=sma_scrollbar.set)
    
    def create_status_card(self, parent, title, status, color, row, col):
        """Create a status card widget."""
        card_frame = ttk.LabelFrame(parent, text="", padding=15)
        card_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        
        title_label = ttk.Label(card_frame, text=title, font=('Arial', 12, 'bold'))
        title_label.pack()
        
        status_label = ttk.Label(card_frame, text=status, foreground=color, font=('Arial', 10))
        status_label.pack(pady=(5, 0))
        
        details_label = ttk.Label(card_frame, text="", foreground="darkblue", font=('Arial', 9))
        details_label.pack(pady=(5, 0))
        
        return {'frame': card_frame, 'title': title_label, 'status': status_label, 'details': details_label}
    
    def auto_refresh(self):
        """Auto-refresh dashboard every 30 seconds."""
        self.refresh_dashboard()
        self.parent.after(30000, self.auto_refresh)
    
    def refresh_dashboard(self):
        """Refresh all dashboard data."""
        self.last_updated_label.config(text=f"🕐 Last updated: {datetime.now().strftime('%H:%M:%S')}")
        
        try:
            engine = self.get_database_engine()
            if not engine:
                self.show_error("❌ Database connection failed")
                return
            
            # Check database status
            bhav_status = self.check_bhav_data(engine)
            sma_status = self.check_sma_data(engine)
            rsi_status = self.check_rsi_data(engine)
            trend_status = self.check_trend_data(engine)
            
            # Update database status cards
            self.update_status_card(self.bhav_card, bhav_status)
            self.update_status_card(self.sma_card, sma_status)
            self.update_status_card(self.rsi_card, rsi_status)
            self.update_status_card(self.trend_card, trend_status)
            
            # Update database details
            self.update_database_details(bhav_status, sma_status, rsi_status, trend_status)
            
            # Refresh other sections
            self.refresh_rsi_divergences()
            self.refresh_trend_ratings()
            self.refresh_sma_trends()
            
        except Exception as e:
            self.show_error(f"❌ Error: {str(e)}")
    
    def refresh_rsi_divergences(self):
        """Refresh RSI divergences section - placeholder for now."""
        try:
            self.rsi_content_text.delete(1.0, tk.END)
            content = """🔄 Refreshing RSI Divergences data...

📈 RSI DIVERGENCE ANALYSIS
========================

This section will contain:
• Recent RSI divergence signals (bullish/bearish)
• Signal strength and reliability analysis
• Symbol-wise divergence counts and patterns
• Historical divergence success rates
• Alert notifications for new divergences

🚧 DEVELOPMENT STATUS
===================
▪ Data collection methods: Coming soon
▪ Divergence detection algorithms: Coming soon  
▪ Signal strength analysis: Coming soon
▪ Real-time monitoring: Coming soon

📊 PLANNED FEATURES
=================
1. Bullish divergences (RSI up, Price down)
2. Bearish divergences (RSI down, Price up)  
3. Hidden divergences for trend continuation
4. Multi-timeframe divergence analysis
5. Integration with price action patterns

🔍 Current Status: Infrastructure ready, implementation next..."""

            self.rsi_content_text.insert(tk.END, content)
        except Exception as e:
            self.rsi_content_text.insert(tk.END, f"❌ Error refreshing RSI data: {e}")
    
    def refresh_trend_ratings(self):
        """Refresh trend ratings section - placeholder for now."""
        try:
            self.trend_content_text.delete(1.0, tk.END)
            content = """🔄 Refreshing Trend Ratings data...

🎯 TREND RATINGS ANALYSIS
=======================

This section will contain:
• Trend rating distribution (-3 to +3 scale)
• Daily, weekly, monthly trend breakdowns
• Strong uptrend/downtrend symbol counts
• Trend momentum and strength analysis
• Trend direction changes and alerts

🚧 DEVELOPMENT STATUS
===================
▪ Trend calculation engine: Already implemented
▪ Rating distribution analysis: Coming soon
▪ Visual charts and graphs: Coming soon
▪ Trend change notifications: Coming soon

📊 RATING SCALE
==============
+3: Very Strong Uptrend
+2: Strong Uptrend  
+1: Weak Uptrend
 0: Sideways/Neutral
-1: Weak Downtrend
-2: Strong Downtrend
-3: Very Strong Downtrend

🔍 PLANNED FEATURES
=================
1. Real-time trend rating distribution
2. Sector-wise trend analysis
3. Market breadth based on trend ratings
4. Historical trend persistence analysis
5. Automated trend alerts and notifications

🔍 Current Status: Trend analysis table active, visualization next..."""

            self.trend_content_text.insert(tk.END, content)
        except Exception as e:
            self.trend_content_text.insert(tk.END, f"❌ Error refreshing trend data: {e}")
    
    def refresh_sma_trends(self):
        """Refresh SMA trends section - placeholder for now."""
        try:
            self.sma_content_text.delete(1.0, tk.END)
            content = """🔄 Refreshing SMA Trends data...

📊 SMA TRENDS ANALYSIS
====================

This section will contain:
• SMA crossover patterns and signals
• Golden cross / Death cross detection
• Price vs SMA positioning analysis
• Moving average trend strength indicators
• Multi-timeframe SMA analysis

🚧 DEVELOPMENT STATUS
===================
▪ SMA calculation engine: Active (moving_averages table)
▪ Crossover detection: Coming soon
▪ Trend strength analysis: Coming soon
▪ Signal generation: Coming soon

📈 SMA INDICATORS
===============
• 5, 10, 20, 50, 100, 200 day moving averages
• Price above/below SMA analysis
• SMA slope and momentum calculation
• Volume-weighted moving averages

🔍 CROSSOVER SIGNALS
==================
Golden Cross: 50 SMA crosses above 200 SMA (Bullish)
Death Cross: 50 SMA crosses below 200 SMA (Bearish)
Short-term: 5 SMA vs 20 SMA crossovers
Medium-term: 20 SMA vs 50 SMA crossovers

📊 PLANNED FEATURES
=================
1. Real-time crossover signal detection
2. SMA trend strength scoring system
3. Price momentum vs SMA analysis
4. Multi-symbol SMA screening
5. Historical crossover success analysis
6. Automated SMA alerts

🔍 Current Status: Data infrastructure ready, analysis algorithms next..."""

            self.sma_content_text.insert(tk.END, content)
        except Exception as e:
            self.sma_content_text.insert(tk.END, f"❌ Error refreshing SMA data: {e}")
    
    def get_database_engine(self):
        """Get database engine for queries."""
        try:
            import reporting_adv_decl as rad
            return rad.engine()
        except Exception:
            try:
                from services.market_breadth_service import get_engine
                return get_engine()
            except Exception:
                return None
    
    def check_bhav_data(self, engine) -> Dict[str, Any]:
        """Check BHAV data availability."""
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                query = text("""
                    SELECT MIN(trade_date) as earliest_date, MAX(trade_date) as latest_date,
                           COUNT(DISTINCT trade_date) as trading_days, COUNT(*) as total_records
                    FROM nse_equity_bhavcopy_full WHERE trade_date IS NOT NULL
                """)
                result = conn.execute(query).fetchone()
                
                if result and result.latest_date:
                    days_behind = (date.today() - result.latest_date).days
                    status = "✅ Up to Date" if days_behind <= 3 else "⚠️ Behind" if days_behind <= 7 else "❌ Outdated"
                    color = "green" if days_behind <= 3 else "orange" if days_behind <= 7 else "red"
                    
                    return {
                        'status': status, 'color': color,
                        'details': f"{result.trading_days:,} trading days\\n{result.total_records:,} records",
                        'earliest_date': result.earliest_date, 'latest_date': result.latest_date,
                        'trading_days': result.trading_days, 'total_records': result.total_records,
                        'days_behind': days_behind
                    }
                else:
                    return {'status': "❌ No Data", 'color': "red", 'details': "No BHAV data found", 'error': "No data"}
        except Exception as e:
            return {'status': "❌ Error", 'color': "red", 'details': "Check failed", 'error': str(e)}
    
    def check_sma_data(self, engine) -> Dict[str, Any]:
        """Check SMA data availability."""
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                # Check table exists
                check = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = 'moving_averages'")).fetchone()
                if not check or check[0] == 0:
                    return {'status': "❌ No Table", 'color': "red", 'details': "SMAs table missing", 'error': "Table not found"}
                
                # Get statistics
                query = text("SELECT MAX(trade_date) as latest_date, COUNT(DISTINCT trade_date) as trading_days, COUNT(DISTINCT symbol) as symbols_count, COUNT(*) as total_records FROM moving_averages WHERE trade_date IS NOT NULL")
                result = conn.execute(query).fetchone()
                
                if result and result.latest_date:
                    days_behind = (date.today() - result.latest_date).days
                    status = "✅ Up to Date" if days_behind <= 3 else "⚠️ Behind" if days_behind <= 7 else "❌ Outdated"
                    color = "green" if days_behind <= 3 else "orange" if days_behind <= 7 else "red"
                    
                    return {
                        'status': status, 'color': color,
                        'details': f"{result.symbols_count:,} symbols\\n{result.trading_days:,} trading days",
                        'latest_date': result.latest_date, 'trading_days': result.trading_days,
                        'symbols_count': result.symbols_count, 'total_records': result.total_records,
                        'days_behind': days_behind
                    }
                else:
                    return {'status': "❌ No Data", 'color': "red", 'details': "No SMAs calculated", 'error': "No data"}
        except Exception as e:
            return {'status': "❌ Error", 'color': "red", 'details': "Check failed", 'error': str(e)}
    
    def check_rsi_data(self, engine) -> Dict[str, Any]:
        """Check RSI data availability."""
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                # Check table exists
                check = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = 'nse_rsi_daily'")).fetchone()
                if not check or check[0] == 0:
                    return {'status': "❌ No Table", 'color': "red", 'details': "RSI table missing", 'error': "Table not found"}
                
                # Get statistics
                query = text("SELECT MAX(trade_date) as latest_date, COUNT(DISTINCT trade_date) as trading_days, COUNT(DISTINCT symbol) as symbols_count, COUNT(*) as total_records FROM nse_rsi_daily WHERE trade_date IS NOT NULL")
                result = conn.execute(query).fetchone()
                
                if result and result.latest_date:
                    days_behind = (date.today() - result.latest_date).days
                    status = "✅ Up to Date" if days_behind <= 3 else "⚠️ Behind" if days_behind <= 7 else "❌ Outdated"
                    color = "green" if days_behind <= 3 else "orange" if days_behind <= 7 else "red"
                    
                    return {
                        'status': status, 'color': color,
                        'details': f"{result.symbols_count:,} symbols\\n{result.trading_days:,} trading days",
                        'latest_date': result.latest_date, 'trading_days': result.trading_days,
                        'symbols_count': result.symbols_count, 'total_records': result.total_records,
                        'days_behind': days_behind
                    }
                else:
                    return {'status': "❌ No Data", 'color': "red", 'details': "No RSI data", 'error': "No data"}
        except Exception as e:
            return {'status': "❌ Error", 'color': "red", 'details': "Check failed", 'error': str(e)}
    
    def check_trend_data(self, engine) -> Dict[str, Any]:
        """Check trend analysis data availability."""
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                # Check table exists  
                check = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = 'trend_analysis'")).fetchone()
                if not check or check[0] == 0:
                    return {'status': "❌ No Table", 'color': "red", 'details': "Trends table missing", 'error': "Table not found"}
                
                # Get statistics
                query = text("SELECT MAX(trade_date) as latest_date, COUNT(DISTINCT trade_date) as trading_days, COUNT(DISTINCT symbol) as symbols_count, COUNT(*) as total_records FROM trend_analysis WHERE trade_date IS NOT NULL")
                result = conn.execute(query).fetchone()
                
                if result and result.latest_date:
                    days_behind = (date.today() - result.latest_date).days
                    status = "✅ Up to Date" if days_behind <= 3 else "⚠️ Behind" if days_behind <= 7 else "❌ Outdated"
                    color = "green" if days_behind <= 3 else "orange" if days_behind <= 7 else "red"
                    
                    return {
                        'status': status, 'color': color,
                        'details': f"{result.symbols_count:,} symbols\\n{result.trading_days:,} trading days",
                        'latest_date': result.latest_date, 'trading_days': result.trading_days,
                        'symbols_count': result.symbols_count, 'total_records': result.total_records,
                        'days_behind': days_behind
                    }
                else:
                    return {'status': "❌ No Data", 'color': "red", 'details': "No trend data", 'error': "No data"}
        except Exception as e:
            return {'status': "❌ Error", 'color': "red", 'details': "Check failed", 'error': str(e)}
    
    def update_status_card(self, card, status_info):
        """Update status card with new information."""
        card['status'].config(text=status_info['status'], foreground=status_info['color'])
        card['details'].config(text=status_info['details'])
    
    def update_database_details(self, bhav_status, sma_status, rsi_status, trend_status):
        """Update database details section."""
        self.db_details_text.delete(1.0, tk.END)
        
        content = f"""📊 DATABASE STATUS REPORT
{'=' * 50}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📈 BHAV DATA STATUS:
   Status: {bhav_status['status']}"""
        
        if 'error' not in bhav_status:
            content += f"""
   Date Range: {bhav_status['earliest_date']} to {bhav_status['latest_date']}
   Trading Days: {bhav_status['trading_days']:,}
   Total Records: {bhav_status['total_records']:,}
   Days Behind: {bhav_status['days_behind']}"""
        else:
            content += f"\\n   Error: {bhav_status['error']}"
            
        content += f"""

📊 SMAs STATUS:
   Status: {sma_status['status']}"""
        
        if 'error' not in sma_status:
            content += f"""
   Latest Date: {sma_status['latest_date']}
   Trading Days: {sma_status['trading_days']:,}
   Symbols: {sma_status['symbols_count']:,}
   Total Records: {sma_status['total_records']:,}
   Days Behind: {sma_status['days_behind']}"""
        else:
            content += f"\\n   Error: {sma_status['error']}"
            
        content += f"""

📉 RSI STATUS:
   Status: {rsi_status['status']}"""
        
        if 'error' not in rsi_status:
            content += f"""
   Latest Date: {rsi_status['latest_date']}
   Trading Days: {rsi_status['trading_days']:,}
   Symbols: {rsi_status['symbols_count']:,}
   Total Records: {rsi_status['total_records']:,}
   Days Behind: {rsi_status['days_behind']}"""
        else:
            content += f"\\n   Error: {rsi_status['error']}"
            
        content += f"""

🎯 TREND ANALYSIS STATUS:
   Status: {trend_status['status']}"""
        
        if 'error' not in trend_status:
            content += f"""
   Latest Date: {trend_status['latest_date']}
   Trading Days: {trend_status['trading_days']:,}
   Symbols: {trend_status['symbols_count']:,}
   Total Records: {trend_status['total_records']:,}
   Days Behind: {trend_status['days_behind']}"""
        else:
            content += f"\\n   Error: {trend_status['error']}"
            
        # Summary
        content += f"""

📋 DATA QUALITY SUMMARY:
{'=' * 30}"""

        all_good = True
        for name, status in [("BHAV", bhav_status), ("SMAs", sma_status), ("RSI", rsi_status), ("Trends", trend_status)]:
            if 'error' in status:
                content += f"\\n❌ {name}: ERROR - {status.get('error', 'Unknown error')}"
                all_good = False
            elif status.get('days_behind', 999) > 7:
                content += f"\\n⚠️  {name}: OUTDATED - {status['days_behind']} days behind"
                all_good = False
            else:
                content += f"\\n✅ {name}: OK - Current data available"
        
        if all_good:
            content += "\\n\\n🎉 All systems operational!"
        else:
            content += "\\n\\n⚠️  Some systems need attention."
            
        self.db_details_text.insert(tk.END, content)
    
    def show_error(self, message):
        """Show error message."""
        for card in [self.bhav_card, self.sma_card, self.rsi_card, self.trend_card]:
            card['status'].config(text="❌ Error", foreground="red")
            card['details'].config(text="Check failed")
        
        self.db_details_text.delete(1.0, tk.END)
        self.db_details_text.insert(tk.END, f"{message}\\n\\nPlease check database connection and try again.")


# Test function
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Enhanced Dashboard Test")
    root.geometry("1200x800")
    dashboard = DashboardTab(root)
    root.mainloop()