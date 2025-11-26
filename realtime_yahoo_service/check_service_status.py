"""
Service Status Checker
======================

Check if the Real-Time Yahoo Finance Service is running and view its status.
"""

import sys
import socket
import json
from datetime import datetime
import urllib.request
import urllib.error

def check_port(host='localhost', port=8765):
    """Check if WebSocket port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        return False

def check_service_health():
    """Check service health"""
    try:
        # Try to connect to WebSocket
        ws_running = check_port('localhost', 8765)
        return ws_running
    except Exception as e:
        return False

def print_banner():
    """Print banner"""
    print("=" * 60)
    print("Real-Time Yahoo Finance Service - Status Check")
    print("=" * 60)
    print()

def print_status():
    """Print service status"""
    print_banner()
    
    # Check WebSocket port
    print("🔍 Checking WebSocket Server...")
    ws_running = check_port('localhost', 8765)
    
    if ws_running:
        print("   ✅ WebSocket server is RUNNING on ws://localhost:8765")
        print("   📊 Service appears to be operational")
        print()
        print("📌 How to visualize:")
        print("   1. Open: realtime_yahoo_service\\examples\\test_websocket_client.html")
        print("   2. Click 'Connect' button")
        print("   3. Watch real-time market data streaming!")
        print()
        print("📊 Or connect manually:")
        print("   wscat -c ws://localhost:8765")
        print()
    else:
        print("   ❌ WebSocket server is NOT running")
        print()
        print("🚀 To start the service:")
        print("   Option 1: Double-click 'start_service.bat'")
        print("   Option 2: Run command:")
        print("   cd D:\\MyProjects\\StockScreeer\\realtime_yahoo_service")
        print("   python main.py --config config\\local_test.yaml")
        print()
    
    # Check log file
    print("📄 Checking logs...")
    try:
        with open('test_service.log', 'r') as f:
            lines = f.readlines()
            if lines:
                print(f"   ✅ Log file exists: {len(lines)} lines")
                print()
                print("   Last 5 log entries:")
                for line in lines[-5:]:
                    print(f"   {line.rstrip()}")
            else:
                print("   ⚠️  Log file is empty")
    except FileNotFoundError:
        print("   ⚠️  Log file not found (service not started yet)")
    except Exception as e:
        print(f"   ⚠️  Error reading logs: {e}")
    
    print()
    print("=" * 60)
    
    # Return status code
    return 0 if ws_running else 1

if __name__ == "__main__":
    sys.exit(print_status())
