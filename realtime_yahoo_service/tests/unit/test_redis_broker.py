"""
Unit Tests for Redis Event Broker
==================================

Tests for Redis broker with mocked Redis client.
"""

import sys
import os
import unittest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from redis_broker.base_broker import (
    IEventBroker,
    BrokerError,
    PublishError,
    SubscriptionError,
    ConnectionError,
)
from redis_broker.redis_event_broker import RedisEventBroker
from serialization.json_serializer import JSONSerializer


class TestRedisEventBroker(unittest.IsolatedAsyncioTestCase):
    """Tests for RedisEventBroker"""
    
    async def asyncSetUp(self):
        """Set up test fixtures"""
        self.redis_url = "redis://localhost:6379/0"
        self.serializer = JSONSerializer()
    
    @patch('redis_broker.redis_event_broker.redis')
    async def test_initialization(self, mock_redis):
        """Test broker initialization"""
        broker = RedisEventBroker(
            redis_url=self.redis_url,
            serializer=self.serializer,
            max_connections=50,
        )
        
        self.assertEqual(broker.redis_url, self.redis_url)
        self.assertEqual(broker.max_connections, 50)
        self.assertFalse(broker.is_connected())
    
    @patch('redis_broker.redis_event_broker.ConnectionPool')
    @patch('redis_broker.redis_event_broker.redis')
    async def test_connect(self, mock_redis_module, mock_pool_class):
        """Test connecting to Redis"""
        # Mock Redis components
        mock_pool = AsyncMock()
        mock_client = AsyncMock()
        mock_pubsub = AsyncMock()
        
        mock_pool_class.from_url.return_value = mock_pool
        mock_redis_module.Redis.return_value = mock_client
        mock_client.pubsub.return_value = mock_pubsub
        mock_client.ping = AsyncMock()
        
        broker = RedisEventBroker(
            redis_url=self.redis_url,
            serializer=self.serializer,
        )
        
        await broker.connect()
        
        # Verify connection established
        self.assertTrue(broker.is_connected())
        mock_client.ping.assert_called_once()
    
    @patch('redis_broker.redis_event_broker.redis')
    async def test_disconnect(self, mock_redis):
        """Test disconnecting from Redis"""
        # Mock Redis components
        mock_pool = AsyncMock()
        mock_client = AsyncMock()
        mock_pubsub = AsyncMock()
        
        mock_redis.ConnectionPool.from_url.return_value = mock_pool
        mock_redis.Redis.return_value = mock_client
        mock_client.pubsub.return_value = mock_pubsub
        mock_client.ping = AsyncMock()
        
        broker = RedisEventBroker(
            redis_url=self.redis_url,
            serializer=self.serializer,
        )
        
        await broker.connect()
        await broker.disconnect()
        
        # Verify cleanup
        mock_pubsub.unsubscribe.assert_called_once()
        mock_pubsub.close.assert_called_once()
        mock_client.close.assert_called_once()
    
    @patch('redis_broker.redis_event_broker.redis')
    async def test_publish(self, mock_redis):
        """Test publishing a message"""
        # Mock Redis components
        mock_pool = AsyncMock()
        mock_client = AsyncMock()
        mock_pubsub = AsyncMock()
        
        mock_redis.ConnectionPool.from_url.return_value = mock_pool
        mock_redis.Redis.return_value = mock_client
        mock_client.pubsub.return_value = mock_pubsub
        mock_client.ping = AsyncMock()
        mock_client.publish = AsyncMock()
        
        broker = RedisEventBroker(
            redis_url=self.redis_url,
            serializer=self.serializer,
        )
        
        await broker.connect()
        
        # Publish message
        channel = "test_channel"
        message = b"test message"
        await broker.publish(channel, message)
        
        # Verify publish called
        mock_client.publish.assert_called_once_with(channel, message)
        
        await broker.disconnect()
    
    @patch('redis_broker.redis_event_broker.redis')
    async def test_publish_not_connected(self, mock_redis):
        """Test publishing when not connected raises error"""
        broker = RedisEventBroker(
            redis_url=self.redis_url,
            serializer=self.serializer,
        )
        
        with self.assertRaises(PublishError):
            await broker.publish("test_channel", b"test")
    
    @patch('redis_broker.redis_event_broker.redis')
    async def test_subscribe(self, mock_redis):
        """Test subscribing to a channel"""
        # Mock Redis components
        mock_pool = AsyncMock()
        mock_client = AsyncMock()
        mock_pubsub = AsyncMock()
        
        mock_redis.ConnectionPool.from_url.return_value = mock_pool
        mock_redis.Redis.return_value = mock_client
        mock_client.pubsub.return_value = mock_pubsub
        mock_client.ping = AsyncMock()
        mock_pubsub.subscribe = AsyncMock()
        
        broker = RedisEventBroker(
            redis_url=self.redis_url,
            serializer=self.serializer,
        )
        
        await broker.connect()
        
        # Subscribe to channel
        channel = "test_channel"
        callback = Mock()
        await broker.subscribe(channel, callback)
        
        # Verify subscription
        self.assertIn(channel, broker._subscriptions)
        mock_pubsub.subscribe.assert_called_once_with(channel)
        
        await broker.disconnect()
    
    @patch('redis_broker.redis_event_broker.redis')
    async def test_unsubscribe(self, mock_redis):
        """Test unsubscribing from a channel"""
        # Mock Redis components
        mock_pool = AsyncMock()
        mock_client = AsyncMock()
        mock_pubsub = AsyncMock()
        
        mock_redis.ConnectionPool.from_url.return_value = mock_pool
        mock_redis.Redis.return_value = mock_client
        mock_client.pubsub.return_value = mock_pubsub
        mock_client.ping = AsyncMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        
        broker = RedisEventBroker(
            redis_url=self.redis_url,
            serializer=self.serializer,
        )
        
        await broker.connect()
        
        # Subscribe then unsubscribe
        channel = "test_channel"
        callback = Mock()
        await broker.subscribe(channel, callback)
        await broker.unsubscribe(channel)
        
        # Verify unsubscription
        self.assertNotIn(channel, broker._subscriptions)
        mock_pubsub.unsubscribe.assert_called_once_with(channel)
        
        await broker.disconnect()
    
    @patch('redis_broker.redis_event_broker.redis')
    async def test_health_check_healthy(self, mock_redis):
        """Test health check when connected"""
        # Mock Redis components
        mock_pool = AsyncMock()
        mock_client = AsyncMock()
        mock_pubsub = AsyncMock()
        
        mock_redis.ConnectionPool.from_url.return_value = mock_pool
        mock_redis.Redis.return_value = mock_client
        mock_client.pubsub.return_value = mock_pubsub
        mock_client.ping = AsyncMock()
        
        broker = RedisEventBroker(
            redis_url=self.redis_url,
            serializer=self.serializer,
        )
        
        await broker.connect()
        
        # Perform health check
        health = await broker.health_check()
        
        self.assertTrue(health['healthy'])
        self.assertTrue(health['connected'])
        self.assertIsNotNone(health['latency_ms'])
        self.assertIsNone(health['error'])
        
        await broker.disconnect()
    
    @patch('redis_broker.redis_event_broker.redis')
    async def test_health_check_not_connected(self, mock_redis):
        """Test health check when not connected"""
        broker = RedisEventBroker(
            redis_url=self.redis_url,
            serializer=self.serializer,
        )
        
        health = await broker.health_check()
        
        self.assertFalse(health['healthy'])
        self.assertFalse(health['connected'])
        self.assertIsNone(health['latency_ms'])
        self.assertIsNotNone(health['error'])
    
    @patch('redis_broker.redis_event_broker.redis')
    async def test_get_stats(self, mock_redis):
        """Test getting broker statistics"""
        # Mock Redis components
        mock_pool = AsyncMock()
        mock_client = AsyncMock()
        mock_pubsub = AsyncMock()
        
        mock_redis.ConnectionPool.from_url.return_value = mock_pool
        mock_redis.Redis.return_value = mock_client
        mock_client.pubsub.return_value = mock_pubsub
        mock_client.ping = AsyncMock()
        mock_pubsub.subscribe = AsyncMock()
        
        broker = RedisEventBroker(
            redis_url=self.redis_url,
            serializer=self.serializer,
        )
        
        await broker.connect()
        
        # Add subscription
        await broker.subscribe("test_channel", Mock())
        
        # Get stats
        stats = broker.get_stats()
        
        self.assertTrue(stats['connected'])
        self.assertEqual(stats['active_subscriptions'], 1)
        self.assertIn('test_channel', stats['channels'])
        self.assertEqual(stats['serializer'], 'json')
        
        await broker.disconnect()


class TestBaseBrokerInterface(unittest.TestCase):
    """Tests for IEventBroker interface"""
    
    def test_interface_methods(self):
        """Test that IEventBroker has required methods"""
        required_methods = [
            'connect',
            'disconnect',
            'publish',
            'subscribe',
            'unsubscribe',
            'is_connected',
            'health_check',
        ]
        
        for method in required_methods:
            self.assertTrue(hasattr(IEventBroker, method))
    
    def test_broker_exceptions(self):
        """Test broker exception hierarchy"""
        # Test exception hierarchy
        self.assertTrue(issubclass(PublishError, BrokerError))
        self.assertTrue(issubclass(SubscriptionError, BrokerError))
        self.assertTrue(issubclass(ConnectionError, BrokerError))
        
        # Test exception creation
        error = PublishError("test error")
        self.assertIsInstance(error, BrokerError)
        self.assertEqual(str(error), "test error")


if __name__ == '__main__':
    unittest.main()
