"""
Unit tests for Yahoo Finance publisher
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, MagicMock, patch
from datetime import datetime, timezone
import pandas as pd

from publisher.yahoo_publisher import YahooFinancePublisher
from events.event_models import CandleDataEvent, FetchStatusEvent


class TestYahooFinancePublisher:
    """Test Yahoo Finance publisher functionality"""
    
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
    def sample_symbols(self):
        """Sample symbols for testing"""
        return ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
    
    @pytest.fixture
    def yahoo_publisher(self, mock_broker, mock_serializer, sample_symbols):
        """Create Yahoo Finance publisher for testing"""
        return YahooFinancePublisher(
            publisher_id='yahoo-test',
            broker=mock_broker,
            serializer=mock_serializer,
            symbols=sample_symbols,
            batch_size=2,
            rate_limit=10,
            rate_limit_period=1.0,
            publish_interval=0.1,
            data_interval='1m',
            period='1d',
        )
    
    @pytest.fixture
    def sample_dataframe(self):
        """Create sample DataFrame with OHLCV data"""
        data = {
            'Open': [150.0, 151.0, 152.0],
            'High': [152.0, 153.0, 154.0],
            'Low': [149.0, 150.0, 151.0],
            'Close': [151.0, 152.0, 153.0],
            'Volume': [1000000, 1100000, 1200000],
        }
        index = pd.date_range('2024-01-01', periods=3, freq='1min', tz='UTC')
        return pd.DataFrame(data, index=index)
    
    @pytest.mark.asyncio
    async def test_initialization(self, yahoo_publisher, sample_symbols):
        """Test publisher initialization"""
        assert yahoo_publisher.publisher_id == 'yahoo-test'
        assert yahoo_publisher.symbols == sample_symbols
        assert yahoo_publisher.batch_size == 2
        assert yahoo_publisher.data_interval == '1m'
        assert yahoo_publisher.period == '1d'
        assert yahoo_publisher._fetch_stats['total_fetches'] == 0
    
    @pytest.mark.asyncio
    async def test_safe_float_conversion(self, yahoo_publisher):
        """Test safe float conversion"""
        assert yahoo_publisher._safe_float(150.5) == 150.5
        assert yahoo_publisher._safe_float('151.0') == 151.0
        assert yahoo_publisher._safe_float(None) is None
        assert yahoo_publisher._safe_float(pd.NA) is None
        assert yahoo_publisher._safe_float('invalid') is None
    
    @pytest.mark.asyncio
    async def test_safe_int_conversion(self, yahoo_publisher):
        """Test safe int conversion"""
        assert yahoo_publisher._safe_int(1000) == 1000
        assert yahoo_publisher._safe_int(1000.5) == 1000
        assert yahoo_publisher._safe_int('1000') == 1000
        assert yahoo_publisher._safe_int(None) is None
        assert yahoo_publisher._safe_int(pd.NA) is None
        assert yahoo_publisher._safe_int('invalid') is None
    
    @pytest.mark.asyncio
    async def test_channel_determination(self, yahoo_publisher):
        """Test channel name determination"""
        candle_event = CandleDataEvent(
            symbol='AAPL',
            trade_date='2024-01-01',
            timestamp=1704067200,
            open_price=150.0,
            high_price=151.0,
            low_price=149.0,
            close_price=150.5,
            volume=1000000,
            prev_close=149.5,
            series='EQ',
        )
        
        status_event = FetchStatusEvent(
            publisher_id='test',
            status='HEALTHY',
            timestamp=1704067200,
            symbols_succeeded=5,
            symbols_failed=0,
            total_symbols=5,
            batch_size=50,
            rate_limit=20,
            fetch_duration_ms=500,
            uptime_seconds=100,
            total_events_published=10,
        )
        
        assert yahoo_publisher._get_channel_for_event(candle_event) == 'market.candle'
        assert yahoo_publisher._get_channel_for_event(status_event) == 'market.status'
    
    @pytest.mark.asyncio
    async def test_publish_candle_data(
        self,
        yahoo_publisher,
        sample_dataframe,
        mock_broker
    ):
        """Test publishing candle data"""
        await yahoo_publisher.start()
        
        # Publish candle data
        await yahoo_publisher._publish_candle_data('AAPL', sample_dataframe)
        
        # Verify publish was called
        assert mock_broker.publish.called
        
        await yahoo_publisher.stop()
    
    @pytest.mark.asyncio
    async def test_publish_candle_data_empty_df(
        self,
        yahoo_publisher,
        mock_broker
    ):
        """Test publishing with empty DataFrame"""
        await yahoo_publisher.start()
        
        # Empty DataFrame
        empty_df = pd.DataFrame()
        
        # Should not raise error, just return
        await yahoo_publisher._publish_candle_data('AAPL', empty_df)
        
        # Should not publish
        assert not mock_broker.publish.called
        
        await yahoo_publisher.stop()
    
    @pytest.mark.asyncio
    async def test_publish_fetch_status(
        self,
        yahoo_publisher,
        mock_broker
    ):
        """Test publishing fetch status"""
        await yahoo_publisher.start()
        
        # Publish status
        await yahoo_publisher._publish_fetch_status(
            success_count=5,
            failure_count=0,
            errors=[],
        )
        
        # Verify publish was called
        assert mock_broker.publish.called
        
        await yahoo_publisher.stop()
    
    @pytest.mark.asyncio
    async def test_publish_fetch_status_degraded(
        self,
        yahoo_publisher,
        mock_broker
    ):
        """Test fetch status with degraded health"""
        await yahoo_publisher.start()
        
        # Publish status with some failures
        await yahoo_publisher._publish_fetch_status(
            success_count=4,
            failure_count=1,
            errors=['AAPL: Timeout'],
        )
        
        # Should publish degraded status (80% success rate)
        assert mock_broker.publish.called
        
        await yahoo_publisher.stop()
    
    @pytest.mark.asyncio
    async def test_publish_fetch_status_unhealthy(
        self,
        yahoo_publisher,
        mock_broker
    ):
        """Test fetch status with unhealthy status"""
        await yahoo_publisher.start()
        
        # Publish status with many failures
        await yahoo_publisher._publish_fetch_status(
            success_count=1,
            failure_count=4,
            errors=['Error 1', 'Error 2', 'Error 3', 'Error 4'],
        )
        
        # Should publish unhealthy status (<80% success rate)
        assert mock_broker.publish.called
        
        await yahoo_publisher.stop()
    
    @pytest.mark.asyncio
    async def test_fetch_batch_single_symbol(self, yahoo_publisher):
        """Test fetching a single symbol"""
        with patch('yfinance.download') as mock_download:
            # Mock successful download
            mock_df = pd.DataFrame({
                'Open': [150.0],
                'High': [152.0],
                'Low': [149.0],
                'Close': [151.0],
                'Volume': [1000000],
            }, index=pd.date_range('2024-01-01', periods=1, freq='1min'))
            mock_download.return_value = mock_df
            
            result = yahoo_publisher._fetch_batch(['AAPL'])
            
            assert 'AAPL' in result
            assert result['AAPL'] is not None
            mock_download.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_batch_multiple_symbols(self, yahoo_publisher):
        """Test fetching multiple symbols"""
        with patch('yfinance.download') as mock_download:
            # Mock multi-symbol download
            mock_df = MagicMock()
            mock_df.empty = False
            mock_df.columns = MagicMock()
            mock_df.columns.levels = [['AAPL', 'GOOGL']]
            
            # Mock individual symbol data as real DataFrames
            aapl_df = pd.DataFrame({
                'Open': [150.0],
                'High': [152.0],
                'Low': [149.0],
                'Close': [151.0],
                'Volume': [1000000],
            })
            googl_df = pd.DataFrame({
                'Open': [2800.0],
                'High': [2820.0],
                'Low': [2790.0],
                'Close': [2810.0],
                'Volume': [500000],
            })
            
            # Don't try to set .empty on real DataFrame - it's a property
            mock_df.__getitem__ = lambda self, key: aapl_df if key == 'AAPL' else googl_df
            mock_download.return_value = mock_df
            
            result = yahoo_publisher._fetch_batch(['AAPL', 'GOOGL'])
            
            assert 'AAPL' in result
            assert 'GOOGL' in result
            mock_download.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_batch_error_handling(self, yahoo_publisher):
        """Test error handling in batch fetch"""
        with patch('yfinance.download') as mock_download:
            # Mock download failure
            mock_download.side_effect = Exception("API error")
            
            result = yahoo_publisher._fetch_batch(['AAPL', 'GOOGL'])
            
            # All symbols should be marked as failed (None)
            assert result['AAPL'] is None
            assert result['GOOGL'] is None
    
    @pytest.mark.asyncio
    async def test_fetch_and_publish_integration(
        self,
        yahoo_publisher,
        sample_dataframe,
        mock_broker
    ):
        """Test full fetch and publish cycle"""
        with patch.object(
            yahoo_publisher,
            '_fetch_batch',
            return_value={'AAPL': sample_dataframe, 'GOOGL': sample_dataframe}
        ):
            await yahoo_publisher.start()
            
            # Let it run one cycle
            await asyncio.sleep(0.2)
            
            # Verify publishes occurred
            assert mock_broker.publish.called
            
            # Check fetch statistics
            assert yahoo_publisher._fetch_stats['total_fetches'] > 0
            
            await yahoo_publisher.stop()
    
    @pytest.mark.asyncio
    async def test_get_stats(self, yahoo_publisher):
        """Test getting publisher statistics"""
        stats = yahoo_publisher.get_stats()
        
        assert 'publisher_id' in stats
        assert 'total_symbols' in stats
        assert 'batch_size' in stats
        assert 'data_interval' in stats
        assert 'fetch_stats' in stats
        assert stats['total_symbols'] == 5
        assert stats['batch_size'] == 2
    
    @pytest.mark.asyncio
    async def test_start_and_stop(self, yahoo_publisher):
        """Test starting and stopping publisher"""
        await yahoo_publisher.start()
        assert yahoo_publisher._running
        
        await asyncio.sleep(0.2)
        
        await yahoo_publisher.stop()
        assert not yahoo_publisher._running


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
