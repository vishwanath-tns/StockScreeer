#!/usr/bin/env python3
"""
Test script for 5-year bulk download functionality
Demonstrates the enhanced Yahoo Finance integration system capabilities.
"""

import sys
import os
import logging
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from yahoo_finance_service.bulk_stock_downloader import BulkStockDataDownloader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_5year_bulk_download.log')
    ]
)

logger = logging.getLogger(__name__)

def test_bulk_download_sample():
    """Test bulk download with a small sample of symbols"""
    
    print("🚀 Testing Yahoo Finance 5-Year Bulk Download System")
    print("=" * 60)
    
    try:
        # Initialize the downloader
        downloader = BulkStockDataDownloader()
        
        # Calculate 5-year date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=5 * 365)  # 5 years
        
        print(f"📅 Date Range: {start_date} to {end_date}")
        
        # Test with a small sample of mapped symbols
        test_symbols = [
            {'nse_symbol': 'RELIANCE', 'yahoo_symbol': 'RELIANCE.NS'},
            {'nse_symbol': 'TCS', 'yahoo_symbol': 'TCS.NS'},
            {'nse_symbol': 'INFY', 'yahoo_symbol': 'INFY.NS'}
        ]
        
        print(f"🧪 Testing with {len(test_symbols)} sample symbols:")
        for mapping in test_symbols:
            print(f"   • {mapping['nse_symbol']} -> {mapping['yahoo_symbol']}")
        
        print("\\n⏳ Starting download process...")
        
        # Track results
        total_symbols = len(test_symbols)
        successful_downloads = 0
        failed_downloads = 0
        
        for i, mapping in enumerate(test_symbols, 1):
            print(f"\\n📊 [{i}/{total_symbols}] Downloading {mapping['yahoo_symbol']}...")
            
            try:
                # Download the data using the bulk downloader
                result = downloader.download_single_stock_data(
                    mapping=mapping,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if result['status'] == 'SUCCESS':
                    print(f"✅ {mapping['yahoo_symbol']} - Download successful ({result['records_downloaded']} records)")
                    successful_downloads += 1
                else:
                    print(f"❌ {mapping['yahoo_symbol']} - Download failed: {result.get('error_message', 'Unknown error')}")
                    failed_downloads += 1
                    
            except Exception as e:
                print(f"❌ {mapping['yahoo_symbol']} - Download failed: {e}")
                failed_downloads += 1
                logger.error(f"Error downloading {mapping['yahoo_symbol']}: {e}")
        
        # Summary
        print("\\n" + "=" * 60)
        print("📈 BULK DOWNLOAD TEST SUMMARY")
        print("=" * 60)
        print(f"Total Symbols Tested: {total_symbols}")
        print(f"Successful Downloads: {successful_downloads}")
        print(f"Failed Downloads: {failed_downloads}")
        print(f"Success Rate: {(successful_downloads/total_symbols)*100:.1f}%")
        
        if successful_downloads > 0:
            print("\\n✨ Test completed successfully! The bulk download system is working.")
            print("💡 You can now use the GUI's '📥 5Y All Stocks' button for full bulk download.")
        else:
            print("\\n⚠️ All downloads failed. Please check your internet connection and database configuration.")
        
        return successful_downloads > 0
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        print(f"\\n❌ Test failed: {e}")
        return False

def main():
    """Main test function"""
    print("Yahoo Finance 5-Year Bulk Download Test")
    print("Testing enhanced integration system...")
    print()
    
    success = test_bulk_download_sample()
    
    if success:
        print("\\n🎉 Ready for production use!")
        print("\\n📋 Next steps:")
        print("1. Run the GUI: python yahoo_finance_service\\yfinance_downloader_gui.py")
        print("2. Click '📥 5Y All Stocks' for full bulk download")
        print("3. Monitor progress through the GUI interface")
    else:
        print("\\n🔧 System needs attention before full deployment.")
        
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)