"""
Test script to verify all DHAN Control Center services and their launch paths
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_services():
    """Test all service configurations"""
    
    services = {
        "FNO Feed Launcher": "launch_fno_feed.py",
        "FNO+MCX Feed": "launch_fno_feed.py --include-commodities",
        "FNO Services Monitor": "python -m dhan_trading.dashboard.fno_services_monitor",
        "FNO Database Writer": "python -m dhan_trading.subscribers.fno_db_writer",
        "Market Scheduler": "launch_market_scheduler.py",
        "Instrument Display": "display_fno_instruments.py",
        "Volume Profile": "python -m dhan_trading.visualizers.volume_profile",
        "Market Breadth": "python -m dhan_trading.visualizers.market_breadth",
        "Tick Chart": "python -m dhan_trading.visualizers.tick_chart",
        "Volume Profile Chart": "python -m dhan_trading.visualizers.volume_profile_chart",
        "Quote Visualizer": "python -m dhan_trading.visualizers.quote_visualizer",
    }
    
    print("=" * 80)
    print("DHAN CONTROL CENTER - SERVICE LAUNCH PATH VERIFICATION")
    print("=" * 80)
    print()
    
    results = []
    failed = []
    
    for service_name, launch_cmd in services.items():
        print(f"Testing: {service_name}")
        print(f"  Command: {launch_cmd}")
        
        # Check if it's a module launch
        if "python -m" in launch_cmd:
            module_path = launch_cmd.replace("python -m ", "").split()[0]
            parts = module_path.split(".")
            
            # Construct file path
            file_path = project_root / "/".join(parts) / "__init__.py"
            if parts[-1] != "dhan_trading" and parts[-1] != "dashboard":
                file_path = project_root / "/".join(parts[:-1]) / (parts[-1] + ".py")
            
            if file_path.exists():
                print(f"  ✅ Module found: {file_path.relative_to(project_root)}")
                results.append((service_name, "✅ PASS"))
            else:
                print(f"  ❌ Module NOT found: {file_path.relative_to(project_root)}")
                failed.append((service_name, str(file_path)))
                results.append((service_name, "❌ FAIL"))
        else:
            # Check if it's a script
            script_name = launch_cmd.split()[0]
            file_path = project_root / script_name
            
            if file_path.exists():
                print(f"  ✅ Script found: {file_path.relative_to(project_root)}")
                results.append((service_name, "✅ PASS"))
            else:
                print(f"  ❌ Script NOT found: {file_path.relative_to(project_root)}")
                failed.append((service_name, str(file_path)))
                results.append((service_name, "❌ FAIL"))
        
        print()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print()
    
    passed = sum(1 for _, result in results if "✅" in result)
    total = len(results)
    
    print(f"Total Services: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {len(failed)}")
    print()
    
    if failed:
        print("FAILED SERVICES:")
        print("-" * 80)
        for service, path in failed:
            print(f"❌ {service}")
            print(f"   Expected path: {path}")
            print()
    
    # Results table
    print("SERVICE STATUS TABLE:")
    print("-" * 80)
    for service, status in results:
        print(f"{service:30s} {status}")
    print("-" * 80)
    
    if len(failed) == 0:
        print("\n✅ ALL SERVICES VERIFIED - Control Center Ready!")
        return 0
    else:
        print(f"\n⚠️  {len(failed)} services need attention")
        return 1

def check_imports():
    """Check if all required modules can be imported"""
    print("\n" + "=" * 80)
    print("IMPORT VERIFICATION")
    print("=" * 80)
    print()
    
    modules_to_check = [
        "dhan_trading",
        "dhan_trading.config",
        "dhan_trading.db_setup",
        "dhan_trading.market_feed",
        "dhan_trading.subscribers",
        "dhan_trading.visualizers",
        "dhan_trading.dashboard",
    ]
    
    import_results = []
    
    for module_name in modules_to_check:
        try:
            __import__(module_name)
            print(f"✅ {module_name}")
            import_results.append((module_name, True))
        except ImportError as e:
            print(f"❌ {module_name}: {str(e)}")
            import_results.append((module_name, False))
    
    print()
    passed_imports = sum(1 for _, success in import_results if success)
    print(f"Imports: {passed_imports}/{len(import_results)} passed")
    
    return all(success for _, success in import_results)

def check_database():
    """Check database connectivity"""
    print("\n" + "=" * 80)
    print("DATABASE CONNECTIVITY CHECK")
    print("=" * 80)
    print()
    
    try:
        from dhan_trading.db_setup import get_engine, DHAN_DB_NAME
        from dhan_trading.config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER
        
        print(f"Database Configuration:")
        print(f"  Host: {MYSQL_HOST}")
        print(f"  Port: {MYSQL_PORT}")
        print(f"  User: {MYSQL_USER}")
        print(f"  Database: {DHAN_DB_NAME}")
        print()
        
        engine = get_engine(DHAN_DB_NAME)
        print(f"✅ Engine created successfully")
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            print(f"✅ Database connection successful")
            print(f"✅ Query executed successfully")
        
        return True
    except Exception as e:
        print(f"❌ Database check failed: {str(e)}")
        return False

def check_redis():
    """Check Redis connectivity"""
    print("\n" + "=" * 80)
    print("REDIS CONNECTIVITY CHECK")
    print("=" * 80)
    print()
    
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        print(f"✅ Redis connection successful")
        print(f"✅ Redis is running on localhost:6379")
        return True
    except Exception as e:
        print(f"⚠️  Redis check: {str(e)}")
        print(f"   Note: Redis is optional for control center testing")
        return False

if __name__ == "__main__":
    print("\n")
    print("=" * 80)
    print("DHAN CONTROL CENTER - COMPREHENSIVE VERIFICATION SUITE".center(80))
    print("=" * 80)
    print()
    
    # Run all tests
    services_ok = test_services() == 0
    imports_ok = check_imports()
    db_ok = check_database()
    redis_ok = check_redis()
    
    # Final summary
    print("\n" + "=" * 80)
    print("FINAL VERIFICATION REPORT")
    print("=" * 80)
    print()
    print(f"Services Configuration:  {'✅ PASS' if services_ok else '❌ FAIL'}")
    print(f"Module Imports:          {'✅ PASS' if imports_ok else '❌ FAIL'}")
    print(f"Database Connectivity:   {'✅ PASS' if db_ok else '❌ FAIL'}")
    print(f"Redis Connectivity:      {'✅ PASS' if redis_ok else '⚠️  OPTIONAL'}")
    print()
    
    if services_ok and imports_ok and db_ok:
        print("🎯 CONTROL CENTER READY FOR PRODUCTION")
        print("   All critical systems verified and operational")
        sys.exit(0)
    else:
        print("⚠️  Some systems need attention before deployment")
        sys.exit(1)
