"""
NSE Block & Bulk Deals - Manual CSV Importer

Since NSE blocks automated downloads, this tool processes manually downloaded CSV files.

Workflow:
1. Download CSV files from https://www.nseindia.com/all-reports
2. Place them in a folder (e.g., block_bulk_deals/downloads/)
3. Run this script to batch import them

CSV File Naming Convention (auto-detected):
- block*.csv or *block*.csv → Block Deals
- bulk*.csv or *bulk*.csv → Bulk Deals
"""

import os
import sys
import pandas as pd
from datetime import datetime
from pathlib import Path
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from block_bulk_deals.nse_deals_csv_downloader import NSEDealsDatabase

def detect_deal_type(filename: str) -> str:
    """Detect if file is block or bulk deals"""
    filename_lower = filename.lower()
    if 'block' in filename_lower:
        return 'BLOCK'
    elif 'bulk' in filename_lower:
        return 'BULK'
    else:
        return 'UNKNOWN'

def extract_date_from_filename(filename: str) -> datetime:
    """
    Try to extract date from filename
    Common patterns: block_21112025.csv, block(1).csv, etc.
    """
    # Try DDMMYYYY pattern
    match = re.search(r'(\d{8})', filename)
    if match:
        date_str = match.group(1)
        try:
            return datetime.strptime(date_str, "%d%m%Y")
        except:
            pass
    
    # If not found, return None (will prompt user)
    return None

def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize column names from NSE CSV
    
    Expected columns (from your samples):
    - Date
    - Symbol
    - Security Name
    - Client Name
    - Buy/Sell
    - Quantity Traded
    - Trade Price / Wght. Avg. Price
    - Remarks (bulk deals only)
    """
    # Strip whitespace from column names first
    df.columns = df.columns.str.strip()
    
    column_map = {
        'Date': 'trade_date',
        'Symbol': 'symbol',
        'Security Name': 'security_name',
        'Client Name': 'client_name',
        'Buy/Sell': 'deal_type',
        'Buy / Sell': 'deal_type',  # Alternative format
        'Quantity Traded': 'quantity',
        'Trade Price / Wght. Avg. Price': 'trade_price',
        'Remarks': 'remarks'
    }
    
    # Rename columns
    df_renamed = df.copy()
    for old_col, new_col in column_map.items():
        if old_col in df_renamed.columns:
            df_renamed.rename(columns={old_col: new_col}, inplace=True)
    
    # Ensure required columns
    required_cols = ['trade_date', 'symbol', 'security_name', 'client_name', 
                    'deal_type', 'quantity', 'trade_price']
    
    for col in required_cols:
        if col not in df_renamed.columns:
            df_renamed[col] = None
    
    if 'remarks' not in df_renamed.columns:
        df_renamed['remarks'] = None
    
    # Clean deal_type
    if 'deal_type' in df_renamed.columns:
        df_renamed['deal_type'] = df_renamed['deal_type'].str.upper().str.strip()
    
    # Clean numeric columns (remove commas from Indian number format)
    if 'quantity' in df_renamed.columns:
        df_renamed['quantity'] = df_renamed['quantity'].astype(str).str.replace(',', '').str.strip()
        df_renamed['quantity'] = pd.to_numeric(df_renamed['quantity'], errors='coerce')
    
    if 'trade_price' in df_renamed.columns:
        df_renamed['trade_price'] = df_renamed['trade_price'].astype(str).str.replace(',', '').str.strip()
        df_renamed['trade_price'] = pd.to_numeric(df_renamed['trade_price'], errors='coerce')
    
    # Parse trade_date if it's a string
    if 'trade_date' in df_renamed.columns and df_renamed['trade_date'].dtype == 'object':
        df_renamed['trade_date'] = pd.to_datetime(df_renamed['trade_date'], format='%d-%b-%Y', errors='coerce')
    
    # Select final columns
    final_cols = ['trade_date', 'symbol', 'security_name', 'client_name', 
                 'deal_type', 'quantity', 'trade_price', 'remarks']
    
    return df_renamed[final_cols]

def import_csv_file(filepath: str, database: NSEDealsDatabase, deal_type: str = None):
    """Import a single CSV file"""
    filename = os.path.basename(filepath)
    
    print(f"\n📄 Processing: {filename}")
    print("-" * 80)
    
    # Detect deal type if not specified
    if deal_type is None:
        deal_type = detect_deal_type(filename)
        if deal_type == 'UNKNOWN':
            print("❌ Cannot detect deal type from filename. Use --type flag.")
            return
    
    print(f"   Type: {deal_type}")
    
    try:
        # Read CSV
        df = pd.read_csv(filepath)
        print(f"   Raw records: {len(df)}")
        
        if df.empty:
            print("   ⚠️  Empty file - skipping")
            return
        
        # Standardize columns
        df = standardize_columns(df)
        
        # Extract dates from data
        if 'trade_date' in df.columns:
            dates = df['trade_date'].dropna().unique()
            if len(dates) > 0:
                trade_date = pd.to_datetime(dates[0])
                print(f"   Date: {trade_date.strftime('%d-%b-%Y')}")
            else:
                print("   ❌ No valid dates in CSV")
                return
        else:
            print("   ❌ No Date column found")
            return
        
        # Save to database
        new_records, updated_records = database.save_deals(df, deal_type)
        print(f"   ✅ Saved: {new_records} new records")
        
        # Log import
        database.log_import(trade_date, deal_type, new_records, "SUCCESS")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()

def import_folder(folder_path: str, database: NSEDealsDatabase):
    """Import all CSV files from a folder"""
    folder = Path(folder_path)
    
    if not folder.exists():
        print(f"❌ Folder not found: {folder_path}")
        return
    
    # Find all CSV files
    csv_files = list(folder.glob('*.csv'))
    
    if not csv_files:
        print(f"❌ No CSV files found in: {folder_path}")
        return
    
    print("=" * 80)
    print(f"NSE BLOCK & BULK DEALS - MANUAL CSV IMPORT")
    print("=" * 80)
    print(f"Folder: {folder_path}")
    print(f"Files found: {len(csv_files)}")
    print("=" * 80)
    
    # Process each file
    block_count = 0
    bulk_count = 0
    failed = 0
    
    for csv_file in sorted(csv_files):
        try:
            import_csv_file(str(csv_file), database)
            
            deal_type = detect_deal_type(csv_file.name)
            if deal_type == 'BLOCK':
                block_count += 1
            elif deal_type == 'BULK':
                bulk_count += 1
                
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            failed += 1
    
    # Summary
    print("\n" + "=" * 80)
    print("IMPORT COMPLETE")
    print("=" * 80)
    print(f"Block Deal files: {block_count}")
    print(f"Bulk Deal files: {bulk_count}")
    print(f"Failed: {failed}")
    print("=" * 80)

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Import manually downloaded NSE Block & Bulk Deals CSV files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import all CSV files from downloads folder
  python import_csv.py --folder block_bulk_deals/downloads
  
  # Import a single file
  python import_csv.py --file block_21112025.csv --type BLOCK
  
  # Show database statistics
  python import_csv.py --stats

Download CSV files from:
  https://www.nseindia.com/all-reports
  → Daily Reports → Equities & SME → Bulk and Block Deals
        """
    )
    
    parser.add_argument(
        '--folder',
        type=str,
        help='Folder containing CSV files to import'
    )
    
    parser.add_argument(
        '--file',
        type=str,
        help='Single CSV file to import'
    )
    
    parser.add_argument(
        '--type',
        choices=['BLOCK', 'BULK'],
        help='Deal type (if not auto-detectable from filename)'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show database statistics'
    )
    
    args = parser.parse_args()
    
    # Initialize database
    database = NSEDealsDatabase()
    
    # Show stats
    if args.stats:
        stats = database.get_import_stats()
        
        print("=" * 80)
        print("DATABASE STATISTICS")
        print("=" * 80)
        
        print("\n📊 BLOCK DEALS:")
        block = stats['block_deals']
        print(f"  Total Deals: {block['total_deals']:,}")
        if block['total_deals'] > 0:
            print(f"  Date Range: {block['earliest_date']} to {block['latest_date']}")
            print(f"  Unique Symbols: {block['unique_symbols']:,}")
            print(f"  Unique Clients: {block['unique_clients']:,}")
        
        print("\n📊 BULK DEALS:")
        bulk = stats['bulk_deals']
        print(f"  Total Deals: {bulk['total_deals']:,}")
        if bulk['total_deals'] > 0:
            print(f"  Date Range: {bulk['earliest_date']} to {bulk['latest_date']}")
            print(f"  Unique Symbols: {bulk['unique_symbols']:,}")
            print(f"  Unique Clients: {bulk['unique_clients']:,}")
        
        print("\n" + "=" * 80)
        return 0
    
    # Import folder
    if args.folder:
        import_folder(args.folder, database)
        return 0
    
    # Import single file
    if args.file:
        if not os.path.exists(args.file):
            print(f"❌ File not found: {args.file}")
            return 1
        
        import_csv_file(args.file, database, args.type)
        return 0
    
    # No action specified
    parser.print_help()
    return 1

if __name__ == "__main__":
    sys.exit(main())
