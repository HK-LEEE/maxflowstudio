#!/usr/bin/env python3
"""
Simple WebSocket test client for FlowStudio
"""

import asyncio
import websockets
import json

async def test_websocket():
    # Use the access token we got from login
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyMWEyYWFhNy00NDRhLTQwMzgtYmRhMy1kOGJmMmM0ZWYxNjIiLCJ1c2VyX2lkIjoiMjFhMmFhYTctNDQ0YS00MDM4LWJkYTMtZDhiZjJjNGVmMTYyIiwiZW1haWwiOiJhZG1pbkB0ZXN0LmNvbSIsImlzX2FkbWluIjp0cnVlLCJncm91cF9pZCI6IjEiLCJncm91cF9uYW1lIjoiXHVhYzFjXHViYzFjXHVkMzAwIiwicm9sZV9pZCI6IjEiLCJyb2xlX25hbWUiOiJhZG1pbiIsImV4cCI6MTc1MDkyNDUxNCwidHlwZSI6ImFjY2VzcyIsImlhdCI6MTc1MDkyMjcxNH0.xQ6a3fivHs9iQ4j10QvjsziOFFeUzZypAMCoqXchlLY"
    flow_id = "2f38814d-0b7e-4b1f-8b9c-891171522b7f"  # tmpman flow with OLLAMA node
    
    url = f"ws://localhost:8005/ws/flow-test/{flow_id}?token={token}"
    
    try:
        print(f"Connecting to: {url}")
        async with websockets.connect(url) as websocket:
            print("✅ Connected successfully!")
            
            # Wait for initial messages
            try:
                message_count = 0
                while message_count < 20:  # Receive up to 20 messages
                    message = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                    data = json.loads(message)
                    print(f"📨 Received: {data}")
                    
                    if data.get("type") == "connected":
                        print("🔗 Connection established")
                        # Send a test flow input
                        test_message = {
                            "type": "flow_input",
                            "message": "Hello, this is a test message!",
                            "timestamp": "2025-06-26T03:50:00Z"
                        }
                        await websocket.send(json.dumps(test_message))
                        print(f"📤 Sent: {test_message}")
                        
                    elif data.get("type") == "input_required":
                        print("🔢 Input required, sending user input...")
                        # Send user input to the input node
                        user_input = {
                            "type": "user_input",
                            "node_id": data.get("node_id"),
                            "input": {"value": "hi"}
                        }
                        await websocket.send(json.dumps(user_input))
                        print(f"📤 Sent: {user_input}")
                        
                    elif data.get("type") == "node_complete":
                        print(f"✅ Node completed: {data.get('node_id')}")
                        
                    elif data.get("type") == "node_output":
                        print(f"📄 Node output: {data.get('output')}")
                    
                    message_count += 1
                        
            except asyncio.TimeoutError:
                print("⏰ Timeout waiting for messages")
            except Exception as e:
                print(f"❌ Error: {e}")
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())