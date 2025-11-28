#!/usr/bin/env python3
"""
AI Context Loader - Read this before starting any work!

This script displays all the context an AI assistant needs before starting work:
- Recent progress from logs
- Current project state
- Known issues and next steps

Usage:
    python ai_context.py
    
Or from AI chat:
    "Read ai_context.py output before we start"
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).parent
PROGRESS_DIR = PROJECT_ROOT / "DAILY_PROGRESS"
PROGRESS_HUB = PROJECT_ROOT / "PROGRESS_HUB.py"

def read_progress_hub():
    """Read and display PROGRESS_HUB.py"""
    if PROGRESS_HUB.exists():
        print("=" * 80)
        print("📊 PROGRESS HUB - AI READ THIS FIRST!")
        print("=" * 80)
        print()
        
        content = PROGRESS_HUB.read_text(encoding='utf-8')
        
        # Extract key sections
        for line in content.split('\n'):
            if line.startswith('#'):
                # Color code by type
                if 'PROGRESS:' in line:
                    print(f"✅ {line[2:]}")
                elif 'TODO:' in line:
                    print(f"📋 {line[2:]}")
                elif 'DONE:' in line:
                    print(f"✔️  {line[2:]}")
                elif 'WORKING:' in line:
                    print(f"🔄 {line[2:]}")
                elif 'NEXT:' in line:
                    print(f"➡️  {line[2:]}")
                elif 'FIXME:' in line:
                    print(f"⚠️  {line[2:]}")
                elif 'BUG:' in line:
                    print(f"🐛 {line[2:]}")
                elif 'DOCS:' in line:
                    print(f"📚 {line[2:]}")
                elif line.startswith('# ==='):
                    print("\n" + "-" * 80)
                elif line.startswith('# 🔴') or line.startswith('# 📊') or line.startswith('# 🎯'):
                    print(f"\n{line[2:]}")
                    print("-" * 80)
    else:
        print("⚠️  PROGRESS_HUB.py not found!")
        print("Run: python progress_tracker.py")

def read_recent_logs(days=2):
    """Read last N days of detailed logs"""
    print("\n")
    print("=" * 80)
    print(f"📅 DETAILED LOGS - LAST {days} DAYS")
    print("=" * 80)
    print()
    
    logs = sorted(PROGRESS_DIR.glob("*_progress.md"), reverse=True)[:days]
    
    for log_file in logs:
        date_str = log_file.stem.replace("_progress", "")
        print(f"\n📆 {date_str}")
        print("-" * 80)
        
        content = log_file.read_text(encoding='utf-8')
        
        # Extract just the action headers
        in_changes = False
        for line in content.split('\n'):
            if '## Changes Log' in line:
                in_changes = True
                continue
            if in_changes and line.startswith('###'):
                # Extract time and action
                print(f"  {line[4:]}")

def show_quick_reference():
    """Show quick commands"""
    print("\n")
    print("=" * 80)
    print("🚀 QUICK REFERENCE FOR AI")
    print("=" * 80)
    print()
    print("📝 To log changes:")
    print("   from progress_tracker import log_progress")
    print("   log_progress('modify', 'file.py', 'What I did', 'feature')")
    print()
    print("📁 Key files:")
    print("   - PROGRESS_HUB.py - Current status (read first!)")
    print("   - MASTER_INDEX.md - All 566 files documented")
    print("   - TODAY.md - Today's detailed log")
    print("   - .github/copilot-instructions.md - AI instructions")
    print()
    print("🎯 Main applications:")
    print("   - realtime_adv_decl_dashboard.py - Market dashboard")
    print("   - quick_download_nifty500.py - Bulk data downloader")
    print("   - sync_bhav_gui.py - NSE BHAV importer")
    print()
    print("=" * 80)

def main():
    """Display all context for AI"""
    read_progress_hub()
    read_recent_logs(days=2)
    show_quick_reference()
    
    print("\n✅ Context loaded! AI is now ready to work.")
    print("💡 Tip: Always check PROGRESS_HUB.py before making changes\n")

if __name__ == "__main__":
    main()
