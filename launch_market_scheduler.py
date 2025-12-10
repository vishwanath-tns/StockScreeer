"""
Launch Dhan Market Services Scheduler
=====================================
A background service that automatically starts/stops Dhan market data services
based on Indian market hours.

Schedule (IST):
- Start: 8:55 AM Monday-Friday (before MCX 9:00 AM and NSE 9:15 AM)
- Stop: 12:00 AM (Midnight)

Features:
- System tray icon
- Auto-start on Windows boot (optional)
- Manual start/stop controls
- Service status monitoring

Usage:
    python launch_market_scheduler.py
    python launch_market_scheduler.py --install-startup   # Add to Windows startup
    python launch_market_scheduler.py --remove-startup    # Remove from Windows startup
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def install_startup():
    """Install to Windows startup"""
    try:
        import winshell
        from win32com.client import Dispatch
        
        startup_path = winshell.startup()
        shortcut_path = os.path.join(startup_path, "Dhan Market Scheduler.lnk")
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = sys.executable
        shortcut.Arguments = f'"{PROJECT_ROOT / "launch_market_scheduler.py"}"'
        shortcut.WorkingDirectory = str(PROJECT_ROOT)
        shortcut.Description = "Dhan Market Services Scheduler"
        shortcut.save()
        
        print(f"✅ Startup shortcut created: {shortcut_path}")
        print("   The scheduler will now start automatically when Windows boots.")
        return True
        
    except ImportError:
        print("❌ Required packages not installed.")
        print("   Run: pip install pywin32 winshell")
        return False
    except Exception as e:
        print(f"❌ Error creating startup shortcut: {e}")
        return False


def remove_startup():
    """Remove from Windows startup"""
    try:
        import winshell
        
        startup_path = winshell.startup()
        shortcut_path = os.path.join(startup_path, "Dhan Market Scheduler.lnk")
        
        if os.path.exists(shortcut_path):
            os.remove(shortcut_path)
            print(f"✅ Startup shortcut removed: {shortcut_path}")
        else:
            print("ℹ️ Startup shortcut not found - nothing to remove.")
        return True
        
    except ImportError:
        print("❌ Required packages not installed.")
        print("   Run: pip install pywin32 winshell")
        return False
    except Exception as e:
        print(f"❌ Error removing startup shortcut: {e}")
        return False


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        if sys.argv[1] == '--install-startup':
            install_startup()
            return
        elif sys.argv[1] == '--remove-startup':
            remove_startup()
            return
        elif sys.argv[1] in ['--help', '-h']:
            print(__doc__)
            return
            
    # Launch the scheduler
    from dhan_trading.scheduler.market_scheduler import main as scheduler_main
    scheduler_main()


if __name__ == "__main__":
    main()
