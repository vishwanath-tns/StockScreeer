#!/usr/bin/env python3
"""
DHAN Trading - Quick Service Launcher & Validator
==================================================
Launch and test services with a single command.

Usage:
    python quick_launch_dhan.py                    # List all services
    python quick_launch_dhan.py --test             # Run all tests
    python quick_launch_dhan.py --launch control   # Launch control center
    python quick_launch_dhan.py --launch feed      # Launch FNO feed
    python quick_launch_dhan.py --launch writer    # Launch DB writer
    python quick_launch_dhan.py --launch viz       # Launch visualizer menu
    python quick_launch_dhan.py --health           # Health check all services
"""

import sys
import os
import subprocess
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header():
    print(f"{Colors.BOLD}{Colors.CYAN}")
    print("=" * 70)
    print("DHAN TRADING - SERVICE LAUNCHER".center(70))
    print("=" * 70)
    print(Colors.RESET)

def print_section(title):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{title}{Colors.RESET}")
    print("-" * 70)

def print_service(num, name, description, command):
    print(f"{Colors.CYAN}[{num}]{Colors.RESET} {Colors.BOLD}{name}{Colors.RESET}")
    print(f"    {description}")
    print(f"    {Colors.YELLOW}$ {command}{Colors.RESET}")

def list_services():
    """List all available services."""
    print_header()
    
    print_section("CORE SERVICES")
    print_service(1, "DHAN Control Center", 
                 "Unified hub for all services (recommended)",
                 "python launch_dhan_control_center.py")
    
    print_service(2, "Service Dashboard", 
                 "Detailed service monitoring and control",
                 "python -m dhan_trading.dashboard.service_dashboard")
    
    print_section("MARKET FEED SERVICES")
    print_service(3, "Market Feed (Spot)", 
                 "NSE equity quotes - NIFTY 50, BSE 100, etc.",
                 "python -m dhan_trading.market_feed.launcher --force")
    
    print_service(4, "FNO Feed Launcher", 
                 "FNO derivatives - 128 instruments (NIFTY/BANKNIFTY futures + options)",
                 "python -m dhan_trading.market_feed.fno_launcher --force")
    
    print_section("DATABASE WRITERS")
    print_service(5, "Database Writer (Spot)", 
                 "Persists NSE equity quotes to MySQL dhan_trading database",
                 "python -m dhan_trading.subscribers.db_writer")
    
    print_service(6, "FNO Database Writer", 
                 "Persists FNO derivatives quotes to MySQL dhan_trading database",
                 "python -m dhan_trading.subscribers.fno_db_writer")
    
    print_section("VISUALIZERS (Real-time Analysis)")
    print_service(7, "Volume Profile", 
                 "Volume distribution by price level - POC, Value Area",
                 "python -m dhan_trading.visualizers.volume_profile")
    
    print_service(8, "Market Breadth", 
                 "NIFTY 50 advances vs declines - market sentiment",
                 "python -m dhan_trading.visualizers.market_breadth")
    
    print_service(9, "Tick Chart", 
                 "OHLC charts by tick count (10/25/50/100/200 ticks)",
                 "python -m dhan_trading.visualizers.tick_chart")
    
    print_service(10, "Volume Profile Chart", 
                  "Time-series volume profiles - 5-minute aggregations",
                  "python -m dhan_trading.visualizers.volume_profile_chart")
    
    print_service(11, "Quote Visualizer", 
                  "Terminal-based real-time quote display",
                  "python -m dhan_trading.visualizers.quote_visualizer")
    
    print_section("SCHEDULER")
    print_service(12, "Market Scheduler", 
                 "Auto-start services at 8:55 AM, auto-stop at market close",
                 "python -m dhan_trading.scheduler.market_scheduler")
    
    print_section("TESTING & VALIDATION")
    print_service(13, "Run All Tests (36 tests)", 
                 "Comprehensive validation of all services",
                 "python -m dhan_trading.test_all_services")
    
    print_section("RECOMMENDED WORKFLOW")
    print(f"""
{Colors.BOLD}1. First Time Setup:{Colors.RESET}
   python -m dhan_trading.test_all_services          # Verify all systems
   
{Colors.BOLD}2. Start Services (Option A - Using Control Center):{Colors.RESET}
   Terminal 1: python launch_dhan_control_center.py  # Launch unified hub
   
   From Control Center GUI:
   - Click "Start All" to launch all services
   - Monitor status in real-time
   - View logs and statistics
   
{Colors.BOLD}3. Start Services (Option B - Manual)::{Colors.RESET}
   Terminal 1: python -m dhan_trading.market_feed.launcher --force
   Terminal 2: python -m dhan_trading.subscribers.db_writer
   Terminal 3: python -m dhan_trading.visualizers.volume_profile
   
{Colors.BOLD}4. Monitor Performance:{Colors.RESET}
   python -m dhan_trading.dashboard.service_dashboard
   
{Colors.BOLD}5. Stop Services:{Colors.RESET}
   Press Ctrl+C in each terminal, or
   Use Control Center "Stop All" button
""")

def run_tests():
    """Run the test suite."""
    print_header()
    print(f"{Colors.BOLD}Running Comprehensive Test Suite...{Colors.RESET}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "dhan_trading.test_all_services"],
            cwd=str(Path(__file__).parent),
            capture_output=False
        )
        return result.returncode == 0
    except Exception as e:
        print(f"{Colors.RED}Error running tests: {e}{Colors.RESET}")
        return False

def health_check():
    """Perform health check on all services."""
    print_header()
    print_section("SYSTEM HEALTH CHECK")
    
    checks = []
    
    # Configuration
    print(f"\n{Colors.BOLD}Configuration:{Colors.RESET}")
    checks.append(("DHAN_CLIENT_ID", bool(os.getenv('DHAN_CLIENT_ID'))))
    checks.append(("DHAN_ACCESS_TOKEN", bool(os.getenv('DHAN_ACCESS_TOKEN'))))
    checks.append(("MYSQL_HOST", bool(os.getenv('MYSQL_HOST'))))
    checks.append(("MYSQL_DB", bool(os.getenv('MYSQL_DB'))))
    
    # Database
    print(f"\n{Colors.BOLD}Database Connectivity:{Colors.RESET}")
    try:
        from dhan_trading.db_setup import get_engine, DHAN_DB_NAME
        from sqlalchemy import text
        
        engine = get_engine(DHAN_DB_NAME)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks.append(("MySQL dhan_trading connection", True))
    except Exception as e:
        checks.append(("MySQL dhan_trading connection", False))
    
    # Redis
    print(f"\n{Colors.BOLD}Redis Connectivity:{Colors.RESET}")
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, socket_connect_timeout=2)
        r.ping()
        checks.append(("Redis connection", True))
    except:
        checks.append(("Redis connection", False))
    
    # Service Imports
    print(f"\n{Colors.BOLD}Service Imports:{Colors.RESET}")
    services = [
        "dhan_trading.market_feed.launcher",
        "dhan_trading.market_feed.fno_launcher",
        "dhan_trading.subscribers.db_writer",
        "dhan_trading.visualizers.volume_profile",
        "dhan_trading.dashboard.dhan_control_center",
    ]
    
    for service in services:
        try:
            __import__(service)
            checks.append((service.split('.')[-1], True))
        except:
            checks.append((service.split('.')[-1], False))
    
    # Print results
    print(f"\n{Colors.BOLD}Results:{Colors.RESET}")
    passed = 0
    for name, status in checks:
        if status:
            print(f"{Colors.GREEN}[PASS]{Colors.RESET} {name}")
            passed += 1
        else:
            print(f"{Colors.RED}[FAIL]{Colors.RESET} {name}")
    
    print(f"\n{Colors.BOLD}Summary: {passed}/{len(checks)} checks passed{Colors.RESET}")
    return passed == len(checks)

def launch_service(service_type):
    """Launch a specific service."""
    print_header()
    
    commands = {
        'control': ['python', 'launch_dhan_control_center.py'],
        'feed': ['python', '-m', 'dhan_trading.market_feed.launcher', '--force'],
        'fno': ['python', '-m', 'dhan_trading.market_feed.fno_launcher', '--force'],
        'writer': ['python', '-m', 'dhan_trading.subscribers.db_writer'],
        'fno-writer': ['python', '-m', 'dhan_trading.subscribers.fno_db_writer'],
        'viz': ['python', '-m', 'dhan_trading.visualizers.volume_profile'],
        'dashboard': ['python', '-m', 'dhan_trading.dashboard.service_dashboard'],
    }
    
    if service_type not in commands:
        print(f"{Colors.RED}Unknown service: {service_type}{Colors.RESET}")
        print(f"Available services: {', '.join(commands.keys())}")
        return False
    
    print(f"{Colors.BOLD}Launching {service_type}...{Colors.RESET}\n")
    
    try:
        subprocess.run(commands[service_type], cwd=str(Path(__file__).parent))
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Service stopped by user{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.RED}Error launching service: {e}{Colors.RESET}")
        return False
    
    return True

def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        
        if arg == '--test':
            success = run_tests()
            sys.exit(0 if success else 1)
        
        elif arg == '--health':
            success = health_check()
            sys.exit(0 if success else 1)
        
        elif arg == '--launch' and len(sys.argv) > 2:
            success = launch_service(sys.argv[2])
            sys.exit(0 if success else 1)
        
        else:
            print(f"{Colors.RED}Unknown argument: {arg}{Colors.RESET}\n")
            list_services()
    else:
        list_services()

if __name__ == '__main__':
    main()
