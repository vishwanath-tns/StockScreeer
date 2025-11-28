"""
Daily Work Startup Script - Run this every morning!

Shows you:
1. What you did yesterday
2. What you did this week
3. What's next on the roadmap
4. Quick commands reminder

Usage: python start_work.py
"""

import os
from pathlib import Path
from datetime import datetime, timedelta
from progress_tracker import get_recent_progress

def print_section(title, color="cyan"):
    """Print a section header"""
    colors = {
        'cyan': '\033[96m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'reset': '\033[0m'
    }
    print(f"\n{colors.get(color, '')}{title}{colors['reset']}")
    print("=" * 70)

def show_yesterday_work():
    """Show what was done yesterday"""
    yesterday = datetime.now() - timedelta(days=1)
    yesterday_file = Path(__file__).parent / "DAILY_PROGRESS" / f"{yesterday.strftime('%Y-%m-%d')}_progress.md"
    
    print_section("📅 YESTERDAY'S WORK", "cyan")
    
    if yesterday_file.exists():
        with open(yesterday_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Extract summary if exists
        if "## Summary" in content:
            summary_start = content.index("## Summary")
            changes_start = content.index("## Changes Log") if "## Changes Log" in content else len(content)
            summary = content[summary_start:changes_start].strip()
            print(summary)
        else:
            # Count entries
            entry_count = content.count("###") - 1  # Subtract header
            print(f"   {entry_count} changes logged yesterday")
            print(f"   📄 View full log: cat DAILY_PROGRESS\\{yesterday.strftime('%Y-%m-%d')}_progress.md")
    else:
        print("   ℹ️  No work logged yesterday (or it was your day off!)")
        print("   💡 Start fresh today!")

def show_this_week():
    """Show this week's activity summary"""
    print_section("📊 THIS WEEK'S PROGRESS", "green")
    
    weekly_stats = {
        'total_changes': 0,
        'days_active': 0,
        'categories': {}
    }
    
    for i in range(7):
        date = datetime.now() - timedelta(days=i)
        log_file = Path(__file__).parent / "DAILY_PROGRESS" / f"{date.strftime('%Y-%m-%d')}_progress.md"
        
        if log_file.exists():
            weekly_stats['days_active'] += 1
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                entries = content.count("###") - 1
                weekly_stats['total_changes'] += entries
                
                # Count by category
                for cat in ['feature', 'bugfix', 'cleanup', 'docs', 'database', 'refactor']:
                    count = content.count(f"Category:** {cat}")
                    weekly_stats['categories'][cat] = weekly_stats['categories'].get(cat, 0) + count
    
    print(f"   Days Active:     {weekly_stats['days_active']}/7")
    print(f"   Total Changes:   {weekly_stats['total_changes']}")
    if weekly_stats['days_active'] > 0:
        print(f"   Avg Changes/Day: {weekly_stats['total_changes'] / weekly_stats['days_active']:.1f}")
    
    if weekly_stats['categories']:
        print("\n   Top Categories:")
        for cat, count in sorted(weekly_stats['categories'].items(), key=lambda x: x[1], reverse=True)[:3]:
            if count > 0:
                print(f"      • {cat}: {count} changes")

def show_quick_commands():
    """Show frequently used commands"""
    print_section("🚀 QUICK COMMANDS", "yellow")
    
    print("""
   Daily Routine:
      python quick_download_nifty500.py        # Download latest data
      python realtime_adv_decl_dashboard.py    # Start dashboard
      python log.py                             # Log your changes
   
   Documentation:
      cat MASTER_INDEX.md                       # Find anything
      cat QUICKSTART.md                         # Command reference
      python progress_dashboard.py              # View statistics
   
   Progress Tracking:
      python log.py create "file.py" "desc" feature    # Quick log
      cat TODAY.md                                      # Today's work
      cat DAILY_PROGRESS\\2025-11-28_progress.md       # Specific day
""")

def show_next_steps():
    """Show what to work on next"""
    print_section("🎯 SUGGESTED NEXT STEPS", "magenta")
    
    # Try to read from SETUP_COMPLETE.md or PROJECT_CLEANUP_PLAN.md
    setup_file = Path(__file__).parent / "SETUP_COMPLETE.md"
    
    if setup_file.exists():
        with open(setup_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if "### Short Term (This Week)" in content:
                start = content.index("### Short Term (This Week)")
                end = content.index("### Long Term", start) if "### Long Term" in content[start:] else len(content)
                next_steps = content[start:end].strip()
                # Extract just the bullet points
                lines = next_steps.split('\n')
                for line in lines[1:6]:  # Show first 5 items
                    if line.strip().startswith('- ['):
                        print(f"   {line.strip()}")
    else:
        print("   • Continue daily progress logging")
        print("   • Archive test/demo files (200 files)")
        print("   • Create central launcher GUI")

def show_ai_reminder():
    """Remind about AI capabilities"""
    print_section("🤖 AI ASSISTANT TIP", "blue")
    print("""
   When starting a new chat with AI, say:
   
   "Check TODAY.md and summarize what I did yesterday"
   
   or
   
   "Read my recent progress logs and tell me where we left off"
   
   The AI can read all your progress logs to understand context!
   📚 See: AI_ASSISTANT_GUIDE.md for more tips
""")

def main():
    """Main startup routine"""
    print("\n" + "=" * 70)
    print("  🌅 GOOD MORNING! LET'S START YOUR WORK DAY")
    print("=" * 70)
    
    show_yesterday_work()
    show_this_week()
    show_quick_commands()
    show_next_steps()
    show_ai_reminder()
    
    print("\n" + "=" * 70)
    print("  ✨ Ready to work! Don't forget to log your progress today!")
    print("=" * 70 + "\n")
    
    # Log that you started work
    from progress_tracker import log_progress
    log_progress("general", "work_session", "Started work day - reviewed yesterday's progress", "general")

if __name__ == "__main__":
    main()
