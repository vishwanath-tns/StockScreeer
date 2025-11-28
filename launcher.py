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
    "📊 Dashboards": [
        ("Real-Time Market Dashboard", "realtime_adv_decl_dashboard.py", "Live advance-decline tracking for Nifty 500"),
        ("Yahoo Finance Dashboard", "yahoo_finance_dashboard.py", "General market dashboard"),
        ("Progress Dashboard", "progress_dashboard.py", "View project progress statistics"),
    ],
    
    "📥 Data Download": [
        ("Quick Nifty500 Download", "quick_download_nifty500.py", "Download last 7 days for all Nifty 500 stocks"),
        ("BHAV Data Sync (GUI)", "sync_bhav_gui.py", "Import NSE BHAV copy files"),
        ("Bulk Stock Downloader", "yfinance_downloader/yfinance_downloader_gui.py", "GUI for bulk stock downloads"),
        ("NSE Indices Download", "download_nse_indices_bulk.py", "Download NSE index data"),
    ],
    
    "🔍 Scanners": [
        ("VCP Scanner", "vcp_patterns/vcp_scanner.py", "Volatility Contraction Pattern scanner"),
        ("Cup & Handle Scanner", "cup_handle_scanner.py", "Cup and handle pattern scanner"),
        ("RSI Cross Scanner", "rsi_cross_scanner.py", "RSI crossover scanner"),
        ("52-Week Scanner", "week52_scanner.py", "52-week high/low scanner"),
        ("Momentum Scanner", "nifty500_momentum_scanner.py", "Momentum-based stock scanner"),
        ("Pattern Scanner GUI", "pattern_scanner/pattern_scanner_gui.py", "Visual pattern scanner"),
    ],
    
    "📈 Charts & Analysis": [
        ("Stock Chart Viewer", "chart_window.py", "Interactive stock charts"),
        ("Chart Visualizer", "chart_visualizer/chart_visualizer.py", "Advanced chart visualization"),
        ("VCP Charts", "vcp_patterns/vcp_visualizer.py", "VCP pattern visualization"),
        ("Cup Handle Charts", "cup_handle_charts.py", "Cup and handle pattern charts"),
        ("Sector Charts PDF", "pdf_reports/sector_charts_pdf_generator.py", "Generate sector chart PDFs"),
    ],
    
    "📑 Reports": [
        ("Nifty50 Report", "generate_full_nifty50_report.py", "Complete Nifty 50 analysis report"),
        ("Sector Report", "sector_analysis/sector_report_generator.py", "Sectoral analysis report"),
        ("Momentum Report", "nifty500_momentum_report.py", "Momentum rankings report"),
        ("PDF Report Generator", "pdf_reports/pdf_report_generator.py", "Custom PDF report builder"),
    ],
    
    "🛠️ Utilities": [
        ("Start Work Day", "start_work.py", "Morning summary and context"),
        ("Log Progress", "log.py", "Log project changes"),
        ("AI Context", "ai_context.py", "Show all context for AI assistant"),
        ("Check Data Coverage", "scripts/check_data_completeness.py", "Verify data completeness"),
    ],
    
    "🔮 Vedic Astrology": [
        ("Vedic Dashboard", "vedic_astrology/vedic_dashboard.py", "Planetary position analysis"),
        ("Zodiac Report", "vedic_astrology/zodiac_market_report.py", "Zodiac-based market report"),
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
