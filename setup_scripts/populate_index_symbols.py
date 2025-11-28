"""
Simple Index Symbols Populator
==============================

A simplified approach to populate index symbols in the database.
"""

import os
import pandas as pd
from datetime import datetime, date
import sys
from sqlalchemy import text

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reporting_adv_decl import engine

def populate_index_symbols():
    """
    Populate index symbols from CSV files
    """
    indices_folder = "indices"
    
    if not os.path.exists(indices_folder):
        print(f"ERROR: {indices_folder} folder not found")
        return
    
    csv_files = [f for f in os.listdir(indices_folder) if f.endswith('.csv')]
    print(f"Found {len(csv_files)} CSV files")
    
    stats = {"processed": 0, "symbols_added": 0, "errors": 0}
    
    with engine().connect() as conn:
        
        for csv_file in csv_files:
            try:
                print(f"\nProcessing: {csv_file}")
                
                # Parse filename to get index code
                index_code = parse_index_code(csv_file)
                if not index_code:
                    print(f"  Could not parse index code from {csv_file}")
                    stats["errors"] += 1
                    continue
                
                # Get index ID
                result = conn.execute(text("SELECT id FROM nse_indices WHERE index_code = :code"), {"code": index_code})
                row = result.fetchone()
                
                if not row:
                    print(f"  Index {index_code} not found in database")
                    stats["errors"] += 1
                    continue
                
                index_id = row[0]
                print(f"  Found index ID: {index_id} for {index_code}")
                
                # Read CSV and extract symbols
                file_path = os.path.join(indices_folder, csv_file)
                df = pd.read_csv(file_path)
                
                if df.empty:
                    print(f"  Empty CSV file")
                    continue
                
                # Extract symbols (skip first row which is usually index data)
                symbols = []
                for idx, row in df.iterrows():
                    if idx == 0:  # Skip index data
                        continue
                    
                    symbol = str(row.iloc[0]).strip()
                    if symbol and symbol != 'nan' and len(symbol) > 1:
                        symbols.append(symbol)
                
                print(f"  Found {len(symbols)} symbols")
                
                # Clear existing constituents for this index
                conn.execute(text("DELETE FROM nse_index_constituents WHERE index_id = :id"), {"id": index_id})
                
                # Insert new constituents
                data_date = date(2025, 11, 15)  # Use consistent date
                
                for symbol in symbols:
                    try:
                        conn.execute(text("""
                            INSERT INTO nse_index_constituents 
                            (index_id, symbol, data_date, series, is_active) 
                            VALUES (:index_id, :symbol, :data_date, :series, :is_active)
                        """), {
                            "index_id": index_id, 
                            "symbol": symbol, 
                            "data_date": data_date, 
                            "series": 'EQ', 
                            "is_active": True
                        })
                        
                        stats["symbols_added"] += 1
                        
                    except Exception as e:
                        print(f"    Failed to insert {symbol}: {e}")
                
                print(f"  ✅ Added {len(symbols)} symbols for {index_code}")
                stats["processed"] += 1
                
            except Exception as e:
                print(f"  ❌ Error processing {csv_file}: {e}")
                stats["errors"] += 1
        
        # Commit all changes
        conn.commit()
        print(f"\n✅ Completed! Stats: {stats}")

def parse_index_code(filename):
    """Extract index code from filename like MW-NIFTY-50-15-Nov-2025.csv"""
    try:
        # Remove MW- prefix and .csv suffix
        base_name = filename.replace('MW-', '').replace('.csv', '')
        
        # Split by dash and take all parts except last 3 (which are date)
        parts = base_name.split('-')
        if len(parts) < 4:
            return None
        
        # Index code is everything except last 3 parts (DD-Mon-YYYY)
        index_code = '-'.join(parts[:-3])
        return index_code
        
    except Exception as e:
        print(f"Error parsing filename {filename}: {e}")
        return None

def test_symbol_access():
    """Test accessing symbols from database"""
    print("\n🧪 Testing symbol access...")
    
    with engine().connect() as conn:
        # Get all indices with constituent counts
        result = conn.execute(text("""
            SELECT ni.index_code, ni.index_name, COUNT(nc.symbol) as symbol_count
            FROM nse_indices ni
            LEFT JOIN nse_index_constituents nc ON ni.id = nc.index_id
            GROUP BY ni.id, ni.index_code, ni.index_name
            ORDER BY symbol_count DESC
        """))
        
        indices = result.fetchall()
        print(f"Index Summary ({len(indices)} indices):")
        for idx in indices:
            print(f"  {idx[0]:<25} {idx[1]:<30} {idx[2]:>3} symbols")
        
        # Test getting symbols for specific indices
        test_indices = ['NIFTY-50', 'NIFTY-BANK', 'NIFTY-IT', 'NIFTY-PHARMA']
        
        for index_code in test_indices:
            result = conn.execute(text("""
                SELECT nc.symbol
                FROM nse_index_constituents nc
                JOIN nse_indices ni ON nc.index_id = ni.id
                WHERE ni.index_code = :code
                ORDER BY nc.symbol
            """), {"code": index_code})
            
            symbols = [row[0] for row in result.fetchall()]
            print(f"\n{index_code} ({len(symbols)} symbols):")
            if symbols:
                # Show first 10 symbols
                for symbol in symbols[:10]:
                    print(f"  {symbol}")
                if len(symbols) > 10:
                    print(f"  ... and {len(symbols) - 10} more")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "populate":
        populate_index_symbols()
    elif len(sys.argv) > 1 and sys.argv[1] == "test":
        test_symbol_access()
    else:
        print("Usage:")
        print("  python populate_index_symbols.py populate")
        print("  python populate_index_symbols.py test")