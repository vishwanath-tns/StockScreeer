"""
WebSocket Server Demo
=====================

Example of running the WebSocket server with the real-time Yahoo Finance service.

Usage:
    python examples/websocket_demo.py
"""

import asyncio
import logging
from datetime import datetime

from serialization import JSONSerializer
from redis_broker import InMemoryBroker
from clients.websocket_server import WebSocketServer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Run WebSocket server demo"""
    
    # Create broker and serializer
    broker = InMemoryBroker()
    serializer = JSONSerializer()
    
    # Create WebSocket server
    ws_server = WebSocketServer(
        subscriber_id='demo-ws-server',
        broker=broker,
        serializer=serializer,
        host='0.0.0.0',
        port=8765,
        channels=['market.candle', 'market.breadth', 'market.trend', 'market.status'],
        heartbeat_interval=30.0,
    )
    
    try:
        # Start server
        logger.info("Starting WebSocket server...")
        await ws_server.start()
        
        logger.info("WebSocket server running on ws://0.0.0.0:8765")
        logger.info("Press Ctrl+C to stop")
        logger.info("\nClients can connect using:")
        logger.info("  JavaScript: const ws = new WebSocket('ws://localhost:8765');")
        logger.info("  Python: websockets.connect('ws://localhost:8765')")
        logger.info("\nAvailable channels: market.candle, market.breadth, market.trend, market.status")
        
        # Simulate publishing some test data every 5 seconds
        while True:
            await asyncio.sleep(5)
            
            # Publish test candle data
            test_candle = {
                'symbol': 'AAPL',
                'trade_date': datetime.now().strftime('%Y-%m-%d'),
                'timestamp': int(datetime.now().timestamp()),
                'close_price': 150.0,
                'volume': 1000000,
                'data_source': 'demo'
            }
            
            serialized = serializer.serialize(test_candle)
            await broker.publish('market.candle', serialized)
            
            logger.info(f"Published test data. Active clients: {len(ws_server._clients)}")
            
            # Show stats
            stats = ws_server.get_stats()
            logger.info(f"Stats: {stats['messages_broadcast']} messages broadcast to {stats['active_clients']} clients")
    
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
    finally:
        await ws_server.stop()
        logger.info("WebSocket server stopped")


if __name__ == '__main__':
    asyncio.run(main())
