"""
Quick test for chart window functionality
"""
import tkinter as tk
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_chart_window():
    """Test the chart window with a simple parent."""
    try:
        root = tk.Tk()
        root.title("Chart Test Parent")
        root.geometry("200x100")
        
        # Test button
        def show_chart():
            try:
                from chart_window import show_stock_chart
                print(f"Parent type: {type(root)}")
                print(f"Parent has tk: {hasattr(root, 'tk')}")
                chart = show_stock_chart(root, "PIIND", 60)
                print("Chart created successfully!")
            except Exception as e:
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()
        
        btn = tk.Button(root, text="Show Chart", command=show_chart)
        btn.pack(pady=20)
        
        root.mainloop()
        
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_chart_window()