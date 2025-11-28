"""
Market Breadth Date Selection Demo

This demonstrates the complete market breadth analysis with date selection
functionality that's integrated with the scanner GUI.
"""
import sys
import os
sys.path.append('d:/MyProjects/StockScreeer')
os.chdir('d:/MyProjects/StockScreeer')

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
import threading

from services.market_breadth_service import (
    get_current_market_breadth,
    get_market_breadth_for_date,
    get_available_dates,
    calculate_market_breadth_score
)


class MarketBreadthDateDemo:
    """Standalone demo of market breadth date selection functionality."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Market Breadth Analysis - Date Selection Demo")
        self.root.geometry("900x700")
        
        self.current_data = {}
        self.available_dates = []
        
        self.setup_ui()
        self.load_dates()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Title
        title_frame = ttk.Frame(self.root)
        title_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(title_frame, text="Market Breadth Analysis - Date Selection", 
                 font=('Arial', 16, 'bold')).pack()
        
        # Date selection frame
        date_frame = ttk.LabelFrame(self.root, text="Select Analysis Date", padding=10)
        date_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Date controls
        controls_frame = ttk.Frame(date_frame)
        controls_frame.pack(fill=tk.X)
        
        ttk.Label(controls_frame, text="Choose Date:").pack(side=tk.LEFT)
        
        self.date_var = tk.StringVar(value="Latest")
        self.date_combo = ttk.Combobox(controls_frame, textvariable=self.date_var, 
                                      values=["Latest"], width=15, state="readonly")
        self.date_combo.pack(side=tk.LEFT, padx=(10, 0))
        
        analyze_btn = ttk.Button(controls_frame, text="Analyze Selected Date", 
                               command=self.analyze_date, style='Accent.TButton')
        analyze_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(controls_frame, textvariable=self.status_var, 
                               foreground="blue")
        status_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Results frame
        results_frame = ttk.LabelFrame(self.root, text="Analysis Results", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Create text widget for results
        text_frame = ttk.Frame(results_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.results_text = tk.Text(text_frame, wrap=tk.WORD, font=('Consolas', 10))
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=scrollbar.set)
        
        self.results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Instructions
        self.results_text.insert(tk.END, 
            "📅 MARKET BREADTH ANALYSIS - DATE SELECTION DEMO\\n"
            "=" * 55 + "\\n\\n"
            "INSTRUCTIONS:\\n"
            "1. Select a date from the dropdown above\\n"
            "2. Click 'Analyze Selected Date' button\\n"
            "3. View comprehensive market breadth analysis\\n\\n"
            "FEATURES DEMONSTRATED:\\n"
            "✓ Historical date selection\\n"
            "✓ Market breadth metrics by trend ratings\\n"
            "✓ Bullish/bearish stock distribution\\n"
            "✓ Market breadth scoring (0-100)\\n"
            "✓ Rating category breakdown\\n\\n"
            "Loading available dates...\\n"
        )
    
    def load_dates(self):
        """Load available analysis dates."""
        def fetch_dates():
            try:
                self.status_var.set("🔄 Loading dates...")
                dates = get_available_dates(30)
                
                # Update UI on main thread
                self.root.after(0, lambda: self.update_dates(dates))
                
            except Exception as e:
                self.root.after(0, lambda: self.handle_error(f"Failed to load dates: {e}"))
        
        threading.Thread(target=fetch_dates, daemon=True).start()
    
    def update_dates(self, dates):
        """Update the date dropdown with available dates."""
        self.available_dates = dates
        
        if dates:
            date_options = ["Latest"]
            for date_obj in dates:
                date_str = date_obj.strftime('%Y-%m-%d')
                date_options.append(date_str)
            
            self.date_combo['values'] = date_options
            self.status_var.set(f"✅ {len(dates)} dates loaded")
            
            # Update instructions
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, 
                "📅 MARKET BREADTH ANALYSIS - DATE SELECTION DEMO\\n"
                "=" * 55 + "\\n\\n"
                f"✅ Found {len(dates)} available analysis dates\\n\\n"
                "AVAILABLE DATES:\\n"
            )
            
            for i, date_obj in enumerate(dates[:10]):
                self.results_text.insert(tk.END, f"   {i+1:2d}. {date_obj}\\n")
            
            if len(dates) > 10:
                self.results_text.insert(tk.END, f"   ... and {len(dates) - 10} more dates\\n")
            
            self.results_text.insert(tk.END, 
                "\\n📊 SELECT A DATE ABOVE AND CLICK 'ANALYZE' TO VIEW MARKET BREADTH\\n\\n"
                "The analysis will show:\\n"
                "• Total stocks analyzed\\n"
                "• Bullish vs bearish percentages\\n"
                "• Market average rating\\n"
                "• Market breadth score (0-100)\\n"
                "• Detailed rating distribution\\n"
            )
        else:
            self.status_var.set("❌ No dates found")
            self.handle_error("No analysis dates found in database")
    
    def analyze_date(self):
        """Analyze market breadth for selected date."""
        selected_date = self.date_var.get()
        
        if not selected_date:
            messagebox.showwarning("No Selection", "Please select a date to analyze.")
            return
        
        self.status_var.set("🔄 Analyzing...")
        
        def fetch_analysis():
            try:
                if selected_date == "Latest":
                    data = get_current_market_breadth()
                    analysis_label = "Latest Available"
                else:
                    # Parse date and analyze
                    date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
                    data = get_market_breadth_for_date(date_obj)
                    analysis_label = selected_date
                
                # Update UI on main thread
                self.root.after(0, lambda: self.display_results(data, analysis_label))
                
            except Exception as e:
                self.root.after(0, lambda: self.handle_error(f"Analysis failed: {e}"))
        
        threading.Thread(target=fetch_analysis, daemon=True).start()
    
    def display_results(self, data, analysis_label):
        """Display analysis results."""
        if not data.get('success', False):
            error_msg = data.get('error', 'Unknown error')
            self.status_var.set("❌ Error")
            self.handle_error(f"Analysis failed: {error_msg}")
            return
        
        summary = data.get('summary', {})
        distribution = data.get('rating_distribution', [])
        
        # Update status
        total_stocks = summary.get('total_stocks', 0)
        self.status_var.set(f"✅ {total_stocks:,} stocks analyzed")
        
        # Clear and show results
        self.results_text.delete(1.0, tk.END)
        
        # Header
        self.results_text.insert(tk.END, 
            f"📊 MARKET BREADTH ANALYSIS RESULTS\\n"
            f"Analysis Date: {analysis_label}\\n"
            f"=" * 60 + "\\n\\n"
        )
        
        # Basic metrics
        analysis_date = summary.get('analysis_date', 'N/A')
        avg_rating = summary.get('market_avg_rating', 0)
        bullish_count = summary.get('bullish_count', 0)
        bearish_count = summary.get('bearish_count', 0)
        neutral_count = summary.get('neutral_count', 0)
        bullish_pct = summary.get('bullish_percentage', 0)
        bearish_pct = summary.get('bearish_percentage', 0)
        neutral_pct = summary.get('neutral_percentage', 0)
        bb_ratio = summary.get('bullish_bearish_ratio', 0)
        
        self.results_text.insert(tk.END, 
            f"📈 BASIC METRICS:\\n"
            f"   Database Date: {analysis_date}\\n"
            f"   Total Stocks: {total_stocks:,}\\n"
            f"   Market Avg Rating: {avg_rating:.2f}\\n\\n"
            
            f"📊 BULLISH/BEARISH BREAKDOWN:\\n"
            f"   Bullish Stocks: {bullish_count:,} ({bullish_pct:.1f}%)\\n"
            f"   Bearish Stocks: {bearish_count:,} ({bearish_pct:.1f}%)\\n"
            f"   Neutral Stocks: {neutral_count:,} ({neutral_pct:.1f}%)\\n"
            f"   Bull/Bear Ratio: {bb_ratio:.2f}\\n\\n"
        )
        
        # Strong signals
        strong_bullish = summary.get('strong_bullish_count', 0)
        strong_bearish = summary.get('strong_bearish_count', 0)
        
        self.results_text.insert(tk.END, 
            f"🔥 STRONG SIGNALS:\\n"
            f"   Very Bullish (≥5): {strong_bullish:,}\\n"
            f"   Very Bearish (≤-5): {strong_bearish:,}\\n\\n"
        )
        
        # Market breadth score
        score, interpretation = calculate_market_breadth_score(summary)
        self.results_text.insert(tk.END, 
            f"🎯 MARKET BREADTH SCORE:\\n"
            f"   Score: {score}/100\\n"
            f"   Interpretation: {interpretation}\\n\\n"
        )
        
        # Rating distribution
        if distribution:
            self.results_text.insert(tk.END, 
                f"📋 RATING DISTRIBUTION:\\n"
                f"{'Category':<30} {'Count':<8} {'Avg Rating':<12}\\n"
                f"{'-' * 52}\\n"
            )
            
            for dist in distribution:
                category = dist['rating_category']
                count = dist['stock_count']
                avg_rating = dist['avg_rating']
                self.results_text.insert(tk.END, 
                    f"{category:<30} {count:<8} {avg_rating:<12.1f}\\n"
                )
        
        self.results_text.insert(tk.END, 
            f"\\n" + "=" * 60 + "\\n"
            f"✅ Analysis completed successfully!\\n\\n"
            f"💡 This demonstrates the market breadth date selection\\n"
            f"   functionality that's integrated in your Scanner GUI.\\n"
            f"   You can select any available date and get comprehensive\\n"
            f"   market sentiment analysis based on trend ratings.\\n"
        )
        
        # Scroll to top
        self.results_text.see(1.0)
        
        # Show summary popup
        messagebox.showinfo("Analysis Complete", 
                          f"Market Breadth Analysis for {analysis_label}:\\n\\n"
                          f"📊 Total Stocks: {total_stocks:,}\\n"
                          f"📈 Bullish: {bullish_pct:.1f}%\\n"
                          f"📉 Bearish: {bearish_pct:.1f}%\\n"
                          f"⭐ Score: {score}/100 ({interpretation})")
    
    def handle_error(self, error_msg):
        """Handle and display errors."""
        self.status_var.set("❌ Error")
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, 
            f"❌ ERROR OCCURRED:\\n"
            f"=" * 40 + "\\n\\n"
            f"{error_msg}\\n\\n"
            f"TROUBLESHOOTING:\\n"
            f"• Check database connection\\n"
            f"• Ensure .env file is configured\\n"
            f"• Verify trend_analysis table has data\\n"
        )
        messagebox.showerror("Error", error_msg)


def main():
    """Run the market breadth date selection demo."""
    root = tk.Tk()
    
    # Configure ttk style for better appearance
    style = ttk.Style()
    try:
        style.theme_use('clam')  # Use a modern theme
    except:
        pass  # Use default theme if clam not available
    
    app = MarketBreadthDateDemo(root)
    
    # Center the window
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    root.mainloop()


if __name__ == "__main__":
    main()