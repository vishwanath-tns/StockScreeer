"""
Unit tests for base subscriber
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, MagicMock, patch

from subscribers.base_subscriber import (
    ISubscriber,
    BaseSubscriber,
    SubscriberError,
)


class TestBaseSubscriber:
    """Test base subscriber functionality"""
    
    @pytest.fixture
    def mock_broker(self):
        """Create mock broker"""
        broker = AsyncMock()
        broker.subscribe = AsyncMock()
        broker.unsubscribe = AsyncMock()
        return broker
    
    @pytest.fixture
    def mock_serializer(self):
        """Create mock serializer"""
        serializer = Mock()
        serializer.deserialize = Mock(return_value={'test': 'data'})
        return serializer
    
    @pytest.fixture
    def mock_dlq(self):
        """Create mock DLQ manager"""
        dlq = AsyncMock()
        dlq.add_failed_message = AsyncMock()
        return dlq
    
    @pytest.fixture
    def base_subscriber(self, mock_broker, mock_serializer):
        """Create base subscriber for testing"""
        
        class TestSubscriber(BaseSubscriber):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.messages_received = []
            
            async def on_message(self, channel: str, data: dict) -> None:
                # Store received messages
                self.messages_received.append({'channel': channel, 'data': data})
        
        return TestSubscriber(
            subscriber_id='test-subscriber',
            broker=mock_broker,
            serializer=mock_serializer,
            channels=['test.channel'],
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self, base_subscriber):
        """Test subscriber initialization"""
        assert base_subscriber.subscriber_id == 'test-subscriber'
        assert base_subscriber.channels == ['test.channel']
        assert not base_subscriber._running
        assert not base_subscriber._shutdown
        assert base_subscriber._stats['total_received'] == 0
        assert base_subscriber._stats['total_processed'] == 0
        assert base_subscriber._health_status['status'] == 'stopped'
    
    @pytest.mark.asyncio
    async def test_start_and_stop(self, base_subscriber, mock_broker):
        """Test starting and stopping subscriber"""
        # Start
        await base_subscriber.start()
        assert base_subscriber._running
        assert base_subscriber._health_status['status'] == 'healthy'
        assert mock_broker.subscribe.called
        
        # Stop
        await base_subscriber.stop()
        assert not base_subscriber._running
        assert base_subscriber._health_status['status'] == 'stopped'
        assert mock_broker.unsubscribe.called
    
    @pytest.mark.asyncio
    async def test_message_handling(self, base_subscriber, mock_serializer):
        """Test message handling"""
        await base_subscriber.start()
        
        # Simulate message
        await base_subscriber._handle_message('test.channel', b'{"test": "data"}')
        
        # Verify
        assert base_subscriber._stats['total_received'] == 1
        assert base_subscriber._stats['total_processed'] == 1
        assert len(base_subscriber.messages_received) == 1
        assert base_subscriber.messages_received[0]['channel'] == 'test.channel'
        
        await base_subscriber.stop()
    
    @pytest.mark.asyncio
    async def test_deserialization_error(self, base_subscriber, mock_serializer, mock_dlq):
        """Test handling deserialization errors"""
        base_subscriber.dlq_manager = mock_dlq
        await base_subscriber.start()
        
        # Make deserializer raise error
        mock_serializer.deserialize.side_effect = Exception("Bad data")
        
        # Handle message
        await base_subscriber._handle_message('test.channel', b'invalid')
        
        # Verify error handling
        assert base_subscriber._stats['total_received'] == 1
        assert base_subscriber._stats['total_processed'] == 0
        assert base_subscriber._stats['total_errors'] == 1
        assert mock_dlq.add_failed_message.called
        
        await base_subscriber.stop()
    
    @pytest.mark.asyncio
    async def test_processing_error(self, base_subscriber, mock_dlq):
        """Test handling processing errors"""
        base_subscriber.dlq_manager = mock_dlq
        
        # Override on_message to raise error
        async def failing_on_message(channel, data):
            raise ValueError("Processing failed")
        
        base_subscriber.on_message = failing_on_message
        await base_subscriber.start()
        
        # Handle message
        await base_subscriber._handle_message('test.channel', b'{"test": "data"}')
        
        # Verify error handling
        assert base_subscriber._stats['total_received'] == 1
        assert base_subscriber._stats['total_processed'] == 0
        assert base_subscriber._stats['total_errors'] == 1
        assert mock_dlq.add_failed_message.called
        
        await base_subscriber.stop()
    
    @pytest.mark.asyncio
    async def test_health_check(self, base_subscriber):
        """Test health check"""
        await base_subscriber.start()
        await asyncio.sleep(0.1)
        
        health = await base_subscriber.health_check()
        
        assert health['subscriber_id'] == 'test-subscriber'
        assert health['status'] == 'healthy'
        assert health['running'] is True
        assert health['uptime_seconds'] > 0
        assert 'db_healthy' in health
        
        await base_subscriber.stop()
    
    @pytest.mark.asyncio
    async def test_get_stats(self, base_subscriber):
        """Test getting statistics"""
        await base_subscriber.start()
        
        # Process some messages
        for i in range(3):
            await base_subscriber._handle_message('test.channel', b'{"test": "data"}')
        
        stats = base_subscriber.get_stats()
        
        assert stats['subscriber_id'] == 'test-subscriber'
        assert stats['running'] is True
        assert stats['total_received'] == 3
        assert stats['total_processed'] == 3
        assert stats['total_errors'] == 0
        assert stats['success_rate'] == 100.0
        
        await base_subscriber.stop()
    
    @pytest.mark.asyncio
    async def test_success_rate_calculation(self, base_subscriber):
        """Test success rate calculation"""
        # Initially 100%
        assert base_subscriber._calculate_success_rate() == 100.0
        
        # After some processing
        base_subscriber._stats['total_received'] = 10
        base_subscriber._stats['total_processed'] = 8
        assert base_subscriber._calculate_success_rate() == 80.0
    
    @pytest.mark.asyncio
    async def test_health_status_degraded(self, base_subscriber):
        """Test health status becomes degraded after errors"""
        await base_subscriber.start()
        
        # Cause multiple errors
        for i in range(5):
            base_subscriber._record_error(f"Error {i}")
        
        # Health should be degraded
        assert base_subscriber._health_status['status'] == 'degraded'
        
        await base_subscriber.stop()
    
    @pytest.mark.asyncio
    async def test_health_status_unhealthy(self, base_subscriber):
        """Test health status becomes unhealthy after many errors"""
        await base_subscriber.start()
        
        # Cause many errors
        for i in range(15):
            base_subscriber._record_error(f"Error {i}")
        
        # Health should be unhealthy
        assert base_subscriber._health_status['status'] == 'unhealthy'
        
        await base_subscriber.stop()
    
    @pytest.mark.asyncio
    async def test_messages_per_channel_tracking(self, base_subscriber):
        """Test per-channel message tracking"""
        await base_subscriber.start()
        
        # Send messages to different channels
        await base_subscriber._handle_message('channel1', b'{"test": "data"}')
        await base_subscriber._handle_message('channel1', b'{"test": "data"}')
        await base_subscriber._handle_message('channel2', b'{"test": "data"}')
        
        # Verify tracking
        assert base_subscriber._stats['messages_per_channel']['channel1'] == 2
        assert base_subscriber._stats['messages_per_channel']['channel2'] == 1
        
        await base_subscriber.stop()
    
    @pytest.mark.asyncio
    async def test_shutdown_ignores_messages(self, base_subscriber):
        """Test that messages are ignored during shutdown"""
        await base_subscriber.start()
        
        # Trigger shutdown
        base_subscriber._shutdown = True
        
        # Try to handle message
        await base_subscriber._handle_message('test.channel', b'{"test": "data"}')
        
        # Should be ignored
        assert base_subscriber._stats['total_received'] == 0
        
        await base_subscriber.stop()
    
    @pytest.mark.asyncio
    async def test_database_session_context(self, mock_broker, mock_serializer):
        """Test database session context manager"""
        try:
            import aiosqlite
        except ImportError:
            pytest.skip("aiosqlite not installed")
        
        # Create subscriber with database URL
        subscriber = BaseSubscriber(
            subscriber_id='test-db-subscriber',
            broker=mock_broker,
            serializer=mock_serializer,
            channels=['test.channel'],
            db_url='sqlite+aiosqlite:///:memory:',
        )
        
        await subscriber.start()
        
        # Test session context
        async with subscriber.get_db_session() as session:
            assert session is not None
        
        await subscriber.stop()
    
    @pytest.mark.asyncio
    async def test_database_session_without_config(self, base_subscriber):
        """Test that database session fails without configuration"""
        await base_subscriber.start()
        
        with pytest.raises(SubscriberError, match="Database not configured"):
            async with base_subscriber.get_db_session() as session:
                pass
        
        await base_subscriber.stop()
    
    @pytest.mark.asyncio
    async def test_multiple_channel_subscription(self, mock_broker, mock_serializer):
        """Test subscribing to multiple channels"""
        subscriber = BaseSubscriber(
            subscriber_id='multi-channel-subscriber',
            broker=mock_broker,
            serializer=mock_serializer,
            channels=['channel1', 'channel2', 'channel3'],
        )
        
        # Override on_message
        subscriber.on_message = AsyncMock()
        
        await subscriber.start()
        
        # Verify subscribed to all channels
        assert mock_broker.subscribe.call_count == 3
        
        await subscriber.stop()
        
        # Verify unsubscribed from all channels
        assert mock_broker.unsubscribe.call_count == 3


class TestISubscriber:
    """Test ISubscriber interface"""
    
    def test_interface_methods(self):
        """Test that interface defines required methods"""
        assert hasattr(ISubscriber, 'start')
        assert hasattr(ISubscriber, 'stop')
        assert hasattr(ISubscriber, 'on_message')
        assert hasattr(ISubscriber, 'health_check')
        assert hasattr(ISubscriber, 'get_stats')
    
    def test_abstract_methods(self):
        """Test that interface methods are abstract"""
        # Cannot instantiate abstract class
        with pytest.raises(TypeError):
            ISubscriber()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
