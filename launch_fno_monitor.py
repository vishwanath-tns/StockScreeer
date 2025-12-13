#!/usr/bin/env python3
"""
Launch FNO Services Monitor GUI
================================

Monitors both FNO Feed Launcher and FNO Database Writer services
with a real-time dashboard.

Usage:
  python launch_fno_monitor.py
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from dhan_trading.dashboard.fno_services_monitor import main

if __name__ == '__main__':
    main()
