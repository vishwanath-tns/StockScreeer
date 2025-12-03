"""Symbol service - manage symbols and lookups."""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy import text

from ..core.enums import AssetType
from ..infrastructure.database import Database, get_database
from ..infrastructure.redis_client import RedisClient, get_redis
from ..workers.price_monitor import get_yahoo_symbol

logger = logging.getLogger(__name__)


# Common symbol lists
POPULAR_NSE_SYMBOLS = [
    'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK',
    'HINDUNILVR', 'ITC', 'SBIN', 'BHARTIARTL', 'KOTAKBANK',
    'LT', 'AXISBANK', 'ASIANPAINT', 'MARUTI', 'TITAN',
    'BAJFINANCE', 'WIPRO', 'ULTRACEMCO', 'NESTLEIND', 'SUNPHARMA'
]

POPULAR_COMMODITIES = [
    ('GOLD', 'GC=F', 'Gold Futures'),
    ('SILVER', 'SI=F', 'Silver Futures'),
    ('CRUDE', 'CL=F', 'Crude Oil WTI'),
    ('BRENT', 'BZ=F', 'Brent Crude Oil'),
    ('NATURALGAS', 'NG=F', 'Natural Gas'),
    ('COPPER', 'HG=F', 'Copper Futures'),
    ('PLATINUM', 'PL=F', 'Platinum Futures'),
    ('PALLADIUM', 'PA=F', 'Palladium Futures'),
]

POPULAR_CRYPTO = [
    ('BTC', 'BTC-USD', 'Bitcoin'),
    ('ETH', 'ETH-USD', 'Ethereum'),
    ('BNB', 'BNB-USD', 'Binance Coin'),
    ('SOL', 'SOL-USD', 'Solana'),
    ('XRP', 'XRP-USD', 'Ripple'),
    ('ADA', 'ADA-USD', 'Cardano'),
    ('DOGE', 'DOGE-USD', 'Dogecoin'),
    ('DOT', 'DOT-USD', 'Polkadot'),
]

NSE_INDICES = [
    ('NIFTY50', '^NSEI', 'NIFTY 50'),
    ('NIFTYBANK', '^NSEBANK', 'Bank NIFTY'),
    ('NIFTYIT', '^CNXIT', 'NIFTY IT'),
    ('NIFTYNEXT50', '^NSMIDCP', 'NIFTY Next 50'),
]


class SymbolService:
    """Service for symbol management and lookup."""
    
    def __init__(
        self,
        database: Optional[Database] = None,
        redis: Optional[RedisClient] = None,
    ):
        self.db = database or get_database()
        self.redis = redis or get_redis()
    
    def get_yahoo_symbol(self, symbol: str, asset_type: AssetType) -> str:
        """Convert symbol to Yahoo Finance format."""
        return get_yahoo_symbol(symbol, asset_type)
    
    def search_symbols(
        self,
        query: str,
        asset_type: Optional[AssetType] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search for symbols by name or code."""
        query = query.upper()
        results = []
        
        # Search NSE symbols (from cache if available)
        if asset_type is None or asset_type == AssetType.NSE_EQUITY:
            for symbol in POPULAR_NSE_SYMBOLS:
                if query in symbol:
                    results.append({
                        'symbol': symbol,
                        'yahoo_symbol': f"{symbol}.NS",
                        'name': symbol,
                        'asset_type': AssetType.NSE_EQUITY.value,
                        'exchange': 'NSE',
                    })
        
        # Search commodities
        if asset_type is None or asset_type == AssetType.COMMODITY:
            for symbol, yahoo_sym, name in POPULAR_COMMODITIES:
                if query in symbol or query in name.upper():
                    results.append({
                        'symbol': symbol,
                        'yahoo_symbol': yahoo_sym,
                        'name': name,
                        'asset_type': AssetType.COMMODITY.value,
                        'exchange': 'COMMODITY',
                    })
        
        # Search crypto
        if asset_type is None or asset_type == AssetType.CRYPTO:
            for symbol, yahoo_sym, name in POPULAR_CRYPTO:
                if query in symbol or query in name.upper():
                    results.append({
                        'symbol': symbol,
                        'yahoo_symbol': yahoo_sym,
                        'name': name,
                        'asset_type': AssetType.CRYPTO.value,
                        'exchange': 'CRYPTO',
                    })
        
        # Search indices
        if asset_type is None or asset_type == AssetType.NSE_INDEX:
            for symbol, yahoo_sym, name in NSE_INDICES:
                if query in symbol or query in name.upper():
                    results.append({
                        'symbol': symbol,
                        'yahoo_symbol': yahoo_sym,
                        'name': name,
                        'asset_type': AssetType.NSE_INDEX.value,
                        'exchange': 'NSE',
                    })
        
        # Also search database cache
        db_results = self._search_symbol_cache(query, asset_type, limit)
        results.extend(db_results)
        
        # Deduplicate
        seen = set()
        unique_results = []
        for r in results:
            key = r['yahoo_symbol']
            if key not in seen:
                seen.add(key)
                unique_results.append(r)
        
        return unique_results[:limit]
    
    def _search_symbol_cache(
        self,
        query: str,
        asset_type: Optional[AssetType],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Search symbol cache in database."""
        try:
            engine = self.db.get_sync_engine()
            
            sql = """
                SELECT * FROM symbol_cache 
                WHERE (symbol LIKE :query OR name LIKE :query)
            """
            params = {'query': f"%{query}%", 'limit': limit}
            
            if asset_type:
                sql += " AND asset_type = :asset_type"
                params['asset_type'] = asset_type.value
            
            sql += " LIMIT :limit"
            
            with engine.connect() as conn:
                result = conn.execute(text(sql), params)
                return [dict(row._mapping) for row in result]
                
        except Exception as e:
            logger.debug(f"Symbol cache search error: {e}")
            return []
    
    def cache_symbol(
        self,
        yahoo_symbol: str,
        symbol: str,
        asset_type: AssetType,
        name: Optional[str] = None,
        exchange: Optional[str] = None,
        currency: Optional[str] = None,
    ):
        """Cache symbol information."""
        try:
            engine = self.db.get_sync_engine()
            
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO symbol_cache (yahoo_symbol, symbol, name, asset_type, exchange, currency)
                    VALUES (:yahoo_symbol, :symbol, :name, :asset_type, :exchange, :currency)
                    ON DUPLICATE KEY UPDATE
                        name = COALESCE(:name, name),
                        exchange = COALESCE(:exchange, exchange),
                        currency = COALESCE(:currency, currency),
                        last_updated = NOW()
                """), {
                    'yahoo_symbol': yahoo_symbol,
                    'symbol': symbol,
                    'name': name or symbol,
                    'asset_type': asset_type.value,
                    'exchange': exchange,
                    'currency': currency,
                })
                
        except Exception as e:
            logger.error(f"Error caching symbol: {e}")
    
    def get_popular_symbols(self, asset_type: AssetType) -> List[Dict[str, Any]]:
        """Get list of popular symbols for an asset type."""
        if asset_type == AssetType.NSE_EQUITY:
            return [
                {'symbol': s, 'yahoo_symbol': f"{s}.NS", 'asset_type': asset_type.value}
                for s in POPULAR_NSE_SYMBOLS
            ]
        
        elif asset_type == AssetType.COMMODITY:
            return [
                {'symbol': s, 'yahoo_symbol': y, 'name': n, 'asset_type': asset_type.value}
                for s, y, n in POPULAR_COMMODITIES
            ]
        
        elif asset_type == AssetType.CRYPTO:
            return [
                {'symbol': s, 'yahoo_symbol': y, 'name': n, 'asset_type': asset_type.value}
                for s, y, n in POPULAR_CRYPTO
            ]
        
        elif asset_type == AssetType.NSE_INDEX:
            return [
                {'symbol': s, 'yahoo_symbol': y, 'name': n, 'asset_type': asset_type.value}
                for s, y, n in NSE_INDICES
            ]
        
        return []
    
    def validate_symbol(self, symbol: str, asset_type: AssetType) -> bool:
        """Validate a symbol exists and is tradeable."""
        yahoo_symbol = self.get_yahoo_symbol(symbol, asset_type)
        
        try:
            import yfinance as yf
            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.fast_info
            
            # Check if we got valid data
            if hasattr(info, 'last_price') and info.last_price:
                return True
            
            # Try getting history
            hist = ticker.history(period='1d')
            return not hist.empty
            
        except Exception as e:
            logger.debug(f"Symbol validation failed for {yahoo_symbol}: {e}")
            return False
    
    def get_current_price(self, symbol: str, asset_type: AssetType) -> Optional[Dict[str, Any]]:
        """Get current price for a symbol."""
        yahoo_symbol = self.get_yahoo_symbol(symbol, asset_type)
        
        # Check Redis cache first
        cached = self.redis.get_cached_price(yahoo_symbol)
        if cached:
            return cached
        
        # Fetch from Yahoo
        try:
            import yfinance as yf
            ticker = yf.Ticker(yahoo_symbol)
            hist = ticker.history(period='2d')
            
            if hist.empty:
                return None
            
            latest = hist.iloc[-1]
            prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else latest['Close']
            
            price = float(latest['Close'])
            change = price - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0
            
            result = {
                'symbol': symbol,
                'yahoo_symbol': yahoo_symbol,
                'price': price,
                'prev_close': float(prev_close),
                'change': round(change, 2),
                'change_pct': round(change_pct, 2),
                'high': float(latest['High']),
                'low': float(latest['Low']),
                'volume': int(latest['Volume']),
                'timestamp': datetime.now().isoformat(),
            }
            
            # Cache it
            self.redis.cache_price(yahoo_symbol, result, ttl=30)
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None
