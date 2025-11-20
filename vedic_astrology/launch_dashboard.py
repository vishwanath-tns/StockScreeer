#!/usr/bin/env python3
"""
Vedic Astrology Trading Dashboard Launcher

Quick launcher for the Vedic astrology trading GUI application.
This ensures proper path setup and error handling.
"""

import sys
import os
import subprocess
from pathlib import Path

def main():
    """Launch the Vedic trading dashboard"""
    
    print("🌙 Vedic Astrology Trading Dashboard Launcher")
    print("=" * 50)
    
    # Set up paths
    current_dir = Path(__file__).parent
    gui_dir = current_dir / "gui" 
    gui_script = gui_dir / "vedic_trading_gui.py"
    
    # Check if GUI script exists
    if not gui_script.exists():
        print(f"❌ Error: GUI script not found at {gui_script}")
        print("Please ensure the vedic_trading_gui.py file exists in the gui folder.")
        input("Press Enter to exit...")
        return
    
    try:
        print(f"📂 Working directory: {current_dir}")
        print(f"🚀 Starting GUI from: {gui_script}")
        print()
        
        # Change to GUI directory and run
        os.chdir(gui_dir)
        
        # Run the GUI
        result = subprocess.run([sys.executable, "vedic_trading_gui.py"], 
                              cwd=gui_dir)
        
        if result.returncode == 0:
            print("\n✅ Dashboard closed successfully.")
        else:
            print(f"\n⚠️  Dashboard exited with code: {result.returncode}")
            
    except FileNotFoundError:
        print("❌ Error: Python not found in system PATH")
        print("Please ensure Python is properly installed.")
        
    except KeyboardInterrupt:
        print("\n🛑 Dashboard interrupted by user")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("Please check the error and try again.")
    
    finally:
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()