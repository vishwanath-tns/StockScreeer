#!/usr/bin/env python3
"""
Test script for parallel trends processing.
"""

import time
from services.trends_service import scan_all_historical_trends_parallel

def test_progress_callback(message):
    """Simple progress callback for testing"""
    print(f"Progress: {message}")

def main():
    print("Testing parallel historical trends scanning...")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        # Test with 2 workers for this test
        results = scan_all_historical_trends_parallel(
            max_workers=2,
            progress_callback=test_progress_callback
        )
        
        elapsed = time.time() - start_time
        print(f"\nParallel scan completed successfully!")
        print(f"Results: {results}")
        print(f"Time taken: {elapsed:.2f} seconds")
        
        if 'total_scanned' in results:
            rate = results['total_scanned'] / elapsed
            print(f"Processing rate: {rate:.1f} symbols/second")
        
    except Exception as e:
        print(f"Error during parallel scan: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()