#!/usr/bin/env python3
"""
NSE Indices Setup Script
=======================

This script sets up the NSE Indices Management System and imports all available index files.
"""

import os
import sys
from datetime import datetime
import logging

# Ensure we can import from indices_manager
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from indices_manager.database import db_manager
from indices_manager.importer import IndicesImporter
from indices_manager.api import indices_api


def setup_logging():
    """Set up logging for the setup process"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def create_indices_tables():
    """Create the database tables for indices"""
    print("🏗️  Creating database tables...")
    
    try:
        db_manager.create_tables_if_not_exist()
        print("✅ Database tables created/verified successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create database tables: {e}")
        return False


def import_index_files():
    """Import all index CSV files from the indices directory"""
    print("📥 Importing index files...")
    
    indices_dir = "indices"
    if not os.path.exists(indices_dir):
        print(f"❌ Indices directory not found: {indices_dir}")
        return False
    
    try:
        importer = IndicesImporter()
        
        # Import all CSV files from indices directory
        results = importer.import_directory(
            directory_path=indices_dir,
            file_pattern="*.csv",
            skip_duplicates=True
        )
        
        if results['success']:
            print(f"✅ Import completed successfully!")
            print(f"   📁 Files processed: {results['files_processed']}")
            print(f"   📊 Files imported: {results['files_imported']}")
            
            if results.get('files_skipped', 0) > 0:
                print(f"   ⏭️  Files skipped (duplicates): {results['files_skipped']}")
            
            if results.get('failed_files'):
                print(f"   ❌ Failed files: {len(results['failed_files'])}")
                for failed_file in results['failed_files'][:5]:  # Show first 5 failures
                    print(f"      - {failed_file}")
                if len(results['failed_files']) > 5:
                    print(f"      ... and {len(results['failed_files']) - 5} more")
            
            if results.get('errors'):
                print("   🔍 Errors encountered:")
                for error in results['errors'][:3]:  # Show first 3 errors
                    print(f"      - {error}")
                if len(results['errors']) > 3:
                    print(f"      ... and {len(results['errors']) - 3} more errors")
            
            return True
        else:
            print(f"❌ Import failed: {results.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Import process failed: {e}")
        return False


def verify_data_import():
    """Verify that data was imported correctly"""
    print("🔍 Verifying imported data...")
    
    try:
        # Get all indices
        indices = indices_api.get_all_indices()
        print(f"✅ Found {len(indices)} indices in database")
        
        # Show breakdown by category
        categories = {}
        for index in indices:
            category = index['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(index['index_code'])
        
        for category, index_codes in categories.items():
            print(f"   📈 {category}: {len(index_codes)} indices")
            # Show first few indices in each category
            sample_indices = index_codes[:3]
            print(f"      Examples: {', '.join(sample_indices)}")
            if len(index_codes) > 3:
                print(f"      ... and {len(index_codes) - 3} more")
        
        # Check data availability
        availability = indices_api.get_data_availability()
        if not availability.empty:
            total_data_points = availability['data_points'].sum()
            print(f"✅ Total data points imported: {total_data_points:,}")
            
            # Show indices with most data
            top_indices = availability.head(5)
            print("   📊 Top indices by data points:")
            for _, row in top_indices.iterrows():
                print(f"      - {row['index_code']}: {row['data_points']} points")
        
        # Show import status
        import_status = indices_api.get_import_status(days=1)
        if not import_status.empty:
            successful_imports = len(import_status[import_status['status'] == 'COMPLETED'])
            failed_imports = len(import_status[import_status['status'] == 'FAILED'])
            print(f"✅ Import status: {successful_imports} successful, {failed_imports} failed")
        
        return True
        
    except Exception as e:
        print(f"❌ Data verification failed: {e}")
        return False


def show_sample_data():
    """Show some sample data to demonstrate the system works"""
    print("📋 Sample data preview...")
    
    try:
        # Show NIFTY-50 latest data
        nifty50_data = indices_api.get_latest_index_data('NIFTY-50')
        if nifty50_data:
            print("📈 NIFTY-50 Latest Data:")
            print(f"   Date: {nifty50_data['data_date']}")
            print(f"   Close: {nifty50_data['close_value']:,.2f}")
            print(f"   Change: {nifty50_data['change_points']:+,.2f} ({nifty50_data['change_percent']:+.2f}%)")
            print(f"   Volume: {nifty50_data['volume']:,}")
            print(f"   Turnover: ₹{nifty50_data['value_crores']:,.2f} Cr")
        
        # Show top 5 constituents by weight
        nifty50_constituents = indices_api.get_index_constituents('NIFTY-50')
        if not nifty50_constituents.empty:
            print("🏢 NIFTY-50 Top 5 Constituents by Weight:")
            top_constituents = nifty50_constituents.head(5)
            for _, row in top_constituents.iterrows():
                print(f"   - {row['symbol']}: {row['weight_percent']:.2f}% "
                      f"(₹{row['close_price']:.2f}, {row['change_percent']:+.2f}%)")
        
        # Show sectoral performance
        sector_performance = indices_api.get_sector_performance()
        if not sector_performance.empty:
            print("🏭 Sectoral Performance:")
            for _, row in sector_performance.head(5).iterrows():
                sector_name = row['sector'] or 'N/A'
                avg_change = row['avg_change_percent'] or 0
                print(f"   - {sector_name}: {avg_change:+.2f}% avg")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to show sample data: {e}")
        return False


def main():
    """Main setup function"""
    print("🚀 NSE Indices Management System Setup")
    print("=" * 50)
    
    setup_logging()
    
    success_steps = 0
    total_steps = 4
    
    # Step 1: Create database tables
    if create_indices_tables():
        success_steps += 1
    else:
        print("⚠️  Setup failed at database creation step")
        return False
    
    print()
    
    # Step 2: Import index files
    if import_index_files():
        success_steps += 1
    else:
        print("⚠️  Setup failed at import step")
        return False
    
    print()
    
    # Step 3: Verify data
    if verify_data_import():
        success_steps += 1
    else:
        print("⚠️  Setup completed but data verification failed")
    
    print()
    
    # Step 4: Show sample data
    if show_sample_data():
        success_steps += 1
    
    print()
    print("=" * 50)
    
    if success_steps == total_steps:
        print("🎉 Setup completed successfully!")
        print()
        print("📝 Next steps:")
        print("  1. Explore data: python indices_cli.py list indices")
        print("  2. Show NIFTY-50: python indices_cli.py show NIFTY-50")
        print("  3. Show constituents: python indices_cli.py show NIFTY-50 --constituents")
        print("  4. Check status: python indices_cli.py status")
        print()
        print("💻 API Usage:")
        print("  from indices_manager import indices_api")
        print("  indices = indices_api.get_all_indices()")
        print("  nifty50_data = indices_api.get_latest_index_data('NIFTY-50')")
        print("  constituents = indices_api.get_index_constituents('NIFTY-50')")
        
        return True
    else:
        print(f"⚠️  Setup completed with issues ({success_steps}/{total_steps} steps successful)")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)