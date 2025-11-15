"""
Index Symbols API
=================

Simple API for accessing index symbols from database.
Ready to import into other modules for sectoral analysis.
"""

import sys
import os
from typing import List, Dict, Optional
from sqlalchemy import text

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reporting_adv_decl import engine

class IndexSymbolsAPI:
    """
    API for accessing index symbols from database
    """
    
    def __init__(self):
        """Initialize the API"""
        self.engine = engine
        self._cache = {}
    
    def get_index_symbols(self, index_code: str, use_cache: bool = True) -> List[str]:
        """
        Get all symbols for a given index
        
        Args:
            index_code: Index code (e.g., 'NIFTY-50', 'NIFTY-BANK')
            use_cache: Whether to use cached results
            
        Returns:
            List of symbol strings
        """
        if use_cache and index_code in self._cache:
            return self._cache[index_code]
        
        with self.engine().connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT nc.symbol 
                FROM nse_index_constituents nc
                JOIN nse_indices ni ON nc.index_id = ni.id
                WHERE ni.index_code = :code
                ORDER BY nc.symbol
            """), {"code": index_code})
            
            symbols = [row[0] for row in result.fetchall()]
            
            if use_cache:
                self._cache[index_code] = symbols
            
            return symbols
    
    def get_sectoral_symbols(self, sector_codes: List[str]) -> Dict[str, List[str]]:
        """
        Get symbols for multiple sectors for comparative analysis
        
        Args:
            sector_codes: List of sector index codes
            
        Returns:
            Dict mapping sector -> list of symbols
        """
        result = {}
        for sector in sector_codes:
            result[sector] = self.get_index_symbols(sector)
        return result
    
    def get_all_indices(self) -> Dict[str, Dict[str, str]]:
        """
        Get all available indices with metadata
        
        Returns:
            Dict mapping index_code -> {name, category, symbol_count}
        """
        with self.engine().connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    ni.index_code, 
                    ni.index_name, 
                    ni.category,
                    COUNT(nc.symbol) as symbol_count
                FROM nse_indices ni
                LEFT JOIN nse_index_constituents nc ON ni.id = nc.index_id
                WHERE ni.is_active = 1
                GROUP BY ni.id, ni.index_code, ni.index_name, ni.category
                ORDER BY ni.category, symbol_count DESC
            """))
            
            indices = {}
            for row in result.fetchall():
                indices[row[0]] = {
                    "name": row[1],
                    "category": row[2],
                    "symbol_count": row[3]
                }
            
            return indices
    
    def search_indices(self, search_term: str) -> List[str]:
        """
        Search for indices by name or code
        
        Args:
            search_term: Search string
            
        Returns:
            List of matching index codes
        """
        with self.engine().connect() as conn:
            result = conn.execute(text("""
                SELECT index_code
                FROM nse_indices 
                WHERE (index_code LIKE :term OR index_name LIKE :term) 
                AND is_active = 1
                ORDER BY index_code
            """), {"term": f"%{search_term}%"})
            
            return [row[0] for row in result.fetchall()]
    
    def get_category_indices(self, category: str) -> List[str]:
        """
        Get all indices in a category
        
        Args:
            category: Category ('MAIN', 'SECTORAL', etc.)
            
        Returns:
            List of index codes in that category
        """
        with self.engine().connect() as conn:
            result = conn.execute(text("""
                SELECT index_code
                FROM nse_indices 
                WHERE category = :category AND is_active = 1
                ORDER BY index_code
            """), {"category": category})
            
            return [row[0] for row in result.fetchall()]
    
    def get_symbol_count(self, index_code: str) -> int:
        """
        Get count of symbols in an index
        
        Args:
            index_code: Index code
            
        Returns:
            Number of symbols in the index
        """
        with self.engine().connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM nse_index_constituents nc
                JOIN nse_indices ni ON nc.index_id = ni.id
                WHERE ni.index_code = :code
            """), {"code": index_code})
            
            return result.fetchone()[0]


# Global API instance for easy importing
_api_instance = None

def get_api() -> IndexSymbolsAPI:
    """Get singleton API instance"""
    global _api_instance
    if _api_instance is None:
        _api_instance = IndexSymbolsAPI()
    return _api_instance


# Convenience functions for direct importing
def get_index_symbols(index_code: str) -> List[str]:
    """
    Get symbols for an index
    
    Args:
        index_code: Index code (e.g., 'NIFTY-50')
        
    Returns:
        List of symbols
        
    Example:
        from services.index_symbols_api import get_index_symbols
        nifty50_symbols = get_index_symbols('NIFTY-50')
    """
    return get_api().get_index_symbols(index_code)


def get_sectoral_symbols(sectors: List[str]) -> Dict[str, List[str]]:
    """
    Get symbols for multiple sectors
    
    Args:
        sectors: List of sector index codes
        
    Returns:
        Dict mapping sector -> symbols
        
    Example:
        from services.index_symbols_api import get_sectoral_symbols
        sectors = get_sectoral_symbols(['NIFTY-BANK', 'NIFTY-IT', 'NIFTY-PHARMA'])
    """
    return get_api().get_sectoral_symbols(sectors)


def get_all_bank_symbols() -> List[str]:
    """Get all banking symbols"""
    return get_index_symbols('NIFTY-BANK')


def get_all_it_symbols() -> List[str]:
    """Get all IT symbols"""  
    return get_index_symbols('NIFTY-IT')


def get_all_pharma_symbols() -> List[str]:
    """Get all pharma symbols"""
    return get_index_symbols('NIFTY-PHARMA')


def get_all_auto_symbols() -> List[str]:
    """Get all auto symbols"""
    return get_index_symbols('NIFTY-AUTO')


def get_all_nifty50_symbols() -> List[str]:
    """Get all NIFTY-50 symbols"""
    return get_index_symbols('NIFTY-50')


def list_all_indices() -> Dict[str, Dict[str, str]]:
    """
    Get all available indices
    
    Returns:
        Dict with index info
        
    Example:
        from services.index_symbols_api import list_all_indices
        indices = list_all_indices()
        for code, info in indices.items():
            print(f"{code}: {info['name']} ({info['symbol_count']} stocks)")
    """
    return get_api().get_all_indices()


if __name__ == "__main__":
    # Demo usage
    print("🧪 Index Symbols API Demo")
    print("=" * 40)
    
    # Test basic functionality
    api = get_api()
    
    # Get NIFTY-50 symbols
    nifty50 = get_index_symbols('NIFTY-50')
    print(f"NIFTY-50 symbols ({len(nifty50)}):")
    for i, symbol in enumerate(nifty50[:10]):
        print(f"  {symbol}")
    if len(nifty50) > 10:
        print(f"  ... and {len(nifty50) - 10} more")
    
    # Test sectoral analysis
    print(f"\n📊 Sectoral Analysis:")
    sectors = get_sectoral_symbols(['NIFTY-BANK', 'NIFTY-IT', 'NIFTY-PHARMA'])
    for sector, symbols in sectors.items():
        print(f"  {sector}: {len(symbols)} symbols")
    
    # List all indices
    print(f"\n📈 All Available Indices:")
    all_indices = list_all_indices()
    for code, info in list(all_indices.items())[:10]:
        print(f"  {code:<25} {info['name']:<30} {info['symbol_count']:>3} stocks")
    
    print(f"\n✅ API is ready for use!")