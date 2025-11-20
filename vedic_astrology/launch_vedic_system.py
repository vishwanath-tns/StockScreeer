#!/usr/bin/env python3
"""
Quick Launcher for Professional Vedic Astrology System
Easy entry point for the minute-level planetary data collection system

Simple usage:
    python launch_vedic_system.py
"""

import sys
import os
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        'mysql-connector-python',
        'schedule', 
        'tkcalendar',
        'pandas',
        'swisseph'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages

def install_dependencies(packages):
    """Install missing dependencies"""
    if not packages:
        return True
        
    print(f"📦 Installing missing packages: {', '.join(packages)}")
    
    try:
        cmd = [sys.executable, '-m', 'pip', 'install'] + packages
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install packages: {e}")
        return False

def main():
    """Main launcher function"""
    print("""
🌟 Professional Vedic Astrology System Launcher
================================================

Checking system requirements...
""")
    
    # Check Python version
    if sys.version_info < (3, 7):
        print("❌ Python 3.7+ required")
        sys.exit(1)
    else:
        print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}")
    
    # Check dependencies
    missing = check_dependencies()
    if missing:
        print(f"⚠️  Missing packages detected: {', '.join(missing)}")
        install_choice = input("📦 Install missing packages automatically? (y/n): ").lower().strip()
        
        if install_choice in ['y', 'yes']:
            if not install_dependencies(missing):
                print("❌ Failed to install dependencies. Please install manually:")
                print(f"   pip install {' '.join(missing)}")
                sys.exit(1)
        else:
            print("Please install missing packages manually:")
            print(f"   pip install {' '.join(missing)}")
            sys.exit(1)
    else:
        print("✅ All dependencies satisfied")
    
    # Check if database directory exists
    db_dir = Path(__file__).parent / "database"
    if not db_dir.exists():
        print("❌ Database directory not found")
        sys.exit(1)
    
    # Launch main implementation
    implementation_script = db_dir / "implement_minute_system.py"
    if not implementation_script.exists():
        print("❌ Implementation script not found")
        sys.exit(1)
    
    print("""
🚀 Launching Professional Vedic Astrology System...

This will:
1. Setup MySQL database schema
2. Start minute-level data collection
3. Launch GUI interface

Press Enter to continue or Ctrl+C to cancel...
""")
    
    try:
        input()
        
        # Change to database directory
        os.chdir(db_dir)
        
        # Launch implementation
        subprocess.run([sys.executable, str(implementation_script)], check=True)
        
    except KeyboardInterrupt:
        print("\n🛑 Launch cancelled by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Launch failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()