"""Test script to see what data is actually being sent via WebSocket"""
import asyncio
import websockets
import json

async def test_connection():
    uri = "ws://localhost:8765"
    print(f"Connecting to {uri}...")
    
    async with websockets.connect(uri) as websocket:
        print("Connected! Waiting for messages...\n")
        
        # Receive first 5 messages
        for i in range(5):
            try:
                message = await websocket.recv()
                data = json.loads(message)
                print(f"Message {i+1}:")
                print(json.dumps(data, indent=2))
                print("-" * 80)
            except Exception as e:
                print(f"Error: {e}")
                break

if __name__ == "__main__":
    asyncio.run(test_connection())
