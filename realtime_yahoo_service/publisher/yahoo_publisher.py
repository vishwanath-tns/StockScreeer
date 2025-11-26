"""
Yahoo Finance Publisher
=======================

Publisher that fetches market data from Yahoo Finance and publishes events.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from decimal import Decimal

import yfinance as yf
import pandas as pd

from .base_publisher import BasePublisher, PublisherError
from events.event_models import CandleDataEvent, FetchStatusEvent

logger = logging.getLogger(__name__)


class YahooFinancePublisher(BasePublisher):
    """
    Yahoo Finance publisher for real-time market data
    
    Features:
    - Batch fetching with configurable batch size
    - Rate limiting (20 requests per minute default)
    - Error handling and retry logic
    - Health status reporting via FetchStatusEvent
    - Support for 500+ symbols
    """
    
    def __init__(
        self,
        publisher_id: str,
        broker,  # IEventBroker
        serializer,  # IMessageSerializer
        symbols: List[str],
        batch_size: int = 50,
        rate_limit: int = 20,
        rate_limit_period: float = 60.0,
        publish_interval: float = 5.0,
        data_interval: str = '1m',
        period: str = '1d',
    ):
        """
        Initialize Yahoo Finance publisher
        
        Args:
            publisher_id: Unique publisher identifier
            broker: Event broker instance
            serializer: Message serializer
            symbols: List of stock symbols to fetch
            batch_size: Number of symbols per batch (default: 50)
            rate_limit: Maximum requests per period (default: 20)
            rate_limit_period: Rate limit period in seconds (default: 60)
            publish_interval: Interval between fetch cycles (default: 5s)
            data_interval: Yahoo Finance data interval (1m, 5m, 15m, etc.)
            period: Yahoo Finance period (1d, 5d, 1mo, etc.)
        """
        super().__init__(
            publisher_id=publisher_id,
            broker=broker,
            serializer=serializer,
            rate_limit=rate_limit,
            rate_limit_period=rate_limit_period,
            publish_interval=publish_interval,
        )
        
        self.symbols = symbols
        self.batch_size = batch_size
        self.data_interval = data_interval
        self.period = period
        
        # Fetch statistics
        self._fetch_stats = {
            'total_fetches': 0,
            'total_fetch_errors': 0,
            'symbols_fetched': 0,
            'symbols_failed': 0,
            'last_fetch_time': None,
            'last_fetch_duration': None,
        }
        
        logger.info(
            f"YahooFinancePublisher initialized: id={publisher_id}, "
            f"symbols={len(symbols)}, batch_size={batch_size}, "
            f"interval={data_interval}"
        )
    
    async def _fetch_and_publish(self) -> None:
        """
        Fetch data from Yahoo Finance and publish events
        
        This method:
        1. Splits symbols into batches
        2. Fetches data for each batch
        3. Publishes CandleDataEvent for each symbol
        4. Publishes FetchStatusEvent with overall status
        """
        fetch_start = asyncio.get_event_loop().time()
        symbols_success = 0
        symbols_failed = 0
        errors = []
        
        try:
            # Split symbols into batches
            batches = [
                self.symbols[i:i + self.batch_size]
                for i in range(0, len(self.symbols), self.batch_size)
            ]
            
            logger.info(
                f"Starting fetch cycle: {len(self.symbols)} symbols "
                f"in {len(batches)} batches"
            )
            
            # Process each batch
            for batch_idx, batch in enumerate(batches):
                try:
                    # Fetch batch (runs in thread pool to avoid blocking)
                    batch_data = await asyncio.get_event_loop().run_in_executor(
                        None,
                        self._fetch_batch,
                        batch
                    )
                    
                    # Publish events for successful fetches
                    for symbol, data in batch_data.items():
                        if data is not None:
                            try:
                                await self._publish_candle_data(symbol, data)
                                symbols_success += 1
                            except Exception as e:
                                logger.error(f"Failed to publish {symbol}: {e}")
                                symbols_failed += 1
                                errors.append(f"{symbol}: {str(e)}")
                        else:
                            symbols_failed += 1
                            errors.append(f"{symbol}: No data returned")
                    
                    logger.debug(
                        f"Batch {batch_idx + 1}/{len(batches)} complete: "
                        f"{len(batch)} symbols"
                    )
                
                except Exception as e:
                    logger.error(f"Batch {batch_idx} fetch failed: {e}")
                    symbols_failed += len(batch)
                    errors.append(f"Batch {batch_idx}: {str(e)}")
            
            # Update fetch statistics
            fetch_duration = asyncio.get_event_loop().time() - fetch_start
            self._fetch_stats['total_fetches'] += 1
            self._fetch_stats['symbols_fetched'] += symbols_success
            self._fetch_stats['symbols_failed'] += symbols_failed
            self._fetch_stats['last_fetch_time'] = fetch_start
            self._fetch_stats['last_fetch_duration'] = fetch_duration
            
            # Publish status event
            await self._publish_fetch_status(
                success_count=symbols_success,
                failure_count=symbols_failed,
                errors=errors[:10],  # Limit to first 10 errors
            )
            
            logger.info(
                f"Fetch cycle complete: {symbols_success} success, "
                f"{symbols_failed} failed, {fetch_duration:.2f}s"
            )
        
        except Exception as e:
            logger.error(f"Fetch cycle error: {e}")
            self._fetch_stats['total_fetch_errors'] += 1
            raise PublisherError(f"Fetch cycle failed: {e}") from e
    
    def _fetch_batch(self, symbols: List[str]) -> Dict[str, Optional[pd.DataFrame]]:
        """
        Fetch data for a batch of symbols using yfinance
        
        Args:
            symbols: List of symbols to fetch
        
        Returns:
            Dictionary mapping symbol to DataFrame (or None if failed)
        """
        result = {}
        
        try:
            # Download batch data
            # Note: yfinance.download() is synchronous
            data = yf.download(
                tickers=symbols,
                period=self.period,
                interval=self.data_interval,
                group_by='ticker',
                auto_adjust=True,
                prepost=False,
                threads=True,
                progress=False,
            )
            
            # Handle single symbol vs multiple symbols
            if len(symbols) == 1:
                symbol = symbols[0]
                if not data.empty:
                    result[symbol] = data
                else:
                    result[symbol] = None
            else:
                # Multiple symbols - extract each
                for symbol in symbols:
                    try:
                        if symbol in data.columns.levels[0]:
                            symbol_data = data[symbol]
                            if not symbol_data.empty:
                                result[symbol] = symbol_data
                            else:
                                result[symbol] = None
                        else:
                            result[symbol] = None
                    except Exception as e:
                        logger.debug(f"Error extracting {symbol}: {e}")
                        result[symbol] = None
        
        except Exception as e:
            logger.error(f"Batch fetch failed for {len(symbols)} symbols: {e}")
            # Mark all symbols as failed
            for symbol in symbols:
                result[symbol] = None
        
        return result
    
    async def _publish_candle_data(
        self,
        symbol: str,
        data: pd.DataFrame
    ) -> None:
        """
        Publish candle data event for a symbol
        
        Args:
            symbol: Stock symbol
            data: DataFrame with OHLCV data
        """
        try:
            # Get the latest row
            if data.empty:
                return
            
            latest = data.iloc[-1]
            timestamp = data.index[-1]
            
            # Convert to datetime with timezone
            if isinstance(timestamp, pd.Timestamp):
                if timestamp.tzinfo is None:
                    timestamp = timestamp.tz_localize('UTC')
                else:
                    timestamp = timestamp.tz_convert('UTC')
                timestamp_dt = timestamp.to_pydatetime()
            else:
                timestamp_dt = timestamp
            
            # Extract trade date and unix timestamp
            trade_date = timestamp_dt.date().isoformat()
            unix_timestamp = int(timestamp_dt.timestamp())
            
            # Extract OHLCV values with safe conversion
            event = CandleDataEvent(
                symbol=symbol,
                trade_date=trade_date,
                timestamp=unix_timestamp,
                open_price=self._safe_float(latest.get('Open')),
                high_price=self._safe_float(latest.get('High')),
                low_price=self._safe_float(latest.get('Low')),
                close_price=self._safe_float(latest.get('Close')),
                volume=self._safe_int(latest.get('Volume')),
                prev_close=self._safe_float(latest.get('Close')),  # Previous close
                series='EQ',  # Default to equity series
                delivery_qty=None,  # Not available from Yahoo Finance
                delivery_per=None,  # Not available from Yahoo Finance
            )
            
            # Publish event
            await self.publish_event(event)
            
            logger.debug(
                f"Published candle data: {symbol} @ {trade_date}, "
                f"close={event.close_price}"
            )
        
        except Exception as e:
            logger.error(f"Failed to create candle event for {symbol}: {e}")
            raise
    
    async def _publish_fetch_status(
        self,
        success_count: int,
        failure_count: int,
        errors: List[str],
    ) -> None:
        """
        Publish fetch status event
        
        Args:
            success_count: Number of successful fetches
            failure_count: Number of failed fetches
            errors: List of error messages
        """
        try:
            total = success_count + failure_count
            success_rate = (success_count / total * 100) if total > 0 else 0
            
            # Determine status
            if failure_count == 0:
                status = 'HEALTHY'
            elif success_rate >= 80:
                status = 'DEGRADED'
            else:
                status = 'UNHEALTHY'
            
            # Calculate uptime
            uptime_secs = int(asyncio.get_event_loop().time() - self._start_time) if self._start_time else 0
            
            # Get last fetch duration
            fetch_duration_ms = int((self._fetch_stats.get('last_fetch_duration', 0) or 0) * 1000)
            
            event = FetchStatusEvent(
                publisher_id=self.publisher_id,
                status=status,
                timestamp=int(datetime.now(timezone.utc).timestamp()),
                symbols_succeeded=success_count,
                symbols_failed=failure_count,
                total_symbols=len(self.symbols),
                batch_size=self.batch_size,
                rate_limit=int(self.rate_limiter.rate),
                failed_symbols=errors[:10],  # Limit to 10
                fetch_duration_ms=fetch_duration_ms,
                uptime_seconds=uptime_secs,
                total_events_published=self._stats['total_published'],
            )
            
            await self.publish_event(event)
            
            logger.debug(f"Published fetch status: {status}, {success_count}/{total}")
        
        except Exception as e:
            logger.error(f"Failed to publish fetch status: {e}")
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float"""
        if value is None or pd.isna(value):
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _safe_int(self, value: Any) -> Optional[int]:
        """Safely convert value to int"""
        if value is None or pd.isna(value):
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    def _get_channel_for_event(self, event: Any) -> str:
        """
        Determine channel name from event type
        
        Args:
            event: Event object
        
        Returns:
            Channel name
        """
        if isinstance(event, CandleDataEvent):
            return 'market.candle'
        elif isinstance(event, FetchStatusEvent):
            return 'market.status'
        else:
            return super()._get_channel_for_event(event)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get publisher statistics including fetch stats"""
        stats = super().get_stats()
        stats.update({
            'total_symbols': len(self.symbols),
            'batch_size': self.batch_size,
            'data_interval': self.data_interval,
            'fetch_stats': self._fetch_stats.copy(),
        })
        return stats
