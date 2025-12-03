"""Price monitor worker - fetches prices from Yahoo Finance."""

import asyncio
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, time
import pytz

import yfinance as yf
import pandas as pd

from .base_worker import BaseWorker
from ..core.enums import AssetType, EventType
from ..core.models import PriceData
from ..events.events import PriceUpdateEvent, PriceBatchUpdateEvent
from ..infrastructure.redis_client import RedisClient, get_redis
from ..infrastructure.config import Config, get_config

logger = logging.getLogger(__name__)

# Indian timezone for market hours detection
IST = pytz.timezone('Asia/Kolkata')


class PriceMonitorWorker(BaseWorker):
    """
    Fetches real-time prices from Yahoo Finance.
    
    Features:
    - Batch fetching by asset type for efficiency
    - Smart polling (faster during market hours)
    - Caches prices in Redis
    - Publishes PRICE_UPDATE events
    """
    
    def __init__(
        self,
        config: Optional[Config] = None,
        redis_client: Optional[RedisClient] = None,
        **kwargs
    ):
        super().__init__(name="PriceMonitorWorker", config=config, **kwargs)
        self.redis = redis_client or get_redis()
        
        # Symbols to monitor, grouped by asset type
        self._symbols: Dict[AssetType, Set[str]] = {
            asset_type: set() for asset_type in AssetType
        }
        
        # Last fetch timestamps
        self._last_fetch: Dict[AssetType, datetime] = {}
        
        # Technical indicator computation
        self._compute_technicals = True
    
    @property
    def total_symbols(self) -> int:
        return sum(len(s) for s in self._symbols.values())
    
    async def on_start(self):
        """Load monitored symbols from Redis/DB."""
        await self._load_monitored_symbols()
        logger.info(f"Loaded {self.total_symbols} symbols to monitor")
    
    async def _load_monitored_symbols(self):
        """Load symbols that have active alerts from Redis."""
        for asset_type in AssetType:
            symbols = self.redis.get_monitored_symbols(asset_type.value)
            self._symbols[asset_type] = set(symbols)
            logger.debug(f"Loaded {len(symbols)} {asset_type.value} symbols")
    
    def add_symbol(self, yahoo_symbol: str, asset_type: AssetType):
        """Add symbol to monitoring."""
        self._symbols[asset_type].add(yahoo_symbol)
        self.redis.add_monitored_symbol(yahoo_symbol, asset_type.value)
        logger.debug(f"Added {yahoo_symbol} to {asset_type.value} monitoring")
    
    def remove_symbol(self, yahoo_symbol: str, asset_type: AssetType):
        """Remove symbol from monitoring."""
        self._symbols[asset_type].discard(yahoo_symbol)
        self.redis.remove_monitored_symbol(yahoo_symbol, asset_type.value)
        logger.debug(f"Removed {yahoo_symbol} from monitoring")
    
    def _is_market_hours(self) -> bool:
        """Check if NSE market is open."""
        now = datetime.now(IST)
        
        # Weekend check
        if now.weekday() >= 5:
            return False
        
        # Market hours: 9:15 AM - 3:30 PM IST
        market_open = time(9, 15)
        market_close = time(15, 30)
        current_time = now.time()
        
        return market_open <= current_time <= market_close
    
    def _get_poll_interval(self, asset_type: AssetType) -> float:
        """Get polling interval based on asset type and market hours."""
        if asset_type in (AssetType.CRYPTO, AssetType.FOREX):
            # Crypto/Forex: 24/7 markets, always use market interval
            return self.config.yahoo.market_hours_interval
        
        if self._is_market_hours():
            return self.config.yahoo.market_hours_interval
        else:
            return self.config.yahoo.off_hours_interval
    
    async def run(self):
        """Main loop - fetch prices for all asset types."""
        tasks = []
        
        for asset_type in AssetType:
            symbols = self._symbols[asset_type]
            if not symbols:
                continue
            
            # Check if enough time has passed since last fetch
            interval = self._get_poll_interval(asset_type)
            last_fetch = self._last_fetch.get(asset_type)
            
            if last_fetch:
                elapsed = (datetime.now() - last_fetch).total_seconds()
                if elapsed < interval:
                    continue
            
            # Schedule fetch
            tasks.append(self._fetch_asset_type(asset_type, list(symbols)))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Nothing to fetch, sleep briefly
            await asyncio.sleep(1)
    
    async def _fetch_asset_type(self, asset_type: AssetType, symbols: List[str]):
        """Fetch prices for all symbols of an asset type."""
        if not symbols:
            return
        
        self._last_fetch[asset_type] = datetime.now()
        batch_size = self._get_batch_size(asset_type)
        
        logger.debug(f"Fetching {len(symbols)} {asset_type.value} symbols")
        
        # Batch the symbols
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            await self._fetch_batch(asset_type, batch)
    
    def _get_batch_size(self, asset_type: AssetType) -> int:
        """Get batch size for asset type."""
        if asset_type in (AssetType.NSE_EQUITY, AssetType.BSE_EQUITY):
            return self.config.yahoo.nse_batch_size
        elif asset_type == AssetType.COMMODITY:
            return self.config.yahoo.commodity_batch_size
        elif asset_type == AssetType.CRYPTO:
            return self.config.yahoo.crypto_batch_size
        else:
            return 20
    
    async def _fetch_batch(self, asset_type: AssetType, symbols: List[str]):
        """Fetch a batch of symbols."""
        try:
            # Run yfinance in executor (it's synchronous)
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                self._fetch_yfinance_data,
                symbols
            )
            
            if data.empty:
                logger.warning(f"No data returned for {symbols[:3]}...")
                return
            
            # Process and publish prices
            price_events = []
            
            for symbol in symbols:
                try:
                    price_data = self._extract_price_data(symbol, asset_type, data)
                    if price_data:
                        # Cache in Redis
                        self.redis.cache_price(symbol, price_data.to_dict())
                        
                        # Create event
                        event = PriceUpdateEvent(
                            symbol=price_data.symbol,
                            yahoo_symbol=price_data.yahoo_symbol,
                            asset_type=price_data.asset_type,
                            price=price_data.price,
                            prev_close=price_data.prev_close,
                            change=price_data.change,
                            change_pct=price_data.change_pct,
                            volume=price_data.volume,
                            high=price_data.high,
                            low=price_data.low,
                            open_price=price_data.open_price,
                            rsi_14=price_data.rsi_14,
                            sma_20=price_data.sma_20,
                            sma_50=price_data.sma_50,
                            high_52w=price_data.high_52w,
                            low_52w=price_data.low_52w,
                        )
                        
                        # Publish individual event
                        await self.event_bus.publish_async(event)
                        price_events.append(event.payload)
                        
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}")
            
            logger.debug(f"Published {len(price_events)} price updates for {asset_type.value}")
            
        except Exception as e:
            logger.error(f"Batch fetch error for {asset_type.value}: {e}")
    
    def _fetch_yfinance_data(self, symbols: List[str]) -> pd.DataFrame:
        """Synchronous yfinance data fetch."""
        try:
            # Use download for batch
            tickers = yf.Tickers(' '.join(symbols))
            
            # Get current prices
            data = {}
            for symbol in symbols:
                try:
                    ticker = tickers.tickers.get(symbol)
                    if ticker:
                        info = ticker.fast_info
                        hist = ticker.history(period='2d')
                        
                        if not hist.empty:
                            latest = hist.iloc[-1]
                            prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else latest['Close']
                            
                            data[symbol] = {
                                'price': float(latest['Close']),
                                'open': float(latest['Open']),
                                'high': float(latest['High']),
                                'low': float(latest['Low']),
                                'volume': int(latest['Volume']),
                                'prev_close': float(prev_close),
                                'high_52w': getattr(info, 'year_high', None),
                                'low_52w': getattr(info, 'year_low', None),
                            }
                except Exception as e:
                    logger.debug(f"Error fetching {symbol}: {e}")
            
            return pd.DataFrame.from_dict(data, orient='index')
            
        except Exception as e:
            logger.error(f"yfinance fetch error: {e}")
            return pd.DataFrame()
    
    def _extract_price_data(
        self,
        symbol: str,
        asset_type: AssetType,
        data: pd.DataFrame
    ) -> Optional[PriceData]:
        """Extract PriceData from DataFrame."""
        if symbol not in data.index:
            return None
        
        row = data.loc[symbol]
        
        price = float(row.get('price', 0))
        prev_close = float(row.get('prev_close', price))
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0
        
        # Extract base symbol (remove suffix)
        base_symbol = symbol
        if symbol.endswith('.NS'):
            base_symbol = symbol[:-3]
        elif symbol.endswith('.BO'):
            base_symbol = symbol[:-3]
        
        return PriceData(
            symbol=base_symbol,
            yahoo_symbol=symbol,
            asset_type=asset_type,
            price=price,
            prev_close=prev_close,
            open_price=float(row.get('open', 0)),
            high=float(row.get('high', 0)),
            low=float(row.get('low', 0)),
            volume=int(row.get('volume', 0)),
            change=round(change, 2),
            change_pct=round(change_pct, 2),
            timestamp=datetime.now(),
            high_52w=row.get('high_52w'),
            low_52w=row.get('low_52w'),
        )
    
    async def on_stop(self):
        """Cleanup on stop."""
        logger.info(f"Price monitor stats: {self._iterations} iterations, {self._error_count} errors")


def get_yahoo_symbol(symbol: str, asset_type: AssetType) -> str:
    """Convert symbol to Yahoo Finance format."""
    if asset_type == AssetType.NSE_EQUITY:
        return f"{symbol}.NS"
    elif asset_type == AssetType.BSE_EQUITY:
        return f"{symbol}.BO"
    elif asset_type == AssetType.NSE_INDEX:
        # Common index mappings
        index_map = {
            'NIFTY': '^NSEI',
            'NIFTY50': '^NSEI',
            'NIFTYBANK': '^NSEBANK',
            'BANKNIFTY': '^NSEBANK',
            'NIFTYIT': '^CNXIT',
        }
        return index_map.get(symbol.upper(), symbol)
    elif asset_type == AssetType.COMMODITY:
        # Common commodity mappings
        commodity_map = {
            'GOLD': 'GC=F',
            'SILVER': 'SI=F',
            'CRUDE': 'CL=F',
            'CRUDEOIL': 'CL=F',
            'NATURALGAS': 'NG=F',
            'COPPER': 'HG=F',
        }
        return commodity_map.get(symbol.upper(), symbol)
    elif asset_type == AssetType.CRYPTO:
        # Add USD suffix if not present
        if not symbol.endswith('-USD'):
            return f"{symbol}-USD"
        return symbol
    elif asset_type == AssetType.FOREX:
        if not symbol.endswith('=X'):
            return f"{symbol}=X"
        return symbol
    
    return symbol
