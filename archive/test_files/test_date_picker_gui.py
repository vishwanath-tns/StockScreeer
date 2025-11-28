"""
Test the new Market Breadth GUI with Date Picker
"""
import sys
import os
sys.path.append('d:/MyProjects/StockScreeer')
os.chdir('d:/MyProjects/StockScreeer')

import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry
from datetime import date, datetime

from services.market_breadth_service import get_or_calculate_market_breadth


def test_date_picker_gui():
    """Test a simple date picker GUI for market breadth."""
    print("🧪 Creating date picker GUI test...")
    
    root = tk.Tk()
    root.title("Market Breadth Date Picker Test")
    root.geometry("800x600")
    
    # Main frame
    main_frame = ttk.Frame(root, padding=20)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Title
    ttk.Label(main_frame, text="Market Breadth Analysis with Date Picker", 
             font=('Arial', 16, 'bold')).pack(pady=(0, 20))
    
    # Date selection frame
    date_frame = ttk.LabelFrame(main_frame, text="Date Selection", padding=15)
    date_frame.pack(fill=tk.X, pady=(0, 20))
    
    # Latest data toggle
    use_latest = tk.BooleanVar(value=True)
    latest_check = ttk.Checkbutton(date_frame, text="Use Latest Data", 
                                 variable=use_latest, 
                                 command=lambda: toggle_date_picker())
    latest_check.pack(side=tk.LEFT, padx=(0, 20))
    
    # Date picker
    ttk.Label(date_frame, text="Select Date:").pack(side=tk.LEFT)
    
    date_picker = DateEntry(date_frame, width=12, background='darkblue',
                          foreground='white', borderwidth=2,
                          date_pattern='yyyy-mm-dd', state='disabled')
    date_picker.pack(side=tk.LEFT, padx=(10, 0))
    
    # Analyze button
    analyze_btn = ttk.Button(date_frame, text="Analyze", state='disabled')
    analyze_btn.pack(side=tk.LEFT, padx=(10, 0))
    
    # Status label
    status_label = ttk.Label(date_frame, text="Using latest data", 
                           foreground="green")
    status_label.pack(side=tk.LEFT, padx=(20, 0))
    
    # Results frame
    results_frame = ttk.LabelFrame(main_frame, text="Analysis Results", padding=15)
    results_frame.pack(fill=tk.BOTH, expand=True)
    
    # Results text
    results_text = tk.Text(results_frame, height=15, width=80)
    scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=results_text.yview)
    results_text.configure(yscrollcommand=scrollbar.set)
    
    results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def toggle_date_picker():
        """Toggle between latest data and date picker."""
        if use_latest.get():
            date_picker.configure(state='disabled')
            analyze_btn.configure(state='disabled')
            status_label.configure(text="Using latest data", foreground="green")
        else:
            date_picker.configure(state='normal')
            analyze_btn.configure(state='normal')
            status_label.configure(text="Select a date to analyze", foreground="blue")
    
    def analyze_data():
        """Analyze market breadth for selected date."""
        results_text.delete(1.0, tk.END)
        
        if use_latest.get():
            status_label.configure(text="Analyzing latest data...", foreground="orange")
            selected_date = None
            date_label = "Latest"
        else:
            selected_date = date_picker.get_date()
            date_label = selected_date.strftime('%Y-%m-%d')
            status_label.configure(text=f"Analyzing {date_label}...", foreground="orange")
        
        def fetch_and_display():
            try:
                if selected_date:
                    result = get_or_calculate_market_breadth(selected_date)
                else:
                    from services.market_breadth_service import get_current_market_breadth
                    result = get_current_market_breadth()
                
                # Update GUI in main thread
                def update_results():
                    if result['success']:
                        summary = result['summary']
                        total = summary.get('total_stocks', 0)
                        bullish_pct = summary.get('bullish_percentage', 0)
                        bearish_pct = summary.get('bearish_percentage', 0)
                        
                        results_text.insert(tk.END, f"📊 MARKET BREADTH ANALYSIS - {date_label}\\n")
                        results_text.insert(tk.END, "=" * 50 + "\\n\\n")
                        results_text.insert(tk.END, f"📈 Total Stocks Analyzed: {total:,}\\n")
                        results_text.insert(tk.END, f"🟢 Bullish Percentage: {bullish_pct:.1f}%\\n")
                        results_text.insert(tk.END, f"🔴 Bearish Percentage: {bearish_pct:.1f}%\\n\\n")
                        
                        if result.get('newly_calculated'):
                            results_text.insert(tk.END, "✨ This data was newly calculated!\\n\\n")
                        else:
                            results_text.insert(tk.END, "💾 Retrieved from existing analysis\\n\\n")
                        
                        # Show rating distribution
                        results_text.insert(tk.END, "📋 RATING DISTRIBUTION:\\n")
                        results_text.insert(tk.END, "-" * 30 + "\\n")
                        for dist in result['rating_distribution']:
                            category = dist['rating_category']
                            count = dist['stock_count']
                            results_text.insert(tk.END, f"{category}: {count:,} stocks\\n")
                        
                        status_label.configure(text=f"✅ Analysis complete for {date_label}", 
                                             foreground="green")
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        results_text.insert(tk.END, f"❌ ANALYSIS FAILED\\n\\n")
                        results_text.insert(tk.END, f"Error: {error_msg}\\n")
                        status_label.configure(text=f"❌ Analysis failed", foreground="red")
                
                root.after(0, update_results)
                
            except Exception as e:
                def show_error():
                    results_text.insert(tk.END, f"❌ UNEXPECTED ERROR\\n\\n")
                    results_text.insert(tk.END, f"Error: {str(e)}\\n")
                    status_label.configure(text="❌ Error occurred", foreground="red")
                
                root.after(0, show_error)
        
        # Run analysis in background thread
        import threading
        threading.Thread(target=fetch_and_display, daemon=True).start()
    
    # Connect analyze button
    analyze_btn.configure(command=analyze_data)
    
    # Instructions
    instructions = ttk.Label(main_frame, 
                           text="💡 Toggle 'Use Latest Data' to enable date picker. "
                                "Select any date and click 'Analyze' to get market breadth analysis.",
                           foreground="blue", font=('Arial', 10))
    instructions.pack(pady=10)
    
    print("🎮 Date picker GUI test window created!")
    root.mainloop()


if __name__ == "__main__":
    test_date_picker_gui()