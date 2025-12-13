#!/usr/bin/env python3
"""
StockScreeer Central Launcher
============================
Single entry point for all project features.

Run: python launcher.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

# =============================================================================
# APPLICATION REGISTRY
# =============================================================================

APPS = {
    "🧙 Wizards": [
        ("Daily Data Wizard", "wizards/daily_data_wizard.py", "Daily sync, MA, RSI calculations - Run this every day!"),
    ],
    
    "💼 Portfolio & Analysis": [
        ("Portfolio Manager", "portfolio_gui.py", "Manage portfolios from scanner results, track P&L and performance"),
        ("🎯 Swing Trade Scanner", "analysis/swing_trade_scanner.py", "Weekly stock selection for swing trades based on volume analysis"),
        ("Volume Analysis Scanner", "volume_analysis_gui.py", "Detect accumulation/distribution patterns with OBV, CMF, VWAP"),
        ("Turnover Analysis GUI", "analysis/turnover_analysis_gui.py", "Daily, weekly, monthly turnover with charts and unusual detection"),
        ("Turnover Analysis CLI", "analysis/turnover_analysis.py", "Command-line turnover analysis (--daily, --weekly, --top, --unusual)"),
        ("Fast Price Monitor", "fast_price_monitor.py", "Real-time price alerts with 5-second updates (BTC-USD, etc.)"),
    ],
    
    "📊 Volume Cluster Analysis": [
        ("Volume Analysis Suite", "volume_cluster_analysis/volume_analysis_suite.py", "Full GUI: Scanner, Alerts, Patterns, Stock Events (4 tabs)"),
        ("Trading Rules GUI", "volume_cluster_analysis/trading_rules_gui.py", "Interactive GUI for trading signals with rule performance"),
        ("Chart Visualizer", "volume_cluster_analysis/chart_visualizer.py", "Interactive PyQtGraph chart with SMAs, Bollinger Bands, RSI, volume events"),
        ("Trading Rules Engine", "volume_cluster_analysis/trading_rules.py", "Generate trading signals based on volume patterns"),
        ("Volume Events GUI", "volume_cluster_analysis/volume_events_gui.py", "Simple view of high volume events with forward returns"),
        ("Volume Scanner (CLI)", "volume_cluster_analysis/scanner.py", "Find recent high volume events from command line"),
        ("Volume Alerts (CLI)", "volume_cluster_analysis/alerts.py", "Check and manage volume alerts from command line"),
        ("Pattern Analyzer (CLI)", "volume_cluster_analysis/pattern_analyzer.py", "Analyze volume-price patterns from command line"),
        ("Populate Events DB", "volume_cluster_analysis/populate_events.py", "Analyze all Nifty 50 stocks and store events in DB"),
    ],
    
    "⭐ Stock Ratings": [
        ("Price & Ratings Analyzer", "launch_price_ratings_analyzer.py", "Price correlation, signals, sector rotation analysis"),
        ("Rankings Data Analyzer", "launch_rankings_analyzer.py", "Validate and explore historical rankings data"),
        ("Parallel Rankings Builder", "ranking/parallel/parallel_gui.py", "Build historical rankings with Redis workers"),
        ("Index Ratings Test", "test_index_ratings.py", "View current sector/index ratings"),
    ],
    
    "📊 Bollinger Bands": [
        ("BB Visualizer", "bollinger/launch_bb_visualizer.py", "Interactive chart: Price with BB overlay, %b, BandWidth indicators"),
        ("BB Analyzer", "bollinger/launch_bb_analyzer.py", "Bollinger Bands analysis with %b, BandWidth, ratings & signals"),
        ("BB Scanner", "bollinger/launch_bb_scanner.py", "Scan for squeeze, bulge, trend, pullback setups"),
        ("BB Historical Backfill", "bollinger/launch_bb_backfill_gui.py", "One-time: Compute BB for all historical data (GUI with progress)"),
    ],
    
    "📊 Dashboards": [
        ("Historical A/D Visualizer", "historical_ad_visualizer.py", "Historical Advance/Decline analysis with NIFTY overlay, turning points"),
        ("Real-Time Market Breadth (PyQtGraph)", "realtime_adv_decl_dashboard_pyqt.py", "High-performance live A/D monitor with PyQtGraph charts"),
        ("Real-Time Market Breadth (Classic)", "realtime_adv_decl_dashboard.py", "Live advance-decline tracking (Tkinter/Matplotlib)"),
        ("Progress Dashboard", "progress_dashboard.py", "View project progress statistics"),
        ("Vedic Dashboard", "vedic_astrology/launch_dashboard.py", "Planetary position analysis"),
    ],
    
    "📥 Data Download": [
        ("Yahoo Finance Downloader", "data_tools/yahoo_downloader_gui.py", "Download daily & intraday data from Yahoo Finance"),
        ("Quick Nifty500 Download", "data_tools/quick_download_nifty500.py", "Download last 7 days for all Nifty 500 stocks"),
        ("BHAV Data Sync (GUI)", "data_tools/sync_bhav_gui.py", "Import NSE BHAV copy files"),
        ("Rebuild Intraday Data", "data_tools/rebuild_intraday_data.py", "Rebuild intraday candle data"),
        ("Refetch Nifty Today", "data_tools/refetch_nifty_today.py", "Refresh today's Nifty data"),
    ],
    
    "🔍 Scanners": [
        ("Golden/Death Cross Scanner", "scanners/golden_death_cross/scanner_gui.py", "50/200 SMA crossover signals with historical tracking"),
        ("Momentum Scanner GUI", "scanners/momentum_scanner_gui.py", "Visual momentum scanner (Yahoo Finance)"),
        ("Cup & Handle Scanner", "scanners/cup_handle_scanner.py", "Cup and handle pattern scanner"),
        ("Cup & Handle Analyzer", "scanners/cup_handle_analyzer.py", "Detailed cup and handle analysis"),
        ("Momentum Scanner (CLI)", "scanners/nifty500_momentum_scanner.py", "Momentum-based stock scanner (NSE BHAV)"),
        ("RSI Divergences", "scanners/rsi_divergences.py", "RSI divergence scanner"),
        ("RSI Fractals", "scanners/rsi_fractals.py", "RSI fractal scanner"),
        ("RSI Overbought/Oversold (GUI)", "rsi_overbought_oversold_gui.py", "Interactive RSI >= 80 / <= 20 analyzer for NIFTY & NIFTY 500"),
        ("RSI Overbought/Oversold (CLI)", "rsi_overbought_oversold_analyzer.py", "Command-line RSI analysis with CSV export"),
        ("52-Week Scanner", "scanners/week52_v2.py", "52-week high/low scanner"),
        ("Volatility Screener", "scanners/volatility_trading_screener.py", "Volatility trading scanner"),
        ("Minervini Screener", "scanners/minervini_screener.py", "Mark Minervini criteria scanner"),
        ("Scanner GUI", "scanners/scanner_gui.py", "Visual scanner interface"),
        ("VCP Scanner", "volatility_patterns/analysis/vcp_scanner.py", "Volatility Contraction Pattern"),
        ("Mean Reversion Scanner", "mean_reversion/ui/scanner_gui.py", "Event-Driven Parallel Scanner (RSI, BB)"),
    ],
    
    "📈 Charts & Analysis": [
        ("Volume Profile Analyzer", "volume_profile/visualizer.py", "Daily volume profiles with VPOC, VAH, VAL from 1-min data"),
        ("Coppock Curve (PyQtGraph)", "analysis/coppock_curve_pyqt.py", "Long-term momentum indicator - High performance interactive charts"),
        ("Coppock Curve (Matplotlib)", "analysis/coppock_curve.py", "Long-term momentum indicator - Classic Tkinter/Matplotlib version"),
        ("Chart Tool", "charts/chart_tool.py", "Interactive stock charts"),
        ("Chart Window", "charts/chart_window.py", "Standalone chart window"),
        ("Price Cluster Analyzer", "analysis/price_cluster_analyzer.py", "Find support/resistance price zones"),
        ("Compute Moving Averages", "analysis/compute_moving_averages.py", "Calculate SMAs for stocks"),
    ],
    
    "📑 Reports": [
        ("Nifty50 Report", "analysis/generate_full_nifty50_report.py", "Complete Nifty 50 analysis report"),
        ("Momentum Report", "analysis/nifty500_momentum_report.py", "Momentum rankings report"),
        ("Sector Report", "services/sector_report_generator.py", "Sectoral analysis report"),
        ("Block/Bulk Deals PDF", "block_bulk_deals/generate_pdf_report.py", "Block and bulk deals report"),
        ("Zodiac Market Report", "vedic_astrology/zodiac_market_report.py", "Zodiac-based market report"),
    ],
    
    "🛠️ Utilities": [
        ("Start Work Day", "start_work.py", "Morning summary and context"),
        ("Log Progress", "log.py", "Log project changes"),
        ("AI Context", "ai_context.py", "Show all context for AI assistant"),
        ("Symbol Mapping", "utilities/update_symbol_mappings.py", "Update NSE-Yahoo symbol mappings"),
        ("Available Stocks", "utilities/available_stocks_list.py", "List available stock symbols"),
    ],
    
    "🔮 Vedic Astrology": [
        ("Launch Dashboard", "vedic_astrology/launch_dashboard.py", "Main vedic dashboard"),
        ("Zodiac Report", "vedic_astrology/zodiac_market_report.py", "Zodiac-based market report"),
        ("Generate PDF Report", "vedic_astrology/generate_zodiac_pdf_report.py", "Generate zodiac PDF"),
    ],
    
    "🪙 Crypto": [
        ("Crypto Data Wizard", "crypto/wizards/crypto_data_wizard.py", "Sync Top 100 cryptos: daily data, MAs, RSI, A/D breadth"),
        ("Crypto Visualizer", "crypto/gui/crypto_visualizer.py", "Price chart with candlesticks, SMAs, RSI - PyQtGraph"),
        ("Crypto Breadth Visualizer", "crypto/gui/crypto_breadth_visualizer.py", "Market breadth: A/D Line, distribution, BTC overlay"),
        ("Crypto Symbol List", "crypto/data/crypto_symbols.py", "View Top 100 crypto symbols by market cap"),
    ],
    
    "📊 SMA Breadth Analysis": [
        ("SMA Breadth Visualizer", "analysis/sma_breadth_visualizer.py", "Interactive % stocks above SMA (5,10,20,50,100,150,200) with peak/trough detection"),
        ("Intraday SMA Breadth", "intraday_breadth/visualizer.py", "Nifty 50 intraday (5-min) % above SMA10/20/50/200 with live refresh"),
        ("Sector SMA Analysis", "analysis/sector_sma_visualizer.py", "Sector rotation analysis - find leading/lagging sectors and stock picks"),
        ("Swing Trade Scanner", "analysis/swing_trade_scanner_gui.py", "Find swing trade candidates (Long/Short) based on SMA analysis"),
        ("Sector Analysis CLI", "analysis/sector_sma_analysis.py", "Command-line sector rotation and stock picker"),
        ("SMA Breadth Calculator", "analysis/sma_breadth_analysis.py", "Calculate and store % above SMA for Nifty 50/500"),
        ("Historical A/D Visualizer", "historical_ad_visualizer.py", "Historical Advance/Decline + % above SMA50/200 with NIFTY overlay"),
    ],
}


class LauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("StockScreeer - Central Launcher")
        self.root.geometry("900x650")
        self.root.configure(bg='#1e1e1e')
        
        # Style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.configure_styles()
        
        self.create_widgets()
        
    def configure_styles(self):
        """Configure ttk styles for dark theme"""
        self.style.configure('Title.TLabel', 
                           font=('Segoe UI', 24, 'bold'),
                           foreground='#00ff88',
                           background='#1e1e1e')
        
        self.style.configure('Subtitle.TLabel',
                           font=('Segoe UI', 10),
                           foreground='#888888',
                           background='#1e1e1e')
        
        self.style.configure('Category.TLabelframe',
                           background='#2d2d2d',
                           foreground='#ffffff')
        
        self.style.configure('Category.TLabelframe.Label',
                           font=('Segoe UI', 12, 'bold'),
                           foreground='#00aaff',
                           background='#1e1e1e')
        
        self.style.configure('App.TButton',
                           font=('Segoe UI', 10),
                           padding=(10, 8))
        
        self.style.configure('TNotebook',
                           background='#1e1e1e')
        
        self.style.configure('TNotebook.Tab',
                           font=('Segoe UI', 10),
                           padding=(15, 8))
    
    def create_widgets(self):
        """Create main UI widgets"""
        # Header
        header_frame = tk.Frame(self.root, bg='#1e1e1e')
        header_frame.pack(fill='x', padx=20, pady=15)
        
        title = ttk.Label(header_frame, text="📈 StockScreeer", style='Title.TLabel')
        title.pack(side='left')
        
        subtitle = ttk.Label(header_frame, 
                           text="Central Launcher • 430+ Python files organized",
                           style='Subtitle.TLabel')
        subtitle.pack(side='left', padx=20, pady=10)
        
        # Notebook for categories
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Create tabs for each category
        for category, apps in APPS.items():
            tab = tk.Frame(self.notebook, bg='#2d2d2d')
            self.notebook.add(tab, text=category)
            self.create_app_buttons(tab, apps)
        
        # Footer
        footer_frame = tk.Frame(self.root, bg='#1e1e1e')
        footer_frame.pack(fill='x', padx=20, pady=10)
        
        # Quick actions
        quick_frame = tk.Frame(footer_frame, bg='#1e1e1e')
        quick_frame.pack(side='left')
        
        ttk.Button(quick_frame, text="🌅 Start Work Day", 
                  command=lambda: self.run_app("start_work.py")).pack(side='left', padx=5)
        ttk.Button(quick_frame, text="📝 Log Progress",
                  command=lambda: self.run_app("log.py")).pack(side='left', padx=5)
        ttk.Button(quick_frame, text="📊 View Progress",
                  command=lambda: self.run_app("progress_dashboard.py")).pack(side='left', padx=5)
        
        # Exit button
        ttk.Button(footer_frame, text="❌ Exit",
                  command=self.root.quit).pack(side='right', padx=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready. Select an application to launch.")
        status_bar = tk.Label(self.root, textvariable=self.status_var,
                            bg='#252525', fg='#888888',
                            anchor='w', padx=10, pady=5)
        status_bar.pack(fill='x', side='bottom')
    
    def create_app_buttons(self, parent, apps):
        """Create buttons for apps in a category"""
        # Create scrollable frame
        canvas = tk.Canvas(parent, bg='#2d2d2d', highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#2d2d2d')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Create app cards
        for i, (name, script, description) in enumerate(apps):
            self.create_app_card(scrollable_frame, name, script, description, i)
    
    def create_app_card(self, parent, name, script, description, row):
        """Create a card for an application"""
        card = tk.Frame(parent, bg='#3d3d3d', padx=15, pady=12)
        card.pack(fill='x', padx=10, pady=5)
        
        # Name and launch button
        top_row = tk.Frame(card, bg='#3d3d3d')
        top_row.pack(fill='x')
        
        name_label = tk.Label(top_row, text=name, 
                            font=('Segoe UI', 11, 'bold'),
                            fg='#ffffff', bg='#3d3d3d', anchor='w')
        name_label.pack(side='left')
        
        launch_btn = tk.Button(top_row, text="▶ Launch",
                             font=('Segoe UI', 9),
                             bg='#00aa55', fg='white',
                             activebackground='#00cc66',
                             cursor='hand2',
                             command=lambda s=script: self.run_app(s))
        launch_btn.pack(side='right')
        
        # Description
        desc_label = tk.Label(card, text=description,
                            font=('Segoe UI', 9),
                            fg='#aaaaaa', bg='#3d3d3d', anchor='w')
        desc_label.pack(fill='x', pady=(5, 0))
        
        # Script path
        path_label = tk.Label(card, text=f"📁 {script}",
                            font=('Consolas', 8),
                            fg='#666666', bg='#3d3d3d', anchor='w')
        path_label.pack(fill='x', pady=(3, 0))
    
    def run_app(self, script):
        """Launch an application"""
        script_path = PROJECT_ROOT / script
        
        if not script_path.exists():
            # Try without subdirectory
            script_path = PROJECT_ROOT / Path(script).name
            
        if not script_path.exists():
            messagebox.showerror("Error", f"Script not found: {script}")
            self.status_var.set(f"❌ Error: {script} not found")
            return
        
        self.status_var.set(f"🚀 Launching: {script}...")
        self.root.update()
        
        try:
            # Run in new process
            subprocess.Popen([sys.executable, str(script_path)],
                           cwd=str(PROJECT_ROOT))
            self.status_var.set(f"✅ Launched: {script}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch: {e}")
            self.status_var.set(f"❌ Failed: {e}")


def main():
    root = tk.Tk()
    app = LauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
