"""
Unit Tests for In-Memory Event Broker
======================================

Tests for in-memory broker (no Redis required).
"""

import sys
import os
import unittest
import asyncio
from unittest.mock import Mock, AsyncMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from redis_broker.inmemory_broker import InMemoryBroker, create_inmemory_broker
from serialization.json_serializer import JSONSerializer


class TestInMemoryBroker(unittest.IsolatedAsyncioTestCase):
    """Tests for InMemoryBroker"""
    
    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.serializer = JSONSerializer()
        self.broker = InMemoryBroker(
            serializer=self.serializer,
            max_message_history=100,
            enable_history=True,
        )
    
    async def asyncTearDown(self):
        """Clean up after tests"""
        if self.broker.is_connected():
            await self.broker.disconnect()
    
    async def test_initialization(self):
        """Test broker initialization"""
        self.assertEqual(self.broker.max_message_history, 100)
        self.assertTrue(self.broker.enable_history)
        self.assertFalse(self.broker.is_connected())
    
    async def test_connect(self):
        """Test connecting"""
        await self.broker.connect()
        self.assertTrue(self.broker.is_connected())
    
    async def test_disconnect(self):
        """Test disconnecting"""
        await self.broker.connect()
        await self.broker.disconnect()
        self.assertFalse(self.broker.is_connected())
    
    async def test_publish_and_subscribe(self):
        """Test basic publish/subscribe"""
        await self.broker.connect()
        
        # Track received messages
        received_messages = []
        
        def callback(channel: str, message: bytes):
            received_messages.append((channel, message))
        
        # Subscribe to channel
        channel = "test_channel"
        await self.broker.subscribe(channel, callback)
        
        # Publish message
        test_message = b"Hello, World!"
        await self.broker.publish(channel, test_message)
        
        # Verify message received
        self.assertEqual(len(received_messages), 1)
        self.assertEqual(received_messages[0], (channel, test_message))
    
    async def test_multiple_subscribers(self):
        """Test multiple subscribers on same channel"""
        await self.broker.connect()
        
        # Track received messages for each subscriber
        received_1 = []
        received_2 = []
        
        def callback_1(channel: str, message: bytes):
            received_1.append(message)
        
        def callback_2(channel: str, message: bytes):
            received_2.append(message)
        
        # Subscribe both callbacks
        channel = "test_channel"
        await self.broker.subscribe(channel, callback_1)
        await self.broker.subscribe(channel, callback_2)
        
        # Publish message
        test_message = b"Test message"
        await self.broker.publish(channel, test_message)
        
        # Both should receive the message
        self.assertEqual(len(received_1), 1)
        self.assertEqual(len(received_2), 1)
        self.assertEqual(received_1[0], test_message)
        self.assertEqual(received_2[0], test_message)
    
    async def test_multiple_channels(self):
        """Test publishing to multiple channels"""
        await self.broker.connect()
        
        received_a = []
        received_b = []
        
        def callback_a(channel: str, message: bytes):
            received_a.append(message)
        
        def callback_b(channel: str, message: bytes):
            received_b.append(message)
        
        # Subscribe to different channels
        await self.broker.subscribe("channel_a", callback_a)
        await self.broker.subscribe("channel_b", callback_b)
        
        # Publish to each channel
        await self.broker.publish("channel_a", b"Message A")
        await self.broker.publish("channel_b", b"Message B")
        
        # Each should receive only their message
        self.assertEqual(len(received_a), 1)
        self.assertEqual(len(received_b), 1)
        self.assertEqual(received_a[0], b"Message A")
        self.assertEqual(received_b[0], b"Message B")
    
    async def test_unsubscribe_channel(self):
        """Test unsubscribing from a channel"""
        await self.broker.connect()
        
        received = []
        
        def callback(channel: str, message: bytes):
            received.append(message)
        
        # Subscribe and publish
        channel = "test_channel"
        await self.broker.subscribe(channel, callback)
        await self.broker.publish(channel, b"Message 1")
        
        # Unsubscribe and publish again
        await self.broker.unsubscribe(channel)
        await self.broker.publish(channel, b"Message 2")
        
        # Should only receive first message
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0], b"Message 1")
    
    async def test_unsubscribe_specific_callback(self):
        """Test unsubscribing a specific callback"""
        await self.broker.connect()
        
        received_1 = []
        received_2 = []
        
        def callback_1(channel: str, message: bytes):
            received_1.append(message)
        
        def callback_2(channel: str, message: bytes):
            received_2.append(message)
        
        # Subscribe both
        channel = "test_channel"
        await self.broker.subscribe(channel, callback_1)
        await self.broker.subscribe(channel, callback_2)
        
        # Publish message
        await self.broker.publish(channel, b"Message 1")
        
        # Unsubscribe callback_1
        await self.broker.unsubscribe_callback(channel, callback_1)
        
        # Publish again
        await self.broker.publish(channel, b"Message 2")
        
        # callback_1 should receive 1 message, callback_2 should receive 2
        self.assertEqual(len(received_1), 1)
        self.assertEqual(len(received_2), 2)
    
    async def test_async_callback(self):
        """Test async callback support"""
        await self.broker.connect()
        
        received = []
        
        async def async_callback(channel: str, message: bytes):
            await asyncio.sleep(0.01)  # Simulate async work
            received.append(message)
        
        # Subscribe with async callback
        channel = "test_channel"
        await self.broker.subscribe(channel, async_callback)
        
        # Publish message
        await self.broker.publish(channel, b"Async message")
        
        # Verify message received
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0], b"Async message")
    
    async def test_message_history(self):
        """Test message history tracking"""
        await self.broker.connect()
        
        channel = "test_channel"
        
        # Publish multiple messages
        for i in range(5):
            await self.broker.publish(channel, f"Message {i}".encode())
        
        # Get history
        history = self.broker.get_message_history(channel)
        
        self.assertEqual(len(history), 5)
        # Each entry is (timestamp, message)
        for i, (timestamp, message) in enumerate(history):
            self.assertEqual(message, f"Message {i}".encode())
            self.assertIsInstance(timestamp, float)
    
    async def test_message_history_limit(self):
        """Test message history limit"""
        # Create broker with small history limit
        broker = InMemoryBroker(
            serializer=self.serializer,
            max_message_history=3,
            enable_history=True,
        )
        await broker.connect()
        
        channel = "test_channel"
        
        # Publish more messages than limit
        for i in range(5):
            await broker.publish(channel, f"Message {i}".encode())
        
        # Should only keep last 3
        history = broker.get_message_history(channel)
        self.assertEqual(len(history), 3)
        
        # Should be messages 2, 3, 4
        self.assertEqual(history[0][1], b"Message 2")
        self.assertEqual(history[1][1], b"Message 3")
        self.assertEqual(history[2][1], b"Message 4")
        
        await broker.disconnect()
    
    async def test_clear_history(self):
        """Test clearing message history"""
        await self.broker.connect()
        
        channel = "test_channel"
        
        # Publish messages
        for i in range(3):
            await self.broker.publish(channel, f"Message {i}".encode())
        
        # Clear history
        self.broker.clear_history(channel)
        
        # History should be empty
        history = self.broker.get_message_history(channel)
        self.assertEqual(len(history), 0)
    
    async def test_health_check(self):
        """Test health check"""
        await self.broker.connect()
        
        health = await self.broker.health_check()
        
        self.assertTrue(health['healthy'])
        self.assertTrue(health['connected'])
        self.assertEqual(health['latency_ms'], 0.0)  # No network latency
        self.assertIsNone(health['error'])
    
    async def test_health_check_not_connected(self):
        """Test health check when not connected"""
        health = await self.broker.health_check()
        
        self.assertFalse(health['healthy'])
        self.assertFalse(health['connected'])
        self.assertIsNotNone(health['error'])
    
    async def test_get_stats(self):
        """Test getting broker statistics"""
        await self.broker.connect()
        
        # Subscribe and publish
        await self.broker.subscribe("channel1", Mock())
        await self.broker.subscribe("channel2", Mock())
        await self.broker.publish("channel1", b"Message 1")
        await self.broker.publish("channel1", b"Message 2")
        await self.broker.publish("channel2", b"Message 3")
        
        stats = self.broker.get_stats()
        
        self.assertTrue(stats['connected'])
        self.assertEqual(stats['type'], 'in-memory')
        self.assertEqual(stats['total_published'], 3)
        self.assertEqual(stats['total_delivered'], 3)
        self.assertEqual(stats['active_channels'], 2)
        self.assertIn('channel1', stats['channels'])
        self.assertIn('channel2', stats['channels'])
        self.assertEqual(stats['messages_by_channel']['channel1'], 2)
        self.assertEqual(stats['messages_by_channel']['channel2'], 1)
        self.assertEqual(stats['serializer'], 'json')
    
    async def test_get_subscribers(self):
        """Test getting subscriber count"""
        await self.broker.connect()
        
        channel = "test_channel"
        
        # Initially no subscribers
        self.assertEqual(self.broker.get_subscribers(channel), 0)
        
        # Add subscribers
        await self.broker.subscribe(channel, Mock())
        self.assertEqual(self.broker.get_subscribers(channel), 1)
        
        await self.broker.subscribe(channel, Mock())
        self.assertEqual(self.broker.get_subscribers(channel), 2)
    
    async def test_publish_not_connected(self):
        """Test publishing when not connected raises error"""
        from redis_broker.base_broker import PublishError
        
        with self.assertRaises(PublishError):
            await self.broker.publish("test", b"message")
    
    async def test_subscribe_not_connected(self):
        """Test subscribing when not connected raises error"""
        from redis_broker.base_broker import SubscriptionError
        
        with self.assertRaises(SubscriptionError):
            await self.broker.subscribe("test", Mock())
    
    async def test_callback_exception_handling(self):
        """Test that callback exceptions don't break the broker"""
        await self.broker.connect()
        
        received_by_good = []
        
        def bad_callback(channel: str, message: bytes):
            raise ValueError("Callback error")
        
        def good_callback(channel: str, message: bytes):
            received_by_good.append(message)
        
        channel = "test_channel"
        await self.broker.subscribe(channel, bad_callback)
        await self.broker.subscribe(channel, good_callback)
        
        # Publish should not crash despite bad callback
        await self.broker.publish(channel, b"Test message")
        
        # Good callback should still receive message
        self.assertEqual(len(received_by_good), 1)
    
    async def test_create_inmemory_broker_factory(self):
        """Test convenience factory function"""
        broker = create_inmemory_broker(
            serializer=self.serializer,
            max_message_history=50,
        )
        
        self.assertIsInstance(broker, InMemoryBroker)
        self.assertEqual(broker.max_message_history, 50)
        
        await broker.connect()
        await broker.disconnect()


if __name__ == '__main__':
    unittest.main()
