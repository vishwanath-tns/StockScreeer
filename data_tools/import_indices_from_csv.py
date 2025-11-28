#!/usr/bin/env python3
"""
Import NSE Indices from CSV files into nse_indices and nse_index_constituents tables
Handles MW-NIFTY-*.csv files from indices folder

Requirements:
1. No duplicate data - check before importing
2. Create index in nse_indices table if not exists
3. Add constituents to nse_index_constituents (duplicates across indices are OK)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sync_bhav_gui import engine
from sqlalchemy import text
import pandas as pd
from datetime import datetime
import re
from pathlib import Path

def parse_index_name_from_filename(filename):
    """
    Parse index code and name from MW-NIFTY-*.csv filename
    Examples:
        MW-NIFTY-50-15-Nov-2025.csv -> (NIFTY-50, Nifty 50)
        MW-NIFTY-BANK-15-Nov-2025.csv -> (NIFTY-BANK, Nifty Bank)
    """
    # Remove MW- prefix and .csv suffix
    name = filename.replace('MW-', '').replace('.csv', '')
    
    # Remove date pattern (DD-MMM-YYYY)
    name = re.sub(r'-\d{1,2}-[A-Za-z]{3}-\d{4}$', '', name)
    
    # Index code (with hyphens)
    index_code = name
    
    # Index name (replace hyphens with spaces, title case)
    index_name = name.replace('-', ' ').title()
    # Fix specific cases
    index_name = index_name.replace('It ', 'IT ')
    index_name = index_name.replace('Psu ', 'PSU ')
    index_name = index_name.replace('Fmcg', 'FMCG')
    
    return index_code, index_name

def get_or_create_index(conn, index_code, index_name):
    """
    Get index_id if exists, otherwise create new index
    Returns: index_id
    """
    # Check if index exists
    result = conn.execute(text("""
        SELECT id FROM nse_indices 
        WHERE index_code = :index_code
    """), {'index_code': index_code})
    
    existing = result.fetchone()
    if existing:
        print(f"  ✓ Index {index_code} already exists (ID: {existing[0]})")
        return existing[0]
    
    # Create new index
    result = conn.execute(text("""
        INSERT INTO nse_indices 
        (index_code, index_name, category, is_active, created_at, updated_at)
        VALUES (:code, :name, 'SECTORAL', 1, NOW(), NOW())
    """), {'code': index_code, 'name': index_name})
    
    index_id = result.lastrowid
    print(f"  ✓ Created new index: {index_code} (ID: {index_id})")
    return index_id

def check_existing_constituents(conn, index_id, import_date):
    """
    Check if constituents for this index and date already exist
    Returns: count of existing records
    """
    result = conn.execute(text("""
        SELECT COUNT(*) FROM nse_index_constituents
        WHERE index_id = :index_id 
        AND data_date = :import_date
    """), {'index_id': index_id, 'import_date': import_date})
    
    count = result.fetchone()[0]
    return count

def import_index_file(filepath):
    """
    Import a single index CSV file
    Returns: (success, index_code, constituents_count)
    """
    filename = os.path.basename(filepath)
    print(f"\n{'='*70}")
    print(f"Processing: {filename}")
    print(f"{'='*70}")
    
    # Parse index info from filename
    try:
        index_code, index_name = parse_index_name_from_filename(filename)
        print(f"Index Code: {index_code}")
        print(f"Index Name: {index_name}")
    except Exception as e:
        print(f"❌ Error parsing filename: {e}")
        return False, None, 0
    
    # Extract date from filename
    date_match = re.search(r'(\d{1,2}-[A-Za-z]{3}-\d{4})', filename)
    if date_match:
        import_date_str = date_match.group(1)
        import_date = datetime.strptime(import_date_str, '%d-%b-%Y').date()
        print(f"Import Date: {import_date}")
    else:
        import_date = datetime.now().date()
        print(f"⚠️  No date in filename, using today: {import_date}")
    
    # Read CSV file
    try:
        df = pd.read_csv(filepath)
        print(f"Loaded {len(df)} rows from CSV")
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return False, None, 0
    
    # Clean column names (remove newlines and extra spaces)
    df.columns = [col.strip().replace('\n', ' ').replace('  ', ' ') for col in df.columns]
    
    # Skip first row if it's the index summary
    if df.iloc[0]['SYMBOL'].strip().startswith('NIFTY'):
        df = df.iloc[1:].reset_index(drop=True)
        print(f"Skipped index summary row, {len(df)} constituent rows remaining")
    
    # Connect to database
    conn = engine().connect()
    trans = conn.begin()
    
    try:
        # Get or create index
        index_id = get_or_create_index(conn, index_code, index_name)
        
        # Check for existing data (prevent duplicates)
        existing_count = check_existing_constituents(conn, index_id, import_date)
        if existing_count > 0:
            print(f"⚠️  WARNING: {existing_count} constituents already exist for {index_code} on {import_date}")
            print(f"   Skipping import to prevent duplicates")
            trans.rollback()
            conn.close()
            return True, index_code, existing_count
        
        # Prepare constituent records
        constituents_added = 0
        
        for idx, row in df.iterrows():
            symbol = str(row['SYMBOL']).strip()
            
            # Skip empty rows
            if not symbol or symbol == '' or symbol.upper() == 'NAN':
                continue
            
            # Extract numeric values (handle NaN and string formats)
            def safe_float(val):
                if pd.isna(val):
                    return None
                try:
                    # Remove currency symbols, commas, etc.
                    val_str = str(val).replace(',', '').replace('₹', '').strip()
                    return float(val_str) if val_str else None
                except:
                    return None
            
            ltp = safe_float(row.get('LTP', None))
            prev_close = safe_float(row.get('PREV. CLOSE', None))
            chng = safe_float(row.get('CHNG', None))
            pct_chng = safe_float(row.get('%CHNG', None))
            volume = safe_float(row.get('VOLUME (shares)', None))
            value_cr = safe_float(row.get('VALUE  (₹ Crores)', None))
            
            # Insert constituent
            conn.execute(text("""
                INSERT INTO nse_index_constituents
                (index_id, symbol, data_date, ltp, prev_close, change_points, change_percent, 
                 volume, value_crores, imported_at)
                VALUES (:index_id, :symbol, :import_date, :ltp, :prev_close, :chng, :pct_chng,
                        :volume, :value_cr, NOW())
                ON DUPLICATE KEY UPDATE
                    ltp = VALUES(ltp),
                    prev_close = VALUES(prev_close),
                    change_points = VALUES(change_points),
                    change_percent = VALUES(change_percent),
                    volume = VALUES(volume),
                    value_crores = VALUES(value_crores),
                    imported_at = VALUES(imported_at)
            """), {
                'index_id': index_id,
                'symbol': symbol,
                'import_date': import_date,
                'ltp': ltp,
                'prev_close': prev_close,
                'chng': chng,
                'pct_chng': pct_chng,
                'volume': volume,
                'value_cr': value_cr
            })
            
            constituents_added += 1
        
        trans.commit()
        print(f"✅ Successfully imported {constituents_added} constituents for {index_code}")
        
        conn.close()
        return True, index_code, constituents_added
        
    except Exception as e:
        trans.rollback()
        conn.close()
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()
        return False, index_code, 0

def import_all_indices(folder_path):
    """
    Import all MW-NIFTY-*.csv files from folder
    """
    print("="*70)
    print("NSE INDICES IMPORT UTILITY")
    print("="*70)
    print(f"Folder: {folder_path}")
    print()
    
    # Find all MW-NIFTY-*.csv files
    csv_files = []
    for file in os.listdir(folder_path):
        if file.startswith('MW-NIFTY-') and file.endswith('.csv'):
            csv_files.append(os.path.join(folder_path, file))
    
    csv_files.sort()
    
    if not csv_files:
        print("❌ No MW-NIFTY-*.csv files found")
        return
    
    print(f"Found {len(csv_files)} index files to process")
    print()
    
    # Import statistics
    stats = {
        'total': len(csv_files),
        'success': 0,
        'failed': 0,
        'skipped': 0,
        'total_constituents': 0
    }
    
    results = []
    
    # Process each file
    for csv_file in csv_files:
        success, index_code, count = import_index_file(csv_file)
        
        if success:
            if count > 0:
                stats['success'] += 1
                stats['total_constituents'] += count
                results.append((index_code, count, 'imported'))
            else:
                stats['skipped'] += 1
                results.append((index_code, count, 'skipped'))
        else:
            stats['failed'] += 1
            results.append((index_code, 0, 'failed'))
    
    # Summary
    print()
    print("="*70)
    print("IMPORT SUMMARY")
    print("="*70)
    print(f"Total Files:        {stats['total']}")
    print(f"Successfully Imported: {stats['success']}")
    print(f"Skipped (Duplicates):  {stats['skipped']}")
    print(f"Failed:             {stats['failed']}")
    print(f"Total Constituents: {stats['total_constituents']}")
    print()
    
    print("Detailed Results:")
    print(f"{'Index Code':<40} {'Constituents':>12} {'Status':>12}")
    print("-"*70)
    for index_code, count, status in results:
        status_icon = '✅' if status == 'imported' else '⚠️' if status == 'skipped' else '❌'
        print(f"{index_code:<40} {count:>12} {status_icon} {status:>10}")
    
    print("="*70)

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Import NSE indices from CSV files'
    )
    parser.add_argument(
        '--folder',
        default='indices',
        help='Folder containing MW-NIFTY-*.csv files (default: indices)'
    )
    
    args = parser.parse_args()
    
    folder_path = args.folder
    
    if not os.path.exists(folder_path):
        print(f"❌ Folder not found: {folder_path}")
        return 1
    
    import_all_indices(folder_path)
    return 0

if __name__ == '__main__':
    sys.exit(main())
