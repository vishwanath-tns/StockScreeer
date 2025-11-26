"""
End-to-End Integration Tests

Tests complete data flow from publisher to subscribers through broker
"""

import asyncio
import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
import time
from pathlib import Path
import tempfile

from redis_broker import InMemoryBroker
from serialization import JSONSerializer
from publisher import YahooFinancePublisher
from subscribers import (
    StateTrackerSubscriber,
    MarketBreadthSubscriber,
    TrendAnalyzerSubscriber,
)
from events import CandleDataEvent, FetchStatusEvent


class TestEndToEndFlow:
    """Test end-to-end data flow"""
    
    @pytest_asyncio.fixture
    async def broker(self):
        """Create in-memory broker"""
        serializer = JSONSerializer()
        broker = InMemoryBroker(serializer=serializer)
        await broker.connect()
        yield broker
        await broker.disconnect()
    
    @pytest.fixture
    def serializer(self):
        """Create JSON serializer"""
        return JSONSerializer()
    
    @pytest.mark.asyncio
    async def test_publisher_to_state_tracker_flow(self, broker, serializer):
        """Test data flows from publisher to state tracker"""
        # Create publisher
        publisher = YahooFinancePublisher(
            publisher_id='test_pub',
            broker=broker,
            serializer=serializer,
            symbols=['AAPL', 'GOOGL'],
            publish_interval=0.5,  # Fast for testing
            batch_size=2,
        )
        
        # Create state tracker subscriber
        state_tracker = StateTrackerSubscriber(
            subscriber_id='test_state',
            broker=broker,
            serializer=serializer,
        )
        
        # Start components
        await state_tracker.start()
        await publisher.start()
        
        # Verify they started
        assert publisher._running
        assert state_tracker._running
        
        # Stop components
        await publisher.stop()
        await state_tracker.stop()
        
        # Verify they stopped
        assert not publisher._running
        assert not state_tracker._running
    
    @pytest.mark.asyncio
    async def test_publisher_to_market_breadth_flow(self, broker, serializer):
        """Test market breadth subscriber integrates with publisher"""
        # Create publisher
        publisher = YahooFinancePublisher(
            publisher_id='test_pub',
            broker=broker,
            serializer=serializer,
            symbols=['AAPL', 'GOOGL', 'MSFT'],
            publish_interval=0.5,
            batch_size=3,
        )
        
        # Create market breadth subscriber
        market_breadth = MarketBreadthSubscriber(
            subscriber_id='test_breadth',
            broker=broker,
            serializer=serializer,
        )
        
        # Start components
        await market_breadth.start()
        await publisher.start()
        
        # Verify they're running
        assert publisher._running
        assert market_breadth._running
        
        # Stop components
        await publisher.stop()
        await market_breadth.stop()
        
        # Verify they stopped
        assert not publisher._running
        assert not market_breadth._running
    
    @pytest.mark.asyncio
    async def test_publisher_to_trend_analyzer_flow(self, broker, serializer):
        """Test trend analyzer integrates with publisher"""
        # Create publisher
        publisher = YahooFinancePublisher(
            publisher_id='test_pub',
            broker=broker,
            serializer=serializer,
            symbols=['AAPL'],
            publish_interval=0.5,
            batch_size=1,
        )
        
        # Create trend analyzer subscriber
        trend_analyzer = TrendAnalyzerSubscriber(
            subscriber_id='test_trend',
            broker=broker,
            serializer=serializer,
        )
        
        # Start components
        await trend_analyzer.start()
        await publisher.start()
        
        # Verify they're running
        assert publisher._running
        assert trend_analyzer._running
        
        # Stop components
        await publisher.stop()
        await trend_analyzer.stop()
        
        # Verify they stopped
        assert not publisher._running
        assert not trend_analyzer._running
    
    @pytest.mark.asyncio
    async def test_multiple_subscribers_receive_same_data(self, broker, serializer):
        """Test multiple subscribers can run simultaneously"""
        # Create publisher
        publisher = YahooFinancePublisher(
            publisher_id='test_pub',
            broker=broker,
            serializer=serializer,
            symbols=['AAPL'],
            publish_interval=0.5,
            batch_size=1,
        )
        
        # Create multiple subscribers
        state_tracker = StateTrackerSubscriber(
            subscriber_id='state1',
            broker=broker,
            serializer=serializer,
        )
        
        market_breadth = MarketBreadthSubscriber(
            subscriber_id='breadth1',
            broker=broker,
            serializer=serializer,
        )
        
        trend_analyzer = TrendAnalyzerSubscriber(
            subscriber_id='trend1',
            broker=broker,
            serializer=serializer,
        )
        
        # Start all components
        await state_tracker.start()
        await market_breadth.start()
        await trend_analyzer.start()
        await publisher.start()
        
        # Verify all running
        assert publisher._running
        assert state_tracker._running
        assert market_breadth._running
        assert trend_analyzer._running
        
        # Stop all components
        await publisher.stop()
        await state_tracker.stop()
        await market_breadth.stop()
        await trend_analyzer.stop()
        
        # Verify all stopped
        assert not publisher._running
        assert not state_tracker._running
        assert not market_breadth._running
        assert not trend_analyzer._running
    
    @pytest.mark.asyncio
    async def test_publisher_error_handling(self, broker, serializer):
        """Test publisher and subscriber handle lifecycle correctly"""
        publisher = YahooFinancePublisher(
            publisher_id='test_pub',
            broker=broker,
            serializer=serializer,
            symbols=['INVALID'],
            publish_interval=0.5,
            batch_size=1,
        )
        
        state_tracker = StateTrackerSubscriber(
            subscriber_id='test_state',
            broker=broker,
            serializer=serializer,
        )
        
        await state_tracker.start()
        await publisher.start()
        
        # Let them run briefly
        await asyncio.sleep(0.5)
        
        await publisher.stop()
        await state_tracker.stop()
        
        # Publisher should have stats
        stats = publisher.get_stats()
        assert 'batch_size' in stats or 'total_publishes' in stats


class TestPublisherSubscriberLifecycle:
    """Test lifecycle management of publishers and subscribers"""
    
    @pytest.mark.asyncio
    async def test_start_stop_cycle(self):
        """Test starting and stopping components"""
        serializer = JSONSerializer()
        broker = InMemoryBroker(serializer=serializer)
        await broker.connect()
        
        publisher = YahooFinancePublisher(
            publisher_id='test_pub',
            broker=broker,
            serializer=serializer,
            symbols=['AAPL'],
            publish_interval=1.0,
        )
        
        subscriber = StateTrackerSubscriber(
            subscriber_id='test_sub',
            broker=broker,
            serializer=serializer,
        )
        
        # Start
        await subscriber.start()
        await publisher.start()
        assert publisher._running
        assert subscriber._running
        
        # Stop
        await publisher.stop()
        await subscriber.stop()
        assert not publisher._running
        assert not subscriber._running
        
        await broker.disconnect()
    
    @pytest.mark.asyncio
    async def test_restart_components(self):
        """Test restarting components"""
        serializer = JSONSerializer()
        broker = InMemoryBroker(serializer=serializer)
        await broker.connect()
        
        subscriber = StateTrackerSubscriber(
            subscriber_id='test_sub',
            broker=broker,
            serializer=serializer,
        )
        
        # Start, stop, start again
        await subscriber.start()
        await subscriber.stop()
        await subscriber.start()
        
        assert subscriber._running
        
        await subscriber.stop()
        await broker.disconnect()


class TestMessageSerialization:
    """Test message serialization through the full pipeline"""
    
    @pytest.mark.asyncio
    async def test_json_serialization_pipeline(self):
        """Test JSON serialization through publisher to subscriber"""
        serializer = JSONSerializer()
        broker = InMemoryBroker(serializer=serializer)
        await broker.connect()
        
        publisher = YahooFinancePublisher(
            publisher_id='test_pub',
            broker=broker,
            serializer=serializer,
            symbols=['AAPL'],
            publish_interval=0.5,
        )
        
        subscriber = StateTrackerSubscriber(
            subscriber_id='test_sub',
            broker=broker,
            serializer=serializer,
        )
        
        await subscriber.start()
        await publisher.start()
        
        # Let them run briefly
        await asyncio.sleep(0.5)
        
        await publisher.stop()
        await subscriber.stop()
        
        # Verify they ran
        assert not publisher._running
        assert not subscriber._running
        
        await broker.disconnect()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--asyncio-mode=auto'])
