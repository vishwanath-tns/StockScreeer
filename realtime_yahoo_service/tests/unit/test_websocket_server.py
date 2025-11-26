"""
Unit tests for WebSocket server
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

import websockets

from clients.websocket_server import WebSocketServer


class TestWebSocketServer:
    """Test WebSocket server"""
    
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
        serializer.deserialize = Mock(return_value={'test': 'data'})
        return serializer
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_broker, mock_serializer):
        """Test WebSocket server initialization"""
        server = WebSocketServer(
            subscriber_id='ws-server-test',
            broker=mock_broker,
            serializer=mock_serializer,
            host='localhost',
            port=8765,
            channels=['market.candle', 'market.breadth'],
        )
        
        assert server.subscriber_id == 'ws-server-test'
        assert server._host == 'localhost'
        assert server._port == 8765
        assert 'market.candle' in server.channels
        assert 'market.breadth' in server.channels
        assert len(server._clients) == 0
    
    @pytest.mark.asyncio
    async def test_default_channels(self, mock_broker, mock_serializer):
        """Test default channels are set correctly"""
        server = WebSocketServer(
            subscriber_id='ws-server-test',
            broker=mock_broker,
            serializer=mock_serializer,
        )
        
        # Should have default channels
        assert 'market.candle' in server.channels
        assert 'market.breadth' in server.channels
        assert 'market.trend' in server.channels
        assert 'market.status' in server.channels
    
    @pytest.mark.asyncio
    async def test_broadcast_message(self, mock_broker, mock_serializer):
        """Test broadcasting message to clients"""
        server = WebSocketServer(
            subscriber_id='ws-server-test',
            broker=mock_broker,
            serializer=mock_serializer,
        )
        
        # Create mock clients
        client1 = AsyncMock()
        client1.send = AsyncMock()
        client2 = AsyncMock()
        client2.send = AsyncMock()
        
        # Add clients with subscriptions
        server._clients[client1] = {'market.candle', 'market.breadth'}
        server._clients[client2] = {'market.breadth'}
        
        # Broadcast to market.breadth
        message = {'type': 'data', 'value': 123}
        await server._broadcast('market.breadth', message)
        
        # Both clients should receive
        assert client1.send.called
        assert client2.send.called
        
        # Reset mocks
        client1.send.reset_mock()
        client2.send.reset_mock()
        
        # Broadcast to market.candle
        await server._broadcast('market.candle', message)
        
        # Only client1 should receive
        assert client1.send.called
        assert not client2.send.called
    
    @pytest.mark.asyncio
    async def test_on_message_processing(self, mock_broker, mock_serializer):
        """Test processing messages from broker"""
        server = WebSocketServer(
            subscriber_id='ws-server-test',
            broker=mock_broker,
            serializer=mock_serializer,
        )
        
        # Mock broadcast
        server._broadcast = AsyncMock()
        
        # Process message
        test_data = b'{"symbol": "AAPL", "price": 150.0}'
        mock_serializer.deserialize.return_value = {'symbol': 'AAPL', 'price': 150.0}
        
        await server.on_message('market.candle', test_data)
        
        # Should deserialize and broadcast
        assert mock_serializer.deserialize.called
        assert server._broadcast.called
        assert server._stats['total_processed'] == 1
        assert server._stats['messages_broadcast'] == 1
    
    @pytest.mark.asyncio
    async def test_handle_subscribe_message(self, mock_broker, mock_serializer):
        """Test handling client subscribe message"""
        server = WebSocketServer(
            subscriber_id='ws-server-test',
            broker=mock_broker,
            serializer=mock_serializer,
        )
        
        # Create mock client
        client = AsyncMock()
        client.send = AsyncMock()
        server._clients[client] = {'market.candle'}
        
        # Send subscribe message
        subscribe_msg = json.dumps({
            'type': 'subscribe',
            'channel': 'market.breadth'
        })
        
        await server._handle_client_message(client, subscribe_msg)
        
        # Should be subscribed
        assert 'market.breadth' in server._clients[client]
        assert client.send.called
        
        # Check response
        call_args = client.send.call_args[0][0]
        response = json.loads(call_args)
        assert response['type'] == 'subscribed'
        assert response['channel'] == 'market.breadth'
    
    @pytest.mark.asyncio
    async def test_handle_unsubscribe_message(self, mock_broker, mock_serializer):
        """Test handling client unsubscribe message"""
        server = WebSocketServer(
            subscriber_id='ws-server-test',
            broker=mock_broker,
            serializer=mock_serializer,
        )
        
        # Create mock client
        client = AsyncMock()
        client.send = AsyncMock()
        server._clients[client] = {'market.candle', 'market.breadth'}
        
        # Send unsubscribe message
        unsubscribe_msg = json.dumps({
            'type': 'unsubscribe',
            'channel': 'market.candle'
        })
        
        await server._handle_client_message(client, unsubscribe_msg)
        
        # Should be unsubscribed
        assert 'market.candle' not in server._clients[client]
        assert 'market.breadth' in server._clients[client]
        assert client.send.called
        
        # Check response
        call_args = client.send.call_args[0][0]
        response = json.loads(call_args)
        assert response['type'] == 'unsubscribed'
    
    @pytest.mark.asyncio
    async def test_handle_ping_message(self, mock_broker, mock_serializer):
        """Test handling client ping message"""
        server = WebSocketServer(
            subscriber_id='ws-server-test',
            broker=mock_broker,
            serializer=mock_serializer,
        )
        
        # Create mock client
        client = AsyncMock()
        client.send = AsyncMock()
        server._clients[client] = {'market.candle'}
        
        # Send ping message
        ping_msg = json.dumps({'type': 'ping'})
        
        await server._handle_client_message(client, ping_msg)
        
        # Should respond with pong
        assert client.send.called
        call_args = client.send.call_args[0][0]
        response = json.loads(call_args)
        assert response['type'] == 'pong'
    
    @pytest.mark.asyncio
    async def test_handle_get_channels_message(self, mock_broker, mock_serializer):
        """Test handling get channels request"""
        server = WebSocketServer(
            subscriber_id='ws-server-test',
            broker=mock_broker,
            serializer=mock_serializer,
        )
        
        # Create mock client
        client = AsyncMock()
        client.send = AsyncMock()
        server._clients[client] = {'market.candle', 'market.breadth'}
        
        # Send get_channels message
        get_channels_msg = json.dumps({'type': 'get_channels'})
        
        await server._handle_client_message(client, get_channels_msg)
        
        # Should return channels
        assert client.send.called
        call_args = client.send.call_args[0][0]
        response = json.loads(call_args)
        assert response['type'] == 'channels'
        assert set(response['channels']) == {'market.candle', 'market.breadth'}
    
    @pytest.mark.asyncio
    async def test_send_to_client_success(self, mock_broker, mock_serializer):
        """Test sending message to client successfully"""
        server = WebSocketServer(
            subscriber_id='ws-server-test',
            broker=mock_broker,
            serializer=mock_serializer,
        )
        
        # Create mock client
        client = AsyncMock()
        client.send = AsyncMock()
        
        # Send message
        result = await server._send_to_client(client, '{"test": "data"}')
        
        assert result is True
        assert client.send.called
    
    @pytest.mark.asyncio
    async def test_send_to_client_connection_closed(self, mock_broker, mock_serializer):
        """Test handling connection closed during send"""
        server = WebSocketServer(
            subscriber_id='ws-server-test',
            broker=mock_broker,
            serializer=mock_serializer,
        )
        
        # Create mock client that raises ConnectionClosed
        client = AsyncMock()
        client.send = AsyncMock(side_effect=websockets.exceptions.ConnectionClosed(None, None))
        
        # Send message
        result = await server._send_to_client(client, '{"test": "data"}')
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_stats(self, mock_broker, mock_serializer):
        """Test getting server statistics"""
        server = WebSocketServer(
            subscriber_id='ws-server-test',
            broker=mock_broker,
            serializer=mock_serializer,
            host='localhost',
            port=9999,
        )
        
        # Add some mock clients
        client1 = AsyncMock()
        client2 = AsyncMock()
        server._clients[client1] = {'market.candle'}
        server._clients[client2] = {'market.breadth'}
        
        # Set some stats
        server._stats['messages_broadcast'] = 100
        server._stats['total_disconnections'] = 5
        
        stats = server.get_stats()
        
        assert stats['active_clients'] == 2
        assert stats['messages_broadcast'] == 100
        assert stats['total_disconnections'] == 5
        assert stats['host'] == 'localhost'
        assert stats['port'] == 9999
    
    @pytest.mark.asyncio
    async def test_invalid_json_handling(self, mock_broker, mock_serializer):
        """Test handling invalid JSON from client"""
        server = WebSocketServer(
            subscriber_id='ws-server-test',
            broker=mock_broker,
            serializer=mock_serializer,
        )
        
        # Create mock client
        client = AsyncMock()
        client.send = AsyncMock()
        server._clients[client] = {'market.candle'}
        
        # Send invalid JSON
        invalid_msg = "not valid json{{"
        
        await server._handle_client_message(client, invalid_msg)
        
        # Should send error response
        assert client.send.called
        call_args = client.send.call_args[0][0]
        response = json.loads(call_args)
        assert response['type'] == 'error'
        assert 'Invalid JSON' in response['message']
    
    @pytest.mark.asyncio
    async def test_unknown_message_type(self, mock_broker, mock_serializer):
        """Test handling unknown message type"""
        server = WebSocketServer(
            subscriber_id='ws-server-test',
            broker=mock_broker,
            serializer=mock_serializer,
        )
        
        # Create mock client
        client = AsyncMock()
        client.send = AsyncMock()
        server._clients[client] = {'market.candle'}
        
        # Send unknown message type
        unknown_msg = json.dumps({'type': 'unknown_command'})
        
        await server._handle_client_message(client, unknown_msg)
        
        # Should send error response
        assert client.send.called
        call_args = client.send.call_args[0][0]
        response = json.loads(call_args)
        assert response['type'] == 'error'
        assert 'Unknown message type' in response['message']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
