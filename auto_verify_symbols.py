"""
Automated bulk verification script - runs multiple batches automatically
"""
import os
import subprocess
import time

def run_batch_verification():
    """Run a batch verification"""
    try:
        # Run the quick verification with auto-confirmation
        result = subprocess.run([
            'C:/Users/Admin/AppData/Local/Microsoft/WindowsApps/python3.11.exe',
            'quick_symbol_check.py'
        ], input='y\n', text=True, capture_output=True, cwd='D:\\MyProjects\\StockScreeer')
        
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
        
        # Extract remaining symbols count from output
        for line in result.stdout.split('\n'):
            if 'Unmapped symbols:' in line:
                remaining = int(line.split(':')[1].strip())
                return remaining
        return 0
    except Exception as e:
        print(f"Error running batch: {e}")
        return -1

def main():
    print("Automated NSE Symbol Verification")
    print("=================================")
    
    batch_count = 0
    while True:
        batch_count += 1
        print(f"\n--- Running Batch {batch_count} ---")
        
        remaining = run_batch_verification()
        
        if remaining <= 0:
            print("Verification complete!")
            break
        elif remaining == -1:
            print("Error occurred, stopping")
            break
        
        print(f"Remaining symbols: {remaining}")
        
        if batch_count >= 10:  # Safety limit
            print("Reached batch limit, stopping")
            break
        
        # Short pause between batches
        time.sleep(2)

if __name__ == "__main__":
    main()