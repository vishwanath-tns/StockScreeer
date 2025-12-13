"""
Instrument Selector
===================
Select instruments for live feed subscription from database.
"""
import os
import sys
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import logging

from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dhan_trading.db_setup import get_engine, DHAN_DB_NAME
from dhan_trading.market_feed.feed_config import ExchangeSegment, InstrumentType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InstrumentSelector:
    """
    Select instruments from dhan_instruments table for feed subscription.
    
    Example usage:
        selector = InstrumentSelector()
        
        # Get Nifty futures for current and next expiry
        nifty_futs = selector.get_nifty_futures(expiries=[0, 1])
        
        # Get Bank Nifty futures
        bnf_futs = selector.get_banknifty_futures()
        
        # Get Nifty 500 stocks
        stocks = selector.get_nifty500_stocks()
    """
    
    def __init__(self):
        self.engine = get_engine(DHAN_DB_NAME)
    
    def _get_next_expiries(self, underlying_symbol: str, 
                          exchange_segment: str = "NSE_FNO",
                          instrument_type: str = "FUTIDX",
                          count: int = 2) -> List[date]:
        """
        Get next N expiry dates for an underlying.
        
        Args:
            underlying_symbol: e.g., "NIFTY", "BANKNIFTY"
            exchange_segment: NSE_FNO, BSE_FNO, etc.
            instrument_type: FUTIDX, FUTSTK, etc.
            count: Number of expiries to return
        
        Returns:
            List of expiry dates
        """
        today = date.today()
        
        sql = text("""
            SELECT DISTINCT expiry_date 
            FROM dhan_instruments
            WHERE underlying_symbol = :underlying
              AND exchange_segment = :segment
              AND instrument = :inst_type
              AND expiry_date >= :today
            ORDER BY expiry_date
            LIMIT :count
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(sql, {
                'underlying': underlying_symbol,
                'segment': exchange_segment,
                'inst_type': instrument_type,
                'today': today,
                'count': count
            })
            return [row[0] for row in result.fetchall()]
    
    def get_nifty_futures(self, expiries: List[int] = [0, 1]) -> List[Dict]:
        """
        Get Nifty 50 futures for specified expiries.
        
        Args:
            expiries: List of expiry indices (0=current, 1=next, 2=far)
        
        Returns:
            List of instrument dicts with security_id, symbol, etc.
        """
        return self._get_index_futures("NIFTY", "NIFTY 50", expiries)
    
    def get_banknifty_futures(self, expiries: List[int] = [0, 1]) -> List[Dict]:
        """Get Bank Nifty futures for specified expiries."""
        return self._get_index_futures("BANKNIFTY", "NIFTY BANK", expiries)
    
    def get_finnifty_futures(self, expiries: List[int] = [0, 1]) -> List[Dict]:
        """Get Fin Nifty futures for specified expiries."""
        return self._get_index_futures("FINNIFTY", "NIFTY FIN SERVICE", expiries)
    
    def get_commodity_futures(self, commodities: List[str] = None, expiries: List[int] = [0]) -> List[Dict]:
        """
        Get MCX commodity futures for specified commodities.
        
        Args:
            commodities: List of commodity symbols. If None, returns major commodities:
                         GOLD, GOLDM, SILVER, SILVERM, CRUDEOIL, NATURALGAS, COPPER, ZINC, etc.
            expiries: List of expiry indices (0=nearest, 1=next, etc.)
        
        Returns:
            List of instrument dicts with security_id, symbol, exchange_segment, etc.
        """
        # Default major commodities if not specified
        if commodities is None:
            commodities = [
                'GOLD', 'GOLDM', 'GOLDPETAL',
                'SILVER', 'SILVERM', 'SILVERMIC',
                'CRUDEOIL', 'CRUDEOILM',
                'NATURALGAS', 'NATGASMINI',
                'COPPER', 'ALUMINIUM', 'ALUMINI',
                'ZINC', 'ZINCMINI',
                'LEAD', 'LEADMINI',
                'NICKEL'
            ]
        
        all_futures = []
        
        for commodity in commodities:
            futures = self._get_commodity_futures(commodity, expiries)
            all_futures.extend(futures)
        
        logger.info(f"Selected {len(all_futures)} commodity futures")
        return all_futures
    
    def _get_commodity_futures(self, underlying_symbol: str, expiries: List[int]) -> List[Dict]:
        """
        Get commodity futures for a specific underlying.
        
        Args:
            underlying_symbol: Commodity symbol (GOLD, SILVER, CRUDEOIL, etc.)
            expiries: List of expiry indices
        """
        today = date.today()
        
        sql = text("""
            SELECT 
                security_id,
                exchange_segment,
                symbol,
                display_name,
                instrument,
                instrument_type,
                lot_size,
                expiry_date,
                underlying_security_id,
                underlying_symbol
            FROM dhan_instruments
            WHERE underlying_symbol = :underlying
              AND exchange_segment = 'MCX_COMM'
              AND instrument LIKE 'FUT%'
              AND expiry_date >= :today
            ORDER BY expiry_date
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(sql, {
                'underlying': underlying_symbol,
                'today': today
            })
            
            all_futures = [dict(row._mapping) for row in result.fetchall()]
        
        # Filter by requested expiry indices
        selected = []
        for idx in expiries:
            if idx < len(all_futures):
                selected.append(all_futures[idx])
        
        if selected:
            logger.debug(f"Selected {len(selected)} {underlying_symbol} futures: "
                        f"{[f['display_name'] for f in selected]}")
        
        return selected
    
    def get_major_commodity_futures(self, expiries: List[int] = [0]) -> List[Dict]:
        """
        Get futures for major traded commodities only.
        
        Major commodities: GOLD, GOLDM, SILVER, SILVERM, CRUDEOIL, NATURALGAS, COPPER
        """
        major_commodities = [
            'GOLD', 'GOLDM',
            'SILVER', 'SILVERM', 
            'CRUDEOIL', 'CRUDEOILM',
            'NATURALGAS',
            'COPPER'
        ]
        return self.get_commodity_futures(commodities=major_commodities, expiries=expiries)
    
    def _get_index_futures(self, underlying_symbol: str, 
                           underlying_display: str,
                           expiries: List[int]) -> List[Dict]:
        """
        Get index futures for specified expiries.
        
        Args:
            underlying_symbol: NIFTY, BANKNIFTY, etc.
            underlying_display: Full name for display
            expiries: List of expiry indices
        """
        today = date.today()
        
        # Get all future expiries
        sql = text("""
            SELECT 
                security_id,
                exchange_segment,
                symbol,
                display_name,
                instrument,
                instrument_type,
                lot_size,
                expiry_date,
                underlying_security_id,
                underlying_symbol
            FROM dhan_instruments
            WHERE underlying_symbol = :underlying
              AND exchange_segment = 'NSE_FNO'
              AND instrument = 'FUTIDX'
              AND expiry_date >= :today
            ORDER BY expiry_date
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(sql, {
                'underlying': underlying_symbol,
                'today': today
            })
            
            all_futures = [dict(row._mapping) for row in result.fetchall()]
        
        # Filter by requested expiry indices
        selected = []
        for idx in expiries:
            if idx < len(all_futures):
                selected.append(all_futures[idx])
        
        logger.info(f"Selected {len(selected)} {underlying_symbol} futures: "
                    f"{[f['display_name'] for f in selected]}")
        
        return selected
    
    def _get_atm_strike(self, underlying_symbol: str, strike_interval: int = 100) -> Optional[float]:
        """
        Get ATM (At-The-Money) strike price for an underlying.
        
        Uses the current month futures LTP to determine ATM strike.
        This is more reliable than index LTP since futures are always being quoted.
        
        Args:
            underlying_symbol: e.g., "NIFTY", "BANKNIFTY", or stock symbol
            strike_interval: Round to nearest interval (100 for indices, 50 for NIFTY weekly)
        
        Returns:
            ATM strike price, or None if current price not available
        """
        try:
            today = date.today()
            
            # First, try to get current month futures security_id
            # This is more reliable than getting index quotes
            sql_get_futures = text("""
                SELECT security_id, symbol, expiry_date
                FROM dhan_instruments 
                WHERE underlying_symbol = :underlying
                  AND instrument = 'FUTIDX'
                  AND expiry_date >= :today
                ORDER BY expiry_date
                LIMIT 1
            """)
            
            with self.engine.connect() as conn:
                result = conn.execute(sql_get_futures, {
                    'underlying': underlying_symbol,
                    'today': today
                })
                row = result.fetchone()
                
            if not row:
                logger.warning(f"No futures found for {underlying_symbol}")
                return None
            
            security_id = row[0]
            symbol = row[1]
            logger.debug(f"Using futures {symbol} (ID: {security_id}) for ATM calculation")
            
            # Now get the latest LTP for the futures from dhan_quotes
            sql_get_ltp = text("""
                SELECT ltp FROM dhan_quotes 
                WHERE security_id = :security_id
                ORDER BY received_at DESC
                LIMIT 1
            """)
            
            with self.engine.connect() as conn:
                result = conn.execute(sql_get_ltp, {'security_id': security_id})
                row = result.fetchone()
                
            if row and row[0]:
                spot_price = float(row[0])
                atm_strike = round(spot_price / strike_interval) * strike_interval
                logger.info(f"ATM for {underlying_symbol}: futures_ltp={spot_price:.2f}, ATM_strike={atm_strike}")
                return atm_strike
            else:
                logger.warning(f"No quote data found for futures {symbol} (ID: {security_id})")
                return None
        except Exception as e:
            logger.error(f"Error calculating ATM strike for {underlying_symbol}: {e}")
            return None
    
    def get_nifty_options(self, 
                         strike_offset_levels: int = 20,
                         expiries: List[int] = [0],
                         option_types: List[str] = ['CE', 'PE'],
                         atm_strike: Optional[float] = None) -> List[Dict]:
        """
        Get Nifty options around ATM with specified strike offset.
        
        Note: NIFTY options use 100-point strike intervals.
        For strike_offset_levels=20, gets 20 strikes above and below ATM.
        Example: ATM=25000, offset=20 -> strikes 24800 to 25200 (41 strikes total with ATM)
        
        Args:
            strike_offset_levels: Number of 100-point levels above/below ATM (default 20)
            expiries: List of expiry indices (0=current, 1=next)
            option_types: List of option types ('CE', 'PE', or both)
            atm_strike: Optional explicit ATM strike. If None, tries to fetch from quotes table
        
        Returns:
            List of option instrument dicts with security_id, symbol, strike_price, etc.
        """
        # Use FINNIFTY as fallback since NIFTY options might not be available
        # In production, check if NIFTY options exist, else use FINNIFTY
        underlying = "FINNIFTY"  # or "NIFTY" if available in your database
        
        # Get ATM strike if not provided
        if atm_strike is None:
            calculated_atm = self._get_atm_strike(underlying, strike_interval=100)
            if calculated_atm is None:
                # Use default around current market levels if no quote data
                logger.info(f"No ATM data available for {underlying}, using reasonable defaults")
                # For FINNIFTY, typical range is 20000-25000
                atm_strike = 22000  # Default fallback
            else:
                atm_strike = calculated_atm
        
        # Calculate strike range
        strike_interval = 100  # Nifty index options use 100-point spreads
        min_strike = atm_strike - (strike_offset_levels * strike_interval)
        max_strike = atm_strike + (strike_offset_levels * strike_interval)
        
        today = date.today()
        
        # Get expiry dates
        expiry_sql = text("""
            SELECT DISTINCT expiry_date 
            FROM dhan_instruments
            WHERE underlying_symbol = :underlying
              AND instrument = 'OPTIDX'
              AND expiry_date >= :today
            ORDER BY expiry_date
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(expiry_sql, {
                'underlying': underlying,
                'today': today
            })
            available_expiries = [row[0] for row in result.fetchall()]
        
        # Collect options for requested expiry indices
        all_options = []
        
        for expiry_idx in expiries:
            if expiry_idx >= len(available_expiries):
                logger.warning(f"Expiry index {expiry_idx} not available for {underlying}")
                continue
            
            target_expiry = available_expiries[expiry_idx]
            
            # Get options around ATM for this expiry
            opt_sql = text("""
                SELECT 
                    security_id,
                    exchange_segment,
                    symbol,
                    display_name,
                    instrument,
                    instrument_type,
                    lot_size,
                    expiry_date,
                    strike_price,
                    option_type,
                    underlying_security_id,
                    underlying_symbol
                FROM dhan_instruments
                WHERE underlying_symbol = :underlying
                  AND instrument = 'OPTIDX'
                  AND expiry_date = :expiry
                  AND strike_price >= :min_strike
                  AND strike_price <= :max_strike
                  AND option_type IN ({})
                ORDER BY strike_price, option_type
            """.format(', '.join([f"'{ot}'" for ot in option_types])))
            
            with self.engine.connect() as conn:
                result = conn.execute(opt_sql, {
                    'underlying': underlying,
                    'expiry': target_expiry,
                    'min_strike': min_strike,
                    'max_strike': max_strike
                })
                
                expiry_options = [dict(row._mapping) for row in result.fetchall()]
                all_options.extend(expiry_options)
        
        logger.info(f"Selected {len(all_options)} {underlying} options (ATM={atm_strike}, "
                   f"offset={strike_offset_levels}, range={min_strike}-{max_strike})")
        
        return all_options
    
    def get_banknifty_options(self, 
                             strike_offset_levels: int = 20,
                             expiries: List[int] = [0],
                             option_types: List[str] = ['CE', 'PE'],
                             atm_strike: Optional[float] = None) -> List[Dict]:
        """
        Get BankNifty options around ATM with specified strike offset.
        
        Note: BankNifty options use 100-point strike intervals.
        For strike_offset_levels=20, gets 20 strikes above and below ATM.
        
        Args:
            strike_offset_levels: Number of 100-point levels above/below ATM (default 20)
            expiries: List of expiry indices (0=current, 1=next)
            option_types: List of option types ('CE', 'PE', or both)
            atm_strike: Optional explicit ATM strike. If None, tries to fetch from quotes table
        
        Returns:
            List of option instrument dicts with security_id, symbol, strike_price, etc.
        """
        underlying = "BANKNIFTY"
        
        # Get ATM strike if not provided
        if atm_strike is None:
            calculated_atm = self._get_atm_strike(underlying, strike_interval=100)
            if calculated_atm is None:
                # Use default around current market levels if no quote data
                logger.info(f"No ATM data available for {underlying}, using reasonable defaults")
                # For BankNifty, typical range is 45000-50000
                atm_strike = 47500  # Default fallback
            else:
                atm_strike = calculated_atm
        
        # Calculate strike range
        strike_interval = 100  # BankNifty options use 100-point spreads
        min_strike = atm_strike - (strike_offset_levels * strike_interval)
        max_strike = atm_strike + (strike_offset_levels * strike_interval)
        
        today = date.today()
        
        # Get expiry dates
        expiry_sql = text("""
            SELECT DISTINCT expiry_date 
            FROM dhan_instruments
            WHERE underlying_symbol = :underlying
              AND instrument = 'OPTIDX'
              AND expiry_date >= :today
            ORDER BY expiry_date
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(expiry_sql, {
                'underlying': underlying,
                'today': today
            })
            available_expiries = [row[0] for row in result.fetchall()]
        
        # Collect options for requested expiry indices
        all_options = []
        
        for expiry_idx in expiries:
            if expiry_idx >= len(available_expiries):
                logger.warning(f"Expiry index {expiry_idx} not available for {underlying}")
                continue
            
            target_expiry = available_expiries[expiry_idx]
            
            # Get options around ATM for this expiry
            opt_sql = text("""
                SELECT 
                    security_id,
                    exchange_segment,
                    symbol,
                    display_name,
                    instrument,
                    instrument_type,
                    lot_size,
                    expiry_date,
                    strike_price,
                    option_type,
                    underlying_security_id,
                    underlying_symbol
                FROM dhan_instruments
                WHERE underlying_symbol = :underlying
                  AND instrument = 'OPTIDX'
                  AND expiry_date = :expiry
                  AND strike_price >= :min_strike
                  AND strike_price <= :max_strike
                  AND option_type IN ({})
                ORDER BY strike_price, option_type
            """.format(', '.join([f"'{ot}'" for ot in option_types])))
            
            with self.engine.connect() as conn:
                result = conn.execute(opt_sql, {
                    'underlying': underlying,
                    'expiry': target_expiry,
                    'min_strike': min_strike,
                    'max_strike': max_strike
                })
                
                expiry_options = [dict(row._mapping) for row in result.fetchall()]
                all_options.extend(expiry_options)
        
        logger.info(f"Selected {len(all_options)} {underlying} options (ATM={atm_strike}, "
                   f"offset={strike_offset_levels}, range={min_strike}-{max_strike})")
        
        return all_options
    
    def get_nifty_weekly_options(self,
                                 strike_offset_levels: int = 10,
                                 option_types: List[str] = ['CE', 'PE'],
                                 atm_strike: Optional[float] = None) -> List[Dict]:
        """
        Get NIFTY (actual NIFTY index, not FINNIFTY) weekly expiry options.
        Weekly options expire every Tuesday in NSE.
        
        Args:
            strike_offset_levels: Number of 100-point levels above/below ATM (default 10)
            option_types: List of option types ('CE', 'PE', or both)
            atm_strike: Optional explicit ATM strike. If None, tries to fetch from quotes table
        
        Returns:
            List of option instrument dicts with security_id, symbol, strike_price, etc.
        """
        underlying = "NIFTY"
        
        # Get ATM strike if not provided
        # Use 50-point interval for NIFTY weekly options
        if atm_strike is None:
            calculated_atm = self._get_atm_strike(underlying, strike_interval=50)
            if calculated_atm is None:
                logger.info(f"No ATM data available for {underlying}, using reasonable defaults")
                # For NIFTY, typical range is 24000-26000
                atm_strike = 25000  # Default fallback
            else:
                atm_strike = calculated_atm
        
        # Calculate strike range
        strike_interval = 50  # NIFTY weekly options use 50-point spreads
        min_strike = atm_strike - (strike_offset_levels * strike_interval)
        max_strike = atm_strike + (strike_offset_levels * strike_interval)
        
        today = date.today()
        
        # Get next Tuesday (for weekly expiry in NSE)
        # NIFTY weekly options expire every Tuesday
        days_until_tuesday = (1 - today.weekday()) % 7
        if days_until_tuesday == 0:
            days_until_tuesday = 7  # If today is Tuesday, get next Tuesday
        next_tuesday = today + timedelta(days=days_until_tuesday)
        
        logger.info(f"Getting NIFTY weekly options expiring on {next_tuesday} (Tuesday)")
        
        # Get options around ATM for weekly expiry
        opt_sql = text("""
            SELECT 
                security_id,
                exchange_segment,
                symbol,
                display_name,
                instrument,
                instrument_type,
                lot_size,
                expiry_date,
                strike_price,
                option_type,
                underlying_security_id,
                underlying_symbol
            FROM dhan_instruments
            WHERE underlying_symbol = :underlying
              AND instrument = 'OPTIDX'
              AND expiry_date = :expiry
              AND strike_price >= :min_strike
              AND strike_price <= :max_strike
              AND option_type IN ({})
            ORDER BY strike_price, option_type
        """.format(', '.join([f"'{ot}'" for ot in option_types])))
        
        with self.engine.connect() as conn:
            result = conn.execute(opt_sql, {
                'underlying': underlying,
                'expiry': next_tuesday,
                'min_strike': min_strike,
                'max_strike': max_strike
            })
            
            all_options = [dict(row._mapping) for row in result.fetchall()]
        
        logger.info(f"Selected {len(all_options)} {underlying} weekly options "
                   f"(Expiry: {next_tuesday}, ATM={atm_strike}, "
                   f"offset={strike_offset_levels}, range={min_strike}-{max_strike})")
        
        return all_options
    
    def get_banknifty_weekly_options(self,
                                     strike_offset_levels: int = 10,
                                     option_types: List[str] = ['CE', 'PE'],
                                     atm_strike: Optional[float] = None) -> List[Dict]:
        """
        Get BANKNIFTY weekly/nearest expiry options.
        Note: BANKNIFTY may not have weekly options every Tuesday. This gets the nearest available expiry.
        
        Args:
            strike_offset_levels: Number of 100-point levels above/below ATM (default 10)
            option_types: List of option types ('CE', 'PE', or both)
            atm_strike: Optional explicit ATM strike. If None, tries to fetch from quotes table
        
        Returns:
            List of option instrument dicts with security_id, symbol, strike_price, etc.
        """
        underlying = "BANKNIFTY"
        
        # Get ATM strike if not provided
        if atm_strike is None:
            calculated_atm = self._get_atm_strike(underlying, strike_interval=100)
            if calculated_atm is None:
                logger.info(f"No ATM data available for {underlying}, using reasonable defaults")
                # For BankNifty, typical range is 45000-50000
                atm_strike = 47500  # Default fallback
            else:
                atm_strike = calculated_atm
        
        # Calculate strike range
        strike_interval = 100  # BankNifty options use 100-point spreads
        min_strike = atm_strike - (strike_offset_levels * strike_interval)
        max_strike = atm_strike + (strike_offset_levels * strike_interval)
        
        today = date.today()
        
        # Get nearest available expiry for BANKNIFTY
        # First, check what expiries are available
        expiry_sql = text("""
            SELECT MIN(expiry_date) as nearest_expiry
            FROM dhan_instruments
            WHERE underlying_symbol = :underlying
              AND instrument = 'OPTIDX'
              AND expiry_date >= :today
        """)
        
        nearest_expiry = None
        with self.engine.connect() as conn:
            result = conn.execute(expiry_sql, {
                'underlying': underlying,
                'today': today
            })
            row = result.fetchone()
            if row and row[0]:
                nearest_expiry = row[0]
        
        if nearest_expiry is None:
            logger.warning(f"No {underlying} options found for future expiries. Using next Tuesday.")
            days_until_tuesday = (1 - today.weekday()) % 7
            if days_until_tuesday == 0:
                days_until_tuesday = 7
            nearest_expiry = today + timedelta(days=days_until_tuesday)
        
        logger.info(f"Getting BANKNIFTY options expiring on {nearest_expiry}")
        
        # Get options around ATM for weekly expiry
        opt_sql = text("""
            SELECT 
                security_id,
                exchange_segment,
                symbol,
                display_name,
                instrument,
                instrument_type,
                lot_size,
                expiry_date,
                strike_price,
                option_type,
                underlying_security_id,
                underlying_symbol
            FROM dhan_instruments
            WHERE underlying_symbol = :underlying
              AND instrument = 'OPTIDX'
              AND expiry_date = :expiry
              AND strike_price >= :min_strike
              AND strike_price <= :max_strike
              AND option_type IN ({})
            ORDER BY strike_price, option_type
        """.format(', '.join([f"'{ot}'" for ot in option_types])))
        
        with self.engine.connect() as conn:
            result = conn.execute(opt_sql, {
                'underlying': underlying,
                'expiry': nearest_expiry,
                'min_strike': min_strike,
                'max_strike': max_strike
            })
            
            all_options = [dict(row._mapping) for row in result.fetchall()]
        
        logger.info(f"Selected {len(all_options)} {underlying} options "
                   f"(Expiry: {nearest_expiry}, ATM={atm_strike}, "
                   f"offset={strike_offset_levels}, range={min_strike}-{max_strike})")
        
        return all_options
    
    def get_stock_options(self, 
                         symbols: List[str],
                         strike_offset_levels: int = 5,
                         expiries: List[int] = [0, 1],
                         option_types: List[str] = ['CE', 'PE'],
                         atm_strikes: Optional[Dict[str, float]] = None) -> List[Dict]:
        """
        Get options for specified stocks across current and next month.
        
        Note: Stock options use variable strike intervals (typically 5-50 points depending on price).
        For strike_offset_levels=5, gets 5 strikes above and below ATM.
        
        Args:
            symbols: List of stock symbols (e.g., ['HINDUNILVR', 'TCS', 'INFY'])
            strike_offset_levels: Number of strikes above/below ATM (default 5)
            expiries: List of expiry indices (0=current, 1=next, etc.)
            option_types: List of option types ('CE', 'PE', or both)
            atm_strikes: Optional dict mapping symbols to explicit ATM strikes.
                        If None or missing for a symbol, uses reasonable defaults based on symbol.
        
        Returns:
            List of option instrument dicts with security_id, symbol, strike_price, etc.
        """
        today = date.today()
        all_options = []
        
        if atm_strikes is None:
            atm_strikes = {}
        
        for symbol in symbols:
            try:
                # Get ATM for this stock or use provided value
                if symbol in atm_strikes:
                    atm_strike = atm_strikes[symbol]
                    logger.debug(f"Using provided ATM for {symbol}: {atm_strike}")
                else:
                    atm_calc = self._get_atm_strike(symbol, strike_interval=5)
                    if atm_calc:
                        atm_strike = atm_calc
                    else:
                        # Use reasonable default based on typical stock prices
                        # This is a fallback - in production you'd want real quote data
                        logger.debug(f"No ATM data for {symbol}, using default spacing")
                        # Query database for a rough idea of strike prices available
                        sql_check = text("""
                            SELECT AVG(strike_price) FROM dhan_instruments
                            WHERE underlying_symbol = :symbol AND instrument = 'OPTSTK'
                            LIMIT 1
                        """)
                        with self.engine.connect() as conn:
                            result = conn.execute(sql_check, {'symbol': symbol})
                            row = result.fetchone()
                            if row and row[0]:
                                atm_strike = float(row[0])
                            else:
                                logger.debug(f"Skipping {symbol}: no option data available")
                                continue
                
                # Determine strike interval based on price level
                # Common NSE practice: 5 below 100, 10 below 500, 20 below 5000, 50+ above
                if atm_strike < 100:
                    strike_interval = 5
                elif atm_strike < 500:
                    strike_interval = 10
                elif atm_strike < 5000:
                    strike_interval = 20
                else:
                    strike_interval = 50
                
                min_strike = atm_strike - (strike_offset_levels * strike_interval)
                max_strike = atm_strike + (strike_offset_levels * strike_interval)
                
                # Get available expiries for this stock
                expiry_sql = text("""
                    SELECT DISTINCT expiry_date 
                    FROM dhan_instruments
                    WHERE underlying_symbol = :underlying
                      AND instrument = 'OPTSTK'
                      AND expiry_date >= :today
                    ORDER BY expiry_date
                """)
                
                with self.engine.connect() as conn:
                    result = conn.execute(expiry_sql, {
                        'underlying': symbol,
                        'today': today
                    })
                    available_expiries = [row[0] for row in result.fetchall()]
                
                # Collect options for requested expiry indices
                for expiry_idx in expiries:
                    if expiry_idx >= len(available_expiries):
                        continue
                    
                    target_expiry = available_expiries[expiry_idx]
                    
                    # Get options around ATM
                    opt_sql = text("""
                        SELECT 
                            security_id,
                            exchange_segment,
                            symbol,
                            display_name,
                            instrument,
                            instrument_type,
                            lot_size,
                            expiry_date,
                            strike_price,
                            option_type,
                            underlying_security_id,
                            underlying_symbol
                        FROM dhan_instruments
                        WHERE underlying_symbol = :underlying
                          AND instrument = 'OPTSTK'
                          AND expiry_date = :expiry
                          AND strike_price >= :min_strike
                          AND strike_price <= :max_strike
                          AND option_type IN ({})
                        ORDER BY strike_price, option_type
                    """.format(', '.join([f"'{ot}'" for ot in option_types])))
                    
                    with self.engine.connect() as conn:
                        result = conn.execute(opt_sql, {
                            'underlying': symbol,
                            'expiry': target_expiry,
                            'min_strike': min_strike,
                            'max_strike': max_strike
                        })
                        
                        expiry_options = [dict(row._mapping) for row in result.fetchall()]
                        all_options.extend(expiry_options)
                
                logger.debug(f"Collected options for {symbol} (ATM={atm_strike})")
            
            except Exception as e:
                logger.error(f"Error processing stock options for {symbol}: {e}")
                continue
        
        logger.info(f"Selected {len(all_options)} options for {len(symbols)} stocks")
        
        return all_options
    
    def get_index_options(self, underlying_symbol: str,
                         expiry_index: int = 0,
                         option_type: Optional[str] = None,
                         strike_range: int = 10) -> List[Dict]:
        """
        Get index options around ATM for current expiry.
        
        Args:
            underlying_symbol: NIFTY, BANKNIFTY, etc.
            expiry_index: 0=current, 1=next weekly, etc.
            option_type: CE, PE, or None for both
            strike_range: Number of strikes above and below ATM
        """
        today = date.today()
        
        # First get expiry dates
        expiry_sql = text("""
            SELECT DISTINCT expiry_date 
            FROM dhan_instruments
            WHERE underlying_symbol = :underlying
              AND exchange_segment = 'NSE_FNO'
              AND instrument = 'OPTIDX'
              AND expiry_date >= :today
            ORDER BY expiry_date
            LIMIT :limit
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(expiry_sql, {
                'underlying': underlying_symbol,
                'today': today,
                'limit': expiry_index + 1
            })
            expiries = [row[0] for row in result.fetchall()]
        
        if expiry_index >= len(expiries):
            logger.warning(f"Expiry index {expiry_index} not found, using latest")
            target_expiry = expiries[-1] if expiries else None
        else:
            target_expiry = expiries[expiry_index]
        
        if not target_expiry:
            return []
        
        # Get options for target expiry
        opt_sql = text("""
            SELECT 
                security_id,
                exchange_segment,
                symbol,
                display_name,
                instrument,
                instrument_type,
                lot_size,
                expiry_date,
                strike_price,
                option_type,
                underlying_security_id,
                underlying_symbol
            FROM dhan_instruments
            WHERE underlying_symbol = :underlying
              AND exchange_segment = 'NSE_FNO'
              AND instrument = 'OPTIDX'
              AND expiry_date = :expiry
              AND (:opt_type IS NULL OR option_type = :opt_type)
            ORDER BY strike_price, option_type
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(opt_sql, {
                'underlying': underlying_symbol,
                'expiry': target_expiry,
                'opt_type': option_type
            })
            
            options = [dict(row._mapping) for row in result.fetchall()]
        
        logger.info(f"Found {len(options)} {underlying_symbol} options for {target_expiry}")
        
        return options
    
    # Nifty 50 constituent symbols (as of Dec 2025)
    NIFTY50_SYMBOLS = [
        'ADANIPORTS', 'APOLLOHOSP', 'ASIANPAINT', 'AXISBANK',
        'BAJAJ-AUTO', 'BAJFINANCE', 'BAJAJFINSV', 'BEL', 'BPCL',
        'BHARTIARTL', 'BRITANNIA', 'CIPLA', 'COALINDIA', 'DRREDDY',
        'EICHERMOT', 'GRASIM', 'HCLTECH', 'HDFCBANK',
        'HEROMOTOCO', 'HINDALCO', 'HINDUNILVR', 'ICICIBANK', 'ITC',
        'INDUSINDBK', 'INFY', 'JSWSTEEL', 'KOTAKBANK', 'LT',
        'M&M', 'MARUTI', 'NTPC', 'NESTLEIND', 'ONGC',
        'POWERGRID', 'RELIANCE', 'SBILIFE', 'SHRIRAMFIN', 'SBIN',
        'SUNPHARMA', 'TCS', 'TATACONSUM', 'TMPV', 'TATASTEEL',
        'TECHM', 'TITAN', 'TRENT', 'ULTRACEMCO', 'WIPRO'
    ]
    
    def get_nifty50_stocks(self, series: str = "EQ") -> List[Dict]:
        """
        Get Nifty 50 constituent stocks from dhan_instruments.
        
        Args:
            series: Stock series (default "EQ" for equity)
            
        Returns:
            List of instrument dicts with security_id, symbol, etc.
        """
        # Build placeholders for IN clause
        placeholders = ', '.join([f':sym{i}' for i in range(len(self.NIFTY50_SYMBOLS))])
        
        sql = text(f"""
            SELECT 
                security_id,
                exchange_segment,
                symbol,
                display_name,
                underlying_symbol,
                isin,
                instrument,
                instrument_type,
                series,
                lot_size
            FROM dhan_instruments
            WHERE exchange_segment = 'NSE_EQ'
              AND series = :series
              AND underlying_symbol IN ({placeholders})
            ORDER BY underlying_symbol
        """)
        
        # Build params dict
        params = {'series': series}
        for i, sym in enumerate(self.NIFTY50_SYMBOLS):
            params[f'sym{i}'] = sym
        
        with self.engine.connect() as conn:
            result = conn.execute(sql, params)
            stocks = [dict(row._mapping) for row in result.fetchall()]
        
        logger.info(f"Found {len(stocks)} Nifty 50 stocks in dhan_instruments")
        
        # Log any missing symbols
        found_symbols = {s['underlying_symbol'] for s in stocks}
        missing = set(self.NIFTY50_SYMBOLS) - found_symbols
        if missing:
            logger.warning(f"Missing Nifty 50 symbols in database: {missing}")
        
        return stocks

    def get_nifty500_stocks(self, series: str = "EQ") -> List[Dict]:
        """
        Get Nifty 500 constituent stocks.
        
        Note: This requires having Nifty 500 list somewhere.
        For now, returns all NSE equity instruments.
        """
        sql = text("""
            SELECT 
                security_id,
                exchange_segment,
                symbol,
                display_name,
                isin,
                instrument,
                instrument_type,
                series,
                lot_size
            FROM dhan_instruments
            WHERE exchange_segment = 'NSE_EQ'
              AND series = :series
              AND symbol IS NOT NULL
            ORDER BY symbol
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(sql, {'series': series})
            stocks = [dict(row._mapping) for row in result.fetchall()]
        
        logger.info(f"Found {len(stocks)} NSE equity stocks")
        
        return stocks
    
    def get_indices(self) -> List[Dict]:
        """Get all index instruments."""
        sql = text("""
            SELECT 
                security_id,
                exchange_segment,
                symbol,
                display_name,
                instrument
            FROM dhan_instruments
            WHERE instrument = 'INDEX'
               OR exchange_segment LIKE '%_I'
            ORDER BY symbol
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(sql)
            indices = [dict(row._mapping) for row in result.fetchall()]
        
        logger.info(f"Found {len(indices)} indices")
        
        return indices
    
    def add_to_subscriptions(self, instruments: List[Dict], 
                            feed_type: str = "QUOTE",
                            clear_existing: bool = False) -> int:
        """
        Add instruments to feed subscription table.
        
        Args:
            instruments: List of instrument dicts
            feed_type: TICKER, QUOTE, or FULL
            clear_existing: If True, clear existing subscriptions first
        
        Returns:
            Number of instruments added
        """
        if not instruments:
            return 0
        
        with self.engine.connect() as conn:
            if clear_existing:
                conn.execute(text("DELETE FROM dhan_feed_subscriptions"))
                logger.info("Cleared existing subscriptions")
            
            # Build upsert SQL
            sql = text("""
                INSERT INTO dhan_feed_subscriptions 
                (security_id, exchange_segment, symbol, display_name, 
                 instrument_type, feed_type, expiry_date, strike_price, option_type)
                VALUES 
                (:security_id, :exchange_segment, :symbol, :display_name,
                 :instrument_type, :feed_type, :expiry_date, :strike_price, :option_type)
                ON DUPLICATE KEY UPDATE
                    feed_type = VALUES(feed_type),
                    is_active = 1,
                    updated_at = CURRENT_TIMESTAMP
            """)
            
            count = 0
            for inst in instruments:
                conn.execute(sql, {
                    'security_id': inst['security_id'],
                    'exchange_segment': inst.get('exchange_segment', ''),
                    'symbol': inst.get('symbol', ''),
                    'display_name': inst.get('display_name', ''),
                    'instrument_type': inst.get('instrument', inst.get('instrument_type', '')),
                    'feed_type': feed_type,
                    'expiry_date': inst.get('expiry_date'),
                    'strike_price': inst.get('strike_price'),
                    'option_type': inst.get('option_type')
                })
                count += 1
            
            conn.commit()
        
        logger.info(f"Added {count} instruments to feed subscriptions")
        return count
    
    def get_active_subscriptions(self, feed_type: Optional[str] = None) -> List[Dict]:
        """
        Get all active feed subscriptions.
        
        Args:
            feed_type: Optional filter by feed type
        
        Returns:
            List of subscription dicts
        """
        sql = text("""
            SELECT 
                security_id,
                exchange_segment,
                symbol,
                display_name,
                instrument_type,
                feed_type,
                expiry_date,
                strike_price,
                option_type
            FROM dhan_feed_subscriptions
            WHERE is_active = 1
              AND (:feed_type IS NULL OR feed_type = :feed_type)
            ORDER BY priority DESC, security_id
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(sql, {'feed_type': feed_type})
            subs = [dict(row._mapping) for row in result.fetchall()]
        
        return subs
    
    def get_subscription_count(self) -> int:
        """Get count of active subscriptions."""
        with self.engine.connect() as conn:
            result = conn.execute(text(
                "SELECT COUNT(*) FROM dhan_feed_subscriptions WHERE is_active = 1"
            ))
            return result.fetchone()[0]


def setup_initial_subscriptions():
    """Setup initial subscriptions for Nifty Futures."""
    selector = InstrumentSelector()
    
    print("\n" + "="*50)
    print("Setting up initial feed subscriptions")
    print("="*50)
    
    # Get Nifty Futures (current + next expiry)
    nifty_futs = selector.get_nifty_futures(expiries=[0, 1])
    
    # Get Bank Nifty Futures
    bnf_futs = selector.get_banknifty_futures(expiries=[0, 1])
    
    # Combine all
    all_instruments = nifty_futs + bnf_futs
    
    if all_instruments:
        # Add to subscriptions
        count = selector.add_to_subscriptions(
            all_instruments, 
            feed_type="QUOTE",
            clear_existing=True
        )
        
        print(f"\n✅ Added {count} instruments to feed subscriptions:")
        for inst in all_instruments:
            print(f"   - {inst['display_name']} ({inst['security_id']})")
    else:
        print("❌ No instruments found! Check if dhan_instruments is populated.")
    
    return all_instruments


if __name__ == "__main__":
    setup_initial_subscriptions()
