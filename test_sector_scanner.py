"""
Test script for Sector Pattern Scanner

This script tests the complete sector pattern scanning system including:
1. Database connectivity
2. Pattern detection functionality  
3. Breakout analysis
4. PDF report generation
5. GUI components

Run this to verify everything is working correctly.
"""

import sys
import os
import traceback
from datetime import datetime

def test_database_connectivity():
    """Test database connection and basic queries"""
    print("Testing database connectivity...")
    try:
        from services.sector_pattern_scanner import SectorPatternScanner
        
        scanner = SectorPatternScanner()
        
        # Test basic queries
        sectors = scanner.get_available_sectors()
        print(f"✓ Found {len(sectors)} sectors in database")
        
        latest_dates = scanner.get_latest_dates()
        print(f"✓ Latest data dates: {latest_dates}")
        
        # Test constituent lookup for a major sector
        if sectors:
            bank_sector_id = next((s[0] for s in sectors if 'Bank' in s[1]), None)
            if bank_sector_id:
                constituents = scanner.get_sector_constituents([bank_sector_id])
                if constituents:
                    sector_name = list(constituents.keys())[0]
                    stock_count = len(constituents[sector_name])
                    print(f"✓ Found {stock_count} stocks in {sector_name}")
                else:
                    print("⚠ No constituents found for Bank sector")
            else:
                print("⚠ Bank sector not found")
        
        return True
        
    except Exception as e:
        print(f"✗ Database connectivity failed: {e}")
        traceback.print_exc()
        return False

def test_pattern_detection():
    """Test pattern detection functionality"""
    print("\nTesting pattern detection...")
    try:
        from services.sector_pattern_scanner import scan_nifty_bank_patterns
        
        patterns, summaries = scan_nifty_bank_patterns()
        
        if patterns:
            print(f"✓ Found {len(patterns)} patterns in Nifty Bank")
            
            # Show sample patterns
            for i, pattern in enumerate(patterns[:3]):
                print(f"  Sample {i+1}: {pattern.symbol} - {pattern.pattern_type} ({pattern.timeframe})")
                
            # Test breakout detection
            breakouts = [p for p in patterns if p.breakout_signal]
            print(f"✓ Found {len(breakouts)} breakout signals")
            
        else:
            print("⚠ No patterns found (this may be normal if no patterns exist for latest dates)")
        
        if summaries:
            print(f"✓ Generated {len(summaries)} sector summaries")
        
        return True
        
    except Exception as e:
        print(f"✗ Pattern detection failed: {e}")
        traceback.print_exc()
        return False

def test_pdf_generation():
    """Test PDF report generation"""
    print("\nTesting PDF report generation...")
    try:
        # Test if reportlab is available
        import reportlab
        print("✓ ReportLab available")
        
        # Test if matplotlib is available  
        import matplotlib
        print("✓ Matplotlib available")
        
        # Test if seaborn is available
        import seaborn
        print("✓ Seaborn available")
        
        # Test quick report generation
        from services.sector_report_generator import generate_nifty_bank_report
        
        # Ensure reports directory exists
        os.makedirs("reports/test", exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_report_path = f"reports/test/test_nifty_bank_report_{timestamp}.pdf"
        
        print("Generating test PDF report...")
        result_path = generate_nifty_bank_report(test_report_path)
        
        if os.path.exists(result_path):
            file_size = os.path.getsize(result_path)
            print(f"✓ PDF report generated successfully: {result_path}")
            print(f"✓ File size: {file_size:,} bytes")
            
            # Clean up test file
            try:
                os.remove(result_path)
                print("✓ Test file cleaned up")
            except:
                pass
                
            return True
        else:
            print("✗ PDF file was not created")
            return False
            
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print("Run: pip install reportlab seaborn")
        return False
    except Exception as e:
        print(f"✗ PDF generation failed: {e}")
        traceback.print_exc()
        return False

def test_gui_components():
    """Test GUI component imports"""
    print("\nTesting GUI components...")
    try:
        # Test sector pattern GUI import
        from gui.sector_pattern_gui import SectorPatternGUI
        print("✓ Sector Pattern GUI imported successfully")
        
        # Test service imports
        from services.sector_pattern_scanner import SectorPatternScanner
        from services.sector_report_generator import SectorPatternReportGenerator
        print("✓ Service classes imported successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ GUI component import failed: {e}")
        traceback.print_exc()
        return False

def install_missing_dependencies():
    """Install missing dependencies"""
    print("\nChecking and installing missing dependencies...")
    
    required_packages = [
        'reportlab',
        'seaborn', 
        'matplotlib',
        'pandas',
        'sqlalchemy',
        'pymysql'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} is installed")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package} is missing")
    
    if missing_packages:
        print(f"\nInstalling missing packages: {', '.join(missing_packages)}")
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
            print("✓ All missing packages installed successfully")
            return True
        except Exception as e:
            print(f"✗ Failed to install packages: {e}")
            return False
    else:
        print("✓ All required packages are already installed")
        return True

def main():
    """Run all tests"""
    print("🔍 Sector Pattern Scanner System Test")
    print("=" * 50)
    
    # Install dependencies first
    deps_ok = install_missing_dependencies()
    if not deps_ok:
        print("\n❌ Dependency installation failed. Please install manually:")
        print("pip install reportlab seaborn matplotlib pandas sqlalchemy pymysql")
        return False
    
    # Run tests
    tests = [
        ("Database Connectivity", test_database_connectivity),
        ("Pattern Detection", test_pattern_detection),
        ("PDF Generation", test_pdf_generation),
        ("GUI Components", test_gui_components),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print(f"\n{'='*50}")
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Sector Pattern Scanner is ready to use.")
        print("\nNext steps:")
        print("1. Run: python scanner_gui.py")
        print("2. Navigate to the 'Sector Scanner' tab")
        print("3. Select sectors and timeframes")
        print("4. Click 'Start Pattern Scan' to analyze patterns")
        print("5. Use 'Generate PDF Report' to create detailed reports")
        return True
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)