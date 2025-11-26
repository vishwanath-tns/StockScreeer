"""
WebSocket Server - Bridge Redis events to WebSocket clients
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional
from datetime import datetime
import websockets
from websockets.server import WebSocketServerProtocol

from subscribers.base_subscriber import BaseSubscriber


logger = logging.getLogger(__name__)


class WebSocketServer(BaseSubscriber):
    """
    WebSocket server that bridges Redis events to external WebSocket clients.
    
    Features:
    - Multiple concurrent client connections
    - Per-client channel subscriptions
    - Heartbeat/ping-pong monitoring
    - Authentication support (optional)
    - Automatic reconnection handling
    - Message broadcasting to subscribed clients
    """
    
    def __init__(
        self,
        subscriber_id: str,
        broker,
        serializer,
        host: str = '0.0.0.0',
        port: int = 8765,
        channels: Optional[list] = None,
        heartbeat_interval: float = 30.0,
        auth_token: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize WebSocket server.
        
        Args:
            subscriber_id: Unique identifier for this server
            broker: Message broker instance
            serializer: Serializer instance
            host: WebSocket server host (default: 0.0.0.0)
            port: WebSocket server port (default: 8765)
            channels: Default channels to subscribe to (default: ['market.candle', 'market.breadth', 'market.trend', 'market.status'])
            heartbeat_interval: Seconds between heartbeat pings
            auth_token: Optional authentication token
            **kwargs: Additional arguments for BaseSubscriber
        """
        default_channels = channels or [
            'market.candle',
            'market.breadth', 
            'market.trend',
            'market.status'
        ]
        
        super().__init__(
            subscriber_id=subscriber_id,
            broker=broker,
            serializer=serializer,
            channels=default_channels,
            **kwargs
        )
        
        self._host = host
        self._port = port
        self._heartbeat_interval = heartbeat_interval
        self._auth_token = auth_token
        
        # Connected clients and their subscriptions
        # {websocket: set(channels)}
        self._clients: Dict[WebSocketServerProtocol, Set[str]] = {}
        
        # WebSocket server instance
        self._ws_server = None
        
        # Heartbeat task
        self._heartbeat_task: Optional[asyncio.Task] = None
        
        logger.info(
            f"WebSocketServer initialized: {host}:{port}, "
            f"default_channels={default_channels}, heartbeat={heartbeat_interval}s"
        )
    
    async def start(self):
        """Start the WebSocket server and subscriber"""
        await super().start()
        
        # Start WebSocket server
        self._ws_server = await websockets.serve(
            self._handle_client,
            self._host,
            self._port,
            ping_interval=20,
            ping_timeout=10,
        )
        
        # Start heartbeat task
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        logger.info(f"WebSocket server started on ws://{self._host}:{self._port}")
    
    async def stop(self):
        """Stop the WebSocket server and subscriber"""
        # Stop heartbeat
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Close all client connections
        if self._clients:
            close_tasks = [ws.close() for ws in self._clients.keys()]
            await asyncio.gather(*close_tasks, return_exceptions=True)
            self._clients.clear()
        
        # Stop WebSocket server
        if self._ws_server:
            self._ws_server.close()
            await self._ws_server.wait_closed()
        
        await super().stop()
        logger.info("WebSocket server stopped")
    
    async def on_message(self, channel: str, data: bytes):
        """
        Process incoming messages from broker and broadcast to subscribed clients.
        
        Args:
            channel: Channel name
            data: Serialized message data (bytes) or already deserialized dict
        """
        try:
            # Deserialize message (handle both bytes and already-deserialized dict)
            if isinstance(data, bytes):
                message = self.serializer.deserialize(data)
            elif isinstance(data, dict):
                # Already deserialized (in-memory broker optimization)
                message = data
            else:
                # Unknown type, try to deserialize
                message = self.serializer.deserialize(data)
            
            # Create WebSocket message
            ws_message = {
                'channel': channel,
                'data': message,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Broadcast to subscribed clients
            await self._broadcast(channel, ws_message)
            
            self._stats['total_processed'] += 1
            self._stats['messages_broadcast'] = self._stats.get('messages_broadcast', 0) + 1
            
        except Exception as e:
            logger.error(f"Error processing message on {channel}: {e}")
            self._stats['total_errors'] = self._stats.get('total_errors', 0) + 1
    
    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """
        Handle a new WebSocket client connection.
        
        Args:
            websocket: WebSocket connection
            path: Request path
        """
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"New client connected: {client_id}")
        
        try:
            # Authentication (if enabled)
            if self._auth_token:
                auth_msg = await websocket.recv()
                auth_data = json.loads(auth_msg)
                
                if auth_data.get('type') != 'auth' or auth_data.get('token') != self._auth_token:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'Authentication failed'
                    }))
                    await websocket.close()
                    return
                
                await websocket.send(json.dumps({
                    'type': 'auth_success',
                    'message': 'Authenticated successfully'
                }))
            
            # Initialize client with default channels
            self._clients[websocket] = set(self.channels)
            
            # Send welcome message
            await websocket.send(json.dumps({
                'type': 'welcome',
                'server_id': self.subscriber_id,
                'subscribed_channels': list(self.channels),
                'timestamp': datetime.utcnow().isoformat()
            }))
            
            # Handle client messages
            async for message in websocket:
                await self._handle_client_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            # Remove client
            if websocket in self._clients:
                del self._clients[websocket]
            
            self._stats['total_disconnections'] = self._stats.get('total_disconnections', 0) + 1
    
    async def _handle_client_message(self, websocket: WebSocketServerProtocol, message: str):
        """
        Handle messages from client (subscribe, unsubscribe, ping).
        
        Args:
            websocket: Client WebSocket connection
            message: JSON message from client
        """
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'subscribe':
                # Subscribe to channel
                channel = data.get('channel')
                if channel and websocket in self._clients:
                    self._clients[websocket].add(channel)
                    await websocket.send(json.dumps({
                        'type': 'subscribed',
                        'channel': channel,
                        'timestamp': datetime.utcnow().isoformat()
                    }))
                    logger.debug(f"Client subscribed to: {channel}")
            
            elif msg_type == 'unsubscribe':
                # Unsubscribe from channel
                channel = data.get('channel')
                if channel and websocket in self._clients:
                    self._clients[websocket].discard(channel)
                    await websocket.send(json.dumps({
                        'type': 'unsubscribed',
                        'channel': channel,
                        'timestamp': datetime.utcnow().isoformat()
                    }))
                    logger.debug(f"Client unsubscribed from: {channel}")
            
            elif msg_type == 'ping':
                # Respond to ping
                await websocket.send(json.dumps({
                    'type': 'pong',
                    'timestamp': datetime.utcnow().isoformat()
                }))
            
            elif msg_type == 'get_channels':
                # Return list of subscribed channels
                if websocket in self._clients:
                    await websocket.send(json.dumps({
                        'type': 'channels',
                        'channels': list(self._clients[websocket]),
                        'timestamp': datetime.utcnow().isoformat()
                    }))
            
            else:
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': f'Unknown message type: {msg_type}'
                }))
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from client: {e}")
            await websocket.send(json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
        except Exception as e:
            logger.error(f"Error handling client message: {e}")
    
    async def _broadcast(self, channel: str, message: dict):
        """
        Broadcast message to all clients subscribed to the channel.
        
        Args:
            channel: Channel name
            message: Message to broadcast
        """
        if not self._clients:
            return
        
        # Find subscribed clients
        subscribed_clients = [
            ws for ws, channels in self._clients.items()
            if channel in channels
        ]
        
        if not subscribed_clients:
            return
        
        # Serialize message once
        json_message = json.dumps(message)
        
        # Send to all subscribed clients
        send_tasks = [
            self._send_to_client(ws, json_message)
            for ws in subscribed_clients
        ]
        
        results = await asyncio.gather(*send_tasks, return_exceptions=True)
        
        # Count successful sends
        successful = sum(1 for r in results if r is True)
        logger.debug(f"Broadcast to {successful}/{len(subscribed_clients)} clients on {channel}")
    
    async def _send_to_client(self, websocket: WebSocketServerProtocol, message: str) -> bool:
        """
        Send message to a single client.
        
        Args:
            websocket: Client WebSocket connection
            message: JSON message string
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            await websocket.send(message)
            return True
        except websockets.exceptions.ConnectionClosed:
            # Client disconnected, will be cleaned up
            return False
        except Exception as e:
            logger.error(f"Error sending to client: {e}")
            return False
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat messages to all clients"""
        while self._running:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                
                if not self._clients:
                    continue
                
                heartbeat_msg = json.dumps({
                    'type': 'heartbeat',
                    'timestamp': datetime.utcnow().isoformat(),
                    'active_clients': len(self._clients)
                })
                
                send_tasks = [
                    self._send_to_client(ws, heartbeat_msg)
                    for ws in self._clients.keys()
                ]
                
                await asyncio.gather(*send_tasks, return_exceptions=True)
                
                logger.debug(f"Heartbeat sent to {len(self._clients)} clients")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
    
    def get_stats(self) -> dict:
        """Get WebSocket server statistics"""
        stats = super().get_stats()
        stats.update({
            'active_clients': len(self._clients),
            'messages_broadcast': self._stats.get('messages_broadcast', 0),
            'total_disconnections': self._stats.get('total_disconnections', 0),
            'host': self._host,
            'port': self._port,
        })
        return stats
