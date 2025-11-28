#!/usr/bin/env python3
"""
Monitor Nifty 500 Momentum Scan Progress
========================================

Real-time monitoring of the Nifty 500 momentum scanning progress.
Shows coverage statistics and completion status.
"""

import sys
import os
sys.path.append('.')

import time
from datetime import datetime
from services.market_breadth_service import get_engine
from sqlalchemy import text
from nifty500_stocks_list import NIFTY_500_STOCKS

def monitor_nifty500_progress():
    """Monitor the progress of Nifty 500 momentum scanning"""
    
    print("📊 NIFTY 500 MOMENTUM SCAN MONITOR")
    print("=" * 50)
    print(f"🎯 Target: 500 stocks × 6 durations = 3,000 total records")
    print(f"⏰ Started monitoring: {datetime.now().strftime('%H:%M:%S')}")
    print()
    
    engine = get_engine()
    start_time = time.time()
    last_total = 0
    
    try:
        while True:
            with engine.connect() as conn:
                # Get current progress
                query = text("""
                    SELECT 
                        duration_type,
                        COUNT(*) as count
                    FROM momentum_analysis 
                    WHERE DATE(calculation_date) = CURDATE()
                        AND symbol IN :nifty500_symbols
                    GROUP BY duration_type
                    ORDER BY duration_type
                """)
                
                nifty500_tuple = tuple(NIFTY_500_STOCKS)
                result = conn.execute(query, {"nifty500_symbols": nifty500_tuple})
                stats = result.fetchall()
                
                # Calculate totals
                current_total = sum(count for _, count in stats)
                expected_total = 3000
                completion_pct = (current_total / expected_total) * 100
                
                # Calculate rate
                elapsed = time.time() - start_time
                if elapsed > 0 and current_total > last_total:
                    rate = (current_total - last_total) / (elapsed if elapsed > 60 else 60)  # per minute
                    eta_minutes = (expected_total - current_total) / rate if rate > 0 else 0
                else:
                    rate = 0
                    eta_minutes = 0
                
                # Clear screen and show progress
                os.system('cls' if os.name == 'nt' else 'clear')
                print("📊 NIFTY 500 MOMENTUM SCAN PROGRESS")
                print("=" * 50)
                print(f"⏰ {datetime.now().strftime('%H:%M:%S')} | Elapsed: {int(elapsed/60):02d}:{int(elapsed%60):02d}")
                print()
                
                # Progress bar
                bar_width = 40
                filled = int(bar_width * completion_pct / 100)
                bar = "█" * filled + "░" * (bar_width - filled)
                print(f"Progress: [{bar}] {completion_pct:5.1f}%")
                print(f"Records:  {current_total:4d} / {expected_total:4d}")
                
                if rate > 0:
                    print(f"Rate:     {rate:5.1f} records/min")
                    print(f"ETA:      {int(eta_minutes):2d}:{int((eta_minutes % 1) * 60):02d} minutes")
                print()
                
                # Duration breakdown
                print("📈 Duration Breakdown:")
                print("-" * 30)
                duration_order = ['1W', '1M', '3M', '6M', '9M', '12M']
                duration_dict = dict(stats)
                
                for duration in duration_order:
                    count = duration_dict.get(duration, 0)
                    pct = (count / 500) * 100
                    bar_len = int(20 * pct / 100)
                    duration_bar = "█" * bar_len + "░" * (20 - bar_len)
                    print(f"{duration:3}: [{duration_bar}] {count:3d}/500 ({pct:4.1f}%)")
                
                print()
                
                # Status
                if completion_pct >= 100:
                    print("🎉 NIFTY 500 MOMENTUM SCAN COMPLETE!")
                    print("✅ All durations calculated for all 500 stocks")
                    break
                elif completion_pct >= 90:
                    print("🚀 Almost complete! Final stocks being processed...")
                elif completion_pct >= 70:
                    print("⚡ Making good progress...")
                elif completion_pct >= 50:
                    print("💪 Halfway there...")
                elif completion_pct >= 25:
                    print("🔄 Processing in progress...")
                else:
                    print("🏃 Scan is starting up...")
                
                print()
                print("Press Ctrl+C to exit monitor")
                
                last_total = current_total
                start_time = time.time()  # Reset for next rate calculation
                
                time.sleep(30)  # Update every 30 seconds
                
    except KeyboardInterrupt:
        print(f"\n📊 Monitoring stopped. Current progress: {completion_pct:.1f}%")
    except Exception as e:
        print(f"\n❌ Error monitoring progress: {e}")

if __name__ == "__main__":
    monitor_nifty500_progress()