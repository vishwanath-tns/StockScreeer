"""
Sector-wise Candlestick Pattern Scanner with Breakout Detection

This service provides comprehensive sector analysis including:
1. Latest date pattern detection for Daily/Weekly/Monthly timeframes  
2. Breakout detection from previous narrow range patterns
3. PDF report generation capabilities
4. Multi-sector scanning support

Author: Stock Screener System
Date: November 2025
"""

import os
import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from dotenv import load_dotenv
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

load_dotenv()

@dataclass
class PatternResult:
    """Data class for pattern detection results"""
    symbol: str
    sector: str
    pattern_type: str
    timeframe: str
    pattern_date: str
    current_range: float
    range_rank: int
    high_price: float
    low_price: float
    close_price: float
    volume: int
    breakout_signal: Optional[str] = None
    previous_nr_date: Optional[str] = None
    previous_nr_high: Optional[float] = None
    previous_nr_low: Optional[float] = None

@dataclass
class SectorSummary:
    """Data class for sector-level summary"""
    sector_name: str
    total_stocks: int
    pattern_counts: Dict[str, int]
    timeframe_counts: Dict[str, int] 
    breakout_counts: Dict[str, int]
    top_patterns: List[PatternResult]

class SectorPatternScanner:
    """
    Main service class for sector-wise pattern scanning and breakout detection
    """
    
    def __init__(self):
        self.engine = self._create_engine()
        self.logger = self._setup_logging()
        
        # Timeframe table mappings
        self.TIMEFRAME_TABLES = {
            'DAILY': 'nse_equity_bhavcopy_full',
            'WEEKLY': 'nse_bhav_weekly', 
            'MONTHLY': 'nse_bhav_monthly'
        }
        
        # Pattern types to scan for
        self.PATTERN_TYPES = ['NR4', 'NR7', 'NR13', 'NR21']
    
    def _create_engine(self):
        """Create database engine with connection pooling"""
        host = os.getenv('MYSQL_HOST', 'localhost')
        port = os.getenv('MYSQL_PORT', 3306)
        user = os.getenv('MYSQL_USER', 'root')
        password = os.getenv('MYSQL_PASSWORD', '')
        database = os.getenv('MYSQL_DB', 'marketdata')
        
        encoded_password = quote_plus(password) if password else ''
        connection_string = f'mysql+pymysql://{user}:{encoded_password}@{host}:{port}/{database}?charset=utf8mb4'
        
        return create_engine(
            connection_string,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False
        )
    
    def _setup_logging(self):
        """Setup logging for the scanner"""
        logger = logging.getLogger('SectorPatternScanner')
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def get_available_sectors(self) -> List[Tuple[int, str]]:
        """Get all available sectors from nse_indices table"""
        try:
            with self.engine.connect() as conn:
                query = text("SELECT id, index_name FROM nse_indices ORDER BY index_name")
                result = conn.execute(query)
                return [(row[0], row[1]) for row in result.fetchall()]
        except Exception as e:
            self.logger.error(f"Error fetching sectors: {e}")
            return []
    
    def get_sector_constituents(self, sector_ids: List[int]) -> Dict[str, List[str]]:
        """Get active constituents for given sector IDs"""
        try:
            with self.engine.connect() as conn:
                if len(sector_ids) == 1:
                    # Special case for single ID
                    query = text("""
                        SELECT DISTINCT nc.symbol, ni.index_name
                        FROM nse_index_constituents nc
                        JOIN nse_indices ni ON nc.index_id = ni.id
                        WHERE nc.index_id = :sector_id
                        AND nc.is_active = 1
                        ORDER BY ni.index_name, nc.symbol
                    """)
                    result = conn.execute(query, {"sector_id": sector_ids[0]})
                else:
                    # Multiple IDs - build query dynamically
                    placeholders = ','.join([str(id) for id in sector_ids])
                    query = text(f"""
                        SELECT DISTINCT nc.symbol, ni.index_name
                        FROM nse_index_constituents nc
                        JOIN nse_indices ni ON nc.index_id = ni.id
                        WHERE nc.index_id IN ({placeholders})
                        AND nc.is_active = 1
                        ORDER BY ni.index_name, nc.symbol
                    """)
                    result = conn.execute(query)
                
                constituents = {}
                for row in result.fetchall():
                    symbol, sector_name = row
                    if sector_name not in constituents:
                        constituents[sector_name] = []
                    constituents[sector_name].append(symbol)
                
                return constituents
        except Exception as e:
            self.logger.error(f"Error fetching constituents: {e}")
            return {}
    
    def get_latest_dates(self) -> Dict[str, str]:
        """Get latest available dates for each timeframe"""
        latest_dates = {}
        
        try:
            with self.engine.connect() as conn:
                # Daily
                result = conn.execute(text("SELECT MAX(trade_date) FROM nse_equity_bhavcopy_full"))
                latest_dates['DAILY'] = result.fetchone()[0]
                
                # Weekly  
                result = conn.execute(text("SELECT MAX(trade_date) FROM nse_bhav_weekly"))
                latest_dates['WEEKLY'] = result.fetchone()[0]
                
                # Monthly
                result = conn.execute(text("SELECT MAX(trade_date) FROM nse_bhav_monthly"))
                latest_dates['MONTHLY'] = result.fetchone()[0]
                
        except Exception as e:
            self.logger.error(f"Error fetching latest dates: {e}")
            
        return latest_dates
    
    def scan_patterns_for_latest_dates(self, sector_ids: List[int], timeframes: List[str] = None) -> List[PatternResult]:
        """
        Scan for patterns on latest available dates for specified sectors and timeframes
        """
        if timeframes is None:
            timeframes = ['DAILY', 'WEEKLY', 'MONTHLY']
            
        # Get sector constituents
        constituents = self.get_sector_constituents(sector_ids)
        if not constituents:
            self.logger.warning("No constituents found for selected sectors")
            return []
        
        # Get latest dates
        latest_dates = self.get_latest_dates()
        
        all_patterns = []
        
        for timeframe in timeframes:
            if timeframe not in latest_dates:
                continue
                
            latest_date = latest_dates[timeframe]
            self.logger.info(f"Scanning {timeframe} patterns for date: {latest_date}")
            
            patterns = self._scan_timeframe_patterns(constituents, timeframe, latest_date)
            all_patterns.extend(patterns)
        
        return all_patterns
    
    def _scan_timeframe_patterns(self, constituents: Dict[str, List[str]], timeframe: str, scan_date: str) -> List[PatternResult]:
        """Scan patterns for a specific timeframe and date"""
        patterns = []
        
        try:
            with self.engine.connect() as conn:
                # Get all symbols from constituents
                all_symbols = []
                symbol_to_sector = {}
                for sector_name, symbols in constituents.items():
                    all_symbols.extend(symbols)
                    for symbol in symbols:
                        symbol_to_sector[symbol] = sector_name
                
                if not all_symbols:
                    return patterns
                
                # Build query dynamically to handle list of symbols
                symbol_placeholders = ','.join([f"'{symbol}'" for symbol in all_symbols])
                query = text(f"""
                    SELECT 
                        cp.symbol,
                        cp.pattern_date,
                        cp.pattern_type,
                        cp.timeframe,
                        cp.current_range,
                        cp.range_rank,
                        cp.high_price,
                        cp.low_price,
                        cp.close_price,
                        cp.volume
                    FROM candlestick_patterns cp
                    WHERE cp.symbol IN ({symbol_placeholders})
                    AND cp.timeframe = :timeframe
                    AND cp.pattern_date = :scan_date
                    ORDER BY cp.symbol, cp.pattern_type
                """)
                
                result = conn.execute(query, {"timeframe": timeframe, "scan_date": scan_date})
                
                for row in result.fetchall():
                    symbol = row[0]
                    if symbol in symbol_to_sector:
                        # Handle potential null values safely
                        try:
                            current_range = float(row[4]) if row[4] is not None else 0.0
                            high_price = float(row[6]) if row[6] is not None else 0.0
                            low_price = float(row[7]) if row[7] is not None else 0.0
                            close_price = float(row[8]) if row[8] is not None else 0.0
                            volume = int(row[9]) if row[9] is not None else 0
                            range_rank = int(row[5]) if row[5] is not None else 0
                            
                            pattern = PatternResult(
                                symbol=symbol,
                                sector=symbol_to_sector[symbol],
                                pattern_type=row[2],
                                timeframe=row[3],
                                pattern_date=str(row[1]),
                                current_range=current_range,
                                range_rank=range_rank,
                                high_price=high_price,
                                low_price=low_price,
                                close_price=close_price,
                                volume=volume
                            )
                            patterns.append(pattern)
                        except (ValueError, TypeError) as e:
                            self.logger.warning(f"Skipping pattern for {symbol} due to data issue: {e}")
                            continue
                        
        except Exception as e:
            self.logger.error(f"Error scanning {timeframe} patterns: {e}")
        
        return patterns
    
    def detect_breakouts(self, patterns: List[PatternResult]) -> List[PatternResult]:
        """
        Detect breakouts from previous narrow range patterns
        Check if current price is above previous NR high or below NR low
        """
        breakout_patterns = []
        
        try:
            with self.engine.connect() as conn:
                for pattern in patterns:
                    # Get current price data
                    current_data = self._get_current_price_data(conn, pattern.symbol, pattern.timeframe)
                    if not current_data:
                        continue
                    
                    # Find previous NR pattern
                    previous_nr = self._find_previous_nr_pattern(conn, pattern.symbol, pattern.timeframe, pattern.pattern_date)
                    if not previous_nr:
                        continue
                    
                    # Check for breakout
                    breakout_signal = self._check_breakout(current_data, previous_nr)
                    if breakout_signal:
                        # Create new pattern with breakout info
                        breakout_pattern = PatternResult(
                            symbol=pattern.symbol,
                            sector=pattern.sector,
                            pattern_type=pattern.pattern_type,
                            timeframe=pattern.timeframe,
                            pattern_date=pattern.pattern_date,
                            current_range=pattern.current_range,
                            range_rank=pattern.range_rank,
                            high_price=current_data['high'],
                            low_price=current_data['low'],
                            close_price=current_data['close'],
                            volume=current_data['volume'],
                            breakout_signal=breakout_signal,
                            previous_nr_date=str(previous_nr['date']),
                            previous_nr_high=previous_nr['high'],
                            previous_nr_low=previous_nr['low']
                        )
                        breakout_patterns.append(breakout_pattern)
                        
        except Exception as e:
            self.logger.error(f"Error detecting breakouts: {e}")
        
        return breakout_patterns
    
    def _get_current_price_data(self, conn, symbol: str, timeframe: str) -> Optional[Dict]:
        """Get current/latest price data for a symbol"""
        try:
            table = self.TIMEFRAME_TABLES[timeframe]
            
            if timeframe == 'DAILY':
                query = text(f"""
                    SELECT high_price, low_price, close_price, deliv_qty
                    FROM {table}
                    WHERE symbol = :symbol
                    ORDER BY trade_date DESC
                    LIMIT 1
                """)
            else:
                query = text(f"""
                    SELECT high, low, close, volume
                    FROM {table}
                    WHERE symbol = :symbol
                    ORDER BY trade_date DESC
                    LIMIT 1
                """)
            
            result = conn.execute(query, {"symbol": symbol})
            row = result.fetchone()
            
            if row:
                return {
                    'high': float(row[0]) if row[0] is not None else 0.0,
                    'low': float(row[1]) if row[1] is not None else 0.0, 
                    'close': float(row[2]) if row[2] is not None else 0.0,
                    'volume': int(row[3]) if row[3] is not None else 0
                }
        except Exception as e:
            self.logger.error(f"Error getting current data for {symbol}: {e}")
        
        return None
    
    def _find_previous_nr_pattern(self, conn, symbol: str, timeframe: str, current_date: str) -> Optional[Dict]:
        """Find the most recent previous narrow range pattern for a symbol"""
        try:
            # Look for previous NR patterns (any type)
            query = text("""
                SELECT pattern_date, high_price, low_price, pattern_type
                FROM candlestick_patterns
                WHERE symbol = :symbol
                AND timeframe = :timeframe
                AND pattern_date < :current_date
                AND pattern_type IN ('NR4', 'NR7', 'NR13', 'NR21')
                ORDER BY pattern_date DESC
                LIMIT 1
            """)
            
            result = conn.execute(query, {
                "symbol": symbol,
                "timeframe": timeframe, 
                "current_date": current_date
            })
            row = result.fetchone()
            
            if row:
                return {
                    'date': row[0],
                    'high': float(row[1]) if row[1] is not None else 0.0,
                    'low': float(row[2]) if row[2] is not None else 0.0,
                    'pattern_type': row[3]
                }
        except Exception as e:
            self.logger.error(f"Error finding previous NR for {symbol}: {e}")
        
        return None
    
    def _check_breakout(self, current_data: Dict, previous_nr: Dict) -> Optional[str]:
        """Check if current price shows breakout from previous NR pattern"""
        current_high = current_data['high']
        current_low = current_data['low']
        nr_high = previous_nr['high']
        nr_low = previous_nr['low']
        
        # Breakout above previous NR high
        if current_high > nr_high:
            return f"BREAKOUT_ABOVE (Current High: {current_high:.2f} > NR High: {nr_high:.2f})"
        
        # Breakdown below previous NR low  
        if current_low < nr_low:
            return f"BREAKDOWN_BELOW (Current Low: {current_low:.2f} < NR Low: {nr_low:.2f})"
        
        return None
    
    def generate_sector_summaries(self, patterns: List[PatternResult]) -> List[SectorSummary]:
        """Generate summary statistics for each sector"""
        sector_data = {}
        
        # Group patterns by sector
        for pattern in patterns:
            sector = pattern.sector
            if sector not in sector_data:
                sector_data[sector] = {
                    'patterns': [],
                    'symbols': set()
                }
            
            sector_data[sector]['patterns'].append(pattern)
            sector_data[sector]['symbols'].add(pattern.symbol)
        
        # Create summaries
        summaries = []
        for sector_name, data in sector_data.items():
            patterns_list = data['patterns']
            
            # Count patterns by type
            pattern_counts = {}
            for pattern_type in self.PATTERN_TYPES:
                pattern_counts[pattern_type] = sum(1 for p in patterns_list if p.pattern_type == pattern_type)
            
            # Count patterns by timeframe
            timeframe_counts = {}
            for timeframe in ['DAILY', 'WEEKLY', 'MONTHLY']:
                timeframe_counts[timeframe] = sum(1 for p in patterns_list if p.timeframe == timeframe)
            
            # Count breakouts
            breakout_counts = {
                'BREAKOUT_ABOVE': sum(1 for p in patterns_list if p.breakout_signal and 'BREAKOUT_ABOVE' in p.breakout_signal),
                'BREAKDOWN_BELOW': sum(1 for p in patterns_list if p.breakout_signal and 'BREAKDOWN_BELOW' in p.breakout_signal),
                'NO_BREAKOUT': sum(1 for p in patterns_list if not p.breakout_signal)
            }
            
            # Get top patterns (sorted by volume)
            top_patterns = sorted(patterns_list, key=lambda x: x.volume, reverse=True)[:10]
            
            summary = SectorSummary(
                sector_name=sector_name,
                total_stocks=len(data['symbols']),
                pattern_counts=pattern_counts,
                timeframe_counts=timeframe_counts,
                breakout_counts=breakout_counts,
                top_patterns=top_patterns
            )
            
            summaries.append(summary)
        
        return sorted(summaries, key=lambda x: x.sector_name)
    
    def scan_sectors_comprehensive(self, sector_ids: List[int], timeframes: List[str] = None, 
                                  include_breakouts: bool = True) -> Tuple[List[PatternResult], List[SectorSummary]]:
        """
        Comprehensive sector scanning including patterns and breakouts
        Returns both detailed patterns and sector summaries
        """
        self.logger.info(f"Starting comprehensive sector scan for {len(sector_ids)} sectors")
        
        # Scan for patterns on latest dates
        patterns = self.scan_patterns_for_latest_dates(sector_ids, timeframes)
        self.logger.info(f"Found {len(patterns)} patterns")
        
        # Detect breakouts if requested
        if include_breakouts:
            breakout_patterns = self.detect_breakouts(patterns)
            self.logger.info(f"Found {len(breakout_patterns)} breakout patterns")
            
            # Combine patterns (keeping originals + adding breakouts)
            all_patterns = patterns + breakout_patterns
        else:
            all_patterns = patterns
        
        # Generate sector summaries
        summaries = self.generate_sector_summaries(all_patterns)
        self.logger.info(f"Generated summaries for {len(summaries)} sectors")
        
        return all_patterns, summaries

# Convenience functions for quick usage
def scan_nifty_bank_patterns():
    """Quick function to scan Nifty Bank patterns"""
    scanner = SectorPatternScanner()
    bank_sector_id = 4  # Nifty Bank
    patterns, summaries = scanner.scan_sectors_comprehensive([bank_sector_id])
    return patterns, summaries

def scan_all_nifty_sectors():
    """Quick function to scan all major Nifty sectors"""
    scanner = SectorPatternScanner()
    # Major sectors: Nifty 50, Bank, Financial Services, etc.
    major_sectors = [1, 2, 4, 5, 8, 9]  # Key sector IDs
    patterns, summaries = scanner.scan_sectors_comprehensive(major_sectors)
    return patterns, summaries

if __name__ == "__main__":
    # Demo usage
    scanner = SectorPatternScanner()
    
    # Get available sectors
    sectors = scanner.get_available_sectors()
    print("Available sectors:")
    for sector_id, sector_name in sectors[:10]:
        print(f"  {sector_id}: {sector_name}")
    
    # Quick scan of Nifty Bank
    print("\nScanning Nifty Bank patterns...")
    patterns, summaries = scan_nifty_bank_patterns()
    
    if summaries:
        summary = summaries[0]
        print(f"\n{summary.sector_name} Summary:")
        print(f"  Total stocks: {summary.total_stocks}")
        print(f"  Pattern counts: {summary.pattern_counts}")
        print(f"  Breakout counts: {summary.breakout_counts}")
        
        if summary.top_patterns:
            print(f"  Top pattern: {summary.top_patterns[0].symbol} - {summary.top_patterns[0].pattern_type}")