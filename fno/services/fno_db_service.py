"""
FNO Database Service
Handles all database operations for NSE F&O data
"""

import os
import re
import hashlib
from datetime import datetime, date
from typing import Optional, Dict, List, Tuple
from urllib.parse import quote_plus
import pandas as pd
import pymysql
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': 'fno_marketdata'
}


class FNODBService:
    """Database service for FNO data operations."""
    
    def __init__(self):
        self.engine = None
        self._connect()
    
    def _connect(self):
        """Create SQLAlchemy engine."""
        try:
            # URL-encode password to handle special characters like @
            encoded_password = quote_plus(DB_CONFIG['password'])
            connection_string = (
                f"mysql+pymysql://{DB_CONFIG['user']}:{encoded_password}"
                f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
                f"?charset=utf8mb4"
            )
            self.engine = create_engine(
                connection_string,
                pool_pre_ping=True,
                pool_recycle=3600
            )
        except Exception as e:
            print(f"Error connecting to database: {e}")
            raise
    
    def get_connection(self):
        """Get a new connection from the engine."""
        return self.engine.connect()
    
    # ─────────────────────────────────────────────────────────────────
    # Import Tracking
    # ─────────────────────────────────────────────────────────────────
    
    def is_already_imported(self, trade_date: date, file_type: str) -> bool:
        """Check if data for a specific date and type has been imported."""
        with self.get_connection() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) FROM fno_imports_log 
                WHERE trade_date = :trade_date 
                AND file_type = :file_type
                AND import_status = 'success'
            """), {'trade_date': trade_date, 'file_type': file_type})
            count = result.scalar()
            return count > 0
    
    def get_import_log(self, trade_date: Optional[date] = None) -> pd.DataFrame:
        """Get import log entries."""
        query = "SELECT * FROM fno_imports_log"
        if trade_date:
            query += f" WHERE trade_date = '{trade_date}'"
        query += " ORDER BY imported_at DESC"
        
        with self.get_connection() as conn:
            return pd.read_sql(query, conn)
    
    def log_import(self, trade_date: date, file_type: str, file_name: str,
                   file_checksum: str, records_imported: int, 
                   records_updated: int = 0, status: str = 'success',
                   error_message: str = None):
        """Log an import operation."""
        with self.get_connection() as conn:
            conn.execute(text("""
                INSERT INTO fno_imports_log 
                (trade_date, file_type, file_name, file_checksum, 
                 records_imported, records_updated, import_status, error_message)
                VALUES (:trade_date, :file_type, :file_name, :checksum,
                        :imported, :updated, :status, :error)
                ON DUPLICATE KEY UPDATE
                    file_name = VALUES(file_name),
                    file_checksum = VALUES(file_checksum),
                    records_imported = VALUES(records_imported),
                    records_updated = VALUES(records_updated),
                    import_status = VALUES(import_status),
                    error_message = VALUES(error_message),
                    imported_at = CURRENT_TIMESTAMP
            """), {
                'trade_date': trade_date,
                'file_type': file_type,
                'file_name': file_name,
                'checksum': file_checksum,
                'imported': records_imported,
                'updated': records_updated,
                'status': status,
                'error': error_message
            })
            conn.commit()
    
    def get_latest_trade_date(self, file_type: str = None) -> Optional[date]:
        """Get the most recent trade date in the database."""
        table = 'nse_futures' if file_type == 'futures' else 'nse_options'
        if file_type is None:
            table = 'nse_futures'
        
        with self.get_connection() as conn:
            result = conn.execute(text(f"SELECT MAX(trade_date) FROM {table}"))
            return result.scalar()
    
    def get_available_dates(self) -> List[date]:
        """Get all available trade dates in the database."""
        with self.get_connection() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT trade_date FROM nse_futures
                ORDER BY trade_date DESC
            """))
            return [row[0] for row in result.fetchall()]
    
    # ─────────────────────────────────────────────────────────────────
    # Futures Operations
    # ─────────────────────────────────────────────────────────────────
    
    def insert_futures_data(self, df: pd.DataFrame, trade_date: date) -> Tuple[int, int]:
        """Insert futures data into database."""
        if df.empty:
            return 0, 0
        
        df['trade_date'] = trade_date
        
        # Get previous day's data for OI change calculation
        prev_date = self.get_previous_trade_date(trade_date)
        prev_oi = {}
        if prev_date:
            prev_df = self.get_futures_data(prev_date)
            if not prev_df.empty:
                prev_oi = prev_df.set_index(['symbol', 'expiry_date'])['open_interest'].to_dict()
        
        # Calculate OI change
        if prev_oi:
            df['oi_change'] = df.apply(
                lambda row: row['open_interest'] - prev_oi.get((row['symbol'], row['expiry_date']), row['open_interest']),
                axis=1
            )
            df['oi_change_pct'] = df.apply(
                lambda row: (row['oi_change'] / prev_oi.get((row['symbol'], row['expiry_date']), 1) * 100) 
                            if prev_oi.get((row['symbol'], row['expiry_date']), 0) > 0 else 0,
                axis=1
            )
        else:
            df['oi_change'] = 0
            df['oi_change_pct'] = 0.0
        
        # Insert using temporary table and upsert
        with self.get_connection() as conn:
            # Create temp table
            conn.execute(text("DROP TEMPORARY TABLE IF EXISTS tmp_futures"))
            conn.execute(text("CREATE TEMPORARY TABLE tmp_futures LIKE nse_futures"))
            
            # Insert to temp
            df.to_sql('tmp_futures', conn, if_exists='append', index=False, method='multi', chunksize=1000)
            
            # Upsert
            result = conn.execute(text("""
                INSERT INTO nse_futures 
                (trade_date, symbol, expiry_date, instrument_type, previous_close, 
                 open_price, high_price, low_price, close_price, settlement_price,
                 net_change_pct, open_interest, oi_change, oi_change_pct, 
                 traded_quantity, number_of_trades, traded_value, contract_descriptor)
                SELECT trade_date, symbol, expiry_date, instrument_type, previous_close,
                       open_price, high_price, low_price, close_price, settlement_price,
                       net_change_pct, open_interest, oi_change, oi_change_pct,
                       traded_quantity, number_of_trades, traded_value, contract_descriptor
                FROM tmp_futures
                ON DUPLICATE KEY UPDATE
                    previous_close = VALUES(previous_close),
                    open_price = VALUES(open_price),
                    high_price = VALUES(high_price),
                    low_price = VALUES(low_price),
                    close_price = VALUES(close_price),
                    settlement_price = VALUES(settlement_price),
                    net_change_pct = VALUES(net_change_pct),
                    open_interest = VALUES(open_interest),
                    oi_change = VALUES(oi_change),
                    oi_change_pct = VALUES(oi_change_pct),
                    traded_quantity = VALUES(traded_quantity),
                    number_of_trades = VALUES(number_of_trades),
                    traded_value = VALUES(traded_value)
            """))
            
            conn.commit()
            
            # Get counts (approximate)
            inserted = len(df)
            updated = result.rowcount - inserted if result.rowcount > inserted else 0
            
            return inserted, max(0, updated)
    
    def get_futures_data(self, trade_date: date, symbol: str = None) -> pd.DataFrame:
        """Get futures data for a specific date."""
        query = """
            SELECT * FROM nse_futures 
            WHERE trade_date = :trade_date
        """
        params = {'trade_date': trade_date}
        
        if symbol:
            query += " AND symbol = :symbol"
            params['symbol'] = symbol
        
        query += " ORDER BY symbol, expiry_date"
        
        with self.get_connection() as conn:
            return pd.read_sql(text(query), conn, params=params)
    
    # ─────────────────────────────────────────────────────────────────
    # Options Operations  
    # ─────────────────────────────────────────────────────────────────
    
    def insert_options_data(self, df: pd.DataFrame, trade_date: date) -> Tuple[int, int]:
        """Insert options data into database."""
        if df.empty:
            return 0, 0
        
        df['trade_date'] = trade_date
        
        # Get previous day's data for OI change calculation
        prev_date = self.get_previous_trade_date(trade_date)
        prev_oi = {}
        if prev_date:
            with self.get_connection() as conn:
                result = conn.execute(text("""
                    SELECT symbol, expiry_date, option_type, strike_price, open_interest
                    FROM nse_options WHERE trade_date = :prev_date
                """), {'prev_date': prev_date})
                for row in result.fetchall():
                    key = (row[0], row[1], row[2], float(row[3]))
                    prev_oi[key] = row[4]
        
        # Calculate OI change
        if prev_oi:
            df['oi_change'] = df.apply(
                lambda row: row['open_interest'] - prev_oi.get(
                    (row['symbol'], row['expiry_date'], row['option_type'], float(row['strike_price'])), 
                    row['open_interest']
                ),
                axis=1
            )
        else:
            df['oi_change'] = 0
        
        df['oi_change_pct'] = 0.0  # Will calculate properly if needed
        
        # Insert using temporary table and upsert
        with self.get_connection() as conn:
            conn.execute(text("DROP TEMPORARY TABLE IF EXISTS tmp_options"))
            conn.execute(text("CREATE TEMPORARY TABLE tmp_options LIKE nse_options"))
            
            df.to_sql('tmp_options', conn, if_exists='append', index=False, method='multi', chunksize=5000)
            
            result = conn.execute(text("""
                INSERT INTO nse_options 
                (trade_date, symbol, expiry_date, option_type, strike_price, instrument_type,
                 previous_close, open_price, high_price, low_price, close_price, settlement_price,
                 net_change_pct, open_interest, oi_change, oi_change_pct, traded_quantity,
                 number_of_trades, underlying_price, notional_value, premium_traded, contract_descriptor)
                SELECT trade_date, symbol, expiry_date, option_type, strike_price, instrument_type,
                       previous_close, open_price, high_price, low_price, close_price, settlement_price,
                       net_change_pct, open_interest, oi_change, oi_change_pct, traded_quantity,
                       number_of_trades, underlying_price, notional_value, premium_traded, contract_descriptor
                FROM tmp_options
                ON DUPLICATE KEY UPDATE
                    previous_close = VALUES(previous_close),
                    open_price = VALUES(open_price),
                    high_price = VALUES(high_price),
                    low_price = VALUES(low_price),
                    close_price = VALUES(close_price),
                    settlement_price = VALUES(settlement_price),
                    net_change_pct = VALUES(net_change_pct),
                    open_interest = VALUES(open_interest),
                    oi_change = VALUES(oi_change),
                    oi_change_pct = VALUES(oi_change_pct),
                    traded_quantity = VALUES(traded_quantity),
                    number_of_trades = VALUES(number_of_trades),
                    underlying_price = VALUES(underlying_price),
                    notional_value = VALUES(notional_value),
                    premium_traded = VALUES(premium_traded)
            """))
            
            conn.commit()
            
            inserted = len(df)
            updated = result.rowcount - inserted if result.rowcount > inserted else 0
            
            return inserted, max(0, updated)
    
    def get_options_data(self, trade_date: date, symbol: str = None, 
                         expiry_date: date = None) -> pd.DataFrame:
        """Get options data for a specific date."""
        query = """
            SELECT * FROM nse_options 
            WHERE trade_date = :trade_date
        """
        params = {'trade_date': trade_date}
        
        if symbol:
            query += " AND symbol = :symbol"
            params['symbol'] = symbol
        
        if expiry_date:
            query += " AND expiry_date = :expiry_date"
            params['expiry_date'] = expiry_date
        
        query += " ORDER BY symbol, expiry_date, option_type, strike_price"
        
        with self.get_connection() as conn:
            return pd.read_sql(text(query), conn, params=params)
    
    def get_option_chain(self, trade_date: date, symbol: str, 
                         expiry_date: date = None) -> pd.DataFrame:
        """Get option chain for a specific symbol."""
        # Get nearest expiry if not specified
        if expiry_date is None:
            with self.get_connection() as conn:
                result = conn.execute(text("""
                    SELECT MIN(expiry_date) FROM nse_options
                    WHERE trade_date = :trade_date AND symbol = :symbol
                    AND expiry_date >= :trade_date
                """), {'trade_date': trade_date, 'symbol': symbol})
                expiry_date = result.scalar()
        
        if expiry_date is None:
            return pd.DataFrame()
        
        # Get CE and PE data
        with self.get_connection() as conn:
            ce_df = pd.read_sql(text("""
                SELECT strike_price, open_interest as ce_oi, oi_change as ce_oi_change,
                       close_price as ce_ltp, traded_quantity as ce_volume
                FROM nse_options
                WHERE trade_date = :trade_date AND symbol = :symbol 
                AND expiry_date = :expiry_date AND option_type = 'CE'
                ORDER BY strike_price
            """), conn, params={'trade_date': trade_date, 'symbol': symbol, 'expiry_date': expiry_date})
            
            pe_df = pd.read_sql(text("""
                SELECT strike_price, open_interest as pe_oi, oi_change as pe_oi_change,
                       close_price as pe_ltp, traded_quantity as pe_volume
                FROM nse_options
                WHERE trade_date = :trade_date AND symbol = :symbol 
                AND expiry_date = :expiry_date AND option_type = 'PE'
                ORDER BY strike_price
            """), conn, params={'trade_date': trade_date, 'symbol': symbol, 'expiry_date': expiry_date})
        
        # Merge CE and PE
        if ce_df.empty and pe_df.empty:
            return pd.DataFrame()
        
        chain = pd.merge(ce_df, pe_df, on='strike_price', how='outer')
        chain = chain.sort_values('strike_price').reset_index(drop=True)
        chain = chain.fillna(0)
        
        return chain
    
    # ─────────────────────────────────────────────────────────────────
    # Helper Methods
    # ─────────────────────────────────────────────────────────────────
    
    def get_previous_trade_date(self, trade_date: date) -> Optional[date]:
        """Get the previous trade date from available data."""
        with self.get_connection() as conn:
            result = conn.execute(text("""
                SELECT MAX(trade_date) FROM nse_futures
                WHERE trade_date < :trade_date
            """), {'trade_date': trade_date})
            return result.scalar()
    
    def get_fno_symbols(self, instrument_type: str = None) -> List[str]:
        """Get all FNO symbols."""
        query = "SELECT DISTINCT symbol FROM fno_symbols WHERE is_active = 1"
        if instrument_type:
            query += f" AND instrument_type = '{instrument_type}'"
        query += " ORDER BY symbol"
        
        with self.get_connection() as conn:
            result = conn.execute(text(query))
            return [row[0] for row in result.fetchall()]
    
    def update_symbol_master(self, trade_date: date):
        """Update symbols master table from today's data."""
        with self.get_connection() as conn:
            # Get unique symbols from futures
            conn.execute(text("""
                INSERT INTO fno_symbols (symbol, instrument_type, first_seen_date, last_seen_date)
                SELECT DISTINCT 
                    symbol,
                    CASE WHEN symbol IN ('NIFTY', 'BANKNIFTY', 'NIFTYIT', 'FINNIFTY', 'MIDCPNIFTY') 
                         THEN 'INDEX' ELSE 'STOCK' END,
                    :trade_date,
                    :trade_date
                FROM nse_futures WHERE trade_date = :trade_date
                ON DUPLICATE KEY UPDATE 
                    last_seen_date = VALUES(last_seen_date),
                    is_active = 1
            """), {'trade_date': trade_date})
            conn.commit()
    
    # ─────────────────────────────────────────────────────────────────
    # Analysis Methods
    # ─────────────────────────────────────────────────────────────────
    
    def calculate_support_resistance(self, trade_date: date, symbol: str, 
                                      expiry_date: date = None) -> Dict:
        """Calculate support and resistance levels from option chain."""
        chain = self.get_option_chain(trade_date, symbol, expiry_date)
        
        if chain.empty:
            return {}
        
        # Get underlying price
        with self.get_connection() as conn:
            result = conn.execute(text("""
                SELECT underlying_price FROM nse_options
                WHERE trade_date = :trade_date AND symbol = :symbol
                AND underlying_price > 0 LIMIT 1
            """), {'trade_date': trade_date, 'symbol': symbol})
            underlying = result.scalar() or 0
        
        # Resistance = Strike with highest CE OI (above current price)
        ce_above = chain[chain['strike_price'] > underlying].nlargest(2, 'ce_oi')
        resistance_1 = ce_above['strike_price'].iloc[0] if len(ce_above) > 0 else None
        resistance_2 = ce_above['strike_price'].iloc[1] if len(ce_above) > 1 else None
        
        # Support = Strike with highest PE OI (below current price)
        pe_below = chain[chain['strike_price'] < underlying].nlargest(2, 'pe_oi')
        support_1 = pe_below['strike_price'].iloc[0] if len(pe_below) > 0 else None
        support_2 = pe_below['strike_price'].iloc[1] if len(pe_below) > 1 else None
        
        # Calculate PCR
        total_ce_oi = chain['ce_oi'].sum()
        total_pe_oi = chain['pe_oi'].sum()
        pcr_oi = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 0
        
        total_ce_vol = chain['ce_volume'].sum()
        total_pe_vol = chain['pe_volume'].sum()
        pcr_volume = total_pe_vol / total_ce_vol if total_ce_vol > 0 else 0
        
        # Calculate Max Pain
        strikes = chain['strike_price'].values
        max_pain = self._calculate_max_pain(chain, strikes)
        
        return {
            'underlying_price': underlying,
            'resistance_1': resistance_1,
            'resistance_2': resistance_2,
            'support_1': support_1,
            'support_2': support_2,
            'pcr_oi': round(pcr_oi, 2),
            'pcr_volume': round(pcr_volume, 2),
            'max_pain': max_pain,
            'total_ce_oi': total_ce_oi,
            'total_pe_oi': total_pe_oi
        }
    
    def _calculate_max_pain(self, chain: pd.DataFrame, strikes) -> float:
        """Calculate max pain strike - where option writers lose least."""
        min_loss = float('inf')
        max_pain_strike = strikes[len(strikes)//2] if len(strikes) > 0 else 0
        
        for strike in strikes:
            # CE writers loss if expiry above strike
            ce_loss = chain[chain['strike_price'] < strike].apply(
                lambda row: (strike - row['strike_price']) * row['ce_oi'], axis=1
            ).sum()
            
            # PE writers loss if expiry below strike
            pe_loss = chain[chain['strike_price'] > strike].apply(
                lambda row: (row['strike_price'] - strike) * row['pe_oi'], axis=1
            ).sum()
            
            total_loss = ce_loss + pe_loss
            if total_loss < min_loss:
                min_loss = total_loss
                max_pain_strike = strike
        
        return max_pain_strike
    
    def analyze_futures_buildup(self, trade_date: date, symbol: str = None) -> pd.DataFrame:
        """Analyze futures for long/short buildup."""
        query = """
            SELECT 
                trade_date, symbol, expiry_date, close_price, 
                net_change_pct as price_change_pct,
                open_interest, oi_change, oi_change_pct,
                traded_quantity
            FROM nse_futures
            WHERE trade_date = :trade_date
        """
        params = {'trade_date': trade_date}
        
        if symbol:
            query += " AND symbol = :symbol"
            params['symbol'] = symbol
        
        query += " ORDER BY symbol, expiry_date"
        
        with self.get_connection() as conn:
            df = pd.read_sql(text(query), conn, params=params)
        
        if df.empty:
            return df
        
        # Determine interpretation
        def get_interpretation(row):
            price_up = row['price_change_pct'] > 0
            oi_up = row['oi_change'] > 0
            
            if price_up and oi_up:
                return 'LONG_BUILDUP'
            elif not price_up and oi_up:
                return 'SHORT_BUILDUP'
            elif not price_up and not oi_up:
                return 'LONG_UNWINDING'
            else:  # price_up and not oi_up
                return 'SHORT_COVERING'
        
        df['interpretation'] = df.apply(get_interpretation, axis=1)
        
        return df
    
    def save_futures_analysis(self, trade_date: date):
        """Save futures analysis to database."""
        analysis_df = self.analyze_futures_buildup(trade_date)
        
        if analysis_df.empty:
            return 0
        
        # Get previous day volume for comparison
        prev_date = self.get_previous_trade_date(trade_date)
        prev_vol = {}
        if prev_date:
            with self.get_connection() as conn:
                result = conn.execute(text("""
                    SELECT symbol, expiry_date, traded_quantity FROM nse_futures
                    WHERE trade_date = :prev_date
                """), {'prev_date': prev_date})
                for row in result.fetchall():
                    prev_vol[(row[0], row[1])] = row[2]
        
        # Calculate volume change
        analysis_df['volume_change_pct'] = analysis_df.apply(
            lambda row: ((row['traded_quantity'] - prev_vol.get((row['symbol'], row['expiry_date']), row['traded_quantity'])) 
                        / prev_vol.get((row['symbol'], row['expiry_date']), 1) * 100)
                        if prev_vol.get((row['symbol'], row['expiry_date']), 0) > 0 else 0,
            axis=1
        )
        
        # Insert to analysis table
        with self.get_connection() as conn:
            conn.execute(text("DELETE FROM futures_analysis WHERE trade_date = :trade_date"),
                        {'trade_date': trade_date})
            
            for _, row in analysis_df.iterrows():
                conn.execute(text("""
                    INSERT INTO futures_analysis 
                    (trade_date, symbol, expiry_date, close_price, price_change, price_change_pct,
                     open_interest, oi_change, oi_change_pct, interpretation, traded_quantity, volume_change_pct)
                    VALUES (:trade_date, :symbol, :expiry_date, :close_price, :price_change, :price_change_pct,
                            :oi, :oi_change, :oi_change_pct, :interpretation, :volume, :vol_change_pct)
                """), {
                    'trade_date': row['trade_date'],
                    'symbol': row['symbol'],
                    'expiry_date': row['expiry_date'],
                    'close_price': row['close_price'],
                    'price_change': row.get('close_price', 0) * row['price_change_pct'] / 100 if row['price_change_pct'] else 0,
                    'price_change_pct': row['price_change_pct'],
                    'oi': row['open_interest'],
                    'oi_change': row['oi_change'],
                    'oi_change_pct': row['oi_change_pct'],
                    'interpretation': row['interpretation'],
                    'volume': row['traded_quantity'],
                    'vol_change_pct': row['volume_change_pct']
                })
            conn.commit()
        
        return len(analysis_df)
    
    def save_option_chain_summary(self, trade_date: date, symbol: str, expiry_date: date = None):
        """Save option chain analysis summary."""
        analysis = self.calculate_support_resistance(trade_date, symbol, expiry_date)
        
        if not analysis:
            return False
        
        # Get actual expiry date used
        if expiry_date is None:
            with self.get_connection() as conn:
                result = conn.execute(text("""
                    SELECT MIN(expiry_date) FROM nse_options
                    WHERE trade_date = :trade_date AND symbol = :symbol
                    AND expiry_date >= :trade_date
                """), {'trade_date': trade_date, 'symbol': symbol})
                expiry_date = result.scalar()
        
        # Get OI changes
        prev_date = self.get_previous_trade_date(trade_date)
        ce_oi_change = 0
        pe_oi_change = 0
        if prev_date:
            with self.get_connection() as conn:
                result = conn.execute(text("""
                    SELECT option_type, SUM(oi_change) FROM nse_options
                    WHERE trade_date = :trade_date AND symbol = :symbol
                    AND expiry_date = :expiry_date
                    GROUP BY option_type
                """), {'trade_date': trade_date, 'symbol': symbol, 'expiry_date': expiry_date})
                for row in result.fetchall():
                    if row[0] == 'CE':
                        ce_oi_change = row[1] or 0
                    else:
                        pe_oi_change = row[1] or 0
        
        with self.get_connection() as conn:
            conn.execute(text("""
                INSERT INTO option_chain_summary
                (trade_date, symbol, expiry_date, underlying_price, max_pain_strike,
                 pcr_oi, pcr_volume, resistance_1, resistance_2, support_1, support_2,
                 total_ce_oi, total_pe_oi, ce_oi_change, pe_oi_change)
                VALUES (:trade_date, :symbol, :expiry_date, :underlying, :max_pain,
                        :pcr_oi, :pcr_vol, :r1, :r2, :s1, :s2,
                        :ce_oi, :pe_oi, :ce_change, :pe_change)
                ON DUPLICATE KEY UPDATE
                    underlying_price = VALUES(underlying_price),
                    max_pain_strike = VALUES(max_pain_strike),
                    pcr_oi = VALUES(pcr_oi),
                    pcr_volume = VALUES(pcr_volume),
                    resistance_1 = VALUES(resistance_1),
                    resistance_2 = VALUES(resistance_2),
                    support_1 = VALUES(support_1),
                    support_2 = VALUES(support_2),
                    total_ce_oi = VALUES(total_ce_oi),
                    total_pe_oi = VALUES(total_pe_oi),
                    ce_oi_change = VALUES(ce_oi_change),
                    pe_oi_change = VALUES(pe_oi_change)
            """), {
                'trade_date': trade_date,
                'symbol': symbol,
                'expiry_date': expiry_date,
                'underlying': analysis['underlying_price'],
                'max_pain': analysis['max_pain'],
                'pcr_oi': analysis['pcr_oi'],
                'pcr_vol': analysis['pcr_volume'],
                'r1': analysis['resistance_1'],
                'r2': analysis['resistance_2'],
                's1': analysis['support_1'],
                's2': analysis['support_2'],
                'ce_oi': analysis['total_ce_oi'],
                'pe_oi': analysis['total_pe_oi'],
                'ce_change': ce_oi_change,
                'pe_change': pe_oi_change
            })
            conn.commit()
        
        return True
