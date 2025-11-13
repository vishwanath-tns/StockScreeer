#!/usr/bin/env python3
"""
Test RSI Divergence PDF Generation from Reports Tab
=================================================

This script tests the PDF generation functionality integrated
into the Reports tab to ensure everything works end-to-end.
"""

import os
import sys
from pathlib import Path

def test_pdf_generation():
    """Test PDF generation functionality"""
    print("🔬 Testing PDF Generation Integration")
    print("=" * 50)
    
    try:
        # Ensure we're in the right directory
        project_dir = Path(__file__).parent.parent
        os.chdir(project_dir)
        
        # Test import of the PDF generator
        print("📊 Testing PDF generator import...")
        sys.path.insert(0, str(project_dir / "scripts"))
        
        import generate_enhanced_rsi_divergence_pdf as pdf_gen
        print("✅ PDF generator module imported successfully")
        
        # Test the main function
        print("🚀 Testing PDF generation function...")
        
        # Call with small number for testing
        result = pdf_gen.generate_enhanced_pdf_report(max_stocks=5)
        
        if result:
            print("✅ PDF generation completed successfully!")
            
            # Find the generated PDF
            pdf_files = list(project_dir.glob("Enhanced_RSI_Divergences_Grouped_*_EQ_Series.pdf"))
            if pdf_files:
                latest_pdf = max(pdf_files, key=lambda f: f.stat().st_mtime)
                file_size = latest_pdf.stat().st_size / 1024  # KB
                
                print(f"📄 Generated file: {latest_pdf.name}")
                print(f"📊 File size: {file_size:.1f} KB") 
                print(f"📁 Location: {latest_pdf}")
                print("✅ PDF generation test: PASSED")
                return True
            else:
                print("❌ PDF file not found after generation")
                return False
        else:
            print("❌ PDF generation returned False")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Check that generate_enhanced_rsi_divergence_pdf.py exists in scripts/")
        return False
    except Exception as e:
        print(f"💥 Error during PDF generation: {e}")
        import traceback
        print(f"📋 Details: {traceback.format_exc()}")
        return False

def test_database_connectivity():
    """Test database connectivity for Reports tab"""
    print("\n🗄️ Testing Database Connectivity")
    print("=" * 50)
    
    try:
        import reporting_adv_decl as rad
        from sqlalchemy import text
        
        engine = rad.engine()
        with engine.connect() as conn:
            # Test RSI divergences table
            result = conn.execute(text("SELECT COUNT(*) as count FROM nse_rsi_divergences")).fetchone()
            divergence_count = result[0]
            print(f"📊 RSI Divergences: {divergence_count:,} signals found")
            
            # Test RSI daily table
            result = conn.execute(text("SELECT COUNT(DISTINCT symbol) as symbols FROM nse_rsi_daily")).fetchone()
            rsi_symbols = result[0]
            print(f"📈 RSI Daily: {rsi_symbols:,} symbols available")
            
            # Test BHAV data
            result = conn.execute(text("SELECT MAX(trade_date) as latest FROM nse_equity_bhavcopy_full")).fetchone()
            latest_date = result[0]
            print(f"📅 Latest BHAV data: {latest_date}")
            
            if divergence_count > 0 and rsi_symbols > 0:
                print("✅ Database connectivity test: PASSED")
                return True
            else:
                print("❌ Database connectivity test: FAILED (no data)")
                return False
                
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 REPORTS TAB INTEGRATION TEST SUITE")
    print("=" * 60)
    
    # Test database connectivity first
    db_success = test_database_connectivity()
    
    # Test PDF generation if DB is working
    if db_success:
        pdf_success = test_pdf_generation()
    else:
        print("⏭️ Skipping PDF generation test due to database issues")
        pdf_success = False
    
    print("\n" + "=" * 60)
    print("🎯 FINAL RESULTS:")
    print("=" * 60)
    
    if db_success and pdf_success:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Reports tab is fully functional")
        print("✅ Database connectivity working")
        print("✅ PDF generation working")
        print("📊 Ready for production use!")
    else:
        print("❌ SOME TESTS FAILED:")
        print(f"   Database: {'✅ PASS' if db_success else '❌ FAIL'}")
        print(f"   PDF Gen:  {'✅ PASS' if pdf_success else '❌ FAIL'}")
        print("🔧 Please check error messages above")