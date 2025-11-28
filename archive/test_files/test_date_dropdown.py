"""
Test Market Breadth Date Dropdown

This script specifically tests the date dropdown functionality
to debug why dates are not showing up.
"""
import sys
import os
sys.path.append('d:/MyProjects/StockScreeer')
os.chdir('d:/MyProjects/StockScreeer')

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date

from services.market_breadth_service import get_available_dates, get_current_market_breadth


def test_date_service():
    """Test the date service directly."""
    print("🧪 Testing date service...")
    
    try:
        dates = get_available_dates(10)
        if dates:
            print(f"✅ Service returned {len(dates)} dates:")
            for i, d in enumerate(dates):
                print(f"   {i+1}. {d} (type: {type(d)})")
        else:
            print("❌ Service returned no dates")
        return dates
    except Exception as e:
        print(f"❌ Service error: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_date_dropdown():
    """Test the date dropdown in isolation."""
    print("\n🧪 Testing date dropdown GUI...")
    
    # Get dates first
    dates = test_date_service()
    
    if not dates:
        print("❌ Cannot test dropdown without dates")
        return
    
    # Create test window
    root = tk.Tk()
    root.title("Date Dropdown Test")
    root.geometry("600x400")
    
    # Create test frame
    test_frame = ttk.LabelFrame(root, text="Date Dropdown Test", padding=20)
    test_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # Instructions
    ttk.Label(test_frame, text="Testing Market Breadth Date Dropdown", 
             font=('Arial', 14, 'bold')).pack(pady=10)
    
    # Date selection
    date_frame = ttk.Frame(test_frame)
    date_frame.pack(pady=10)
    
    ttk.Label(date_frame, text="Select Date:").pack(side=tk.LEFT)
    
    date_var = tk.StringVar(value="Latest")
    
    # Create date options
    date_options = ["Latest"]
    for date_obj in dates:
        date_str = date_obj.strftime('%Y-%m-%d')
        date_options.append(date_str)
    
    print(f"📋 Creating dropdown with options: {date_options}")
    
    date_combo = ttk.Combobox(date_frame, textvariable=date_var, 
                             values=date_options, width=20, state="readonly")
    date_combo.pack(side=tk.LEFT, padx=(10, 0))
    
    # Status
    status_var = tk.StringVar(value=f"✅ {len(dates)} dates loaded")
    status_label = ttk.Label(date_frame, textvariable=status_var, foreground="green")
    status_label.pack(side=tk.LEFT, padx=(10, 0))
    
    # Selection handler
    def on_date_selected(event=None):
        selected = date_var.get()
        print(f"📅 Date selected: {selected}")
        status_var.set(f"Selected: {selected}")
    
    date_combo.bind('<<ComboboxSelected>>', on_date_selected)
    
    # Test button
    def test_analysis():
        selected = date_var.get()
        print(f"🔍 Testing analysis for: {selected}")
        
        try:
            if selected == "Latest":
                result = get_current_market_breadth()
            else:
                from services.market_breadth_service import get_market_breadth_for_date
                date_obj = datetime.strptime(selected, '%Y-%m-%d').date()
                result = get_market_breadth_for_date(date_obj)
            
            if result.get('success'):
                summary = result['summary']
                total = summary.get('total_stocks', 0)
                bullish_pct = summary.get('bullish_percentage', 0)
                messagebox.showinfo("Analysis Result", 
                                  f"Analysis for {selected}:\n\n"
                                  f"Total Stocks: {total:,}\n"
                                  f"Bullish: {bullish_pct:.1f}%")
            else:
                messagebox.showerror("Error", f"Analysis failed: {result.get('error')}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Test failed: {e}")
    
    ttk.Button(test_frame, text="Test Analysis", command=test_analysis).pack(pady=10)
    
    # Results
    result_text = tk.Text(test_frame, height=10, width=60)
    result_text.pack(fill=tk.BOTH, expand=True, pady=10)
    
    result_text.insert(tk.END, f"📊 DATE DROPDOWN TEST RESULTS\n")
    result_text.insert(tk.END, f"=" * 40 + "\n\n")
    result_text.insert(tk.END, f"✅ Service found {len(dates)} dates\n")
    result_text.insert(tk.END, f"✅ Dropdown created with {len(date_options)} options\n\n")
    result_text.insert(tk.END, f"Available dates:\n")
    for i, d in enumerate(dates):
        result_text.insert(tk.END, f"  {i+1}. {d}\n")
    
    result_text.insert(tk.END, f"\nDropdown options:\n")
    for i, opt in enumerate(date_options):
        result_text.insert(tk.END, f"  {i+1}. {opt}\n")
    
    result_text.insert(tk.END, f"\n💡 Instructions:\n")
    result_text.insert(tk.END, f"1. Click the dropdown above\n")
    result_text.insert(tk.END, f"2. Select any date\n")
    result_text.insert(tk.END, f"3. Click 'Test Analysis' button\n")
    result_text.insert(tk.END, f"4. Check if analysis works for selected date\n")
    
    # Make text read-only
    result_text.configure(state='disabled')
    
    print(f"🎮 GUI test window created with {len(date_options)} dropdown options")
    root.mainloop()


if __name__ == "__main__":
    test_date_dropdown()