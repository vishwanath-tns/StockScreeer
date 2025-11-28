"""
Visual Progress Dashboard - See your daily progress at a glance

Usage: python progress_dashboard.py [days]
       python progress_dashboard.py      # Last 7 days
       python progress_dashboard.py 30   # Last 30 days
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

PROGRESS_DIR = Path(__file__).parent / "DAILY_PROGRESS"

def parse_progress_file(filepath):
    """Parse a progress log file and extract statistics"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    stats = {
        'total': content.count('###'),
        'create': content.count('- CREATE -'),
        'modify': content.count('- MODIFY -'),
        'fix': content.count('- FIX -'),
        'cleanup': content.count('- CLEANUP -'),
        'refactor': content.count('- REFACTOR -'),
        'categories': {
            'feature': content.count('Category:** feature'),
            'bugfix': content.count('Category:** bugfix'),
            'cleanup': content.count('Category:** cleanup'),
            'docs': content.count('Category:** docs'),
            'database': content.count('Category:** database'),
            'refactor': content.count('Category:** refactor'),
        }
    }
    return stats

def get_progress_files(days=7):
    """Get progress files for last N days"""
    files = []
    for i in range(days):
        date = datetime.now() - timedelta(days=i)
        filename = f"{date.strftime('%Y-%m-%d')}_progress.md"
        filepath = PROGRESS_DIR / filename
        if filepath.exists():
            files.append((date, filepath))
    return sorted(files, reverse=True)

def print_dashboard(days=7):
    """Print visual progress dashboard"""
    print("\n" + "=" * 70)
    print(f"📊 PROGRESS DASHBOARD - Last {days} Days".center(70))
    print("=" * 70 + "\n")
    
    files = get_progress_files(days)
    
    if not files:
        print("❌ No progress logs found!")
        print(f"👉 Start logging: python log.py")
        return
    
    # Daily breakdown
    print("📅 Daily Activity")
    print("-" * 70)
    
    total_changes = 0
    total_by_action = defaultdict(int)
    total_by_category = defaultdict(int)
    
    for date, filepath in files:
        stats = parse_progress_file(filepath)
        total_changes += stats['total']
        
        date_str = date.strftime('%b %d, %Y (%a)')
        bar = "█" * min(stats['total'], 40)
        
        print(f"{date_str:25} │ {bar} {stats['total']}")
        
        # Accumulate totals
        for action in ['create', 'modify', 'fix', 'cleanup', 'refactor']:
            total_by_action[action] += stats[action]
        
        for cat, count in stats['categories'].items():
            total_by_category[cat] += count
    
    # Summary statistics
    print("\n" + "=" * 70)
    print(f"📈 Summary ({len(files)} days with activity)")
    print("-" * 70)
    print(f"Total Changes:     {total_changes}")
    print(f"Avg Changes/Day:   {total_changes / max(len(files), 1):.1f}")
    print(f"Most Active Day:   {max(parse_progress_file(f).get('total', 0) for _, f in files)} changes")
    
    # Action breakdown
    print("\n🎬 By Action Type")
    print("-" * 70)
    for action, count in sorted(total_by_action.items(), key=lambda x: x[1], reverse=True):
        if count > 0:
            bar = "▓" * (count * 2)
            print(f"  {action:10} │ {bar} {count}")
    
    # Category breakdown
    print("\n📦 By Category")
    print("-" * 70)
    for category, count in sorted(total_by_category.items(), key=lambda x: x[1], reverse=True):
        if count > 0:
            bar = "▓" * (count * 2)
            print(f"  {category:10} │ {bar} {count}")
    
    print("\n" + "=" * 70)
    print("💡 Tips:")
    print("   • Log as you work: python log.py")
    print("   • View today: cat TODAY.md")
    print("   • Full history: ls DAILY_PROGRESS")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    print_dashboard(days)
