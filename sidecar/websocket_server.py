"""
WebSocket Server - Bi-directional communication with Rust

Handles WebSocket connections from the Tauri application and
manages command/event exchange.
"""

import asyncio
import json
import websockets
from typing import Optional, Dict, Any
import traceback


class WebSocketServer:
    """WebSocket server for bi-directional communication with Rust."""
    
    def __init__(self, port: int):
        """
        Initialize WebSocket server.
        
        Args:
            port: Port to listen on
        """
        self.port = port
        self.connection: Optional[websockets.WebSocketServerProtocol] = None
        self.message_queue = asyncio.Queue()
        self.command_handlers = {}
        self.pending_messages = []  # Messages queued before event loop starts
    
    def register_handler(self, method: str, handler):
        """
        Register a command handler.
        
        Args:
            method: Command method name
            handler: Async function to handle the command
        """
        self.command_handlers[method] = handler
    
    async def start(self):
        """Start the WebSocket server."""
        print(f"Starting WebSocket server on port {self.port}")
        
        async with websockets.serve(
            self.handle_connection,
            "localhost",
            self.port
        ):
            print(f"WebSocket server listening on ws://localhost:{self.port}")
            
            # Send any pending messages
            if self.pending_messages and self.connection:
                for msg in self.pending_messages:
                    await self.send(msg)
                self.pending_messages.clear()
            
            await asyncio.Future()  # Run forever
    
    async def handle_connection(self, websocket):
        """
        Handle incoming WebSocket connection.
        
        Args:
            websocket: WebSocket connection
        """
        print(f"Client connected from {websocket.remote_address}")
        self.connection = websocket
        
        try:
            async for message in websocket:
                await self.handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            print("Client disconnected")
        except Exception as e:
            print(f"WebSocket error: {e}")
            traceback.print_exc()
        finally:
            self.connection = None
    
    async def handle_message(self, message: str):
        """
        Handle incoming message from Rust.
        
        Args:
            message: JSON-RPC message string
        """
        try:
            data = json.loads(message)
            
            if "method" not in data:
                print(f"Invalid message: {data}")
                return
            
            method = data["method"]
            params = data.get("params", {})
            msg_id = data.get("id")
            
            print(f"Received command: {method}")
            
            # Call handler if registered
            if method in self.command_handlers:
                try:
                    result = await self.command_handlers[method](params)
                    
                    # Send response
                    response = {
                        "jsonrpc": "2.0",
                        "result": result,
                        "id": msg_id,
                    }
                    await self.send(response)
                    
                except Exception as e:
                    print(f"Handler error: {e}")
                    traceback.print_exc()
                    
                    # Send error response
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32603,
                            "message": str(e),
                        },
                        "id": msg_id,
                    }
                    await self.send(error_response)
            else:
                print(f"No handler for method: {method}")
        
        except json.JSONDecodeError:
            print(f"Invalid JSON: {message}")
        except Exception as e:
            print(f"Message handling error: {e}")
            traceback.print_exc()
    
    async def send(self, data: Dict[str, Any]):
        """
        Send message to Rust.
        
        Args:
            data: Message data (will be JSON encoded)
        """
        if self.connection:
            try:
                message = json.dumps(data)
                await self.connection.send(message)
            except Exception as e:
                print(f"Send error: {e}")
    
    def send_to_rust(self, data: Dict[str, Any]):
        """
        Send data to Rust (safe to call from sync or async context).
        
        Args:
            data: Dictionary to send as JSON-RPC message
        """
        # Try to create task if event loop is running
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(self.send(data))
        except RuntimeError:
            # No running loop yet - queue message to send when connected
            print(f"Queuing message (no event loop): {data.get('method', 'unknown')}")
            self.pending_messages.append(data)
