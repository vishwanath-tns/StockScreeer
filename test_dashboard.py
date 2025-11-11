#!/usr/bin/env python3
"""
Test script to validate the Dashboard tab functionality.
Tests the DashboardTab class and its database status monitoring capabilities.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_dashboard_import():
    """Test that the dashboard tab can be imported successfully."""
    try:
        from gui.tabs.dashboard import DashboardTab
        print("✅ Dashboard tab imported successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to import dashboard tab: {e}")
        return False

def test_dashboard_status_methods():
    """Test the status checking methods in the dashboard."""
    try:
        from gui.tabs.dashboard import DashboardTab
        import tkinter as tk
        
        # Create a temporary root window
        root = tk.Tk()
        root.withdraw()  # Hide the window
        
        # Create a frame for testing
        frame = tk.Frame(root)
        
        # Create dashboard instance
        dashboard = DashboardTab(frame)
        
        # Test status methods exist
        methods_to_test = [
            'create_status_cards',
            'create_details_section', 
            'refresh_dashboard',
            'check_bhav_data',
            'check_sma_data',
            'check_rsi_data',
            'check_trend_data'
        ]
        
        for method_name in methods_to_test:
            if hasattr(dashboard, method_name):
                print(f"✅ Method '{method_name}' exists")
            else:
                print(f"❌ Method '{method_name}' missing")
                return False
        
        # Clean up
        root.destroy()
        print("✅ Dashboard methods validation passed")
        return True
        
    except Exception as e:
        print(f"❌ Failed to test dashboard methods: {e}")
        return False

def test_scanner_gui_integration():
    """Test that scanner_gui.py imports the dashboard correctly."""
    try:
        # Test the import without running the GUI
        import scanner_gui
        
        # Check if the scanner GUI class has dashboard-related attributes
        if hasattr(scanner_gui.ScannerGUI, '_build_dashboard_tab'):
            print("✅ Scanner GUI has dashboard tab building method")
        else:
            print("❌ Scanner GUI missing dashboard tab building method")
            return False
        
        print("✅ Scanner GUI integration test passed")
        return True
        
    except Exception as e:
        print(f"❌ Failed scanner GUI integration test: {e}")
        return False

def main():
    """Run all dashboard tests."""
    print("🧪 Testing Dashboard Tab Implementation")
    print("=" * 50)
    
    tests = [
        ("Dashboard Import", test_dashboard_import),
        ("Dashboard Methods", test_dashboard_status_methods),
        ("Scanner GUI Integration", test_scanner_gui_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        if test_func():
            passed += 1
        else:
            print(f"   Test failed!")
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Dashboard implementation is ready.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)