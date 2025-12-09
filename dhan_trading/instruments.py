"""
Dhan Trading System - Instrument Downloader
============================================
Downloads and syncs instrument master from Dhan API.

Dhan provides two CSV files:
1. Compact CSV: ~16 columns, uses SEM_ prefix
2. Detailed CSV: ~40 columns, no prefix, includes margin/trading params

We use the detailed CSV for more complete data.
"""
import os
import sys
import time
import logging
from datetime import datetime, date
from typing import Optional, Dict
from pathlib import Path

import pandas as pd
import requests
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dhan_trading.config import (
    DHAN_INSTRUMENTS_CSV_URL,
    DHAN_INSTRUMENTS_DETAILED_CSV_URL,
    DATA_DIR
)
from dhan_trading.db_setup import get_engine, DHAN_DB_NAME

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class InstrumentDownloader:
    """Downloads and manages Dhan instrument master data."""
    
    # Column mapping for DETAILED CSV (api-scrip-master-detailed.csv)
    DETAILED_COLUMN_MAP = {
        'SECURITY_ID': 'security_id',
        'EXCH_ID': 'exchange',
        'SEGMENT': 'segment',
        'SYMBOL_NAME': 'symbol',
        'DISPLAY_NAME': 'display_name',
        'ISIN': 'isin',
        'INSTRUMENT': 'instrument',
        'INSTRUMENT_TYPE': 'instrument_type',
        'SERIES': 'series',
        'LOT_SIZE': 'lot_size',
        'TICK_SIZE': 'tick_size',
        'SM_EXPIRY_DATE': 'expiry_date',
        'STRIKE_PRICE': 'strike_price',
        'OPTION_TYPE': 'option_type',
        'EXPIRY_FLAG': 'expiry_flag',
        'UNDERLYING_SECURITY_ID': 'underlying_security_id',
        'UNDERLYING_SYMBOL': 'underlying_symbol',
        # Trading flags
        'BRACKET_FLAG': 'bracket_flag',
        'COVER_FLAG': 'cover_flag',
        'ASM_GSM_FLAG': 'asm_gsm_flag',
        'ASM_GSM_CATEGORY': 'asm_gsm_category',
        'BUY_SELL_INDICATOR': 'buy_sell_indicator',
        'MTF_LEVERAGE': 'mtf_leverage',
        # Cover Order margins
        'BUY_CO_MIN_MARGIN_PER': 'buy_co_min_margin_per',
        'SELL_CO_MIN_MARGIN_PER': 'sell_co_min_margin_per',
        'BUY_CO_SL_RANGE_MAX_PERC': 'buy_co_sl_range_max_perc',
        'SELL_CO_SL_RANGE_MAX_PERC': 'sell_co_sl_range_max_perc',
        'BUY_CO_SL_RANGE_MIN_PERC': 'buy_co_sl_range_min_perc',
        'SELL_CO_SL_RANGE_MIN_PERC': 'sell_co_sl_range_min_perc',
        # Bracket Order margins
        'BUY_BO_MIN_MARGIN_PER': 'buy_bo_min_margin_per',
        'SELL_BO_MIN_MARGIN_PER': 'sell_bo_min_margin_per',
        'BUY_BO_SL_RANGE_MAX_PERC': 'buy_bo_sl_range_max_perc',
        'SELL_BO_SL_RANGE_MAX_PERC': 'sell_bo_sl_range_max_perc',
        'BUY_BO_SL_RANGE_MIN_PERC': 'buy_bo_sl_range_min_perc',
        'SELL_BO_SL_MIN_RANGE': 'sell_bo_sl_range_min_perc',
        'BUY_BO_PROFIT_RANGE_MAX_PERC': 'buy_bo_profit_range_max_perc',
        'SELL_BO_PROFIT_RANGE_MAX_PERC': 'sell_bo_profit_range_max_perc',
        'BUY_BO_PROFIT_RANGE_MIN_PERC': 'buy_bo_profit_range_min_perc',
        'SELL_BO_PROFIT_RANGE_MIN_PERC': 'sell_bo_profit_range_min_perc',
    }
    
    # Column mapping for COMPACT CSV (api-scrip-master.csv)
    COMPACT_COLUMN_MAP = {
        'SEM_SMST_SECURITY_ID': 'security_id',
        'SEM_EXM_EXCH_ID': 'exchange',
        'SEM_SEGMENT': 'segment',
        'SM_SYMBOL_NAME': 'symbol',
        'SEM_CUSTOM_SYMBOL': 'display_name',
        'SEM_INSTRUMENT_NAME': 'instrument',
        'SEM_EXCH_INSTRUMENT_TYPE': 'instrument_type',
        'SEM_TRADING_SYMBOL': 'trading_symbol',
        'SEM_SERIES': 'series',
        'SEM_LOT_UNITS': 'lot_size',
        'SEM_TICK_SIZE': 'tick_size',
        'SEM_EXPIRY_DATE': 'expiry_date',
        'SEM_STRIKE_PRICE': 'strike_price',
        'SEM_OPTION_TYPE': 'option_type',
        'SEM_EXPIRY_FLAG': 'expiry_flag',
        'SEM_EXPIRY_CODE': 'expiry_code',
    }
    
    def __init__(self, use_detailed: bool = True):
        """
        Initialize downloader.
        
        Args:
            use_detailed: If True, use detailed CSV (more columns)
        """
        self.use_detailed = use_detailed
        self.csv_url = DHAN_INSTRUMENTS_DETAILED_CSV_URL if use_detailed else DHAN_INSTRUMENTS_CSV_URL
        self.column_map = self.DETAILED_COLUMN_MAP if use_detailed else self.COMPACT_COLUMN_MAP
        self.engine = get_engine(DHAN_DB_NAME)
    
    def download_csv(self, save_local: bool = True) -> pd.DataFrame:
        """
        Download instrument CSV from Dhan.
        
        Args:
            save_local: If True, save a local copy
        
        Returns:
            DataFrame with instrument data
        """
        logger.info(f"Downloading instruments from {self.csv_url}...")
        start_time = time.time()
        
        try:
            response = requests.get(self.csv_url, timeout=120)
            response.raise_for_status()
            
            # Save local copy
            if save_local:
                today_str = date.today().strftime('%Y%m%d')
                csv_type = 'detailed' if self.use_detailed else 'compact'
                filename = f"dhan_instruments_{csv_type}_{today_str}.csv"
                filepath = DATA_DIR / filename
                filepath.write_bytes(response.content)
                logger.info(f"Saved local copy to {filepath}")
            
            # Parse CSV
            from io import StringIO
            df = pd.read_csv(StringIO(response.text), low_memory=False)
            
            duration = time.time() - start_time
            logger.info(f"Downloaded {len(df):,} instruments in {duration:.1f}s")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to download: {e}")
            raise
    
    def process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process and clean the instrument DataFrame.
        
        Args:
            df: Raw DataFrame from CSV
        
        Returns:
            Cleaned DataFrame ready for database
        """
        logger.info("Processing instrument data...")
        logger.info(f"CSV columns ({len(df.columns)}): {df.columns.tolist()[:10]}...")
        
        # Create a clean DataFrame with our target columns
        clean_df = pd.DataFrame()
        
        # Map columns that exist
        for csv_col, db_col in self.column_map.items():
            if csv_col in df.columns:
                clean_df[db_col] = df[csv_col]
            else:
                logger.debug(f"Column {csv_col} not found in CSV")
        
        # Create exchange_segment
        if 'exchange' in clean_df.columns and 'segment' in clean_df.columns:
            segment_map = {'E': 'EQ', 'D': 'FNO', 'C': 'CURRENCY', 'M': 'COMM'}
            clean_df['exchange_segment'] = clean_df.apply(
                lambda r: f"{r['exchange']}_{segment_map.get(str(r['segment']), str(r['segment']))}" 
                if pd.notna(r['exchange']) and pd.notna(r['segment']) else None, 
                axis=1
            )
        
        # Convert expiry_date to proper date format
        if 'expiry_date' in clean_df.columns:
            clean_df['expiry_date'] = pd.to_datetime(clean_df['expiry_date'], errors='coerce').dt.date
        
        # Convert numeric columns
        numeric_cols = [
            'security_id', 'lot_size', 'tick_size', 'strike_price', 'underlying_security_id',
            'mtf_leverage', 'buy_co_min_margin_per', 'sell_co_min_margin_per',
            'buy_co_sl_range_max_perc', 'sell_co_sl_range_max_perc',
            'buy_co_sl_range_min_perc', 'sell_co_sl_range_min_perc',
            'buy_bo_min_margin_per', 'sell_bo_min_margin_per',
            'buy_bo_sl_range_max_perc', 'sell_bo_sl_range_max_perc',
            'buy_bo_sl_range_min_perc', 'sell_bo_sl_range_min_perc',
            'buy_bo_profit_range_max_perc', 'sell_bo_profit_range_max_perc',
            'buy_bo_profit_range_min_perc', 'sell_bo_profit_range_min_perc',
        ]
        
        for col in numeric_cols:
            if col in clean_df.columns:
                clean_df[col] = pd.to_numeric(clean_df[col], errors='coerce')
        
        # Add timestamp
        clean_df['updated_at'] = datetime.now()
        
        logger.info(f"Processed {len(clean_df):,} instruments with {len(clean_df.columns)} columns")
        logger.info(f"DB columns: {clean_df.columns.tolist()}")
        
        return clean_df
    
    def sync_to_database(self, df: pd.DataFrame, chunk_size: int = 5000) -> int:
        """
        Sync instruments to database using batch INSERT with REPLACE.
        
        Args:
            df: Processed DataFrame
            chunk_size: Number of rows per batch
        
        Returns:
            Number of rows synced
        """
        logger.info(f"Syncing {len(df):,} instruments to database...")
        start_time = time.time()
        
        # Get only the columns that exist in the DataFrame
        available_columns = df.columns.tolist()
        
        # Required columns that must exist
        required = ['security_id', 'exchange', 'segment', 'symbol']
        missing = [c for c in required if c not in available_columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        # Filter df to remove any rows with null security_id
        df = df[df['security_id'].notna()].copy()
        df['security_id'] = df['security_id'].astype(int)
        
        total_synced = 0
        
        with self.engine.connect() as conn:
            # Process in chunks
            for i in range(0, len(df), chunk_size):
                chunk = df.iloc[i:i+chunk_size]
                
                # Build INSERT ... ON DUPLICATE KEY UPDATE statement
                columns = [c for c in available_columns if c in chunk.columns]
                placeholders = ', '.join([f':{c}' for c in columns])
                column_names = ', '.join(columns)
                
                # Build UPDATE clause (all columns except security_id)
                update_cols = [c for c in columns if c != 'security_id']
                update_clause = ', '.join([f'{c} = VALUES({c})' for c in update_cols])
                
                sql = f"""
                    INSERT INTO dhan_instruments ({column_names})
                    VALUES ({placeholders})
                    ON DUPLICATE KEY UPDATE {update_clause}
                """
                
                # Convert chunk to list of dicts, handling NaN values
                records = []
                for _, row in chunk.iterrows():
                    record = {}
                    for col in columns:
                        val = row[col]
                        if pd.isna(val):
                            record[col] = None
                        elif isinstance(val, (date, datetime)):
                            record[col] = val
                        else:
                            record[col] = val
                    records.append(record)
                
                # Execute batch insert
                conn.execute(text(sql), records)
                conn.commit()
                
                total_synced += len(chunk)
                logger.info(f"  Synced {total_synced:,}/{len(df):,} instruments...")
        
        duration = time.time() - start_time
        logger.info(f"Synced {total_synced:,} instruments in {duration:.1f}s")
        
        # Log import
        self._log_import(total_synced)
        
        return total_synced
    
    def _log_import(self, count: int):
        """Log the import to dhan_imports_log table."""
        with self.engine.connect() as conn:
            sql = text("""
                INSERT INTO dhan_imports_log 
                (import_date, import_type, records_count, source_url, status)
                VALUES (:import_date, :import_type, :records_count, :source_url, :status)
            """)
            conn.execute(sql, {
                'import_date': date.today(),
                'import_type': 'INSTRUMENTS',
                'records_count': count,
                'source_url': self.csv_url,
                'status': 'SUCCESS'
            })
            conn.commit()
    
    def sync(self, save_local: bool = True) -> Dict:
        """
        Full sync: download, process, and save to database.
        
        Args:
            save_local: If True, save CSV locally
        
        Returns:
            Dict with sync statistics
        """
        print("\n" + "="*50)
        print("Dhan Instruments Sync")
        print("="*50)
        
        # Download
        df = self.download_csv(save_local=save_local)
        
        # Process
        clean_df = self.process_dataframe(df)
        
        # Sync to DB
        count = self.sync_to_database(clean_df)
        
        # Get stats
        stats = self.get_stats()
        
        print("\n" + "="*50)
        print("Sync Complete!")
        print("="*50)
        print(f"  Total instruments: {stats['total']:,}")
        print(f"  Last update: {stats['last_update']}")
        print("\n  By Exchange/Segment:")
        for key, val in stats['by_exchange_segment'].items():
            print(f"    {key}: {val:,}")
        
        return {
            'synced': count,
            'stats': stats
        }
    
    def get_stats(self) -> Dict:
        """Get statistics about instruments in database."""
        with self.engine.connect() as conn:
            # Total count
            result = conn.execute(text("SELECT COUNT(*) as cnt FROM dhan_instruments"))
            total = result.fetchone()[0]
            
            # Last update
            result = conn.execute(text("SELECT MAX(updated_at) FROM dhan_instruments"))
            last_update = result.fetchone()[0]
            
            # By exchange/segment
            result = conn.execute(text("""
                SELECT exchange_segment, COUNT(*) as cnt 
                FROM dhan_instruments 
                WHERE exchange_segment IS NOT NULL
                GROUP BY exchange_segment 
                ORDER BY cnt DESC
            """))
            by_segment = {row[0]: row[1] for row in result.fetchall()}
        
        return {
            'total': total,
            'last_update': last_update,
            'by_exchange_segment': by_segment
        }


def main():
    """Main entry point for instrument sync."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sync Dhan instruments')
    parser.add_argument('--compact', action='store_true', help='Use compact CSV instead of detailed')
    parser.add_argument('--no-save', action='store_true', help='Do not save local CSV copy')
    args = parser.parse_args()
    
    downloader = InstrumentDownloader(use_detailed=not args.compact)
    result = downloader.sync(save_local=not args.no_save)
    
    return result


if __name__ == "__main__":
    main()
