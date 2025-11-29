#!/usr/bin/env python
"""
Quick E2E Test for Parallel Rankings System

Tests the complete flow: enqueue job -> worker processes -> save to DB
"""

import sys
import time
import threading
from datetime import date, timedelta

# Add project root
sys.path.insert(0, '.')

from ranking.parallel import RedisManager, RankingWorker, JobType
from ranking.parallel.job_models import RankingJob


def main():
    print("=" * 50)
    print("Quick E2E Test - Parallel Rankings System")
    print("=" * 50)
    print()
    
    # Clear queue
    manager = RedisManager()
    manager.clear_queue()
    
    # Create one job for a recent date - use ALL symbols (empty list)
    calc_date = date(2025, 11, 25)  # A few days ago
    
    print(f"1. Creating job for {calc_date}...")
    print(f"   Symbols: ALL (empty list = all symbols)")
    job_data = {
        'job_type': JobType.CALCULATE_DATE.value,
        'calculation_date': calc_date.isoformat(),
        'symbols': [],  # Empty = all symbols
        'batch_id': 'test_batch'
    }
    job_id = manager.enqueue_job(job_data)
    print(f"   Created job: {job_id}")
    
    stats = manager.get_queue_stats()
    print(f"   Queue: {stats}")
    
    # Start worker in background thread
    print()
    print("2. Processing job with worker...")
    worker = RankingWorker('test_worker')
    worker_result = [None]
    
    def run_one_job():
        try:
            job = manager.dequeue_job(timeout=5)
            if job:
                rjob = RankingJob.from_dict(job)
                result = worker._process_job(rjob)
                worker_result[0] = result
                manager.complete_job(job['job_id'], result)
        except Exception as e:
            worker_result[0] = {'error': str(e)}
            import traceback
            traceback.print_exc()
    
    t = threading.Thread(target=run_one_job)
    t.start()
    t.join(timeout=120)
    
    print()
    print("3. Result:")
    if worker_result[0]:
        r = worker_result[0]
        if r.get('success'):
            print(f"   ✓ SUCCESS!")
            print(f"   - Symbols ranked: {r.get('symbols_ranked', 0)}")
            print(f"   - Saved to DB: {r.get('symbols_saved', 0)}")
            print(f"   - Calculation date: {r.get('calculation_date')}")
            print(f"   - Top symbols: {r.get('top_5', [])}")
        else:
            print(f"   ✗ FAILED: {r.get('error', 'Unknown error')}")
    else:
        print("   ✗ No result (timeout or error)")
    
    stats = manager.get_queue_stats()
    print()
    print(f"4. Final queue stats: {stats}")
    
    # Verify in database
    print()
    print("5. Verifying in database...")
    try:
        from ranking.db.schema import get_ranking_engine
        from sqlalchemy import text
        
        engine = get_ranking_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT symbol, ranking_date, rs_rating, momentum_score, 
                       composite_score, composite_rank
                FROM stock_rankings_history
                WHERE ranking_date = :calc_date
                ORDER BY composite_rank
                LIMIT 5
            """), {"calc_date": calc_date}).fetchall()
            
            if result:
                print("   Rankings saved:")
                for row in result:
                    print(f"     {row[5]:3d}. {row[0]:10s} RS={row[2]:5.1f} Mom={row[3]:5.1f} Comp={row[4]:5.1f}")
            else:
                print("   No rankings found for this date")
    except Exception as e:
        print(f"   ✗ DB Error: {e}")
    
    print()
    print("=" * 50)
    print("Test Complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
