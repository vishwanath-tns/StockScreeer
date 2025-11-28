#!/usr/bin/env python3
"""
Test script to see what sectors the GUI gets vs PDF generator
"""
import sys
sys.path.append('.')

def test_gui_sectors():
    """Test what sectors the GUI Compare All Major Sectors gets"""
    try:
        from services.index_symbols_api import get_api
        
        print("🔍 Testing GUI sector discovery...")
        api = get_api()
        all_indices = api.get_all_indices()
        
        print(f"📊 Total indices found: {len(all_indices)}")
        
        # Apply the same filtering as GUI
        major_sectors = [s for s in all_indices.keys() if 'NIFTY' in s and len(s) < 25]
        major_sectors = major_sectors[:10]  # Limit to first 10
        
        print(f"\n🎯 GUI would show these {len(major_sectors)} sectors:")
        for i, sector in enumerate(major_sectors, 1):
            print(f"   {i}. {sector}")
        
        return major_sectors
        
    except Exception as e:
        print(f"❌ Error testing GUI sectors: {e}")
        return []

def test_pdf_sectors():
    """Test what sectors the PDF generator uses"""
    pdf_sectors = [
        'NIFTY-PHARMA', 'NIFTY-BANK', 'NIFTY-IT', 'NIFTY-AUTO',
        'NIFTY-FMCG', 'NIFTY-REALTY', 'NIFTY-METAL', 'NIFTY-ENERGY',
        'NIFTY-HEALTHCARE-INDEX', 'NIFTY-CONSUMER-DURABLES'
    ]
    
    print(f"\n📄 PDF generator uses these {len(pdf_sectors)} sectors:")
    for i, sector in enumerate(pdf_sectors, 1):
        print(f"   {i}. {sector}")
    
    return pdf_sectors

def compare_sectors():
    """Compare GUI vs PDF sectors"""
    print("🔍 SECTOR COMPARISON: GUI vs PDF")
    print("=" * 50)
    
    gui_sectors = test_gui_sectors()
    pdf_sectors = test_pdf_sectors()
    
    print(f"\n📊 COMPARISON RESULTS:")
    print(f"   GUI sectors: {len(gui_sectors)}")
    print(f"   PDF sectors: {len(pdf_sectors)}")
    
    if set(gui_sectors) == set(pdf_sectors):
        print("   ✅ MATCH: GUI and PDF use the same sectors!")
    else:
        print("   ❌ MISMATCH: Different sectors used!")
        
        gui_only = set(gui_sectors) - set(pdf_sectors)
        pdf_only = set(pdf_sectors) - set(gui_sectors)
        
        if gui_only:
            print(f"\n   🎯 Only in GUI: {gui_only}")
        
        if pdf_only:
            print(f"\n   📄 Only in PDF: {pdf_only}")
    
    return gui_sectors, pdf_sectors

if __name__ == "__main__":
    gui_sectors, pdf_sectors = compare_sectors()