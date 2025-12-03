"""
Stock Alert System - Launcher Script

This is a convenience launcher for the Stock Alert System.
Place this file in the main project directory for easy access.

Usage:
    python stock_alerts_launcher.py              # Start full system (API + workers)
    python stock_alerts_launcher.py api          # Start API server only
    python stock_alerts_launcher.py worker       # Start workers only
    python stock_alerts_launcher.py init-db      # Initialize database
    python stock_alerts_launcher.py demo         # Run demo (no Redis needed)
    python stock_alerts_launcher.py gui          # Start desktop GUI
    python stock_alerts_launcher.py check        # Check dependencies
"""

import sys
import os

# Add the stock_alerts package to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_dependencies():
    """Check if all required dependencies are installed."""
    print("Checking dependencies...\n")
    
    required = [
        ('redis', 'redis'),
        ('fastapi', 'fastapi'),
        ('uvicorn', 'uvicorn'),
        ('aiomysql', 'aiomysql'),
        ('aiohttp', 'aiohttp'),
        ('yfinance', 'yfinance'),
        ('pandas', 'pandas'),
        ('sqlalchemy', 'sqlalchemy'),
        ('pymysql', 'pymysql'),
        ('dotenv', 'python-dotenv'),
        ('bcrypt', 'bcrypt'),
        ('jwt', 'PyJWT'),
    ]
    
    optional = [
        ('win10toast', 'win10toast'),
        ('plyer', 'plyer'),
    ]
    
    missing = []
    missing_optional = []
    
    for module, package in required:
        try:
            __import__(module)
            print(f"  ✓ {package}")
        except ImportError:
            missing.append(package)
            print(f"  ✗ {package} (MISSING)")
    
    print("\nOptional dependencies:")
    for module, package in optional:
        try:
            __import__(module)
            print(f"  ✓ {package}")
        except ImportError:
            missing_optional.append(package)
            print(f"  ○ {package} (optional)")
    
    print()
    
    if missing:
        print("Missing required packages. Install with:")
        print(f"  pip install {' '.join(missing)}")
        print()
        return False
    
    print("All required dependencies installed!")
    if missing_optional:
        print(f"\nOptional: pip install {' '.join(missing_optional)}")
    
    return True


def run_gui():
    """Start the desktop GUI."""
    try:
        from stock_alerts.gui.main_window import run_gui as gui_main
        gui_main()
    except ImportError as e:
        print(f"Error importing GUI: {e}")
        print("\nMake sure PyQt6 is installed:")
        print("  pip install PyQt6")
        sys.exit(1)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Stock Alert System Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python stock_alerts_launcher.py              Start full system
    python stock_alerts_launcher.py api          Start API only
    python stock_alerts_launcher.py demo         Demo mode (no Redis)
    python stock_alerts_launcher.py gui          Desktop GUI
    python stock_alerts_launcher.py check        Check dependencies
        """
    )
    
    parser.add_argument(
        'command',
        nargs='?',
        default='all',
        choices=['api', 'worker', 'all', 'init-db', 'demo', 'gui', 'check'],
        help='Command to run'
    )
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Handle special commands
    if args.command == 'check':
        check_dependencies()
        return
    
    if args.command == 'gui':
        run_gui()
        return
    
    # Run main module
    sys.argv = [sys.argv[0], args.command]
    if args.debug:
        sys.argv.append('--debug')
    
    from stock_alerts.main import main as stock_alerts_main
    stock_alerts_main()


if __name__ == '__main__':
    main()
