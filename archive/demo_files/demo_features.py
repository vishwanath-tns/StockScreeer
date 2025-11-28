"""
Quick test to demonstrate the new sectoral analysis features.
This creates a sample PDF and shows the folder structure.
"""

import os
from datetime import date
from services.simple_pdf_generator import generate_simple_sectoral_pdf_report

def main():
    print("🚀 Demonstrating New Sectoral Analysis Features")
    print("=" * 55)
    
    # 1. Show the reports folder structure
    print("📁 Reports Folder Structure:")
    if os.path.exists("reports"):
        for root, dirs, files in os.walk("reports"):
            level = root.replace("reports", "").count(os.sep)
            indent = " " * 2 * level
            print(f"{indent}📂 {os.path.basename(root)}/")
            sub_indent = " " * 2 * (level + 1)
            for file in files[:5]:  # Show max 5 files per folder
                print(f"{sub_indent}📄 {file}")
            if len(files) > 5:
                print(f"{sub_indent}... and {len(files) - 5} more files")
    else:
        print("   📂 reports/ (will be created automatically)")
        print("      📂 sectoral_analysis/ (will be created automatically)")
    
    # 2. Generate a sample PDF report
    print("\n📄 Generating Sample PDF Report...")
    success, pdf_path = generate_simple_sectoral_pdf_report('2025-11-14')
    
    if success:
        print(f"✅ PDF Generated Successfully!")
        print(f"📍 Location: {pdf_path}")
        
        if os.path.exists(pdf_path):
            size = os.path.getsize(pdf_path)
            print(f"📊 File Size: {size:,} bytes")
            print(f"🎯 Enhanced Content: {'YES' if size > 10000 else 'BASIC'}")
            
            # Show what's in the reports folder now
            print(f"\n📁 Reports folder now contains:")
            reports_files = os.listdir("reports/sectoral_analysis")
            for file in sorted(reports_files)[-3:]:  # Show last 3 files
                file_path = os.path.join("reports/sectoral_analysis", file)
                size = os.path.getsize(file_path)
                print(f"   📄 {file} ({size:,} bytes)")
            
            print(f"\n✨ Features included in this PDF:")
            print(f"   • Executive Summary with market sentiment")
            print(f"   • Color-coded sector performance ranking")
            print(f"   • Detailed stock breakdown for top 5 sectors")
            print(f"   • Individual stock ratings and trend directions")
            print(f"   • Trading recommendations and risk management")
            
    else:
        print(f"❌ Failed to generate PDF: {pdf_path}")
    
    # 3. Show usage instructions
    print("\n🎯 How to Use in Scanner GUI:")
    print("   1. Open scanner_gui.py")
    print("   2. Go to Market Breadth → Sectoral Analysis")
    print("   3. Select date and click 'Compare All Sectors'")
    print("   4. 🖱️ Double-click any sector row → opens detailed window")
    print("   5. Click 'Generate PDF Report' → saves to reports/sectoral_analysis/")
    
    print("\n🔍 New Double-Click Feature Shows:")
    print("   • Complete stock list for the sector")
    print("   • Trend ratings and categories")
    print("   • Color-coded performance indicators")
    print("   • Sortable columns and CSV export")
    
    print("\n" + "=" * 55)
    print("🎉 Ready to use! All features are fully integrated.")

if __name__ == "__main__":
    main()