"""
Quick verification script to check if the service can run locally.
This script checks all prerequisites before you start the service.
"""
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.11+"""
    print("🔍 Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 11:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro} (OK)")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro} (Need 3.11+)")
        return False

def check_dependencies():
    """Check if required packages are installed"""
    print("\n🔍 Checking dependencies...")
    required = [
        'asyncio',
        'pydantic',
        'sqlalchemy',
        'redis',
        'websockets',
        'yfinance',
        'pymysql'
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} (missing)")
            missing.append(package)
    
    if missing:
        print(f"\n   ⚠️  Install missing packages: pip install {' '.join(missing)}")
        return False
    return True

def check_config_file():
    """Check if config file exists"""
    print("\n🔍 Checking configuration files...")
    config_file = Path("config/local_test.yaml")
    if config_file.exists():
        print(f"   ✅ {config_file} exists")
        return True
    else:
        print(f"   ❌ {config_file} not found")
        print("   Create it using the QUICK_START.md guide")
        return False

def check_mysql_connection():
    """Check if MySQL is accessible (optional)"""
    print("\n🔍 Checking MySQL connection (optional)...")
    try:
        import pymysql
        # Try to connect with common defaults
        try:
            conn = pymysql.connect(
                host='localhost',
                user='root',
                password='',
                connect_timeout=3
            )
            conn.close()
            print("   ✅ MySQL is accessible")
            return True
        except Exception as e:
            print(f"   ⚠️  MySQL not accessible (optional for basic test): {str(e)[:50]}")
            return False
    except ImportError:
        print("   ⚠️  pymysql not installed (optional for basic test)")
        return False

def check_port_available(port=8765):
    """Check if WebSocket port is available"""
    print(f"\n🔍 Checking if port {port} is available...")
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
            print(f"   ✅ Port {port} is available")
            return True
    except OSError:
        print(f"   ❌ Port {port} is in use")
        print(f"   Stop the process using port {port} or use a different port in config")
        return False

def check_internet_connection():
    """Check if Yahoo Finance is accessible"""
    print("\n🔍 Checking internet connection (Yahoo Finance)...")
    try:
        import urllib.request
        urllib.request.urlopen('https://query1.finance.yahoo.com', timeout=5)
        print("   ✅ Yahoo Finance is accessible")
        return True
    except Exception as e:
        print(f"   ❌ Cannot reach Yahoo Finance: {str(e)[:50]}")
        return False

def main():
    print("=" * 60)
    print("Real-Time Yahoo Finance Service - Pre-flight Check")
    print("=" * 60)
    
    checks = [
        ("Python Version", check_python_version()),
        ("Dependencies", check_dependencies()),
        ("Config File", check_config_file()),
        ("WebSocket Port", check_port_available()),
        ("Internet/Yahoo", check_internet_connection()),
    ]
    
    # Optional checks
    checks.append(("MySQL (optional)", check_mysql_connection()))
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    required_passed = sum(1 for name, result in checks[:-1] if result)
    total_required = len(checks) - 1
    
    for name, result in checks:
        status = "✅ PASS" if result else "❌ FAIL"
        optional = " (optional)" if "optional" in name else ""
        print(f"{name:20} {status}{optional}")
    
    print("=" * 60)
    
    if required_passed == total_required:
        print("🎉 All required checks passed! You're ready to start the service.")
        print("\nNext steps:")
        print("1. Run: python main.py --config config\\local_test.yaml")
        print("2. Open: examples\\test_websocket_client.html in your browser")
        print("3. Watch: Real-time market data flowing!")
        return 0
    else:
        print(f"⚠️  {total_required - required_passed} required check(s) failed.")
        print("\nPlease fix the issues above before starting the service.")
        print("See QUICK_START.md for detailed instructions.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
