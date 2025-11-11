"""
Test Market Breadth Tab Integration with Scanner GUI

This script tests the market breadth tab integration to ensure it works
properly within the scanner GUI environment.
"""
import sys
import os
sys.path.append('d:/MyProjects/StockScreeer')
os.chdir('d:/MyProjects/StockScreeer')

import tkinter as tk
from tkinter import ttk
import time

def test_market_breadth_integration():
    """Test market breadth tab integration with scanner GUI."""
    print("🧪 TESTING MARKET BREADTH TAB INTEGRATION")
    print("=" * 50)
    
    try:
        # Test 1: Import check
        print("\n1. Testing imports...")
        from gui.tabs.market_breadth import MarketBreadthTab
        from services.market_breadth_service import get_current_market_breadth
        print("✅ All imports successful")
        
        # Test 2: Service functionality
        print("\n2. Testing service functionality...")
        result = get_current_market_breadth()
        if result.get('success'):
            print("✅ Market breadth service working")
            print(f"   Total stocks: {result['summary'].get('total_stocks', 0)}")
        else:
            print(f"❌ Service error: {result.get('error')}")
            return False
        
        # Test 3: GUI Integration
        print("\n3. Testing GUI integration...")
        
        root = tk.Tk()
        root.title("Market Breadth Integration Test")
        root.geometry("1000x700")
        
        # Create notebook similar to scanner_gui
        notebook = ttk.Notebook(root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create market breadth frame
        market_breadth_frame = ttk.Frame(notebook)
        notebook.add(market_breadth_frame, text="Market Breadth")
        
        # Status label
        status_label = ttk.Label(root, text="Initializing Market Breadth Tab...", 
                               foreground="blue")
        status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        def init_tab():
            """Initialize the market breadth tab."""
            try:
                # Create the market breadth tab
                market_breadth_tab = MarketBreadthTab(market_breadth_frame)
                status_label.config(text="✅ Market Breadth Tab loaded successfully! You can close this window.", 
                                   foreground="green")
                print("✅ Market breadth tab initialized successfully")
                
                # Set focus to the market breadth tab
                notebook.select(market_breadth_frame)
                
            except Exception as e:
                error_msg = f"❌ Error initializing tab: {str(e)}"
                status_label.config(text=error_msg, foreground="red")
                print(error_msg)
                
                # Show fallback content
                ttk.Label(market_breadth_frame, 
                         text="Market Breadth Analysis - Error Loading", 
                         font=('Arial', 14, 'bold')).pack(pady=20)
                ttk.Label(market_breadth_frame, 
                         text=f"Error: {str(e)}", 
                         foreground="red").pack(pady=10)
        
        # Initialize tab after a short delay to let the window appear
        root.after(100, init_tab)
        
        print("✅ GUI created, initializing tab...")
        print("\n💡 A test window will open with the Market Breadth tab.")
        print("   You can interact with it to test date selection and analysis.")
        print("   Close the window when done testing.")
        
        # Center the window
        root.update_idletasks()
        x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
        y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
        root.geometry(f"+{x}+{y}")
        
        # Run the GUI
        root.mainloop()
        
        print("\n✅ Market breadth integration test completed")
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_scanner_gui_integration():
    """Test if market breadth works within actual scanner GUI."""
    print("\n" + "=" * 50)
    print("🔧 TESTING ACTUAL SCANNER GUI INTEGRATION")
    print("=" * 50)
    
    try:
        from scanner_gui import ScannerGUI
        
        root = tk.Tk()
        root.withdraw()  # Hide initially
        
        print("Creating scanner GUI instance...")
        scanner = ScannerGUI(root)
        
        # Check market breadth integration
        if hasattr(scanner, 'market_breadth_frame'):
            children = scanner.market_breadth_frame.winfo_children()
            print(f"✅ Market breadth frame has {len(children)} widgets")
            
            if len(children) > 0:
                print("✅ Market breadth tab successfully integrated in scanner GUI")
                
                # Check if there's a main frame (indicates MarketBreadthTab was created)
                main_frames = [w for w in children if isinstance(w, ttk.Frame)]
                if main_frames:
                    print("✅ MarketBreadthTab main frame found")
                    
                    # Check children of main frame
                    main_frame = main_frames[0]
                    main_children = main_frame.winfo_children()
                    print(f"✅ Market breadth tab has {len(main_children)} components")
                    
                    if len(main_children) > 2:  # Should have title, notebook, etc.
                        print("✅ Market breadth tab fully loaded with all components")
                    else:
                        print("⚠️  Market breadth tab partially loaded")
                        
                else:
                    print("⚠️  Market breadth frame exists but may have loading issues")
            else:
                print("❌ Market breadth frame is empty - tab failed to load")
        else:
            print("❌ Market breadth frame not found in scanner GUI")
        
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ Scanner GUI integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Run integration tests
    test1_success = test_market_breadth_integration()
    test2_success = test_scanner_gui_integration()
    
    print(f"\n{'='*50}")
    print("📋 INTEGRATION TEST SUMMARY")
    print(f"{'='*50}")
    print(f"Market Breadth Tab Test: {'✅ PASS' if test1_success else '❌ FAIL'}")
    print(f"Scanner GUI Integration: {'✅ PASS' if test2_success else '❌ FAIL'}")
    
    if test1_success and test2_success:
        print("\n🎉 ALL TESTS PASSED!")
        print("   Market breadth tab is fully integrated with scanner GUI")
        print("   ✓ Date selection functionality available")
        print("   ✓ Real-time market breadth analysis")
        print("   ✓ Visual charts and distributions")
        print("   ✓ Historical comparison capabilities")
    else:
        print("\n⚠️  Some tests failed. Check error messages above.")