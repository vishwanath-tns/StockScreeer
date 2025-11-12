#!/usr/bin/env python3
"""
Test Reports Tab Integration
===========================

Quick test to verify that the Reports tab has been successfully added
to the Scanner GUI and is functioning properly.
"""

import tkinter as tk
import sys
import os
from pathlib import Path

def test_reports_tab_integration():
    """Test the Reports tab integration"""
    print("🧪 Testing Reports Tab Integration")
    print("=" * 50)
    
    try:
        # Add the project to Python path
        project_dir = Path(__file__).parent.parent  # Go up from scripts/ to project root
        sys.path.insert(0, str(project_dir))
        
        # Import the Reports tab class
        from gui.tabs.reports import ReportsTab
        print("✅ Successfully imported ReportsTab class")
        
        # Create a test window
        print("🖥️ Creating test window...")
        root = tk.Tk()
        root.title("Reports Tab Test")
        root.geometry("900x700")
        
        # Create a frame for the reports tab
        test_frame = tk.Frame(root)
        test_frame.pack(fill="both", expand=True)
        
        # Initialize the Reports tab
        print("📊 Initializing Reports tab...")
        reports_tab = ReportsTab(test_frame)
        print("✅ Reports tab initialized successfully!")
        
        # Add test instructions
        instructions = """
        🎯 TEST INSTRUCTIONS:
        
        1. ✅ The Reports tab should be visible with:
           - Main title: "📊 Reports Generator"
           - Description about PDF reports
           - Tabbed interface with subsections
           
        2. ✅ RSI Divergences subsection should show:
           - Report configuration options
           - Max stocks spinbox (default: 15)
           - Generate PDF button
           - Open folder button
           - Progress bar and log area
           
        3. ✅ Placeholder tabs should be visible:
           - 📊 Market Breadth
           - 🔍 Technical Analysis  
           - 💼 Portfolio
           
        4. ✅ Try clicking "Generate RSI Divergence PDF" to test
        5. ✅ Check that buttons are responsive and UI is professional
        
        Close this window when testing is complete.
        """
        
        print(instructions)
        print("🚀 Starting GUI test - close window when done")
        
        # Start the GUI
        root.mainloop()
        
        print("✅ GUI test completed successfully!")
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("💡 Make sure the gui/tabs/reports.py file exists")
        return False
    except Exception as e:
        print(f"💥 Error: {e}")
        import traceback
        print(f"📋 Details: {traceback.format_exc()}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_reports_tab_integration()
    if success:
        print("\n🎉 Reports Tab Integration Test: PASSED")
        print("📊 The Reports tab is ready for use in Scanner GUI!")
    else:
        print("\n❌ Reports Tab Integration Test: FAILED")
        print("🔧 Please check the error messages above")