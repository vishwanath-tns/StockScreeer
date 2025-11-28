#!/usr/bin/env python3
"""
Test the PDF generation feature in sectoral analysis GUI.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.sectoral_pdf_generator import generate_sectoral_pdf_report

def test_pdf_with_gui_integration():
    """Test PDF generation with GUI-like functionality."""
    print("🔍 Testing Sectoral PDF Generation")
    print("=" * 40)
    
    # Test the same function that GUI will call
    analysis_date = "2025-11-14"
    print(f"📅 Generating PDF for date: {analysis_date}")
    
    try:
        success, result = generate_sectoral_pdf_report(analysis_date)
        
        if success:
            print(f"✅ PDF generated successfully!")
            print(f"📁 File: {result}")
            print(f"📊 File size: {os.path.getsize(result) / 1024:.1f} KB")
            
            # Check if file exists and has content
            if os.path.exists(result) and os.path.getsize(result) > 10000:  # At least 10KB
                print(f"✅ PDF file validation passed")
                
                # List the file details
                print(f"\n📋 PDF Report Details:")
                print(f"   • Filename: {os.path.basename(result)}")
                print(f"   • Full Path: {os.path.abspath(result)}")
                print(f"   • Size: {os.path.getsize(result):,} bytes")
                
                return True
            else:
                print(f"❌ PDF file validation failed - file too small or doesn't exist")
                return False
        else:
            print(f"❌ PDF generation failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

if __name__ == "__main__":
    success = test_pdf_with_gui_integration()
    
    if success:
        print(f"\n🎉 PDF Generation Test: PASSED")
        print(f"✅ The GUI PDF feature is ready to use!")
    else:
        print(f"\n❌ PDF Generation Test: FAILED")
        print(f"🔧 Please check the error messages above")