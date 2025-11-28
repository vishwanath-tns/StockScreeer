"""
Daily Progress Tracker - Automatically log all project changes

Usage:
    from progress_tracker import log_progress
    
    # Log a file creation
    log_progress("create", "new_feature.py", "Added real-time market scanner")
    
    # Log a file modification
    log_progress("modify", "dashboard.py", "Fixed advance-decline calculation bug")
    
    # Log a cleanup action
    log_progress("cleanup", "old_files/", "Archived 50 test files")
"""

import os
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
PROGRESS_DIR = PROJECT_ROOT / "DAILY_PROGRESS"
PROGRESS_DIR.mkdir(exist_ok=True)
PROGRESS_HUB = PROJECT_ROOT / "PROGRESS_HUB.py"

def get_today_filename():
    """Get today's progress log filename"""
    return f"{datetime.now().strftime('%Y-%m-%d')}_progress.md"

def log_progress(action, filename, description, category="general"):
    """
    Log a progress entry to today's log file
    
    Args:
        action: "create", "modify", "delete", "fix", "cleanup", "refactor"
        filename: Name or path of file(s) affected
        description: What was done and why
        category: "feature", "bugfix", "cleanup", "docs", "database", "general"
    """
    today_file = PROGRESS_DIR / get_today_filename()
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Create or append to today's log
    if not today_file.exists():
        # Create new day's log with header
        header = f"""# Daily Progress - {datetime.now().strftime('%B %d, %Y')}

## Summary
<!-- Add daily summary at end of day -->

## Changes Log

"""
        today_file.write_text(header, encoding='utf-8')
    
    # Append the log entry
    entry = f"""### {timestamp} - {action.upper()} - `{filename}`
**Category:** {category}  
**Description:** {description}

"""
    
    with open(today_file, 'a', encoding='utf-8') as f:
        f.write(entry)
    
    # Update PROGRESS_HUB.py for Todo Tree visibility
    update_progress_hub(action, filename, description, category)
    
    # Update TODAY.md to always point to current day
    today_link = PROJECT_ROOT / "TODAY.md"
    today_link.write_text(f"""# Today's Progress

[View today's progress log →](DAILY_PROGRESS/{get_today_filename()})

---

## Quick Log Entry

To log progress from any script:

```python
from progress_tracker import log_progress

# Log what you're doing
log_progress("create", "my_file.py", "Brief description of what and why")
```

## Categories
- **feature** - New functionality added
- **bugfix** - Fixed a bug or error
- **cleanup** - Removed/archived files
- **refactor** - Improved code structure
- **docs** - Documentation updates
- **database** - Database schema/data changes
- **general** - Other changes

## Action Types
- **create** - New file created
- **modify** - Existing file changed
- **delete** - File removed
- **fix** - Bug fixed
- **cleanup** - Files archived/organized
- **refactor** - Code restructured
""", encoding='utf-8')
    
    print(f"✅ Logged: {action} - {filename}")
    return True

def update_progress_hub(action, filename, description, category):
    """Update PROGRESS_HUB.py with latest progress for Todo Tree"""
    today = datetime.now().strftime('%Y-%m-%d')
    timestamp = datetime.now().strftime("%H:%M")
    
    # Read current hub
    if PROGRESS_HUB.exists():
        content = PROGRESS_HUB.read_text(encoding='utf-8')
    else:
        content = ""
    
    # Parse existing entries
    lines = content.split('\n')
    
    # Find the recent changes section
    recent_section_start = -1
    recent_section_end = -1
    for i, line in enumerate(lines):
        if '# 📝 RECENT CHANGES (Last 5)' in line:
            recent_section_start = i
        elif recent_section_start > 0 and recent_section_end < 0 and line.startswith('# ==='):
            recent_section_end = i
            break
    
    # Create new entry
    new_entry = f"# DONE: {today} - {action.upper()} {filename} - {description}"
    
    # Update recent changes section
    if recent_section_start > 0:
        # Get existing DONE entries
        done_entries = []
        for i in range(recent_section_start + 4, recent_section_end):
            if lines[i].startswith('# DONE:'):
                done_entries.append(lines[i])
        
        # Add new entry and keep only last 5
        done_entries.insert(0, new_entry)
        done_entries = done_entries[:5]
        
        # Rebuild content
        new_lines = lines[:recent_section_start + 4]
        new_lines.append("")
        new_lines.extend(done_entries)
        new_lines.append("")
        new_lines.extend(lines[recent_section_end:])
        
        content = '\n'.join(new_lines)
    
    # Update summary line
    content = content.replace(
        '# PROGRESS: 2025-11-28 - Total changes today:',
        f'# PROGRESS: {today} - Total changes today:'
    )
    
    # Count today's changes
    today_file = PROGRESS_DIR / get_today_filename()
    if today_file.exists():
        today_content = today_file.read_text(encoding='utf-8')
        change_count = today_content.count("###")
        content = content.replace(
            f'# PROGRESS: {today} - Total changes today: ',
            f'# PROGRESS: {today} - Total changes today: {change_count}\n# PROGRESS: {today} - Latest at {timestamp}: {action.upper()} {filename}'
        )
    
    # Write back
    PROGRESS_HUB.write_text(content, encoding='utf-8')

def get_recent_progress(days=7):
    """Get list of progress files from last N days"""
    progress_files = sorted(PROGRESS_DIR.glob("*_progress.md"), reverse=True)
    return progress_files[:days]

def print_summary(days=7):
    """Print summary of recent progress"""
    print(f"\n📊 Progress Summary (Last {days} days)")
    print("=" * 60)
    
    for log_file in get_recent_progress(days):
        date_str = log_file.stem.replace("_progress", "")
        print(f"\n📅 {date_str}")
        
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Count entries
            entries = content.count("###")
            print(f"   {entries} changes logged")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    # Example usage
    print("Daily Progress Tracker initialized")
    print(f"Today's log: {get_today_filename()}")
    print_summary()
