"""
Test script for both RSI divergence report types
"""

from scripts.generate_enhanced_rsi_divergence_pdf import generate_enhanced_pdf_report, generate_enhanced_pdf_report_7days

def test_all_signals_report():
    """Test the all signals report with a small sample"""
    print("🧪 Testing All Signals Report...")
    result = generate_enhanced_pdf_report(max_stocks=3)
    print(f"Result: {result}")
    return result

def test_7day_signals_report():
    """Test the 7-day signals report with a small sample"""
    print("🧪 Testing 7-Day Signals Report...")
    result = generate_enhanced_pdf_report_7days(max_stocks=3)
    print(f"Result: {result}")
    return result

def main():
    """Run both tests"""
    print("=" * 60)
    print("📊 RSI DIVERGENCE REPORTS TEST SUITE")
    print("=" * 60)
    
    # Test 1: All signals report
    print("\n1️⃣  TESTING ALL SIGNALS REPORT")
    print("-" * 40)
    all_result = test_all_signals_report()
    
    # Test 2: 7-day signals report
    print("\n2️⃣  TESTING 7-DAY SIGNALS REPORT")
    print("-" * 40)
    seven_day_result = test_7day_signals_report()
    
    # Summary
    print("\n📋 SUMMARY")
    print("-" * 40)
    print(f"All Signals Report: {'✅ SUCCESS' if all_result.get('success') else '❌ FAILED'}")
    if all_result.get('filename'):
        print(f"  📄 File: {all_result['filename']}")
        print(f"  📊 Stocks: {all_result.get('total_stocks', 0)}")
        print(f"  📈 Signals: {all_result.get('total_signals', 0)}")
    
    print(f"7-Day Report: {'✅ SUCCESS' if seven_day_result.get('success') else '❌ FAILED'}")
    if seven_day_result.get('filename'):
        print(f"  📄 File: {seven_day_result['filename']}")
        print(f"  📊 Stocks: {seven_day_result.get('total_stocks', 0)}")
        print(f"  📈 Signals: {seven_day_result.get('total_signals', 0)}")
    
    print("\n🎉 Both report types are now available in the Reports tab!")

if __name__ == "__main__":
    main()