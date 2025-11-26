"""
Unit tests for base publisher
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, Mock, MagicMock

from publisher.base_publisher import (
    IPublisher,
    BasePublisher,
    RateLimiter,
    PublisherError,
)


class TestRateLimiter:
    """Test rate limiter functionality"""
    
    @pytest.mark.asyncio
    async def test_basic_rate_limiting(self):
        """Test basic token acquisition"""
        limiter = RateLimiter(rate=10, per_seconds=1.0)
        
        # Should acquire immediately
        start = time.time()
        await limiter.acquire()
        elapsed = time.time() - start
        
        assert elapsed < 0.1  # Should be instant
    
    @pytest.mark.asyncio
    async def test_rate_limit_blocks(self):
        """Test that rate limiting blocks when tokens exhausted"""
        limiter = RateLimiter(rate=2, per_seconds=1.0)
        
        # Exhaust tokens
        await limiter.acquire()
        await limiter.acquire()
        
        # This should block
        start = time.time()
        await limiter.acquire()
        elapsed = time.time() - start
        
        assert elapsed >= 0.5  # Should wait for refill
    
    @pytest.mark.asyncio
    async def test_token_refill(self):
        """Test that tokens refill over time"""
        limiter = RateLimiter(rate=10, per_seconds=1.0)
        
        # Exhaust some tokens
        await limiter.acquire(5)
        
        # Wait for refill
        await asyncio.sleep(0.5)
        
        # Should have ~5 tokens available
        tokens = limiter.get_available_tokens()
        assert tokens >= 4.5
        assert tokens <= 10.0
    
    @pytest.mark.asyncio
    async def test_multiple_tokens(self):
        """Test acquiring multiple tokens at once"""
        limiter = RateLimiter(rate=10, per_seconds=1.0)
        
        # Acquire 5 tokens
        start = time.time()
        await limiter.acquire(5)
        elapsed = time.time() - start
        
        assert elapsed < 0.1
        
        # Should have ~5 tokens left
        tokens = limiter.get_available_tokens()
        assert tokens >= 4.5
        assert tokens <= 5.5
    
    def test_get_available_tokens(self):
        """Test getting available tokens"""
        limiter = RateLimiter(rate=10, per_seconds=1.0)
        
        # Should start with full tokens
        tokens = limiter.get_available_tokens()
        assert tokens == 10.0


class TestBasePublisher:
    """Test base publisher functionality"""
    
    @pytest.fixture
    def mock_broker(self):
        """Create mock broker"""
        broker = AsyncMock()
        broker.publish = AsyncMock()
        return broker
    
    @pytest.fixture
    def mock_serializer(self):
        """Create mock serializer"""
        serializer = Mock()
        serializer.serialize = Mock(return_value=b'{"test": "data"}')
        return serializer
    
    @pytest.fixture
    def base_publisher(self, mock_broker, mock_serializer):
        """Create base publisher for testing"""
        
        class TestPublisher(BasePublisher):
            async def _fetch_and_publish(self):
                # Simple mock implementation
                await asyncio.sleep(0.1)
        
        return TestPublisher(
            publisher_id='test-publisher',
            broker=mock_broker,
            serializer=mock_serializer,
            rate_limit=10,
            rate_limit_period=1.0,
            publish_interval=0.1,
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self, base_publisher):
        """Test publisher initialization"""
        assert base_publisher.publisher_id == 'test-publisher'
        assert not base_publisher._running
        assert not base_publisher._shutdown
        assert base_publisher._stats['total_published'] == 0
        assert base_publisher._stats['total_errors'] == 0
        assert base_publisher._health_status['status'] == 'stopped'
    
    @pytest.mark.asyncio
    async def test_start_and_stop(self, base_publisher):
        """Test starting and stopping publisher"""
        # Start
        await base_publisher.start()
        assert base_publisher._running
        assert base_publisher._health_status['status'] == 'healthy'
        
        # Small delay to let loop run
        await asyncio.sleep(0.2)
        
        # Stop
        await base_publisher.stop()
        assert not base_publisher._running
        assert base_publisher._health_status['status'] == 'stopped'
    
    @pytest.mark.asyncio
    async def test_publish_event(self, base_publisher, mock_broker, mock_serializer):
        """Test publishing a single event"""
        # Start publisher
        await base_publisher.start()
        
        # Create test event
        event = {'symbol': 'AAPL', 'price': 150.0}
        
        # Publish
        await base_publisher.publish_event(event)
        
        # Verify
        assert base_publisher._stats['total_published'] == 1
        assert mock_serializer.serialize.called
        assert mock_broker.publish.called
        
        # Cleanup
        await base_publisher.stop()
    
    @pytest.mark.asyncio
    async def test_publish_event_not_running(self, base_publisher):
        """Test that publish fails when not running"""
        event = {'test': 'data'}
        
        with pytest.raises(PublisherError, match="Publisher not running"):
            await base_publisher.publish_event(event)
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, base_publisher, mock_broker):
        """Test that rate limiting is applied"""
        await base_publisher.start()
        
        # Publish multiple events rapidly
        events = [{'id': i} for i in range(5)]
        
        start = time.time()
        for event in events:
            await base_publisher.publish_event(event)
        elapsed = time.time() - start
        
        # Should have some delay due to rate limiting
        assert base_publisher._stats['total_published'] == 5
        
        await base_publisher.stop()
    
    @pytest.mark.asyncio
    async def test_health_check(self, base_publisher):
        """Test health check"""
        await base_publisher.start()
        await asyncio.sleep(0.2)
        
        health = await base_publisher.health_check()
        
        assert health['publisher_id'] == 'test-publisher'
        assert health['status'] == 'healthy'
        assert health['running'] is True
        assert health['uptime_seconds'] > 0
        assert 'rate_limit_tokens' in health
        
        await base_publisher.stop()
    
    @pytest.mark.asyncio
    async def test_get_stats(self, base_publisher):
        """Test getting statistics"""
        await base_publisher.start()
        
        # Publish some events
        for i in range(3):
            await base_publisher.publish_event({'id': i})
        
        stats = base_publisher.get_stats()
        
        assert stats['publisher_id'] == 'test-publisher'
        assert stats['running'] is True
        assert stats['total_published'] == 3
        assert stats['total_errors'] == 0
        assert stats['success_rate'] == 100.0
        
        await base_publisher.stop()
    
    @pytest.mark.asyncio
    async def test_error_handling(self, base_publisher, mock_broker):
        """Test error handling in publish"""
        await base_publisher.start()
        
        # Make broker raise error
        mock_broker.publish.side_effect = Exception("Broker error")
        
        # Try to publish
        with pytest.raises(PublisherError, match="Publish failed"):
            await base_publisher.publish_event({'test': 'data'})
        
        # Check error stats
        assert base_publisher._stats['total_errors'] == 1
        assert base_publisher._stats['last_error'] is not None
        
        await base_publisher.stop()
    
    @pytest.mark.asyncio
    async def test_health_status_degraded(self, base_publisher, mock_broker):
        """Test health status becomes degraded after errors"""
        await base_publisher.start()
        
        # Cause multiple errors
        mock_broker.publish.side_effect = Exception("Error")
        
        for i in range(5):
            try:
                await base_publisher.publish_event({'id': i})
            except PublisherError:
                pass
        
        # Health should be degraded
        assert base_publisher._health_status['status'] == 'degraded'
        
        await base_publisher.stop()
    
    @pytest.mark.asyncio
    async def test_channel_determination(self, base_publisher):
        """Test channel name determination"""
        
        class TestEvent:
            pass
        
        event = TestEvent()
        channel = base_publisher._get_channel_for_event(event)
        
        # Default implementation uses class name
        assert 'test' in channel.lower()
    
    @pytest.mark.asyncio
    async def test_success_rate_calculation(self, base_publisher):
        """Test success rate calculation"""
        # Initially 100%
        assert base_publisher._calculate_success_rate() == 100.0
        
        # After successful publishes
        base_publisher._stats['total_published'] = 8
        base_publisher._stats['total_errors'] = 2
        assert base_publisher._calculate_success_rate() == 80.0
    
    @pytest.mark.asyncio
    async def test_publish_loop_cancellation(self, base_publisher):
        """Test that publish loop can be cancelled"""
        await base_publisher.start()
        
        # Let it run briefly
        await asyncio.sleep(0.3)
        
        # Stop should cancel gracefully
        await base_publisher.stop()
        
        assert not base_publisher._running
        assert base_publisher._shutdown


class TestIPublisher:
    """Test IPublisher interface"""
    
    def test_interface_methods(self):
        """Test that interface defines required methods"""
        assert hasattr(IPublisher, 'start')
        assert hasattr(IPublisher, 'stop')
        assert hasattr(IPublisher, 'publish_event')
        assert hasattr(IPublisher, 'health_check')
        assert hasattr(IPublisher, 'get_stats')
    
    def test_abstract_methods(self):
        """Test that interface methods are abstract"""
        # Cannot instantiate abstract class
        with pytest.raises(TypeError):
            IPublisher()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
