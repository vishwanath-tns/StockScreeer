#!/usr/bin/env python
"""
Parallel Rankings Builder Launcher

Provides easy launch options for the parallel historical rankings system.
Can launch GUI mode, workers-only, or dispatcher-only.

Usage:
    python launch_parallel_rankings.py              # Launch GUI (default)
    python launch_parallel_rankings.py gui          # Launch GUI
    python launch_parallel_rankings.py workers 4    # Launch 4 workers
    python launch_parallel_rankings.py dispatcher   # Launch dispatcher
    python launch_parallel_rankings.py status       # Check system status
    python launch_parallel_rankings.py test         # Run integration test
"""

import sys
import os
import time
import argparse
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def check_prerequisites():
    """Check all prerequisites are met."""
    print("=" * 60)
    print("Checking Prerequisites")
    print("=" * 60)
    
    issues = []
    
    # 1. Check Redis
    print("\n1. Checking Redis...")
    try:
        from ranking.parallel import check_redis_available
        if check_redis_available():
            print("   ✓ Redis is available")
        else:
            print("   ✗ Redis is NOT available")
            issues.append("Redis is not running. Start Redis with: redis-server")
    except Exception as e:
        print(f"   ✗ Redis check failed: {e}")
        issues.append(f"Redis check error: {e}")
    
    # 2. Check Database
    print("\n2. Checking Database...")
    try:
        from ranking.db.schema import get_ranking_engine
        from sqlalchemy import text
        engine = get_ranking_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).fetchone()
            print("   ✓ Database is connected")
    except Exception as e:
        print(f"   ✗ Database error: {e}")
        issues.append(f"Database connection error: {e}")
    
    # 3. Check required tables
    print("\n3. Checking required tables...")
    try:
        from sqlalchemy import text
        engine = get_ranking_engine()
        with engine.connect() as conn:
            # Check yfinance_daily_quotes
            result = conn.execute(text("SELECT COUNT(*) FROM yfinance_daily_quotes")).fetchone()
            print(f"   ✓ yfinance_daily_quotes: {result[0]:,} rows")
            
            # Check stock_rankings_history
            try:
                result = conn.execute(text("SELECT COUNT(*) FROM stock_rankings_history")).fetchone()
                print(f"   ✓ stock_rankings_history: {result[0]:,} rows")
            except:
                print("   ⚠ stock_rankings_history table may not exist (will be created)")
            
            # Check date range
            result = conn.execute(text("""
                SELECT MIN(date), MAX(date) 
                FROM yfinance_daily_quotes
            """)).fetchone()
            print(f"   ✓ Date range: {result[0]} to {result[1]}")
    except Exception as e:
        print(f"   ⚠ Table check warning: {e}")
    
    # 4. Check Python packages
    print("\n4. Checking Python packages...")
    required_packages = ['redis', 'pandas', 'sqlalchemy', 'pymysql']
    for pkg in required_packages:
        try:
            __import__(pkg)
            print(f"   ✓ {pkg}")
        except ImportError:
            print(f"   ✗ {pkg} is not installed")
            issues.append(f"Package {pkg} is not installed. Run: pip install {pkg}")
    
    # Summary
    print("\n" + "=" * 60)
    if issues:
        print("⚠ Prerequisites check found issues:")
        for issue in issues:
            print(f"  • {issue}")
        return False
    else:
        print("✓ All prerequisites met!")
        return True


def launch_gui():
    """Launch the parallel rankings GUI."""
    print("\nLaunching Parallel Rankings GUI...")
    print("-" * 40)
    
    from ranking.parallel.parallel_gui import ParallelRankingsGUI
    gui = ParallelRankingsGUI()
    gui.run()


def launch_workers(num_workers: int):
    """Launch worker processes."""
    print(f"\nLaunching {num_workers} worker processes...")
    print("-" * 40)
    
    from ranking.parallel.worker import main as worker_main
    
    # Override sys.argv for the worker
    original_argv = sys.argv
    sys.argv = ['worker', '--workers', str(num_workers)]
    
    try:
        worker_main()
    finally:
        sys.argv = original_argv


def launch_dispatcher(years: int = 3, batch_size: int = 1000):
    """Launch the dispatcher."""
    print(f"\nLaunching Dispatcher (years={years}, batch_size={batch_size})...")
    print("-" * 40)
    
    from ranking.parallel.dispatcher import main as dispatcher_main
    
    # Override sys.argv for the dispatcher
    original_argv = sys.argv
    sys.argv = ['dispatcher', '--years', str(years), '--batch-size', str(batch_size)]
    
    try:
        dispatcher_main()
    finally:
        sys.argv = original_argv


def show_status():
    """Show system status."""
    print("\n" + "=" * 60)
    print("Parallel Rankings System Status")
    print("=" * 60)
    
    # Redis status
    print("\n1. Redis Status:")
    try:
        from ranking.parallel import RedisManager
        manager = RedisManager()
        
        stats = manager.get_queue_stats()
        print(f"   Pending jobs:    {stats.get('pending', 0):,}")
        print(f"   Processing jobs: {stats.get('processing', 0):,}")
        print(f"   Completed jobs:  {stats.get('completed', 0):,}")
        print(f"   Failed jobs:     {stats.get('failed', 0):,}")
        
        # Active workers
        workers = manager.get_active_workers()
        print(f"\n   Active workers: {len(workers)}")
        for w in workers:
            print(f"      • {w}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Database status
    print("\n2. Rankings Database Status:")
    try:
        from ranking.db.schema import get_ranking_engine
        from sqlalchemy import text
        
        engine = get_ranking_engine()
        with engine.connect() as conn:
            # Count rankings
            result = conn.execute(text("SELECT COUNT(*) FROM stock_rankings_history")).fetchone()
            print(f"   Total historical rankings: {result[0]:,}")
            
            # Date range
            result = conn.execute(text("""
                SELECT MIN(ranking_date), MAX(ranking_date) 
                FROM stock_rankings_history
            """)).fetchone()
            if result[0]:
                print(f"   Date range: {result[0]} to {result[1]}")
            
            # Recent activity
            result = conn.execute(text("""
                SELECT ranking_date, COUNT(*) as cnt
                FROM stock_rankings_history
                GROUP BY ranking_date
                ORDER BY ranking_date DESC
                LIMIT 5
            """)).fetchall()
            if result:
                print("\n   Recent calculations:")
                for row in result:
                    print(f"      {row[0]}: {row[1]} symbols")
    except Exception as e:
        print(f"   ⚠ Error: {e}")


def run_integration_test():
    """Run a quick integration test."""
    print("\n" + "=" * 60)
    print("Running Integration Test")
    print("=" * 60)
    
    # Test 1: Redis queue operations
    print("\n1. Testing Redis queue operations...")
    try:
        from ranking.parallel import RedisManager, RankingJob, JobStatus, JobType
        from datetime import date
        
        manager = RedisManager()
        
        # Clear any existing test data
        manager.clear_queue()
        
        # Create test job using correct fields
        test_job = RankingJob(
            job_type=JobType.CALCULATE_DATE,
            calculation_date=date.today(),
            symbols=["TEST"],
            job_id="test_001",
            status=JobStatus.PENDING,
            priority=5
        )
        
        # Enqueue using dict
        job_data = {
            "job_id": test_job.job_id,
            "job_type": test_job.job_type.value,
            "symbols": test_job.symbols,
            "calculation_date": test_job.calculation_date.isoformat(),
            "status": test_job.status.value,
            "priority": test_job.priority
        }
        manager.enqueue_job(job_data)
        
        # Check stats
        stats = manager.get_queue_stats()
        assert stats['pending'] == 1, f"Expected 1 pending, got {stats['pending']}"
        print("   ✓ Job enqueued successfully")
        
        # Dequeue
        dequeued = manager.dequeue_job(timeout=1)
        assert dequeued is not None, "Failed to dequeue job"
        print(f"   ✓ Job dequeued: {dequeued.get('job_id', 'unknown')}")
        
        # Complete
        manager.complete_job(dequeued['job_id'], {"test": True})
        stats = manager.get_queue_stats()
        assert stats['completed'] == 1, f"Expected 1 completed, got {stats['completed']}"
        print("   ✓ Job completed successfully")
        
        # Cleanup
        manager.clear_queue()
        print("   ✓ Queue cleared")
        
    except Exception as e:
        print(f"   ✗ Redis test failed: {e}")
        return False
    
    # Test 2: Database access
    print("\n2. Testing database access...")
    try:
        from ranking.db.schema import get_ranking_engine
        from sqlalchemy import text
        
        engine = get_ranking_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(DISTINCT symbol) FROM yfinance_daily_quotes")).fetchone()
            print(f"   ✓ Found {result[0]} symbols in database")
    except Exception as e:
        print(f"   ✗ Database test failed: {e}")
        return False
    
    # Test 3: Ranking calculations (dry run)
    print("\n3. Testing ranking calculation logic...")
    try:
        from ranking.parallel.worker import RankingWorker
        
        # Just instantiate to test imports
        worker = RankingWorker("test_worker")
        print("   ✓ Worker initialized successfully")
        print("   (Skipping actual calculation - use full run for that)")
    except Exception as e:
        print(f"   ✗ Worker test failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✓ All integration tests passed!")
    print("=" * 60)
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Parallel Rankings Builder Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python launch_parallel_rankings.py              Launch GUI (default)
  python launch_parallel_rankings.py gui          Launch GUI
  python launch_parallel_rankings.py workers 4    Launch 4 worker processes
  python launch_parallel_rankings.py dispatcher   Launch dispatcher for 3 years
  python launch_parallel_rankings.py status       Show system status
  python launch_parallel_rankings.py test         Run integration test
  python launch_parallel_rankings.py check        Check prerequisites only
        """
    )
    
    parser.add_argument(
        'command',
        nargs='?',
        default='gui',
        choices=['gui', 'workers', 'dispatcher', 'status', 'test', 'check'],
        help='Command to run (default: gui)'
    )
    
    parser.add_argument(
        'num_workers',
        nargs='?',
        type=int,
        default=4,
        help='Number of workers (for workers command, default: 4)'
    )
    
    parser.add_argument(
        '--years',
        type=int,
        default=3,
        help='Years of history (for dispatcher, default: 3)'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Batch size (for dispatcher, default: 1000)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  Parallel Rankings Builder")
    print("  Event-driven architecture with Redis")
    print("=" * 60)
    
    # Run prerequisites check for most commands
    if args.command in ['gui', 'workers', 'dispatcher', 'test']:
        if not check_prerequisites():
            print("\n⚠ Fix the issues above before continuing.")
            if args.command != 'test':
                return 1
    
    # Execute command
    if args.command == 'gui':
        launch_gui()
    elif args.command == 'workers':
        launch_workers(args.num_workers)
    elif args.command == 'dispatcher':
        launch_dispatcher(args.years, args.batch_size)
    elif args.command == 'status':
        show_status()
    elif args.command == 'test':
        if not run_integration_test():
            return 1
    elif args.command == 'check':
        if not check_prerequisites():
            return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
