"""
Index Symbols Service
====================

Service for managing index constituents and providing API access to symbols by index.
Handles populating database from CSV files and providing fast access to index symbols.
"""

import os
import pandas as pd
from datetime import datetime, date
from typing import List, Dict, Optional, Set
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IndexSymbolsService:
    """
    Service for managing index symbols and constituents
    """
    
    def __init__(self):
        """Initialize the service"""
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from reporting_adv_decl import engine
        self.engine = engine
        self.indices_folder = "indices"
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Ensure required tables exist"""
        with self.engine().connect() as conn:
            # Check if nse_indices table exists and has data
            try:
                result = conn.execute("SELECT COUNT(*) FROM nse_indices")
                count = result.fetchone()[0]
                if count == 0:
                    logger.info("nse_indices table is empty, will populate from scratch")
            except Exception as e:
                logger.error(f"Error checking tables: {e}")
    
    def populate_indices_from_csv(self, force_refresh: bool = False) -> Dict[str, int]:
        """
        Populate indices and their constituents from CSV files
        
        Args:
            force_refresh: Whether to clear existing data and reload
            
        Returns:
            Dict with import statistics
        """
        stats = {"indices_created": 0, "constituents_imported": 0, "files_processed": 0}
        
        if not os.path.exists(self.indices_folder):
            logger.error(f"Indices folder not found: {self.indices_folder}")
            return stats
        
        csv_files = [f for f in os.listdir(self.indices_folder) if f.endswith('.csv')]
        logger.info(f"Found {len(csv_files)} CSV files in {self.indices_folder}")
        
        with self.engine().connect() as conn:
            if force_refresh:
                logger.info("Clearing existing index data...")
                conn.execute("DELETE FROM nse_index_constituents")
                conn.execute("DELETE FROM nse_indices WHERE id > 0")  # Keep structure
                conn.commit()
            
            for csv_file in csv_files:
                try:
                    result = self._process_csv_file(conn, csv_file)
                    stats["files_processed"] += 1
                    stats["indices_created"] += result["index_created"]
                    stats["constituents_imported"] += result["constituents_count"]
                    
                except Exception as e:
                    logger.error(f"Failed to process {csv_file}: {e}")
            
            conn.commit()
        
        logger.info(f"Import completed: {stats}")
        return stats
    
    def _process_csv_file(self, conn, csv_file: str) -> Dict[str, int]:
        """
        Process a single CSV file and extract index + constituents
        
        Args:
            conn: Database connection
            csv_file: CSV filename
            
        Returns:
            Dict with processing results
        """
        file_path = os.path.join(self.indices_folder, csv_file)
        
        # Extract index info from filename
        index_info = self._parse_filename(csv_file)
        if not index_info:
            raise ValueError(f"Could not parse filename: {csv_file}")
        
        index_code, data_date = index_info
        
        # Read CSV file
        df = pd.read_csv(file_path)
        if df.empty:
            raise ValueError(f"Empty CSV file: {csv_file}")
        
        # Get or create index record
        index_id = self._get_or_create_index(conn, index_code)
        
        # Extract constituents (skip first row which is usually index data)
        constituents = []
        for idx, row in df.iterrows():
            if idx == 0:  # Skip index data row
                continue
            
            symbol = str(row.iloc[0]).strip()
            if symbol and symbol != 'nan' and len(symbol) > 0:
                # Try to get company name from second column if available
                company_name = str(row.iloc[1]).strip() if len(row) > 1 else symbol
                if company_name == 'nan':
                    company_name = symbol
                
                constituents.append({
                    'symbol': symbol,
                    'company_name': company_name
                })
        
        # Insert constituents into database
        constituents_count = 0
        for constituent in constituents:
            try:
                conn.execute("""
                    INSERT INTO nse_index_constituents 
                    (index_id, symbol, data_date) 
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    symbol = VALUES(symbol)
                """, (index_id, constituent['symbol'], data_date))
                constituents_count += 1
            except Exception as e:
                logger.warning(f"Failed to insert constituent {constituent['symbol']}: {e}")
        
        logger.info(f"Processed {index_code}: {constituents_count} constituents")
        
        return {
            "index_created": 1 if index_id else 0,
            "constituents_count": constituents_count
        }
    
    def _parse_filename(self, filename: str) -> Optional[tuple]:
        """Parse index code and date from CSV filename"""
        try:
            # Remove MW- prefix and .csv suffix
            base_name = filename.replace('MW-', '').replace('.csv', '')
            
            # Extract date part (last 3 parts: DD-Mon-YYYY)
            parts = base_name.split('-')
            if len(parts) < 4:
                return None
            
            # Date parts are last 3
            date_parts = parts[-3:]
            date_str = '-'.join(date_parts)
            
            try:
                parsed_date = datetime.strptime(date_str, '%d-%b-%Y').date()
            except ValueError:
                parsed_date = datetime.strptime(date_str, '%d-%B-%Y').date()
            
            # Index code is everything before date parts
            index_code = '-'.join(parts[:-3])
            
            return index_code, parsed_date
            
        except Exception as e:
            logger.error(f"Error parsing filename {filename}: {e}")
            return None
    
    def _get_or_create_index(self, conn, index_code: str) -> int:
        """Get existing index ID or create new index"""
        
        # Try to find existing index
        result = conn.execute(
            "SELECT id FROM nse_indices WHERE index_code = %s OR index_name LIKE %s",
            (index_code, f"%{index_code}%")
        )
        row = result.fetchone()
        if row:
            return row[0]
        
        # Create new index
        index_name = index_code.replace('-', ' ').title()
        category = self._determine_category(index_code)
        
        result = conn.execute("""
            INSERT INTO nse_indices (index_code, index_name, category, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (index_code, index_name, category, True, datetime.now()))
        
        return result.lastrowid
    
    def _determine_category(self, index_code: str) -> str:
        """Determine index category from code"""
        code_lower = index_code.lower()
        
        if any(sector in code_lower for sector in ['bank', 'financial', 'auto', 'it', 'pharma', 'metal', 'fmcg', 'realty', 'oil', 'gas', 'chemicals', 'healthcare', 'media']):
            return 'SECTORAL'
        elif 'nifty-50' == code_lower or 'next-50' in code_lower:
            return 'MAIN'
        else:
            return 'THEMATIC'
    
    def get_index_symbols(self, index_code: str) -> List[str]:
        """
        Get all symbols for a given index
        
        Args:
            index_code: Index code (e.g., 'NIFTY-50', 'NIFTY-BANK')
            
        Returns:
            List of symbol strings
        """
        with self.engine().connect() as conn:
            result = conn.execute("""
                SELECT DISTINCT nc.symbol 
                FROM nse_index_constituents nc
                JOIN nse_indices ni ON nc.index_id = ni.id
                WHERE ni.index_code = %s OR ni.index_name LIKE %s
                ORDER BY nc.symbol
            """, (index_code, f"%{index_code}%"))
            
            return [row[0] for row in result.fetchall()]
    
    def get_all_indices(self) -> List[Dict[str, str]]:
        """
        Get all available indices
        
        Returns:
            List of dicts with index information
        """
        with self.engine().connect() as conn:
            result = conn.execute("""
                SELECT index_code, index_name, category,
                       (SELECT COUNT(*) FROM nse_index_constituents 
                        WHERE index_id = nse_indices.id) as constituent_count
                FROM nse_indices 
                WHERE is_active = 1
                ORDER BY category, index_code
            """)
            
            return [
                {
                    "code": row[0],
                    "name": row[1],
                    "category": row[2],
                    "constituent_count": row[3]
                }
                for row in result.fetchall()
            ]
    
    def get_indices_by_category(self, category: str) -> List[Dict[str, str]]:
        """
        Get indices filtered by category
        
        Args:
            category: Category filter ('MAIN', 'SECTORAL', 'THEMATIC')
            
        Returns:
            List of index information
        """
        with self.engine().connect() as conn:
            result = conn.execute("""
                SELECT index_code, index_name, category,
                       (SELECT COUNT(*) FROM nse_index_constituents 
                        WHERE index_id = nse_indices.id) as constituent_count
                FROM nse_indices 
                WHERE category = %s AND is_active = 1
                ORDER BY index_code
            """, (category,))
            
            return [
                {
                    "code": row[0],
                    "name": row[1], 
                    "category": row[2],
                    "constituent_count": row[3]
                }
                for row in result.fetchall()
            ]
    
    def get_symbols_for_sectoral_analysis(self, sectors: List[str]) -> Dict[str, List[str]]:
        """
        Get symbols for multiple sectors for comparative analysis
        
        Args:
            sectors: List of index codes for sectors
            
        Returns:
            Dict mapping sector -> list of symbols
        """
        result = {}
        
        for sector in sectors:
            symbols = self.get_index_symbols(sector)
            result[sector] = symbols
        
        return result
    
    def search_indices(self, search_term: str) -> List[Dict[str, str]]:
        """
        Search indices by name or code
        
        Args:
            search_term: Search string
            
        Returns:
            List of matching indices
        """
        with self.engine().connect() as conn:
            result = conn.execute("""
                SELECT index_code, index_name, category,
                       (SELECT COUNT(*) FROM nse_index_constituents 
                        WHERE index_id = nse_indices.id) as constituent_count
                FROM nse_indices 
                WHERE (index_code LIKE %s OR index_name LIKE %s) 
                AND is_active = 1
                ORDER BY index_code
            """, (f"%{search_term}%", f"%{search_term}%"))
            
            return [
                {
                    "code": row[0],
                    "name": row[1],
                    "category": row[2], 
                    "constituent_count": row[3]
                }
                for row in result.fetchall()
            ]
    
    def get_index_stats(self) -> Dict[str, int]:
        """Get statistics about indices and constituents"""
        with self.engine().connect() as conn:
            # Total indices
            result = conn.execute("SELECT COUNT(*) FROM nse_indices WHERE is_active = 1")
            total_indices = result.fetchone()[0]
            
            # Total constituents
            result = conn.execute("SELECT COUNT(*) FROM nse_index_constituents")
            total_constituents = result.fetchone()[0]
            
            # Indices by category
            result = conn.execute("""
                SELECT category, COUNT(*) 
                FROM nse_indices 
                WHERE is_active = 1 
                GROUP BY category
            """)
            by_category = {row[0]: row[1] for row in result.fetchall()}
            
            return {
                "total_indices": total_indices,
                "total_constituents": total_constituents,
                "by_category": by_category
            }


# Convenience functions for easy integration
def get_index_symbols(index_code: str) -> List[str]:
    """
    Quick function to get symbols for an index
    
    Args:
        index_code: Index code (e.g., 'NIFTY-50')
        
    Returns:
        List of symbol strings
    """
    service = IndexSymbolsService()
    return service.get_index_symbols(index_code)

def get_sectoral_symbols(sector_codes: List[str]) -> Dict[str, List[str]]:
    """
    Quick function to get symbols for multiple sectors
    
    Args:
        sector_codes: List of sector index codes
        
    Returns:
        Dict mapping sector -> symbols
    """
    service = IndexSymbolsService()
    return service.get_symbols_for_sectoral_analysis(sector_codes)

def populate_index_data(force_refresh: bool = False) -> Dict[str, int]:
    """
    Quick function to populate index data from CSV files
    
    Args:
        force_refresh: Whether to clear and reload all data
        
    Returns:
        Import statistics
    """
    service = IndexSymbolsService()
    return service.populate_indices_from_csv(force_refresh)


if __name__ == "__main__":
    # CLI interface for testing
    import sys
    
    service = IndexSymbolsService()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "populate":
            force = "--force" in sys.argv
            stats = service.populate_indices_from_csv(force_refresh=force)
            print(f"Import completed: {stats}")
        
        elif command == "symbols" and len(sys.argv) > 2:
            index_code = sys.argv[2]
            symbols = service.get_index_symbols(index_code)
            print(f"Symbols in {index_code}: {len(symbols)}")
            for symbol in symbols:
                print(f"  {symbol}")
        
        elif command == "list":
            indices = service.get_all_indices()
            print(f"Available indices: {len(indices)}")
            for idx in indices:
                print(f"  {idx['code']} - {idx['name']} ({idx['constituent_count']} stocks)")
        
        elif command == "stats":
            stats = service.get_index_stats()
            print(f"Index Statistics:")
            print(f"  Total indices: {stats['total_indices']}")
            print(f"  Total constituents: {stats['total_constituents']}")
            print(f"  By category: {stats['by_category']}")
    
    else:
        print("Usage:")
        print("  python index_symbols_service.py populate [--force]")
        print("  python index_symbols_service.py symbols <INDEX_CODE>")
        print("  python index_symbols_service.py list")
        print("  python index_symbols_service.py stats")