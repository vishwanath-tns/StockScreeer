"""
StockScreeer Project Analyzer
==============================
Automatically analyze all Python files and categorize them

This will help us understand:
1. What features we have
2. Which files are duplicates
3. Which files are test/debug/demo
4. File dependencies and import graph
5. Database tables used by each file
"""

import os
import re
from pathlib import Path
from collections import defaultdict
import ast

class ProjectAnalyzer:
    def __init__(self, root_dir):
        self.root_dir = Path(root_dir)
        self.files = []
        self.categories = defaultdict(list)
        self.database_tables = defaultdict(set)
        self.imports = defaultdict(set)
        
    def analyze(self):
        """Run complete analysis"""
        print("=" * 80)
        print("STOCKSCREEER PROJECT ANALYZER")
        print("=" * 80)
        
        self.scan_all_files()
        self.categorize_files()
        self.find_duplicates()
        self.analyze_database_usage()
        self.generate_reports()
        
    def scan_all_files(self):
        """Find all Python files"""
        print("\n📁 Scanning files...")
        
        self.files = list(self.root_dir.rglob("*.py"))
        
        # Exclude virtual environments and node_modules
        self.files = [
            f for f in self.files 
            if 'venv' not in str(f) 
            and 'node_modules' not in str(f)
            and '__pycache__' not in str(f)
        ]
        
        print(f"   Found {len(self.files)} Python files")
        
    def categorize_files(self):
        """Categorize files by type"""
        print("\n📊 Categorizing files...")
        
        patterns = {
            'test': r'^test_|_test\.py$',
            'demo': r'^demo_|_demo\.py$',
            'debug': r'^debug_|_debug\.py$',
            'check': r'^check_|_check\.py$',
            'verify': r'^verify_|_verify\.py$',
            'setup': r'^setup_|_setup\.py$',
            'fix': r'^fix_|_fix\.py$',
            'working': r'working_|_working\.py$',
            'final': r'final_|_final\.py$',
            'temp': r'^temp_|^tmp_|\.tmp\.',
            'backup': r'backup|_old|_v\d+',
        }
        
        for file in self.files:
            name = file.name
            relative_path = file.relative_to(self.root_dir)
            
            # Check against patterns
            categorized = False
            for category, pattern in patterns.items():
                if re.search(pattern, name):
                    self.categories[category].append(relative_path)
                    categorized = True
                    break
            
            if not categorized:
                # Check if it's in a specific directory
                parts = relative_path.parts
                if len(parts) > 1:
                    dir_name = parts[0]
                    if dir_name in ['tests', 'examples', 'tools', 'services']:
                        self.categories[dir_name].append(relative_path)
                    else:
                        self.categories['production'].append(relative_path)
                else:
                    self.categories['production'].append(relative_path)
        
        # Print summary
        print("\n   Category Summary:")
        for category in sorted(self.categories.keys()):
            count = len(self.categories[category])
            print(f"   - {category:15s}: {count:3d} files")
            
    def find_duplicates(self):
        """Find files with similar names (potential duplicates)"""
        print("\n🔍 Finding potential duplicates...")
        
        # Group by base name (removing prefixes/suffixes)
        base_names = defaultdict(list)
        
        for file in self.files:
            name = file.stem
            
            # Remove common prefixes/suffixes
            base = re.sub(r'^(test_|demo_|debug_|check_|verify_|fix_|working_|final_)', '', name)
            base = re.sub(r'(_test|_demo|_debug|_check|_verify|_fix|_working|_final|_v\d+|_old|_backup)$', '', base)
            
            if base:
                base_names[base].append(file.relative_to(self.root_dir))
        
        # Find groups with multiple files
        duplicates = {k: v for k, v in base_names.items() if len(v) > 1}
        
        if duplicates:
            print(f"\n   Found {len(duplicates)} groups of potential duplicates:\n")
            for base, files in sorted(duplicates.items())[:20]:  # Show first 20
                print(f"   📦 {base}:")
                for f in sorted(files):
                    print(f"      - {f}")
                print()
        
        self.duplicates = duplicates
        
    def analyze_database_usage(self):
        """Find which database tables are used by each file"""
        print("\n💾 Analyzing database usage...")
        
        table_patterns = [
            r'FROM\s+(\w+)',
            r'INTO\s+(\w+)',
            r'UPDATE\s+(\w+)',
            r'TABLE\s+(\w+)',
            r'["\'](\w+_\w+)["\']',  # String literals with underscores (likely table names)
        ]
        
        all_tables = set()
        
        for file in self.files:
            try:
                content = file.read_text(encoding='utf-8', errors='ignore')
                
                for pattern in table_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        # Filter likely table names (have underscore, reasonable length)
                        if '_' in match and 3 < len(match) < 50 and match.islower():
                            self.database_tables[file.relative_to(self.root_dir)].add(match)
                            all_tables.add(match)
                            
            except Exception as e:
                pass  # Skip files that can't be read
        
        print(f"   Found {len(all_tables)} unique table names referenced")
        
        # Find most used tables
        table_counts = defaultdict(int)
        for tables in self.database_tables.values():
            for table in tables:
                table_counts[table] += 1
        
        print("\n   Most referenced tables:")
        for table, count in sorted(table_counts.items(), key=lambda x: x[1], reverse=True)[:15]:
            print(f"   - {table:40s}: {count:3d} files")
            
    def generate_reports(self):
        """Generate detailed reports"""
        print("\n📝 Generating reports...")
        
        self.generate_feature_index()
        self.generate_duplicate_report()
        self.generate_database_report()
        self.generate_cleanup_suggestions()
        
    def generate_feature_index(self):
        """Create FEATURE_INDEX.md"""
        output_file = self.root_dir / "FEATURE_INDEX.md"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Feature Index\n\n")
            f.write("*Auto-generated index of all Python files*\n\n")
            f.write(f"**Total Files:** {len(self.files)}\n\n")
            
            f.write("---\n\n")
            
            for category in sorted(self.categories.keys()):
                files = sorted(self.categories[category])
                f.write(f"## {category.upper()} ({len(files)} files)\n\n")
                
                for file in files[:50]:  # Limit to first 50 per category
                    f.write(f"- `{file}`\n")
                
                if len(files) > 50:
                    f.write(f"\n*... and {len(files)-50} more*\n")
                
                f.write("\n")
        
        print(f"   ✅ Created {output_file.name}")
        
    def generate_duplicate_report(self):
        """Create DUPLICATES_REPORT.md"""
        output_file = self.root_dir / "DUPLICATES_REPORT.md"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Duplicate Files Report\n\n")
            f.write("*Files with similar names that may be duplicates*\n\n")
            f.write(f"**Total Groups:** {len(self.duplicates)}\n\n")
            
            f.write("---\n\n")
            
            for base, files in sorted(self.duplicates.items()):
                f.write(f"## {base}\n\n")
                for file in sorted(files):
                    f.write(f"- `{file}`\n")
                f.write("\n**Action:** Review and keep only one version\n\n")
                f.write("---\n\n")
        
        print(f"   ✅ Created {output_file.name}")
        
    def generate_database_report(self):
        """Create DATABASE_USAGE.md"""
        output_file = self.root_dir / "DATABASE_USAGE.md"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Database Usage Report\n\n")
            f.write("*Tables referenced in code*\n\n")
            
            # Get all unique tables
            all_tables = set()
            for tables in self.database_tables.values():
                all_tables.update(tables)
            
            f.write(f"**Total Tables Referenced:** {len(all_tables)}\n\n")
            f.write("---\n\n")
            
            # Count files per table
            table_files = defaultdict(list)
            for file, tables in self.database_tables.items():
                for table in tables:
                    table_files[table].append(file)
            
            f.write("## Tables by Usage\n\n")
            for table in sorted(table_files.keys()):
                files = table_files[table]
                f.write(f"### `{table}` ({len(files)} files)\n\n")
                for file in sorted(files)[:10]:
                    f.write(f"- {file}\n")
                if len(files) > 10:
                    f.write(f"- *... and {len(files)-10} more*\n")
                f.write("\n")
        
        print(f"   ✅ Created {output_file.name}")
        
    def generate_cleanup_suggestions(self):
        """Create CLEANUP_SUGGESTIONS.md"""
        output_file = self.root_dir / "CLEANUP_SUGGESTIONS.md"
        
        test_count = len(self.categories['test'])
        demo_count = len(self.categories['demo'])
        debug_count = len(self.categories['debug'])
        check_count = len(self.categories['check'])
        verify_count = len(self.categories['verify'])
        
        total_deletable = test_count + demo_count + debug_count
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Cleanup Suggestions\n\n")
            f.write("*Recommended actions to clean up the project*\n\n")
            
            f.write("## 📊 Summary\n\n")
            f.write(f"- **Total Files:** {len(self.files)}\n")
            f.write(f"- **Production Files:** {len(self.categories.get('production', []))}\n")
            f.write(f"- **Test Files:** {test_count}\n")
            f.write(f"- **Demo Files:** {demo_count}\n")
            f.write(f"- **Debug Files:** {debug_count}\n")
            f.write(f"- **Check/Verify Files:** {check_count + verify_count}\n")
            f.write(f"- **Duplicate Groups:** {len(self.duplicates)}\n\n")
            
            f.write(f"**Potential Space Savings:** {total_deletable} files can be archived/deleted\n\n")
            
            f.write("---\n\n")
            
            f.write("## 🎯 Recommended Actions\n\n")
            
            f.write("### 1. Archive Test Files\n")
            f.write(f"Move {test_count} test files to `ARCHIVE/tests/`\n\n")
            
            f.write("### 2. Delete Demo Files\n")
            f.write(f"Delete or archive {demo_count} demo files\n\n")
            
            f.write("### 3. Delete Debug Files\n")
            f.write(f"Delete {debug_count} debug files (keep code in git history)\n\n")
            
            f.write("### 4. Consolidate Duplicates\n")
            f.write(f"Review {len(self.duplicates)} groups and keep only latest version\n\n")
            
            f.write("### 5. Organize Production Files\n")
            f.write("Move production files into proper folder structure\n\n")
            
            f.write("---\n\n")
            
            f.write("## 💾 Database Cleanup\n\n")
            f.write("Review database tables and:\n")
            f.write("1. Drop unused tables\n")
            f.write("2. Merge duplicate tables\n")
            f.write("3. Document all tables\n\n")
        
        print(f"   ✅ Created {output_file.name}")
        
    def print_summary(self):
        """Print final summary"""
        print("\n" + "=" * 80)
        print("ANALYSIS COMPLETE!")
        print("=" * 80)
        print("\n📁 Files created:")
        print("   - FEATURE_INDEX.md")
        print("   - DUPLICATES_REPORT.md")
        print("   - DATABASE_USAGE.md")
        print("   - CLEANUP_SUGGESTIONS.md")
        print("\n📊 Next steps:")
        print("   1. Review CLEANUP_SUGGESTIONS.md")
        print("   2. Check DUPLICATES_REPORT.md for files to merge")
        print("   3. Review FEATURE_INDEX.md to understand what you have")
        print("   4. Start with quick wins (archive test/demo files)")
        print("\n" + "=" * 80)


if __name__ == "__main__":
    # Run analyzer
    analyzer = ProjectAnalyzer(r"D:\MyProjects\StockScreeer")
    analyzer.analyze()
    analyzer.print_summary()
