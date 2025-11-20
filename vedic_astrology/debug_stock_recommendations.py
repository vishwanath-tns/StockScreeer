#!/usr/bin/env python3
"""
Debug version of the Vedic Trading Dashboard to test stock recommendations
"""

import tkinter as tk
from tkinter import ttk
import sys
import os
sys.path.append('./tools')

def test_stock_recommendations():
    """Test the stock recommendation logic directly"""
    try:
        from pyjhora_calculator import ProfessionalAstrologyCalculator
        import datetime
        
        calc = ProfessionalAstrologyCalculator()
        today = datetime.date.today()
        trading_time = datetime.datetime.combine(today, datetime.time(9, 15))
        astro_data = calc.get_complete_analysis(trading_time)
        
        # Get current moon sign and element
        moon_data = astro_data['planetary_positions'].get('Moon', {})
        moon_sign = moon_data.get('sign', 'Unknown')
        
        sign_elements = {
            'Aries': 'Fire', 'Taurus': 'Earth', 'Gemini': 'Air', 'Cancer': 'Water',
            'Leo': 'Fire', 'Virgo': 'Earth', 'Libra': 'Air', 'Scorpio': 'Water',
            'Sagittarius': 'Fire', 'Capricorn': 'Earth', 'Aquarius': 'Air', 'Pisces': 'Water'
        }
        element = sign_elements.get(moon_sign, 'Unknown')
        
        recommendations = {
            'moon_sign': moon_sign,
            'element': element,
            'high_conviction': [],
            'accumulation': [],
            'momentum': []
        }
        
        # Element-based sector recommendations
        if element == 'Water':
            recommendations['high_conviction'] = [
                f"💧 Healthcare Focus (9:15AM {moon_sign})",
                "SUNPHARMA (Pharmaceuticals)",
                "DRREDDY (Pharma)",
                "CIPLA (Medicine)"
            ]
            
            recommendations['accumulation'] = [
                "🧪 Chemical & Process",
                "ASIANPAINT (Paints)",
                "PIDILITIND (Chemicals)",
                "NESTLEIND (Beverages)"
            ]
            
            recommendations['momentum'] = [
                "💧 Water Element Momentum",
                "UBL (Beverages)",
                "BRITANNIA (Food Processing)"
            ]
        
        return recommendations
        
    except Exception as e:
        return {'error': str(e)}

class DebugStockGUI:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Debug: Stock Recommendations Test")
        self.window.geometry("800x600")
        
        # Test button
        test_btn = tk.Button(self.window, text="Test Stock Recommendations", 
                            command=self.run_test, font=('Arial', 12))
        test_btn.pack(pady=10)
        
        # Results area
        self.results_text = tk.Text(self.window, height=35, width=100, font=('Courier', 10))
        self.results_text.pack(pady=10, padx=10, fill='both', expand=True)
        
        # Run test automatically
        self.window.after(100, self.run_test)
    
    def run_test(self):
        self.results_text.delete('1.0', tk.END)
        self.results_text.insert(tk.END, "Testing Stock Recommendations...\n")
        self.results_text.insert(tk.END, "=" * 50 + "\n\n")
        
        recommendations = test_stock_recommendations()
        
        if 'error' in recommendations:
            self.results_text.insert(tk.END, f"ERROR: {recommendations['error']}\n")
        else:
            self.results_text.insert(tk.END, f"Moon Sign: {recommendations['moon_sign']}\n")
            self.results_text.insert(tk.END, f"Element: {recommendations['element']}\n\n")
            
            self.results_text.insert(tk.END, "HIGH CONVICTION RECOMMENDATIONS:\n")
            for stock in recommendations['high_conviction']:
                self.results_text.insert(tk.END, f"  • {stock}\n")
            
            self.results_text.insert(tk.END, "\nACCUMULATION RECOMMENDATIONS:\n")
            for stock in recommendations['accumulation']:
                self.results_text.insert(tk.END, f"  • {stock}\n")
            
            self.results_text.insert(tk.END, "\nMOMENTUM RECOMMENDATIONS:\n")
            for stock in recommendations['momentum']:
                self.results_text.insert(tk.END, f"  • {stock}\n")
            
            self.results_text.insert(tk.END, "\n" + "=" * 50 + "\n")
            self.results_text.insert(tk.END, "✅ These recommendations should appear in the main GUI\n")
            self.results_text.insert(tk.END, "✅ If they don't, the issue is in the GUI initialization sequence\n")
    
    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = DebugStockGUI()
    app.run()