#!/usr/bin/env python3
"""
Clean and Re-import NSE Indices Data
====================================

This script cleans up failed imports and re-imports all index data.
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import reporting_adv_decl as rad
from indices_manager.importer import IndicesImporter
from indices_manager.api import indices_api


def clean_failed_imports():
    """Clean up failed/pending imports"""
    print("🧹 Cleaning up failed imports...")
    
    try:
        engine = rad.engine()
        with engine.connect() as conn:
            # Delete all pending/failed import logs
            result = conn.execute(rad.text("""
                DELETE FROM index_import_log 
                WHERE status IN ('PENDING', 'FAILED')
            """))
            
            deleted_count = result.rowcount
            conn.commit()
            
            print(f"✅ Cleaned up {deleted_count} failed import records")
            return True
            
    except Exception as e:
        print(f"❌ Failed to clean imports: {e}")
        return False


def clean_all_data():
    """Clean all indices data to start fresh"""
    print("🗑️  Cleaning all existing data...")
    
    try:
        engine = rad.engine()
        with engine.connect() as conn:
            # Clean in reverse order due to foreign keys
            tables_to_clean = [
                'nse_index_constituents',
                'nse_index_data', 
                'index_import_log'
            ]
            
            for table in tables_to_clean:
                conn.execute(rad.text(f"DELETE FROM {table}"))
                
            conn.commit()
            print(f"✅ Cleaned all data from tables: {', '.join(tables_to_clean)}")
            return True
            
    except Exception as e:
        print(f"❌ Failed to clean data: {e}")
        return False


def import_all_files():
    """Import all CSV files"""
    print("📥 Importing all index files...")
    
    try:
        importer = IndicesImporter()
        
        # Import all files from indices directory
        results = importer.import_directory(
            directory_path="indices",
            file_pattern="*.csv",
            skip_duplicates=False  # Don't skip since we cleaned up
        )
        
        if results['success']:
            print(f"✅ Import completed successfully!")
            print(f"   📁 Files processed: {results['files_processed']}")
            print(f"   📊 Files imported: {results['files_imported']}")
            
            if results.get('failed_files'):
                print(f"   ❌ Failed files: {len(results['failed_files'])}")
                for failed_file in results['failed_files'][:5]:  # Show first 5
                    print(f"      - {failed_file}")
            
            return True
        else:
            print(f"❌ Import failed: {results.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def verify_data():
    """Verify imported data"""
    print("🔍 Verifying imported data...")
    
    try:
        # Check if NIFTY-50 has data
        nifty50_data = indices_api.get_latest_index_data('NIFTY-50')
        if nifty50_data:
            print("✅ NIFTY-50 data available:")
            print(f"   Date: {nifty50_data['data_date']}")
            print(f"   Close: {nifty50_data['close_value']:,.2f}")
            print(f"   Change: {nifty50_data['change_points']:+.2f} ({nifty50_data['change_percent']:+.2f}%)")
        
        # Check constituents
        constituents_df = indices_api.get_index_constituents('NIFTY-50')
        if not constituents_df.empty:
            print(f"✅ NIFTY-50 has {len(constituents_df)} constituents")
            
            # Show top 3 by weight
            top3 = constituents_df.head(3)
            print("   Top 3 constituents by weight:")
            for _, row in top3.iterrows():
                print(f"   - {row['symbol']}: {row['weight_percent']:.2f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Data verification failed: {e}")
        return False


def main():
    """Main function"""
    print("🔄 NSE Indices Data Cleanup and Re-import")
    print("=" * 50)
    
    # Ask user what to do
    print("What would you like to do?")
    print("1. Clean failed imports only (recommended)")
    print("2. Clean all data and re-import from scratch")
    print("3. Just try import without cleaning")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        if not clean_failed_imports():
            return False
    elif choice == "2":
        if not clean_all_data():
            return False
    elif choice == "3":
        print("⏩ Skipping cleanup...")
    else:
        print("❌ Invalid choice")
        return False
    
    print()
    
    # Import files
    if not import_all_files():
        return False
    
    print()
    
    # Verify data
    verify_data()
    
    print()
    print("🎉 Process completed! You can now use:")
    print("   python indices_cli.py show NIFTY-50")
    print("   python indices_cli.py show NIFTY-50 --constituents")
    print("   python indices_cli.py list indices --category SECTORAL")
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)