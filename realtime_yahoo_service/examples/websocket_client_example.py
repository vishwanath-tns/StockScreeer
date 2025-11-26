"""
WebSocket Client Example
========================

Simple Python client to connect to the WebSocket server and receive real-time data.

Usage:
    python examples/websocket_client_example.py
"""

import asyncio
import json
import websockets


async def connect_and_subscribe():
    """Connect to WebSocket server and subscribe to channels"""
    
    uri = "ws://localhost:8765"
    
    async with websockets.connect(uri) as websocket:
        print(f"Connected to {uri}")
        
        # Receive welcome message
        welcome = await websocket.recv()
        print(f"Welcome: {welcome}\n")
        
        # Subscribe to additional channel
        subscribe_msg = json.dumps({
            'type': 'subscribe',
            'channel': 'market.trend'
        })
        await websocket.send(subscribe_msg)
        print(f"Sent: {subscribe_msg}")
        
        # Receive subscription confirmation
        response = await websocket.recv()
        print(f"Response: {response}\n")
        
        # Get current channels
        get_channels_msg = json.dumps({'type': 'get_channels'})
        await websocket.send(get_channels_msg)
        
        response = await websocket.recv()
        print(f"Current channels: {response}\n")
        
        # Listen for messages
        print("Listening for messages (Ctrl+C to stop)...\n")
        
        message_count = 0
        try:
            async for message in websocket:
                data = json.loads(message)
                message_type = data.get('type')
                
                if message_type == 'heartbeat':
                    print(f"❤️  Heartbeat - {data.get('active_clients')} active clients")
                
                elif message_type == 'data':
                    channel = data.get('channel')
                    payload = data.get('data')
                    timestamp = data.get('timestamp')
                    
                    print(f"📊 [{channel}] @ {timestamp}")
                    print(f"   Data: {payload}")
                    
                    message_count += 1
                    
                    if message_count % 10 == 0:
                        # Send ping every 10 messages
                        ping_msg = json.dumps({'type': 'ping'})
                        await websocket.send(ping_msg)
                        print("   Sent ping")
                
                else:
                    print(f"📨 {message_type}: {message}")
                
                print()  # Empty line for readability
                
        except KeyboardInterrupt:
            print("\nClosing connection...")


async def main():
    """Main function"""
    try:
        await connect_and_subscribe()
    except websockets.exceptions.ConnectionRefusedError:
        print("❌ Connection refused. Make sure the WebSocket server is running.")
        print("   Run: python examples/websocket_demo.py")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == '__main__':
    asyncio.run(main())
