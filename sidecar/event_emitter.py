"""
Event Emitter - Plugin API for emitting events back to Rust/UI

This module provides the EventEmitter class that plugins use to send
events back to the Tauri application through the WebSocket connection.
"""

import time
from typing import Any, Literal, Dict, Optional


class EventEmitter:
    """
    API for plugins to emit events back to the UI.
    
    Usage in plugins:
        emitter.notify("Task complete!")
        emitter.progress(75, "Processing...")
        emitter.global_event("VAULT_SYNC", {"vault_id": "123"})
    """
    
    def __init__(self, websocket_server):
        """
        Initialize EventEmitter.
        
        Args:
            websocket_server: WebSocketServer instance for sending messages
        """
        self.ws_server = websocket_server
        self._id_counter = 0
    
    def emit(
        self,
        event_type: str,
        data: Dict[str, Any],
        scope: Literal["window", "global", "vault"] = "window",
    ) -> None:
        """
        Emit a generic event.
        
        Args:
            event_type: Type of event (e.g., "NOTIFY", "UPDATE_STATE")
            data: Event payload
            scope: Routing scope (window, global, vault)
        """
        message = {
            "jsonrpc": "2.0",
            "method": "trigger_event",
            "params": {
                "event_type": event_type,
                "scope": scope,
                "data": data,
                "timestamp": time.time(),
            },
            "id": self._next_id(),
        }
        
        # Send via WebSocket
        self.ws_server.send_to_rust(message)
    
    def notify(self, message: str, severity: str = "info") -> None:
        """
        Show notification in current window.
        
        Args:
            message: Notification message
            severity: Severity level (info, success, warning, error)
        """
        self.emit("NOTIFY", {"message": message, "severity": severity})
    
    def progress(self, percent: int, status: str) -> None:
        """
        Update progress bar.
        
        Args:
            percent: Progress percentage (0-100)
            status: Status message
        """
        self.emit("PROGRESS", {"percent": percent, "status": status})
    
    def update_state(self, key: str, value: Any) -> None:
        """
        Update vault-specific UI state.
        
        Args:
            key: State key
            value: State value
        """
        self.emit("UPDATE_STATE", {"key": key, "value": value})
    
    def global_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Emit event to all windows.
        
        Args:
            event_type: Type of global event
            data: Event data
        """
        self.emit(event_type, data, scope="global")
    
    def vault_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Emit event to all windows with same vault.
        
        Args:
            event_type: Type of vault event
            data: Event data
        """
        self.emit(event_type, data, scope="vault")
    
    def _next_id(self) -> str:
        """Generate next event ID."""
        self._id_counter += 1
        return f"evt_{self._id_counter}"
