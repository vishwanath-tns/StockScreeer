"""
Unit Tests for Dead Letter Queue
=================================

Tests for DLQ manager and message handling.
"""

import sys
import os
import unittest
import asyncio
import tempfile
import shutil
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from dlq.dlq_manager import DLQManager, DLQMessage


class TestDLQMessage(unittest.TestCase):
    """Tests for DLQMessage dataclass"""
    
    def test_create_message(self):
        """Test creating a DLQ message"""
        msg = DLQMessage(
            id="msg_001",
            channel="test_channel",
            payload=b"test payload",
            error_message="Test error",
            error_type="ValueError",
            original_timestamp=1000.0,
            failure_timestamp=2000.0,
            retry_count=0,
            max_retries=3,
            subscriber_id="sub_001",
        )
        
        self.assertEqual(msg.id, "msg_001")
        self.assertEqual(msg.channel, "test_channel")
        self.assertEqual(msg.retry_count, 0)
        self.assertEqual(msg.max_retries, 3)
    
    def test_is_retryable(self):
        """Test retryability check"""
        msg = DLQMessage(
            id="msg_001",
            channel="test",
            payload=b"test",
            error_message="error",
            error_type="Error",
            original_timestamp=1000.0,
            failure_timestamp=2000.0,
            retry_count=2,
            max_retries=3,
            subscriber_id="sub_001",
        )
        
        # Should be retryable
        self.assertTrue(msg.is_retryable())
        
        # After max retries
        msg.retry_count = 3
        self.assertFalse(msg.is_retryable())
    
    def test_should_discard(self):
        """Test age-based discard check"""
        current_time = time.time()
        
        # Recent message
        msg = DLQMessage(
            id="msg_001",
            channel="test",
            payload=b"test",
            error_message="error",
            error_type="Error",
            original_timestamp=current_time,
            failure_timestamp=current_time,
            retry_count=0,
            max_retries=3,
            subscriber_id="sub_001",
        )
        
        # Should not be discarded (< 7 days old)
        self.assertFalse(msg.should_discard(7))
        
        # Old message (8 days ago)
        msg.failure_timestamp = current_time - (8 * 86400)
        self.assertTrue(msg.should_discard(7))
    
    def test_to_dict_and_from_dict(self):
        """Test serialization/deserialization"""
        original = DLQMessage(
            id="msg_001",
            channel="test_channel",
            payload=b"test payload",
            error_message="Test error",
            error_type="ValueError",
            original_timestamp=1000.0,
            failure_timestamp=2000.0,
            retry_count=1,
            max_retries=3,
            subscriber_id="sub_001",
        )
        
        # Convert to dict and back
        data = original.to_dict()
        restored = DLQMessage.from_dict(data)
        
        # Compare all fields
        self.assertEqual(restored.id, original.id)
        self.assertEqual(restored.channel, original.channel)
        self.assertEqual(restored.payload, original.payload)
        self.assertEqual(restored.error_message, original.error_message)
        self.assertEqual(restored.retry_count, original.retry_count)


class TestDLQManager(unittest.IsolatedAsyncioTestCase):
    """Tests for DLQManager"""
    
    async def asyncSetUp(self):
        """Set up test fixtures"""
        # Create temporary directory for DLQ storage
        self.temp_dir = tempfile.mkdtemp()
        
        self.dlq_manager = DLQManager(
            storage_path=self.temp_dir,
            max_retries=3,
            retention_days=7,
            enable_auto_retry=False,  # Disable for testing
        )
        
        await self.dlq_manager.start()
    
    async def asyncTearDown(self):
        """Clean up after tests"""
        await self.dlq_manager.stop()
        
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
    
    async def test_initialization(self):
        """Test DLQ manager initialization"""
        self.assertEqual(self.dlq_manager.max_retries, 3)
        self.assertEqual(self.dlq_manager.retention_days, 7)
        self.assertTrue(Path(self.temp_dir).exists())
    
    async def test_add_failed_message(self):
        """Test adding a failed message"""
        await self.dlq_manager.add_failed_message(
            message_id="msg_001",
            channel="test_channel",
            payload=b"test payload",
            error=ValueError("Test error"),
            subscriber_id="sub_001",
        )
        
        # Verify message was added
        msg = self.dlq_manager.get_message("msg_001")
        self.assertIsNotNone(msg)
        self.assertEqual(msg.channel, "test_channel")
        self.assertEqual(msg.error_type, "ValueError")
        
        # Verify statistics
        stats = self.dlq_manager.get_stats()
        self.assertEqual(stats['total_failures'], 1)
        self.assertEqual(stats['total_messages'], 1)
    
    async def test_retry_message_success(self):
        """Test successful message retry"""
        # Add failed message
        await self.dlq_manager.add_failed_message(
            message_id="msg_001",
            channel="test_channel",
            payload=b"test payload",
            error=ValueError("Test error"),
            subscriber_id="sub_001",
        )
        
        # Create successful retry callback
        async def successful_retry(channel, payload):
            pass  # Success
        
        # Retry the message
        result = await self.dlq_manager.retry_message("msg_001", successful_retry)
        
        self.assertTrue(result)
        
        # Message should be removed from DLQ
        msg = self.dlq_manager.get_message("msg_001")
        self.assertIsNone(msg)
        
        # Statistics should reflect success
        stats = self.dlq_manager.get_stats()
        self.assertEqual(stats['total_successes'], 1)
    
    async def test_retry_message_failure(self):
        """Test failed message retry"""
        # Add failed message
        await self.dlq_manager.add_failed_message(
            message_id="msg_001",
            channel="test_channel",
            payload=b"test payload",
            error=ValueError("Test error"),
            subscriber_id="sub_001",
        )
        
        # Create failing retry callback
        async def failing_retry(channel, payload):
            raise ValueError("Still failing")
        
        # Retry the message
        result = await self.dlq_manager.retry_message("msg_001", failing_retry)
        
        self.assertFalse(result)
        
        # Message should still be in DLQ with incremented retry count
        msg = self.dlq_manager.get_message("msg_001")
        self.assertIsNotNone(msg)
        self.assertEqual(msg.retry_count, 1)
        
        # Statistics should reflect retry
        stats = self.dlq_manager.get_stats()
        self.assertEqual(stats['total_retries'], 1)
    
    async def test_retry_message_max_retries(self):
        """Test message that exceeds max retries"""
        # Add failed message
        await self.dlq_manager.add_failed_message(
            message_id="msg_001",
            channel="test_channel",
            payload=b"test payload",
            error=ValueError("Test error"),
            subscriber_id="sub_001",
        )
        
        # Set retry count to max
        msg = self.dlq_manager.get_message("msg_001")
        msg.retry_count = 3  # At max retries
        
        # Create failing retry callback
        async def failing_retry(channel, payload):
            raise ValueError("Still failing")
        
        # Attempt retry
        result = await self.dlq_manager.retry_message("msg_001", failing_retry)
        
        self.assertFalse(result)
        
        # Message should not be retryable anymore
        msg = self.dlq_manager.get_message("msg_001")
        self.assertFalse(msg.is_retryable())
    
    async def test_get_messages_by_channel(self):
        """Test filtering messages by channel"""
        # Add messages to different channels
        await self.dlq_manager.add_failed_message(
            message_id="msg_001",
            channel="channel_a",
            payload=b"test",
            error=ValueError("Error"),
            subscriber_id="sub_001",
        )
        
        await self.dlq_manager.add_failed_message(
            message_id="msg_002",
            channel="channel_b",
            payload=b"test",
            error=ValueError("Error"),
            subscriber_id="sub_001",
        )
        
        await self.dlq_manager.add_failed_message(
            message_id="msg_003",
            channel="channel_a",
            payload=b"test",
            error=ValueError("Error"),
            subscriber_id="sub_001",
        )
        
        # Get messages for channel_a
        messages_a = self.dlq_manager.get_messages_by_channel("channel_a")
        self.assertEqual(len(messages_a), 2)
        
        # Get messages for channel_b
        messages_b = self.dlq_manager.get_messages_by_channel("channel_b")
        self.assertEqual(len(messages_b), 1)
    
    async def test_get_retryable_messages(self):
        """Test filtering retryable messages"""
        # Add retryable message
        await self.dlq_manager.add_failed_message(
            message_id="msg_001",
            channel="test",
            payload=b"test",
            error=ValueError("Error"),
            subscriber_id="sub_001",
        )
        
        # Add non-retryable message
        await self.dlq_manager.add_failed_message(
            message_id="msg_002",
            channel="test",
            payload=b"test",
            error=ValueError("Error"),
            subscriber_id="sub_001",
        )
        
        # Set msg_002 to max retries
        msg = self.dlq_manager.get_message("msg_002")
        msg.retry_count = 3
        
        # Get retryable messages
        retryable = self.dlq_manager.get_retryable_messages()
        self.assertEqual(len(retryable), 1)
        self.assertEqual(retryable[0].id, "msg_001")
    
    async def test_persistence(self):
        """Test message persistence to disk"""
        # Add a message
        await self.dlq_manager.add_failed_message(
            message_id="msg_persist",
            channel="test_channel",
            payload=b"persist test",
            error=ValueError("Test error"),
            subscriber_id="sub_001",
        )
        
        # Stop manager (saves messages)
        await self.dlq_manager.stop()
        
        # Create new manager with same storage
        new_manager = DLQManager(storage_path=self.temp_dir)
        await new_manager.start()
        
        # Verify message was loaded
        msg = new_manager.get_message("msg_persist")
        self.assertIsNotNone(msg)
        self.assertEqual(msg.channel, "test_channel")
        self.assertEqual(msg.payload, b"persist test")
        
        await new_manager.stop()
    
    async def test_get_stats(self):
        """Test statistics tracking"""
        # Add multiple messages
        await self.dlq_manager.add_failed_message(
            message_id="msg_001",
            channel="channel_a",
            payload=b"test",
            error=ValueError("Error"),
            subscriber_id="sub_001",
        )
        
        await self.dlq_manager.add_failed_message(
            message_id="msg_002",
            channel="channel_a",
            payload=b"test",
            error=ValueError("Error"),
            subscriber_id="sub_002",
        )
        
        await self.dlq_manager.add_failed_message(
            message_id="msg_003",
            channel="channel_b",
            payload=b"test",
            error=ValueError("Error"),
            subscriber_id="sub_001",
        )
        
        stats = self.dlq_manager.get_stats()
        
        self.assertEqual(stats['total_messages'], 3)
        self.assertEqual(stats['total_failures'], 3)
        self.assertEqual(stats['failures_by_channel']['channel_a'], 2)
        self.assertEqual(stats['failures_by_channel']['channel_b'], 1)
        self.assertEqual(stats['failures_by_subscriber']['sub_001'], 2)
        self.assertEqual(stats['failures_by_subscriber']['sub_002'], 1)


if __name__ == '__main__':
    unittest.main()
