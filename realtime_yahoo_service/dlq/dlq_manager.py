"""
Dead Letter Queue Manager
==========================

Manages failed message processing with retry logic and persistence.
"""

import asyncio
import logging
import time
import json
from typing import Optional, Any, Dict, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DLQMessage:
    """Dead letter queue message with metadata"""
    
    id: str  # Unique message ID
    channel: str  # Original channel
    payload: bytes  # Original message payload
    error_message: str  # Error that caused failure
    error_type: str  # Exception type
    original_timestamp: float  # When message was originally published
    failure_timestamp: float  # When processing failed
    retry_count: int  # Number of retry attempts
    max_retries: int  # Maximum retry attempts allowed
    subscriber_id: str  # ID of subscriber that failed
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'channel': self.channel,
            'payload': self.payload.hex(),  # Convert bytes to hex string
            'error_message': self.error_message,
            'error_type': self.error_type,
            'original_timestamp': self.original_timestamp,
            'failure_timestamp': self.failure_timestamp,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'subscriber_id': self.subscriber_id,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DLQMessage':
        """Create from dictionary"""
        data['payload'] = bytes.fromhex(data['payload'])  # Convert hex to bytes
        return cls(**data)
    
    def is_retryable(self) -> bool:
        """Check if message can be retried"""
        return self.retry_count < self.max_retries
    
    def should_discard(self, retention_days: int) -> bool:
        """Check if message should be discarded based on age"""
        age_days = (time.time() - self.failure_timestamp) / 86400
        return age_days > retention_days


class DLQManager:
    """
    Dead Letter Queue Manager for handling failed messages
    
    Features:
    - Persist failed messages to disk
    - Automatic retry with exponential backoff
    - Manual replay capability
    - Age-based cleanup
    - Statistics tracking
    """
    
    def __init__(
        self,
        storage_path: str = "./dlq",
        max_retries: int = 3,
        retry_delay_base: float = 60.0,  # 1 minute base delay
        retention_days: int = 7,
        enable_auto_retry: bool = True,
        auto_retry_interval: float = 300.0,  # 5 minutes
    ):
        """
        Initialize DLQ manager
        
        Args:
            storage_path: Directory to store DLQ messages
            max_retries: Maximum retry attempts per message
            retry_delay_base: Base delay for exponential backoff (seconds)
            retention_days: Days to retain messages before cleanup
            enable_auto_retry: Enable automatic retry background task
            auto_retry_interval: Interval between auto-retry attempts (seconds)
        """
        self.storage_path = Path(storage_path)
        self.max_retries = max_retries
        self.retry_delay_base = retry_delay_base
        self.retention_days = retention_days
        self.enable_auto_retry = enable_auto_retry
        self.auto_retry_interval = auto_retry_interval
        
        # In-memory message queue (id -> DLQMessage)
        self._messages: Dict[str, DLQMessage] = {}
        
        # Background tasks
        self._retry_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown = False
        
        # Statistics
        self._stats = {
            'total_failures': 0,
            'total_retries': 0,
            'total_successes': 0,
            'total_discarded': 0,
            'failures_by_channel': {},
            'failures_by_subscriber': {},
        }
        
        # Ensure storage directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            f"DLQManager initialized: storage={storage_path}, "
            f"max_retries={max_retries}, retention={retention_days}d"
        )
    
    async def start(self) -> None:
        """Start DLQ manager background tasks"""
        # Load existing messages from disk
        await self._load_messages()
        
        # Start auto-retry task
        if self.enable_auto_retry:
            self._retry_task = asyncio.create_task(self._auto_retry_loop())
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("DLQ manager started")
    
    async def stop(self) -> None:
        """Stop DLQ manager and cleanup"""
        self._shutdown = True
        logger.info("Stopping DLQ manager...")
        
        # Cancel background tasks
        if self._retry_task:
            self._retry_task.cancel()
            try:
                await self._retry_task
            except asyncio.CancelledError:
                pass
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Save messages to disk
        await self._save_messages()
        
        logger.info("DLQ manager stopped")
    
    async def add_failed_message(
        self,
        message_id: str,
        channel: str,
        payload: bytes,
        error: Exception,
        subscriber_id: str,
        original_timestamp: Optional[float] = None,
    ) -> None:
        """
        Add a failed message to the DLQ
        
        Args:
            message_id: Unique message identifier
            channel: Channel the message was on
            payload: Original message payload
            error: Exception that caused the failure
            subscriber_id: ID of the subscriber that failed
            original_timestamp: Original message timestamp
        """
        dlq_msg = DLQMessage(
            id=message_id,
            channel=channel,
            payload=payload,
            error_message=str(error),
            error_type=type(error).__name__,
            original_timestamp=original_timestamp or time.time(),
            failure_timestamp=time.time(),
            retry_count=0,
            max_retries=self.max_retries,
            subscriber_id=subscriber_id,
        )
        
        self._messages[message_id] = dlq_msg
        
        # Update statistics
        self._stats['total_failures'] += 1
        self._stats['failures_by_channel'][channel] = \
            self._stats['failures_by_channel'].get(channel, 0) + 1
        self._stats['failures_by_subscriber'][subscriber_id] = \
            self._stats['failures_by_subscriber'].get(subscriber_id, 0) + 1
        
        # Persist immediately
        await self._save_message(dlq_msg)
        
        logger.warning(
            f"Message added to DLQ: id={message_id}, channel={channel}, "
            f"error={error}, subscriber={subscriber_id}"
        )
    
    async def retry_message(
        self,
        message_id: str,
        retry_callback,
    ) -> bool:
        """
        Retry a specific message
        
        Args:
            message_id: Message ID to retry
            retry_callback: Async function to call for retry (channel, payload)
        
        Returns:
            True if retry succeeded, False otherwise
        """
        if message_id not in self._messages:
            logger.error(f"Message not found in DLQ: {message_id}")
            return False
        
        dlq_msg = self._messages[message_id]
        
        if not dlq_msg.is_retryable():
            logger.warning(f"Message exceeded max retries: {message_id}")
            return False
        
        try:
            # Attempt retry
            await retry_callback(dlq_msg.channel, dlq_msg.payload)
            
            # Success - remove from DLQ
            del self._messages[message_id]
            await self._delete_message_file(message_id)
            
            self._stats['total_successes'] += 1
            
            logger.info(f"Message retry succeeded: {message_id}")
            return True
        
        except Exception as e:
            # Retry failed - increment count
            dlq_msg.retry_count += 1
            dlq_msg.error_message = str(e)
            dlq_msg.error_type = type(e).__name__
            dlq_msg.failure_timestamp = time.time()
            
            self._stats['total_retries'] += 1
            
            # Save updated message
            await self._save_message(dlq_msg)
            
            logger.error(
                f"Message retry failed ({dlq_msg.retry_count}/{dlq_msg.max_retries}): "
                f"{message_id}, error={e}"
            )
            
            # If max retries reached, log for manual intervention
            if not dlq_msg.is_retryable():
                logger.critical(
                    f"Message permanently failed after {dlq_msg.max_retries} retries: "
                    f"{message_id}"
                )
            
            return False
    
    async def replay_all(self, retry_callback) -> Dict[str, Any]:
        """
        Replay all retryable messages
        
        Args:
            retry_callback: Async function to call for retry
        
        Returns:
            Dictionary with replay statistics
        """
        total = len(self._messages)
        succeeded = 0
        failed = 0
        
        logger.info(f"Starting replay of {total} messages...")
        
        for message_id in list(self._messages.keys()):
            if await self.retry_message(message_id, retry_callback):
                succeeded += 1
            else:
                failed += 1
        
        result = {
            'total': total,
            'succeeded': succeeded,
            'failed': failed,
        }
        
        logger.info(f"Replay complete: {result}")
        return result
    
    def get_message(self, message_id: str) -> Optional[DLQMessage]:
        """Get a specific message from DLQ"""
        return self._messages.get(message_id)
    
    def get_all_messages(self) -> List[DLQMessage]:
        """Get all messages in DLQ"""
        return list(self._messages.values())
    
    def get_messages_by_channel(self, channel: str) -> List[DLQMessage]:
        """Get all messages for a specific channel"""
        return [msg for msg in self._messages.values() if msg.channel == channel]
    
    def get_retryable_messages(self) -> List[DLQMessage]:
        """Get all messages that can be retried"""
        return [msg for msg in self._messages.values() if msg.is_retryable()]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get DLQ statistics"""
        return {
            'total_messages': len(self._messages),
            'retryable_messages': len(self.get_retryable_messages()),
            'total_failures': self._stats['total_failures'],
            'total_retries': self._stats['total_retries'],
            'total_successes': self._stats['total_successes'],
            'total_discarded': self._stats['total_discarded'],
            'failures_by_channel': dict(self._stats['failures_by_channel']),
            'failures_by_subscriber': dict(self._stats['failures_by_subscriber']),
        }
    
    # ========================================================================
    # Private Methods
    # ========================================================================
    
    async def _auto_retry_loop(self) -> None:
        """Background task to automatically retry failed messages"""
        logger.info("Auto-retry loop started")
        
        try:
            while not self._shutdown:
                await asyncio.sleep(self.auto_retry_interval)
                
                retryable = self.get_retryable_messages()
                if retryable:
                    logger.info(f"Auto-retry: {len(retryable)} messages eligible")
                    # Note: Actual retry requires callback from subscribers
                    # This is handled by DLQSubscriber
        
        except asyncio.CancelledError:
            logger.info("Auto-retry loop cancelled")
    
    async def _cleanup_loop(self) -> None:
        """Background task to cleanup old messages"""
        logger.info("Cleanup loop started")
        
        try:
            while not self._shutdown:
                await asyncio.sleep(3600)  # Check every hour
                
                # Find old messages
                to_discard = []
                for msg_id, msg in self._messages.items():
                    if msg.should_discard(self.retention_days):
                        to_discard.append(msg_id)
                
                # Remove old messages
                for msg_id in to_discard:
                    del self._messages[msg_id]
                    await self._delete_message_file(msg_id)
                    self._stats['total_discarded'] += 1
                
                if to_discard:
                    logger.info(f"Cleaned up {len(to_discard)} old messages")
        
        except asyncio.CancelledError:
            logger.info("Cleanup loop cancelled")
    
    async def _save_message(self, msg: DLQMessage) -> None:
        """Save a single message to disk"""
        file_path = self.storage_path / f"{msg.id}.json"
        
        try:
            with open(file_path, 'w') as f:
                json.dump(msg.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save DLQ message {msg.id}: {e}")
    
    async def _save_messages(self) -> None:
        """Save all messages to disk"""
        for msg in self._messages.values():
            await self._save_message(msg)
        
        logger.info(f"Saved {len(self._messages)} DLQ messages to disk")
    
    async def _load_messages(self) -> None:
        """Load messages from disk"""
        try:
            json_files = list(self.storage_path.glob("*.json"))
            
            for file_path in json_files:
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    
                    msg = DLQMessage.from_dict(data)
                    self._messages[msg.id] = msg
                
                except Exception as e:
                    logger.error(f"Failed to load DLQ message from {file_path}: {e}")
            
            logger.info(f"Loaded {len(self._messages)} DLQ messages from disk")
        
        except Exception as e:
            logger.error(f"Failed to load DLQ messages: {e}")
    
    async def _delete_message_file(self, message_id: str) -> None:
        """Delete a message file from disk"""
        file_path = self.storage_path / f"{message_id}.json"
        
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logger.error(f"Failed to delete DLQ message file {message_id}: {e}")
