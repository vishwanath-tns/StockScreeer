#!/usr/bin/env python3
"""
Launch DHAN Control Center - Unified hub for all Dhan trading services
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Launch the DHAN Control Center"""
    print("=" * 70)
    print("DHAN CONTROL CENTER - Unified Trading Services Hub")
    print("=" * 70)
    print()
    print("Launching DHAN Control Center...")
    print()
    print("Services Available:")
    print("  1. FNO Feed Launcher       - Real-time market data feed (128 instruments)")
    print("  2. FNO Services Monitor    - PyQt5 dashboard for monitoring")
    print("  3. FNO Database Writer     - Persist quotes to MySQL")
    print("  4. Instrument Display      - Show subscribed instruments")
    print()
    print("-" * 70)
    print()
    
    try:
        # Launch the control center
        script_path = Path(__file__).parent / "dhan_trading" / "dashboard" / "dhan_control_center.py"
        subprocess.run([sys.executable, str(script_path)])
    except Exception as e:
        print(f"Error launching DHAN Control Center: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
