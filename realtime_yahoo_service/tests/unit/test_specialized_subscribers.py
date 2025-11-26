"""
Unit tests for specialized subscribers
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, MagicMock, patch
from datetime import datetime, timezone

from subscribers.db_writer_subscriber import DBWriterSubscriber
from subscribers.state_tracker_subscriber import StateTrackerSubscriber
from subscribers.market_breadth_subscriber import MarketBreadthSubscriber
from subscribers.trend_analyzer_subscriber import TrendAnalyzerSubscriber
from events.event_models import CandleDataEvent, FetchStatusEvent


class TestDBWriterSubscriber:
    """Test database writer subscriber"""
    
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
        serializer.serialize = Mock(return_value=b'{"test": "data"}')
        serializer.deserialize = Mock()
        return serializer
    
    @pytest.fixture
    def mock_db_engine(self):
        """Create a mock async database engine"""
        engine = AsyncMock()
        
        # Mock connection context manager
        conn = AsyncMock()
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=None)
        conn.execute = AsyncMock()
        conn.commit = AsyncMock()
        
        # Mock engine.begin() context manager
        engine.begin = MagicMock(return_value=conn)
        engine.dispose = AsyncMock()
        
        return engine
    
    @pytest.fixture
    def sample_candle_data(self):
        """Sample candle data"""
        return {
            'symbol': 'AAPL',
            'trade_date': '2024-01-01',
            'timestamp': 1704067200,
            'prev_close': 149.5,
            'open_price': 150.0,
            'high_price': 152.0,
            'low_price': 149.0,
            'close_price': 151.0,
            'volume': 1000000,
            'delivery_qty': None,
            'delivery_per': None,
            'series': 'EQ',
            'data_source': 'yahoo_finance',
        }
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_broker, mock_serializer, mock_db_engine):
        """Test DB writer initialization"""
        with patch('subscribers.base_subscriber.create_async_engine', return_value=mock_db_engine):
            subscriber = DBWriterSubscriber(
                subscriber_id='db-writer-test',
                broker=mock_broker,
                serializer=mock_serializer,
                db_url='mysql+aiomysql://user:pass@localhost/testdb',
                batch_size=10,
            )
        
        assert subscriber.subscriber_id == 'db-writer-test'
        assert subscriber.channels == ['market.candle']
        assert subscriber.batch_size == 10
        assert len(subscriber._batch) == 0
    
    @pytest.mark.asyncio
    async def test_message_batching(self, mock_broker, mock_serializer, mock_db_engine, sample_candle_data):
        """Test message batching"""
        with patch('subscribers.base_subscriber.create_async_engine', return_value=mock_db_engine):
            subscriber = DBWriterSubscriber(
                subscriber_id='db-writer-test',
                broker=mock_broker,
                serializer=mock_serializer,
                db_url='mysql+aiomysql://user:pass@localhost/testdb',
                batch_size=3,
            )
        
        # Don't actually write to DB
        subscriber._write_batch = AsyncMock()
        
        await subscriber.start()
        
        # Add messages
        await subscriber.on_message('market.candle', sample_candle_data)
        assert len(subscriber._batch) == 1
        
        await subscriber.on_message('market.candle', sample_candle_data)
        assert len(subscriber._batch) == 2
        
        # This should trigger batch write
        await subscriber.on_message('market.candle', sample_candle_data)
        assert subscriber._write_batch.called
        
        await subscriber.stop()
    
    @pytest.mark.asyncio
    async def test_get_stats(self, mock_broker, mock_serializer, mock_db_engine):
        """Test getting statistics"""
        with patch('subscribers.base_subscriber.create_async_engine', return_value=mock_db_engine):
            subscriber = DBWriterSubscriber(
                subscriber_id='db-writer-test',
                broker=mock_broker,
                serializer=mock_serializer,
                db_url='mysql+aiomysql://user:pass@localhost/testdb',
            )
        
        stats = subscriber.get_stats()
        
        assert 'write_stats' in stats
        assert 'batch_pending' in stats
        assert stats['write_stats']['total_written'] == 0


class TestStateTrackerSubscriber:
    """Test state tracker subscriber"""
    
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
        return serializer
    
    @pytest.fixture
    def sample_candle_data(self):
        """Sample candle data"""
        return {
            'symbol': 'AAPL',
            'trade_date': '2024-01-01',
            'timestamp': 1704067200,
            'prev_close': 149.5,
            'open_price': 150.0,
            'high_price': 152.0,
            'low_price': 149.0,
            'close_price': 151.0,
            'volume': 1000000,
            'delivery_qty': None,
            'delivery_per': None,
            'series': 'EQ',
            'data_source': 'yahoo_finance',
        }
    
    @pytest.fixture
    def sample_status_data(self):
        """Sample status data"""
        return {
            'publisher_id': 'yahoo-publisher',
            'status': 'HEALTHY',
            'timestamp': 1704067200,
            'symbols_succeeded': 10,
            'symbols_failed': 0,
            'total_symbols': 10,
            'batch_size': 50,
            'rate_limit': 20,
            'fetch_duration_ms': 500,
            'uptime_seconds': 100,
            'total_events_published': 50,
        }
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_broker, mock_serializer):
        """Test state tracker initialization"""
        subscriber = StateTrackerSubscriber(
            subscriber_id='state-tracker-test',
            broker=mock_broker,
            serializer=mock_serializer,
        )
        
        assert subscriber.subscriber_id == 'state-tracker-test'
        assert 'market.candle' in subscriber.channels
        assert 'market.status' in subscriber.channels
        assert len(subscriber._symbol_state) == 0
        assert len(subscriber._publisher_status) == 0
    
    @pytest.mark.asyncio
    async def test_candle_data_tracking(self, mock_broker, mock_serializer, sample_candle_data):
        """Test tracking candle data"""
        subscriber = StateTrackerSubscriber(
            subscriber_id='state-tracker-test',
            broker=mock_broker,
            serializer=mock_serializer,
        )
        
        await subscriber.start()
        
        # Handle candle data
        await subscriber.on_message('market.candle', sample_candle_data)
        
        # Verify state
        state = subscriber.get_symbol_state('AAPL')
        assert state is not None
        assert state.symbol == 'AAPL'
        assert state.close_price == 151.0
        
        await subscriber.stop()
    
    @pytest.mark.asyncio
    async def test_status_tracking(self, mock_broker, mock_serializer, sample_status_data):
        """Test tracking publisher status"""
        subscriber = StateTrackerSubscriber(
            subscriber_id='state-tracker-test',
            broker=mock_broker,
            serializer=mock_serializer,
        )
        
        await subscriber.start()
        
        # Handle status
        await subscriber.on_message('market.status', sample_status_data)
        
        # Verify status
        status = subscriber.get_publisher_status('yahoo-publisher')
        assert status is not None
        assert status.publisher_id == 'yahoo-publisher'
        assert status.status == 'HEALTHY'
        
        await subscriber.stop()
    
    @pytest.mark.asyncio
    async def test_get_all_symbols(self, mock_broker, mock_serializer, sample_candle_data):
        """Test getting all symbols"""
        subscriber = StateTrackerSubscriber(
            subscriber_id='state-tracker-test',
            broker=mock_broker,
            serializer=mock_serializer,
        )
        
        await subscriber.start()
        
        # Add multiple symbols
        for symbol in ['AAPL', 'GOOGL', 'MSFT']:
            data = sample_candle_data.copy()
            data['symbol'] = symbol
            await subscriber.on_message('market.candle', data)
        
        # Get all
        all_symbols = subscriber.get_all_symbols()
        assert len(all_symbols) == 3
        assert 'AAPL' in all_symbols
        assert 'GOOGL' in all_symbols
        assert 'MSFT' in all_symbols
        
        await subscriber.stop()
    
    @pytest.mark.asyncio
    async def test_get_stats(self, mock_broker, mock_serializer, sample_candle_data):
        """Test getting statistics"""
        subscriber = StateTrackerSubscriber(
            subscriber_id='state-tracker-test',
            broker=mock_broker,
            serializer=mock_serializer,
        )
        
        await subscriber.start()
        
        # Add some data
        await subscriber.on_message('market.candle', sample_candle_data)
        
        stats = subscriber.get_stats()
        
        assert 'symbols_tracked' in stats
        assert stats['symbols_tracked'] == 1
        assert 'publishers_tracked' in stats
        
        await subscriber.stop()


class TestMarketBreadthSubscriber:
    """Test market breadth subscriber"""
    
    @pytest.fixture
    def mock_broker(self):
        """Create mock broker"""
        broker = AsyncMock()
        broker.subscribe = AsyncMock()
        broker.unsubscribe = AsyncMock()
        broker.publish = AsyncMock()
        return broker
    
    @pytest.fixture
    def mock_serializer(self):
        """Create mock serializer"""
        serializer = Mock()
        serializer.serialize = Mock(return_value=b'{"test": "data"}')
        return serializer
    
    def create_candle_data(self, symbol: str, prev_close: float, close: float):
        """Create sample candle data"""
        return {
            'symbol': symbol,
            'trade_date': '2024-01-01',
            'timestamp': 1704067200,
            'prev_close': prev_close,
            'open_price': close,
            'high_price': close * 1.01,
            'low_price': close * 0.99,
            'close_price': close,
            'volume': 1000000,
            'delivery_qty': None,
            'delivery_per': None,
            'series': 'EQ',
            'data_source': 'yahoo_finance',
        }
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_broker, mock_serializer):
        """Test market breadth initialization"""
        subscriber = MarketBreadthSubscriber(
            subscriber_id='breadth-test',
            broker=mock_broker,
            serializer=mock_serializer,
            index_name='NIFTY50',
            publish_interval=60.0,
        )
        
        assert subscriber.subscriber_id == 'breadth-test'
        assert subscriber.index_name == 'NIFTY50'
        assert subscriber.publish_interval == 60.0
        assert len(subscriber._symbol_prices) == 0
    
    @pytest.mark.asyncio
    async def test_breadth_calculation_all_advances(self, mock_broker, mock_serializer):
        """Test breadth calculation with all advancing stocks"""
        subscriber = MarketBreadthSubscriber(
            subscriber_id='breadth-test',
            broker=mock_broker,
            serializer=mock_serializer,
            index_name='NIFTY50',
        )
        
        await subscriber.start()
        
        # Add advancing stocks
        for i in range(5):
            data = self.create_candle_data(f'SYM{i}', 100.0, 105.0)
            await subscriber.on_message('market.candle', data)
        
        # Compute breadth
        breadth = subscriber.compute_breadth()
        
        assert breadth.advances == 5
        assert breadth.declines == 0
        assert breadth.unchanged == 0
        assert breadth.total_stocks == 5
        assert breadth.sentiment_score == 1.0  # All advancing
        
        await subscriber.stop()
    
    @pytest.mark.asyncio
    async def test_breadth_calculation_mixed(self, mock_broker, mock_serializer):
        """Test breadth calculation with mixed market"""
        subscriber = MarketBreadthSubscriber(
            subscriber_id='breadth-test',
            broker=mock_broker,
            serializer=mock_serializer,
            index_name='NIFTY50',
        )
        
        await subscriber.start()
        
        # Add stocks: 3 advances, 2 declines
        await subscriber.on_message('market.candle', self.create_candle_data('ADV1', 100.0, 105.0))
        await subscriber.on_message('market.candle', self.create_candle_data('ADV2', 100.0, 102.0))
        await subscriber.on_message('market.candle', self.create_candle_data('ADV3', 100.0, 101.0))
        await subscriber.on_message('market.candle', self.create_candle_data('DEC1', 100.0, 95.0))
        await subscriber.on_message('market.candle', self.create_candle_data('DEC2', 100.0, 98.0))
        
        # Compute breadth
        breadth = subscriber.compute_breadth()
        
        assert breadth.advances == 3
        assert breadth.declines == 2
        assert breadth.unchanged == 0
        assert breadth.total_stocks == 5
        assert breadth.ad_ratio == 1.5  # 3/2
        assert breadth.sentiment_score == 0.2  # (3-2)/5
        
        await subscriber.stop()
    
    @pytest.mark.asyncio
    async def test_publish_breadth(self, mock_broker, mock_serializer):
        """Test publishing breadth event"""
        subscriber = MarketBreadthSubscriber(
            subscriber_id='breadth-test',
            broker=mock_broker,
            serializer=mock_serializer,
            index_name='NIFTY50',
        )
        
        await subscriber.start()
        
        # Add some data
        await subscriber.on_message('market.candle', self.create_candle_data('AAPL', 100.0, 105.0))
        await subscriber.on_message('market.candle', self.create_candle_data('GOOGL', 100.0, 95.0))
        
        # Publish
        await subscriber.publish_breadth()
        
        # Verify published
        assert mock_broker.publish.called
        call_args = mock_broker.publish.call_args
        assert call_args[0][0] == 'market.breadth'
        
        await subscriber.stop()
    
    @pytest.mark.asyncio
    async def test_get_stats(self, mock_broker, mock_serializer):
        """Test getting statistics"""
        subscriber = MarketBreadthSubscriber(
            subscriber_id='breadth-test',
            broker=mock_broker,
            serializer=mock_serializer,
            index_name='NIFTY50',
        )
        
        await subscriber.start()
        
        # Add data
        await subscriber.on_message('market.candle', self.create_candle_data('AAPL', 100.0, 105.0))
        
        stats = subscriber.get_stats()
        
        assert 'current_breadth' in stats
        assert stats['current_breadth']['advances'] == 1
        
        await subscriber.stop()


class TestTrendAnalyzerSubscriber:
    """Test trend analyzer subscriber"""
    
    @pytest.fixture
    def mock_broker(self):
        """Create mock broker"""
        broker = AsyncMock()
        broker.subscribe = AsyncMock()
        broker.unsubscribe = AsyncMock()
        broker.publish = AsyncMock()
        return broker
    
    @pytest.fixture
    def mock_serializer(self):
        """Create mock serializer"""
        serializer = Mock()
        serializer.serialize = Mock(return_value=b'{"test": "data"}')
        serializer.deserialize = Mock()
        return serializer
    
    def create_candle_data(self, symbol: str, close_price: float):
        """Helper to create candle data"""
        event = CandleDataEvent(
            symbol=symbol,
            trade_date='2024-01-01',
            timestamp=int(datetime.now(timezone.utc).timestamp()),
            series='EQ',
            prev_close=close_price - 1.0,
            open_price=close_price - 0.5,
            high_price=close_price + 1.0,
            low_price=close_price - 1.0,
            close_price=close_price,
            volume=1000000,
            delivery_qty=500000,
            delivery_per=50.0,
            data_source='yahoo_finance',
        )
        return event.model_dump()
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_broker, mock_serializer):
        """Test trend analyzer initialization"""
        subscriber = TrendAnalyzerSubscriber(
            subscriber_id='trend-test',
            broker=mock_broker,
            serializer=mock_serializer,
            window_size=50,
            sma_periods=[20, 50],
        )
        
        assert subscriber.subscriber_id == 'trend-test'
        assert subscriber._window_size == 50
        assert subscriber._sma_periods == [20, 50]
        assert len(subscriber._candle_history) == 0
        assert 'market.candle' in subscriber.channels
    
    @pytest.mark.asyncio
    async def test_candle_tracking(self, mock_broker, mock_serializer):
        """Test tracking candle data"""
        subscriber = TrendAnalyzerSubscriber(
            subscriber_id='trend-test',
            broker=mock_broker,
            serializer=mock_serializer,
            window_size=10,
        )
        
        await subscriber.start()
        
        # Add candles for AAPL
        for i in range(5):
            candle_data = self.create_candle_data('AAPL', 150.0 + i)
            mock_serializer.deserialize.return_value = candle_data
            await subscriber.on_message('market.candle', b'test_data')
        
        # Check history
        assert 'AAPL' in subscriber._candle_history
        assert len(subscriber._candle_history['AAPL']) == 5
        
        await subscriber.stop()
    
    @pytest.mark.asyncio
    async def test_sma_computation(self, mock_broker, mock_serializer):
        """Test SMA computation"""
        subscriber = TrendAnalyzerSubscriber(
            subscriber_id='trend-test',
            broker=mock_broker,
            serializer=mock_serializer,
        )
        
        # Test with sufficient data
        prices = [100.0, 102.0, 104.0, 106.0, 108.0]
        sma = subscriber.compute_sma(prices, 3)
        assert sma == 106.0  # (104 + 106 + 108) / 3
        
        # Test with insufficient data
        sma = subscriber.compute_sma(prices, 10)
        assert sma is None
    
    @pytest.mark.asyncio
    async def test_trend_analysis(self, mock_broker, mock_serializer):
        """Test trend analysis for a symbol"""
        subscriber = TrendAnalyzerSubscriber(
            subscriber_id='trend-test',
            broker=mock_broker,
            serializer=mock_serializer,
            window_size=10,
            sma_periods=[3, 5],
        )
        
        await subscriber.start()
        
        # Add candles with upward trend
        for i in range(10):
            candle_data = self.create_candle_data('AAPL', 100.0 + i * 2)
            mock_serializer.deserialize.return_value = candle_data
            await subscriber.on_message('market.candle', b'test_data')
        
        # Analyze
        analysis = subscriber.analyze_symbol('AAPL')
        
        assert analysis is not None
        assert analysis['symbol'] == 'AAPL'
        assert 'trend_direction' in analysis
        assert 'trend_strength' in analysis
        assert 'smas' in analysis
        assert 'sma_3' in analysis['smas']
        assert 'sma_5' in analysis['smas']
        
        await subscriber.stop()
    
    @pytest.mark.asyncio
    async def test_get_stats(self, mock_broker, mock_serializer):
        """Test getting statistics"""
        subscriber = TrendAnalyzerSubscriber(
            subscriber_id='trend-test',
            broker=mock_broker,
            serializer=mock_serializer,
        )
        
        await subscriber.start()
        
        # Add some data
        candle_data = self.create_candle_data('AAPL', 150.0)
        mock_serializer.deserialize.return_value = candle_data
        await subscriber.on_message('market.candle', b'test_data')
        
        stats = subscriber.get_stats()
        
        assert 'symbols_tracked' in stats
        assert stats['symbols_tracked'] == 1
        assert 'window_size' in stats
        assert 'sma_periods' in stats
        
        await subscriber.stop()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
