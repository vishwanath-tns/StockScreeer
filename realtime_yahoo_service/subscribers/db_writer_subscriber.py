"""
Database Writer Subscriber
===========================

Subscriber that writes candle data events to database.
"""

import logging
from typing import Dict, Any
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.dialects.mysql import insert

from .base_subscriber import BaseSubscriber, SubscriberError
from events.event_models import CandleDataEvent

logger = logging.getLogger(__name__)


class DBWriterSubscriber(BaseSubscriber):
    """
    Subscriber that writes candle data to database
    
    Features:
    - Writes CandleDataEvent to nse_equity_bhavcopy_full table
    - Upsert logic (INSERT ... ON DUPLICATE KEY UPDATE)
    - Batch commit for performance
    - Error handling with DLQ fallback
    """
    
    def __init__(
        self,
        subscriber_id: str,
        broker,
        serializer,
        db_url: str,
        table_name: str = 'nse_equity_bhavcopy_full',
        batch_size: int = 100,
        **kwargs
    ):
        """
        Initialize DB writer subscriber
        
        Args:
            subscriber_id: Unique subscriber identifier
            broker: Event broker instance
            serializer: Message serializer
            db_url: Database connection URL
            table_name: Target table name
            batch_size: Number of records to batch before commit
            **kwargs: Additional arguments for BaseSubscriber
        """
        super().__init__(
            subscriber_id=subscriber_id,
            broker=broker,
            serializer=serializer,
            channels=['market.candle'],  # Subscribe to candle data
            db_url=db_url,
            **kwargs
        )
        
        self.table_name = table_name
        self.batch_size = batch_size
        self._batch = []
        self._write_stats = {
            'total_written': 0,
            'total_upserted': 0,
            'batch_writes': 0,
        }
        
        logger.info(
            f"DBWriterSubscriber initialized: table={table_name}, "
            f"batch_size={batch_size}"
        )
    
    async def on_message(self, channel: str, data: Dict[str, Any]) -> None:
        """
        Handle incoming candle data message
        
        Args:
            channel: Channel name
            data: Deserialized message data
        """
        try:
            # Parse as CandleDataEvent
            event = CandleDataEvent(**data)
            
            # Add to batch
            self._batch.append(event)
            
            # Write batch if full
            if len(self._batch) >= self.batch_size:
                await self._write_batch()
        
        except Exception as e:
            logger.error(f"Error handling candle data: {e}")
            raise SubscriberError(f"Message handling failed: {e}") from e
    
    async def _write_batch(self) -> None:
        """Write batch of candle data to database"""
        if not self._batch:
            return
        
        try:
            async with self.get_db_session() as session:
                # Prepare records
                records = []
                for event in self._batch:
                    record = {
                        'symbol': event.symbol,
                        'series': event.series,
                        'trade_date': event.trade_date,
                        'prev_close': event.prev_close,
                        'open_price': event.open_price,
                        'high_price': event.high_price,
                        'low_price': event.low_price,
                        'close_price': event.close_price,
                        'volume': event.volume,
                        'deliv_qty': event.delivery_qty,
                        'deliv_per': event.delivery_per,
                        'timestamp': event.timestamp,
                        'data_source': event.data_source,
                    }
                    records.append(record)
                
                # Upsert logic - MySQL specific
                stmt = text(f"""
                    INSERT INTO {self.table_name} 
                    (symbol, series, trade_date, prev_close, open_price, high_price, 
                     low_price, close_price, volume, deliv_qty, deliv_per, timestamp, data_source)
                    VALUES 
                    (:symbol, :series, :trade_date, :prev_close, :open_price, :high_price,
                     :low_price, :close_price, :volume, :deliv_qty, :deliv_per, :timestamp, :data_source)
                    ON DUPLICATE KEY UPDATE
                    prev_close = VALUES(prev_close),
                    open_price = VALUES(open_price),
                    high_price = VALUES(high_price),
                    low_price = VALUES(low_price),
                    close_price = VALUES(close_price),
                    volume = VALUES(volume),
                    deliv_qty = VALUES(deliv_qty),
                    deliv_per = VALUES(deliv_per),
                    timestamp = VALUES(timestamp),
                    data_source = VALUES(data_source)
                """)
                
                # Execute batch
                for record in records:
                    await session.execute(stmt, record)
                
                # Commit handled by context manager
                
                # Update statistics
                batch_count = len(self._batch)
                self._write_stats['total_written'] += batch_count
                self._write_stats['batch_writes'] += 1
                
                logger.info(f"Wrote batch: {batch_count} records to {self.table_name}")
                
                # Clear batch
                self._batch.clear()
        
        except Exception as e:
            logger.error(f"Failed to write batch: {e}")
            # Clear batch to avoid retrying bad data
            self._batch.clear()
            raise SubscriberError(f"Batch write failed: {e}") from e
    
    async def stop(self) -> None:
        """Stop subscriber and flush remaining batch"""
        # Write remaining batch
        if self._batch:
            try:
                await self._write_batch()
            except Exception as e:
                logger.error(f"Failed to flush batch on shutdown: {e}")
        
        await super().stop()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics including write stats"""
        stats = super().get_stats()
        stats.update({
            'write_stats': self._write_stats.copy(),
            'batch_pending': len(self._batch),
        })
        return stats
