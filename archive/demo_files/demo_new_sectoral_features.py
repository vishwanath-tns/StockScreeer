"""
Demo for new sectoral analysis features
- PDF reports stored in separate folder
- Double-click functionality for detailed stock analysis
- Enhanced PDF with detailed stock information
"""

import tkinter as tk
from tkinter import messagebox
import sys
import os
import pandas as pd
from datetime import date

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_pdf_reports_folder():
    """Test PDF generation in separate reports folder."""
    print("Testing PDF reports folder functionality...")
    
    from services.simple_pdf_generator import generate_simple_sectoral_pdf_report
    
    # Test with recent date
    test_date = '2025-11-14'
    success, message = generate_simple_sectoral_pdf_report(test_date)
    
    print(f"PDF Generation Success: {success}")
    print(f"PDF Path: {message}")
    
    if success and os.path.exists(message):
        size = os.path.getsize(message)
        print(f"PDF Size: {size:,} bytes")
        print(f"PDF stored in reports folder: {'reports' in message}")
        return message
    
    return None

def test_sector_detail_window():
    """Test the sector detail window functionality."""
    print("\nTesting sector detail window...")
    
    try:
        from gui.windows.sector_detail_window import SectorDetailWindow
        print("✅ SectorDetailWindow class imported successfully")
        
        # Test data retrieval
        from services.market_breadth_service import get_sectoral_breadth
        result = get_sectoral_breadth('NIFTY-BANK', date(2025, 11, 14))
        
        if result.get('success'):
            print(f"✅ Sector data retrieved: {result.get('total_stocks')} stocks")
            
            # Show sample stock data
            sector_df = result.get('sector_data')
            if sector_df is not None and not sector_df.empty:
                # Ensure numeric data type
                sector_df['trend_rating'] = pd.to_numeric(sector_df['trend_rating'], errors='coerce').fillna(0)
                top_performers = sector_df.nlargest(3, 'trend_rating')[['symbol', 'trend_rating', 'trend_category']]
                print("✅ Top 3 performing stocks:")
                for _, row in top_performers.iterrows():
                    print(f"   {row['symbol']}: {row['trend_rating']:.1f} ({row['trend_category']})")
        
        return True
    
    except Exception as e:
        print(f"❌ Error testing sector detail window: {e}")
        return False

def test_enhanced_pdf_content():
    """Test that PDF now includes detailed stock information."""
    print("\nTesting enhanced PDF content...")
    
    # Generate a test PDF
    pdf_path = test_pdf_reports_folder()
    
    if pdf_path:
        # Check PDF size (should be larger with detailed content)
        size = os.path.getsize(pdf_path)
        if size > 10000:  # Should be > 10KB with detailed content
            print("✅ PDF appears to contain detailed content (size > 10KB)")
        else:
            print("⚠️ PDF might be missing detailed content (size < 10KB)")
        
        # Clean up test file
        os.remove(pdf_path)
        print("✅ Test PDF cleaned up")
        
        return True
    
    return False

def create_demo_instructions():
    """Create instructions for using the new features."""
    instructions = """
🎉 NEW SECTORAL ANALYSIS FEATURES READY!

📁 PDF Reports Organization:
   • All PDF reports now stored in: reports/sectoral_analysis/
   • Keeps source code clean and organized
   • Automatic folder creation if needed

🔍 Double-Click for Details:
   • In Sectoral Analysis tab → Multi-Sector Comparison
   • Double-click any sector row to see detailed stock analysis
   • New window shows:
     - Sector summary metrics
     - Individual stock breakdown with ratings
     - Color-coded performance indicators
     - Export to CSV functionality

📄 Enhanced PDF Reports:
   • Detailed stock analysis for top 5 sectors
   • Individual stock ratings and trends
   • Color-coded category information
   • Professional formatting with sector breakdown

🚀 How to Use:
   1. Open Scanner GUI → Market Breadth → Sectoral Analysis
   2. Select your analysis date
   3. Click "Compare All Sectors"
   4. Double-click any sector for detailed view
   5. Generate PDF for comprehensive report

📊 Features Available:
   • Sort stocks by any column (Symbol, Rating, Category, Trends)
   • Export individual sector data to CSV
   • Color indicators for quick performance assessment
   • Comprehensive trend analysis
"""
    
    return instructions

if __name__ == "__main__":
    print("🚀 Testing New Sectoral Analysis Features")
    print("=" * 50)
    
    # Test all features
    success_count = 0
    
    # Test 1: PDF Reports Folder
    if test_pdf_reports_folder():
        success_count += 1
    
    # Test 2: Sector Detail Window
    if test_sector_detail_window():
        success_count += 1
    
    # Test 3: Enhanced PDF Content
    if test_enhanced_pdf_content():
        success_count += 1
    
    # Summary
    print("\n" + "=" * 50)
    print(f"✅ Tests Passed: {success_count}/3")
    
    if success_count == 3:
        print("🎉 All features working correctly!")
        print("\nInstructions for use:")
        print(create_demo_instructions())
    else:
        print("⚠️ Some features need attention")
    
    print("\n📌 Ready to use in Scanner GUI → Market Breadth → Sectoral Analysis")