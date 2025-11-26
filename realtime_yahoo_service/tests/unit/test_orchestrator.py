"""
Unit tests for Orchestrator Service
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from pathlib import Path
import tempfile
import yaml

from orchestrator.service import OrchestratorService


class TestOrchestratorService:
    """Test orchestrator service"""
    
    @pytest.fixture
    def sample_config(self):
        """Create sample configuration"""
        return {
            'broker': {
                'type': 'inmemory'
            },
            'serializer': {
                'type': 'json'
            },
            'dlq': {
                'enabled': True,
                'storage_type': 'file',
                'file_path': './test_dlq',
                'max_retries': 3
            },
            'publishers': [
                {
                    'id': 'test_publisher',
                    'type': 'yahoo_finance',
                    'enabled': True,
                    'symbols': ['AAPL', 'GOOGL'],
                    'fetch_interval': 60,
                    'batch_size': 50
                }
            ],
            'subscribers': [
                {
                    'id': 'test_state_tracker',
                    'type': 'state_tracker',
                    'enabled': True,
                    'channels': ['market.candle']
                }
            ],
            'health': {
                'check_interval': 10,
                'restart_on_failure': True,
                'max_restart_attempts': 3,
                'restart_delay': 5
            },
            'logging': {
                'level': 'INFO'
            }
        }
    
    @pytest.fixture
    def temp_config_file(self, sample_config):
        """Create temporary config file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config, f)
            return f.name
    
    def test_initialization(self, temp_config_file):
        """Test orchestrator initialization"""
        orchestrator = OrchestratorService(temp_config_file)
        
        assert orchestrator.config_path == Path(temp_config_file)
        assert orchestrator.broker is None
        assert orchestrator.serializer is None
        assert len(orchestrator.publishers) == 0
        assert len(orchestrator.subscribers) == 0
        assert orchestrator._running is False
    
    def test_load_config(self, temp_config_file, sample_config):
        """Test loading configuration"""
        orchestrator = OrchestratorService(temp_config_file)
        config = orchestrator.load_config()
        
        assert config is not None
        assert config['broker']['type'] == 'inmemory'
        assert config['serializer']['type'] == 'json'
        assert len(config['publishers']) == 1
        assert len(config['subscribers']) == 1
    
    def test_load_config_file_not_found(self):
        """Test loading non-existent config file"""
        orchestrator = OrchestratorService('nonexistent.yaml')
        
        with pytest.raises(FileNotFoundError):
            orchestrator.load_config()
    
    def test_create_inmemory_broker(self, temp_config_file):
        """Test creating in-memory broker"""
        orchestrator = OrchestratorService(temp_config_file)
        orchestrator.load_config()
        
        # Must create serializer first
        orchestrator._create_serializer()
        broker = orchestrator._create_broker()
        
        assert broker is not None
        assert orchestrator.broker is not None
        from redis_broker import InMemoryBroker
        assert isinstance(broker, InMemoryBroker)
    
    def test_create_json_serializer(self, temp_config_file):
        """Test creating JSON serializer"""
        orchestrator = OrchestratorService(temp_config_file)
        orchestrator.load_config()
        
        serializer = orchestrator._create_serializer()
        
        assert serializer is not None
        assert orchestrator.serializer is not None
        from serialization import JSONSerializer
        assert isinstance(serializer, JSONSerializer)
    
    def test_create_dlq(self, temp_config_file):
        """Test creating DLQ"""
        orchestrator = OrchestratorService(temp_config_file)
        orchestrator.load_config()
        orchestrator._create_serializer()
        orchestrator._create_broker()
        
        dlq = orchestrator._create_dlq()
        
        assert dlq is not None
        assert orchestrator.dlq_manager is not None
    
    def test_create_publishers(self, temp_config_file):
        """Test creating publishers"""
        orchestrator = OrchestratorService(temp_config_file)
        orchestrator.load_config()
        orchestrator._create_serializer()
        orchestrator._create_broker()
        orchestrator._create_dlq()
        
        publishers = orchestrator._create_publishers()
        
        assert len(publishers) == 1
        assert 'test_publisher' in publishers
        from publisher import YahooFinancePublisher
        assert isinstance(publishers['test_publisher'], YahooFinancePublisher)
    
    def test_create_subscribers(self, temp_config_file):
        """Test creating subscribers"""
        orchestrator = OrchestratorService(temp_config_file)
        orchestrator.load_config()
        orchestrator._create_serializer()
        orchestrator._create_broker()
        orchestrator._create_dlq()
        
        subscribers = orchestrator._create_subscribers()
        
        assert len(subscribers) == 1
        assert 'test_state_tracker' in subscribers
        from subscribers import StateTrackerSubscriber
        assert isinstance(subscribers['test_state_tracker'], StateTrackerSubscriber)
    
    @pytest.mark.asyncio
    async def test_start_and_stop(self, temp_config_file):
        """Test starting and stopping orchestrator"""
        orchestrator = OrchestratorService(temp_config_file)
        
        # Mock start methods
        with patch.object(orchestrator, '_create_broker'), \
             patch.object(orchestrator, '_create_serializer'), \
             patch.object(orchestrator, '_create_dlq'), \
             patch.object(orchestrator, '_create_publishers') as mock_create_pubs, \
             patch.object(orchestrator, '_create_subscribers') as mock_create_subs:
            
            # Create mock broker
            mock_broker = AsyncMock()
            orchestrator.broker = mock_broker
            orchestrator.serializer = Mock()
            
            # Create mock publisher and subscriber
            mock_pub = AsyncMock()
            mock_pub._running = True
            mock_pub.start = AsyncMock()
            mock_pub.stop = AsyncMock()
            mock_pub.get_stats = Mock(return_value={})
            
            mock_sub = AsyncMock()
            mock_sub._running = True
            mock_sub.start = AsyncMock()
            mock_sub.stop = AsyncMock()
            mock_sub.get_stats = Mock(return_value={})
            
            orchestrator.publishers = {'test_pub': mock_pub}
            orchestrator.subscribers = {'test_sub': mock_sub}
            
            mock_create_pubs.return_value = orchestrator.publishers
            mock_create_subs.return_value = orchestrator.subscribers
            
            # Start orchestrator
            await orchestrator.start()
            
            assert orchestrator._running is True
            assert mock_broker.connect.called
            assert mock_pub.start.called
            assert mock_sub.start.called
            
            # Stop orchestrator
            await orchestrator.stop()
            
            assert orchestrator._running is False
            assert mock_pub.stop.called
            assert mock_sub.stop.called
            assert mock_broker.disconnect.called
    
    @pytest.mark.asyncio
    async def test_get_stats(self, temp_config_file):
        """Test getting statistics"""
        orchestrator = OrchestratorService(temp_config_file)
        orchestrator.load_config()
        
        # Create mock publisher and subscriber
        mock_pub = Mock()
        mock_pub.get_stats = Mock(return_value={'total_events': 100})
        
        mock_sub = Mock()
        mock_sub.get_stats = Mock(return_value={'total_received': 50})
        
        orchestrator.publishers = {'test_pub': mock_pub}
        orchestrator.subscribers = {'test_sub': mock_sub}
        orchestrator._running = True
        
        stats = orchestrator.get_stats()
        
        assert stats['orchestrator']['running'] is True
        assert stats['orchestrator']['publishers_count'] == 1
        assert stats['orchestrator']['subscribers_count'] == 1
        assert stats['publishers']['test_pub']['total_events'] == 100
        assert stats['subscribers']['test_sub']['total_received'] == 50
    
    @pytest.mark.asyncio
    async def test_disabled_publisher_not_created(self, temp_config_file, sample_config):
        """Test that disabled publishers are not created"""
        # Modify config to disable publisher
        sample_config['publishers'][0]['enabled'] = False
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config, f)
            temp_file = f.name
        
        orchestrator = OrchestratorService(temp_file)
        orchestrator.load_config()
        orchestrator._create_serializer()
        orchestrator._create_broker()
        orchestrator._create_dlq()
        
        publishers = orchestrator._create_publishers()
        
        assert len(publishers) == 0
    
    @pytest.mark.asyncio
    async def test_disabled_subscriber_not_created(self, temp_config_file, sample_config):
        """Test that disabled subscribers are not created"""
        # Modify config to disable subscriber
        sample_config['subscribers'][0]['enabled'] = False
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_config, f)
            temp_file = f.name
        
        orchestrator = OrchestratorService(temp_file)
        orchestrator.load_config()
        orchestrator._create_serializer()
        orchestrator._create_broker()
        orchestrator._create_dlq()
        
        subscribers = orchestrator._create_subscribers()
        
        assert len(subscribers) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
