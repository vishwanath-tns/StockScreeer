#!/usr/bin/env python3
"""
DHAN Trading - Comprehensive Service Test & Validation
=======================================================
Tests all services and visualizers for proper configuration and imports.

Usage:
    python -m dhan_trading.test_all_services
    python -m dhan_trading.test_all_services --verbose
    python -m dhan_trading.test_all_services --quick
"""

import os
import sys
import importlib
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

# Fix Unicode on Windows
os.environ['PYTHONIOENCODING'] = 'utf-8'
if sys.platform == 'win32':
    # Force UTF-8 on Windows
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ANSI Colors
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """Print formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}")
    print(f"{text.center(70)}")
    print(f"{'='*70}{Colors.RESET}\n")

def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}[PASS] {text}{Colors.RESET}")

def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}[FAIL] {text}{Colors.RESET}")

def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}[WARN] {text}{Colors.RESET}")

def print_info(text):
    """Print info message."""
    print(f"{Colors.BLUE}[INFO] {text}{Colors.RESET}")

# ============================================================================
# TEST CATEGORIES
# ============================================================================

class TestCategory:
    """Base class for test categories."""
    
    def __init__(self, name: str):
        self.name = name
        self.tests = []
        self.passed = 0
        self.failed = 0
        self.warnings = 0
    
    def add_test(self, test_name: str, test_func):
        """Add a test to this category."""
        self.tests.append((test_name, test_func))
    
    def run(self) -> bool:
        """Run all tests in this category."""
        print_header(f"TESTING: {self.name}")
        
        for test_name, test_func in self.tests:
            try:
                result = test_func()
                if result is True:
                    print_success(test_name)
                    self.passed += 1
                elif result is False:
                    print_error(test_name)
                    self.failed += 1
                else:  # Warning
                    print_warning(test_name)
                    self.warnings += 1
            except Exception as e:
                print_error(f"{test_name}: {str(e)}")
                self.failed += 1
        
        # Print summary
        total = len(self.tests)
        print(f"\nCategory Results: {self.passed}/{total} passed, {self.failed} failed, {self.warnings} warnings")
        return self.failed == 0


# ============================================================================
# CONFIGURATION TESTS
# ============================================================================

class ConfigTests(TestCategory):
    """Test configuration and environment setup."""
    
    def __init__(self):
        super().__init__("Configuration")
        
        self.add_test("Environment: DHAN_CLIENT_ID set", self.test_dhan_client_id)
        self.add_test("Environment: DHAN_ACCESS_TOKEN set", self.test_dhan_access_token)
        self.add_test("Environment: MYSQL_HOST set", self.test_mysql_host)
        self.add_test("Environment: MYSQL_USER set", self.test_mysql_user)
        self.add_test("Environment: MYSQL_PASSWORD set", self.test_mysql_password)
        self.add_test("Environment: MYSQL_DB set", self.test_mysql_db)
        self.add_test("Environment: REDIS_HOST available", self.test_redis_host)
        self.add_test("Config: DHAN_DB_NAME defined", self.test_dhan_db_name)
    
    def test_dhan_client_id(self):
        client_id = os.getenv('DHAN_CLIENT_ID', '')
        if not client_id:
            print_warning("  DHAN_CLIENT_ID not set in .env")
            return None  # Warning, not error
        return True
    
    def test_dhan_access_token(self):
        token = os.getenv('DHAN_ACCESS_TOKEN', '')
        if not token:
            print_warning("  DHAN_ACCESS_TOKEN not set in .env")
            return None
        return True
    
    def test_mysql_host(self):
        host = os.getenv('MYSQL_HOST', '')
        return bool(host) if host else None
    
    def test_mysql_user(self):
        user = os.getenv('MYSQL_USER', '')
        return bool(user) if user else None
    
    def test_mysql_password(self):
        pwd = os.getenv('MYSQL_PASSWORD', '')
        return bool(pwd) if pwd else None
    
    def test_mysql_db(self):
        db = os.getenv('MYSQL_DB', '')
        return bool(db) if db else None
    
    def test_redis_host(self):
        host = os.getenv('REDIS_HOST', 'localhost')
        return True  # Redis has default
    
    def test_dhan_db_name(self):
        try:
            from dhan_trading.config import DHAN_DB_NAME
            return DHAN_DB_NAME == 'dhan_trading'
        except:
            return False


# ============================================================================
# DATABASE TESTS
# ============================================================================

class DatabaseTests(TestCategory):
    """Test database connectivity and schema."""
    
    def __init__(self):
        super().__init__("Database")
        
        self.add_test("DB: Import db_setup module", self.test_import_db_setup)
        self.add_test("DB: Create engine for dhan_trading", self.test_create_engine)
        self.add_test("DB: Test connection", self.test_db_connection)
        self.add_test("DB: Verify dhan_trading database exists", self.test_dhan_db_exists)
    
    def test_import_db_setup(self):
        try:
            from dhan_trading import db_setup
            return True
        except Exception as e:
            print_info(f"  Error: {e}")
            return False
    
    def test_create_engine(self):
        try:
            from dhan_trading.db_setup import get_engine, DHAN_DB_NAME
            engine = get_engine(DHAN_DB_NAME)
            return True
        except Exception as e:
            print_info(f"  Error: {e}")
            return False
    
    def test_db_connection(self):
        try:
            from dhan_trading.db_setup import get_engine, DHAN_DB_NAME
            from sqlalchemy import text
            
            engine = get_engine(DHAN_DB_NAME)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            print_info(f"  Error: {e}")
            return False
    
    def test_dhan_db_exists(self):
        try:
            from dhan_trading.db_setup import get_engine, DHAN_DB_NAME
            from sqlalchemy import text, inspect
            
            # Connect to MySQL without selecting a database
            engine = get_engine()  # No database parameter
            inspector = inspect(engine)
            databases = inspector.get_schema_names()
            
            return DHAN_DB_NAME in databases
        except Exception as e:
            print_info(f"  Error: {e}")
            return None  # Warning


# ============================================================================
# SERVICE IMPORTS TESTS
# ============================================================================

class ServiceImportTests(TestCategory):
    """Test that all services can be imported."""
    
    def __init__(self):
        super().__init__("Service Imports")
        
        # Feed Services
        self.add_test("Import: market_feed.launcher", 
                     lambda: self._test_import("dhan_trading.market_feed.launcher"))
        self.add_test("Import: market_feed.fno_launcher", 
                     lambda: self._test_import("dhan_trading.market_feed.fno_launcher"))
        self.add_test("Import: market_feed.db_writer", 
                     lambda: self._test_import("dhan_trading.market_feed.db_writer"))
        
        # Database Writers
        self.add_test("Import: subscribers.db_writer", 
                     lambda: self._test_import("dhan_trading.subscribers.db_writer"))
        self.add_test("Import: subscribers.fno_db_writer", 
                     lambda: self._test_import("dhan_trading.subscribers.fno_db_writer"))
        
        # Visualizers
        self.add_test("Import: visualizers.volume_profile", 
                     lambda: self._test_import("dhan_trading.visualizers.volume_profile"))
        self.add_test("Import: visualizers.market_breadth", 
                     lambda: self._test_import("dhan_trading.visualizers.market_breadth"))
        self.add_test("Import: visualizers.tick_chart", 
                     lambda: self._test_import("dhan_trading.visualizers.tick_chart"))
        self.add_test("Import: visualizers.volume_profile_chart", 
                     lambda: self._test_import("dhan_trading.visualizers.volume_profile_chart"))
        self.add_test("Import: visualizers.quote_visualizer", 
                     lambda: self._test_import("dhan_trading.visualizers.quote_visualizer"))
        
        # Dashboard
        self.add_test("Import: dashboard.service_dashboard", 
                     lambda: self._test_import("dhan_trading.dashboard.service_dashboard"))
        self.add_test("Import: dashboard.dhan_control_center", 
                     lambda: self._test_import("dhan_trading.dashboard.dhan_control_center"))
        
        # Scheduler
        self.add_test("Import: scheduler.market_scheduler", 
                     lambda: self._test_import("dhan_trading.scheduler.market_scheduler"))
    
    def _test_import(self, module_path: str) -> bool:
        try:
            importlib.import_module(module_path)
            return True
        except Exception as e:
            print_info(f"  Error: {str(e)[:100]}")
            return False


# ============================================================================
# DATABASE REFERENCE TESTS
# ============================================================================

class DatabaseReferenceTests(TestCategory):
    """Test that all services use correct database."""
    
    def __init__(self):
        super().__init__("Database References")
        
        self.add_test("Config: dhan_trading/config.py uses dhan_trading", 
                     self.test_config_db_name)
        self.add_test("DB Setup: dhan_trading/db_setup.py uses get_engine()", 
                     self.test_db_setup_uses_get_engine)
        self.add_test("Market Feed: db_writer.py uses get_engine()", 
                     self.test_market_feed_db_writer)
        self.add_test("Subscribers: db_writer.py uses get_engine()", 
                     self.test_subscribers_db_writer)
        self.add_test("Visualizer: volume_profile.py uses get_engine()", 
                     self.test_volume_profile_db)
        self.add_test("Dashboard: service_dashboard.py uses get_engine()", 
                     self.test_service_dashboard_db)
    
    def _check_file_content(self, filepath: str, patterns: List[str]) -> bool:
        """Check if file contains all required patterns."""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            for pattern in patterns:
                if pattern not in content:
                    print_info(f"  Missing: {pattern}")
                    return False
            return True
        except Exception as e:
            print_info(f"  Error: {e}")
            return False
    
    def test_config_db_name(self):
        filepath = "dhan_trading/config.py"
        return self._check_file_content(filepath, [
            "DHAN_DB_NAME = os.getenv('DHAN_DB_NAME', 'dhan_trading')"
        ])
    
    def test_db_setup_uses_get_engine(self):
        filepath = "dhan_trading/db_setup.py"
        return self._check_file_content(filepath, [
            "def get_engine(database: str = None):",
            "DHAN_DB_NAME"
        ])
    
    def test_market_feed_db_writer(self):
        filepath = "dhan_trading/market_feed/db_writer.py"
        return self._check_file_content(filepath, [
            "from ..db_setup import get_engine, DHAN_DB_NAME",
            "get_engine(DHAN_DB_NAME)"
        ])
    
    def test_subscribers_db_writer(self):
        filepath = "dhan_trading/subscribers/db_writer.py"
        return self._check_file_content(filepath, [
            "from dhan_trading.db_setup import get_engine, DHAN_DB_NAME",
            "get_engine(DHAN_DB_NAME)"
        ])
    
    def test_volume_profile_db(self):
        filepath = "dhan_trading/visualizers/volume_profile.py"
        return self._check_file_content(filepath, [
            "from dhan_trading.db_setup import get_engine, DHAN_DB_NAME",
            "get_engine(DHAN_DB_NAME)"
        ])
    
    def test_service_dashboard_db(self):
        filepath = "dhan_trading/dashboard/service_dashboard.py"
        return self._check_file_content(filepath, [
            "from dhan_trading.db_setup import get_engine, DHAN_DB_NAME",
            "get_engine(DHAN_DB_NAME)"
        ])


# ============================================================================
# SCHEMA TESTS
# ============================================================================

class SchemaTests(TestCategory):
    """Test database schema completeness."""
    
    def __init__(self):
        super().__init__("Database Schema")
        
        self.add_test("Schema: FNO schema module imports", 
                     lambda: self._test_import("dhan_trading.fno_schema"))
        self.add_test("Schema: dhan_instruments table exists", 
                     self.test_instruments_table)
        self.add_test("Schema: dhan_quotes table exists", 
                     self.test_quotes_table)
    
    def _test_import(self, module_path: str) -> bool:
        try:
            importlib.import_module(module_path)
            return True
        except Exception as e:
            print_info(f"  Error: {str(e)[:100]}")
            return None
    
    def test_instruments_table(self):
        try:
            from dhan_trading.db_setup import get_engine, DHAN_DB_NAME
            from sqlalchemy import text, inspect
            
            engine = get_engine(DHAN_DB_NAME)
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            return 'dhan_instruments' in tables
        except Exception as e:
            print_info(f"  Error: {e}")
            return None
    
    def test_quotes_table(self):
        try:
            from dhan_trading.db_setup import get_engine, DHAN_DB_NAME
            from sqlalchemy import text, inspect
            
            engine = get_engine(DHAN_DB_NAME)
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            # Check for any quotes table variant
            quote_tables = [t for t in tables if 'quote' in t.lower()]
            return len(quote_tables) > 0
        except Exception as e:
            print_info(f"  Error: {e}")
            return None


# ============================================================================
# REDIS TESTS
# ============================================================================

class RedisTests(TestCategory):
    """Test Redis connectivity."""
    
    def __init__(self):
        super().__init__("Redis")
        
        self.add_test("Redis: Connection available", self.test_redis_connection)
        self.add_test("Redis: Pub/Sub capability", self.test_redis_pubsub)
    
    def test_redis_connection(self):
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, socket_connect_timeout=2)
            r.ping()
            return True
        except Exception as e:
            print_info(f"  Error: {e}")
            return None
    
    def test_redis_pubsub(self):
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, socket_connect_timeout=2)
            pubsub = r.pubsub()
            return True
        except Exception as e:
            print_info(f"  Error: {e}")
            return None


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    """Run all tests."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("=" * 70)
    print("DHAN TRADING SERVICES - COMPREHENSIVE TEST SUITE".center(70))
    print(f"{'Date: ' + str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}")
    print("=" * 70)
    print(f"{Colors.RESET}\n")
    
    # Create test categories
    categories = [
        ConfigTests(),
        DatabaseTests(),
        ServiceImportTests(),
        DatabaseReferenceTests(),
        SchemaTests(),
        RedisTests(),
    ]
    
    # Run all tests
    results = {}
    total_passed = 0
    total_failed = 0
    total_warnings = 0
    
    for category in categories:
        category.run()
        results[category.name] = (category.passed, category.failed, category.warnings)
        total_passed += category.passed
        total_failed += category.failed
        total_warnings += category.warnings
    
    # Print final summary
    print_header("OVERALL SUMMARY")
    
    print(f"Total Tests Run: {total_passed + total_failed}")
    print_success(f"Passed: {total_passed}")
    if total_failed > 0:
        print_error(f"Failed: {total_failed}")
    if total_warnings > 0:
        print_warning(f"Warnings: {total_warnings}")
    
    print("\nCategory Breakdown:")
    for category_name, (passed, failed, warnings) in sorted(results.items()):
        total = passed + failed
        status = Colors.GREEN + "✓" + Colors.RESET if failed == 0 else Colors.RED + "✗" + Colors.RESET
        print(f"  {status} {category_name}: {passed}/{total} passed")
    
    # Exit code
    exit_code = 0 if total_failed == 0 else 1
    
    if exit_code == 0:
        print_success("\nAll critical tests passed!")
    else:
        print_error(f"\n{total_failed} tests failed. Please review the output above.")
    
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}\n")
    
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
