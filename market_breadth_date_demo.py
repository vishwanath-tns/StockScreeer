"""
Simple Market Breadth Date Selection Demo

This script provides a simple GUI interface to select dates and 
perform market breadth analysis using trend ratings.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
import threading
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.market_breadth_service import (
    get_current_market_breadth,
    get_market_breadth_for_date,
    get_available_dates,
    calculate_market_breadth_score,
    get_breadth_alerts
)


class MarketBreadthDateSelector:
    """Simple GUI for selecting dates and viewing market breadth analysis."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Market Breadth Analysis - Date Selection")
        self.root.geometry("800x600")
        
        # Current data
        self.current_data = {}
        self.available_dates = []
        
        self.setup_ui()
        self.load_available_dates()
    
    def setup_ui(self):
        """Set up the user interface."""
        
        # Title
        title_label = ttk.Label(self.root, text="Market Breadth Analysis - Date Selection", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=10)
        
        # Date selection frame
        date_frame = ttk.LabelFrame(self.root, text="Select Analysis Date", padding=10)
        date_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Date selection controls
        controls_frame = ttk.Frame(date_frame)
        controls_frame.pack(fill=tk.X)
        
        ttk.Label(controls_frame, text="Choose Date:").pack(side=tk.LEFT)
        
        self.date_var = tk.StringVar(value="Latest")\n        self.date_combo = ttk.Combobox(controls_frame, textvariable=self.date_var, 
                                      values=["Latest"], width=15, state="readonly")
        self.date_combo.pack(side=tk.LEFT, padx=(10, 0))
        
        # Analyze button
        analyze_btn = ttk.Button(controls_frame, text="Analyze", 
                               command=self.analyze_selected_date)
        analyze_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        # Refresh dates button
        refresh_btn = ttk.Button(controls_frame, text="Refresh Dates", 
                               command=self.load_available_dates)
        refresh_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        # Results frame
        results_frame = ttk.LabelFrame(self.root, text="Analysis Results", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Create text widget with scrollbar for results
        text_frame = ttk.Frame(results_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.results_text = tk.Text(text_frame, wrap=tk.WORD, font=('Consolas', 10))
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=scrollbar.set)
        
        self.results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def load_available_dates(self):
        """Load available analysis dates in background."""
        def fetch_dates():
            try:
                self.status_var.set("Loading available dates...")
                dates = get_available_dates(30)  # Last 30 dates
                
                # Update UI on main thread
                self.root.after(0, lambda: self.update_date_options(dates))
                
            except Exception as e:
                self.root.after(0, lambda: self.show_error(f"Failed to load dates: {e}"))
        
        threading.Thread(target=fetch_dates, daemon=True).start()
    
    def update_date_options(self, dates):
        """Update the date dropdown with available dates."""
        self.available_dates = dates
        
        if dates:
            # Create date strings for dropdown
            date_options = ["Latest"]
            for date_obj in dates:
                date_str = date_obj.strftime('%Y-%m-%d')
                date_options.append(date_str)
            
            # Update combobox
            self.date_combo['values'] = date_options
            self.status_var.set(f"Loaded {len(dates)} available dates")
            
            # Show initial message
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, f"📅 Found {len(dates)} available analysis dates\\n")
            self.results_text.insert(tk.END, "Select a date and click 'Analyze' to view market breadth analysis\\n\\n")
            self.results_text.insert(tk.END, "Recent dates available:\\n")
            for i, date_obj in enumerate(dates[:10]):
                self.results_text.insert(tk.END, f"  {i+1:2d}. {date_obj}\\n")
        else:
            self.date_combo['values'] = ["Latest"]
            self.status_var.set("No dates available")
            self.show_error("No analysis dates found")
    
    def analyze_selected_date(self):
        """Analyze market breadth for the selected date."""
        selected_date = self.date_var.get()
        
        def fetch_analysis():
            try:
                self.status_var.set(f"Analyzing market breadth for {selected_date}...")
                
                if selected_date == "Latest":
                    data = get_current_market_breadth()
                else:
                    # Parse date and get analysis
                    try:
                        parsed_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
                        data = get_market_breadth_for_date(parsed_date)
                    except ValueError:
                        data = {'success': False, 'error': 'Invalid date format'}
                
                # Update UI on main thread
                self.root.after(0, lambda: self.display_analysis_results(data, selected_date))
                
            except Exception as e:
                self.root.after(0, lambda: self.show_error(f"Analysis failed: {e}"))
        
        threading.Thread(target=fetch_analysis, daemon=True).start()
    
    def display_analysis_results(self, data, analysis_date):
        """Display the market breadth analysis results."""
        self.results_text.delete(1.0, tk.END)
        
        if not data.get('success', False):
            error_msg = data.get('error', 'Unknown error')
            self.results_text.insert(tk.END, f"❌ Error: {error_msg}\\n")
            self.status_var.set("Analysis failed")
            return
        
        summary = data.get('summary', {})
        distribution = data.get('rating_distribution', [])
        
        # Header
        self.results_text.insert(tk.END, f"{'='*70}\\n")
        self.results_text.insert(tk.END, f"MARKET BREADTH ANALYSIS FOR {analysis_date}\\n")
        self.results_text.insert(tk.END, f"{'='*70}\\n\\n")
        
        # Basic metrics
        self.results_text.insert(tk.END, "📊 BASIC METRICS:\\n")
        self.results_text.insert(tk.END, f"   Total Stocks Analyzed: {summary.get('total_stocks', 0):,}\\n")
        self.results_text.insert(tk.END, f"   Analysis Date: {summary.get('analysis_date', 'N/A')}\\n")
        self.results_text.insert(tk.END, f"   Market Average Rating: {summary.get('market_avg_rating', 0):.2f}\\n\\n")
        
        # Bullish/Bearish breakdown
        self.results_text.insert(tk.END, "📈 BULLISH/BEARISH BREAKDOWN:\\n")
        self.results_text.insert(tk.END, f"   Bullish Stocks: {summary.get('bullish_count', 0):,} ({summary.get('bullish_percentage', 0):.1f}%)\\n")
        self.results_text.insert(tk.END, f"   Bearish Stocks: {summary.get('bearish_count', 0):,} ({summary.get('bearish_percentage', 0):.1f}%)\\n")
        self.results_text.insert(tk.END, f"   Neutral Stocks: {summary.get('neutral_count', 0):,} ({summary.get('neutral_percentage', 0):.1f}%)\\n")
        self.results_text.insert(tk.END, f"   Bull/Bear Ratio: {summary.get('bullish_bearish_ratio', 0):.2f}\\n\\n")
        
        # Strong signals
        self.results_text.insert(tk.END, "🔥 STRONG SIGNALS:\\n")
        self.results_text.insert(tk.END, f"   Very Bullish (≥5): {summary.get('strong_bullish_count', 0):,}\\n")
        self.results_text.insert(tk.END, f"   Very Bearish (≤-5): {summary.get('strong_bearish_count', 0):,}\\n\\n")
        
        # Market breadth score
        score, interpretation = calculate_market_breadth_score(summary)
        self.results_text.insert(tk.END, "🎯 MARKET BREADTH SCORE:\\n")
        self.results_text.insert(tk.END, f"   Score: {score}/100\\n")
        self.results_text.insert(tk.END, f"   Interpretation: {interpretation}\\n\\n")
        
        # Alerts
        alerts = get_breadth_alerts(summary)
        if alerts:
            self.results_text.insert(tk.END, "⚠️  MARKET ALERTS:\\n")
            for alert in alerts:
                severity_icon = "🚨" if alert['severity'] == 'high' else "ℹ️"
                self.results_text.insert(tk.END, f"   {severity_icon} {alert['title']}: {alert['message']}\\n")
        else:
            self.results_text.insert(tk.END, "✅ No alerts - Market conditions are normal\\n")
        
        self.results_text.insert(tk.END, "\\n")
        
        # Rating distribution
        if distribution:
            self.results_text.insert(tk.END, "📋 RATING DISTRIBUTION:\\n")
            self.results_text.insert(tk.END, f"{'Category':<30} {'Count':<8} {'Avg Rating':<12}\\n")
            self.results_text.insert(tk.END, f"{'-'*52}\\n")
            
            for dist in distribution:
                category = dist['rating_category']
                count = dist['stock_count']
                avg_rating = dist['avg_rating']
                self.results_text.insert(tk.END, f"{category:<30} {count:<8} {avg_rating:<12.1f}\\n")
        
        self.status_var.set(f"Analysis completed for {analysis_date}")
        
        # Scroll to top
        self.results_text.see(1.0)
    
    def show_error(self, message):
        """Show error message."""
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, f"❌ Error: {message}\\n")
        self.status_var.set("Error occurred")
        messagebox.showerror("Error", message)


def main():
    """Main function to run the date selection demo."""
    root = tk.Tk()
    app = MarketBreadthDateSelector(root)
    
    # Center the window
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    root.mainloop()


if __name__ == "__main__":
    main()