"""
Quick Progress Logger - Interactive CLI tool

Usage: python log.py
       python log.py "create" "my_file.py" "Added new feature"
"""

import sys
from progress_tracker import log_progress

def interactive_log():
    """Interactive mode - prompts for input"""
    print("\n📝 Quick Progress Logger")
    print("=" * 50)
    
    print("\nAction types:")
    print("  1. create   - New file created")
    print("  2. modify   - Existing file changed")
    print("  3. fix      - Bug fixed")
    print("  4. cleanup  - Files archived/organized")
    print("  5. refactor - Code restructured")
    
    action_map = {
        '1': 'create', '2': 'modify', '3': 'fix',
        '4': 'cleanup', '5': 'refactor'
    }
    
    action_num = input("\nSelect action (1-5): ").strip()
    action = action_map.get(action_num, input("Enter action: ").strip())
    
    filename = input("File/folder name: ").strip()
    description = input("What did you do? ").strip()
    
    print("\nCategories:")
    print("  1. feature  2. bugfix  3. cleanup")
    print("  4. refactor 5. docs    6. database")
    
    category_map = {
        '1': 'feature', '2': 'bugfix', '3': 'cleanup',
        '4': 'refactor', '5': 'docs', '6': 'database'
    }
    
    cat_num = input("Category (1-6, default=general): ").strip()
    category = category_map.get(cat_num, 'general')
    
    log_progress(action, filename, description, category)
    print("\n✅ Progress logged!")
    print("👉 View: TODAY.md")

def quick_log(action, filename, description, category="general"):
    """Quick mode - command line args"""
    log_progress(action, filename, description, category)
    print(f"✅ Logged: {action} - {filename}")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Interactive mode
        interactive_log()
    elif len(sys.argv) >= 4:
        # Quick mode: python log.py action filename "description" [category]
        action = sys.argv[1]
        filename = sys.argv[2]
        description = sys.argv[3]
        category = sys.argv[4] if len(sys.argv) > 4 else "general"
        quick_log(action, filename, description, category)
    else:
        print("Usage:")
        print("  Interactive: python log.py")
        print('  Quick:       python log.py create "file.py" "description" [category]')
