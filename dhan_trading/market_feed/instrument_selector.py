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
        'ADANIENT', 'ADANIPORTS', 'APOLLOHOSP', 'ASIANPAINT', 'AXISBANK',
        'BAJAJ-AUTO', 'BAJFINANCE', 'BAJAJFINSV', 'BEL', 'BPCL',
        'BHARTIARTL', 'BRITANNIA', 'CIPLA', 'COALINDIA', 'DRREDDY',
        'EICHERMOT', 'GRASIM', 'HCLTECH', 'HDFCBANK', 'HDFCLIFE',
        'HEROMOTOCO', 'HINDALCO', 'HINDUNILVR', 'ICICIBANK', 'ITC',
        'INDUSINDBK', 'INFY', 'JSWSTEEL', 'KOTAKBANK', 'LT',
        'M&M', 'MARUTI', 'NTPC', 'NESTLEIND', 'ONGC',
        'POWERGRID', 'RELIANCE', 'SBILIFE', 'SHRIRAMFIN', 'SBIN',
        'SUNPHARMA', 'TCS', 'TATACONSUM', 'TATAMOTORS', 'TATASTEEL',
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
