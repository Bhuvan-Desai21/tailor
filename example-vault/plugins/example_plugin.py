"""
Example Plugin - Demonstrates plugin capabilities

This plugin shows how to:
- Receive EventEmitter in __init__
- Use on_tick hook for periodic tasks
- Emit notifications and events
"""

import asyncio
from datetime import datetime


class Plugin:
    """Example plugin that demonstrates event emission."""
    
    def __init__(self, emitter):
        """
        Initialize plugin with EventEmitter.
        
        Args:
            emitter: EventEmitter instance for sending events
        """
        self.emitter = emitter
        self.name = "example_plugin"
        self.tick_count = 0
        
        print(f"[{self.name}] Plugin initialized")
        
        # Send initialization notification
        self.emitter.notify(
            f"Plugin '{self.name}' loaded successfully!",
            severity="success"
        )
    
    async def on_tick(self, emitter):
        """
        Called every 5 seconds by VaultBrain.
        
        Args:
            emitter: EventEmitter instance
        """
        self.tick_count += 1
        current_time = datetime.now().strftime("%H:%M:%S")
        
        print(f"[{self.name}] Tick #{self.tick_count} at {current_time}")
        
        # Every 3 ticks (15 seconds), send a notification
        if self.tick_count % 3 == 0:
            emitter.notify(
                f"Heartbeat #{self.tick_count // 3} from {self.name}",
                severity="info"
            )
        
        # Update state
        emitter.update_state("tick_count", self.tick_count)
        emitter.update_state("last_tick", current_time)
    
    async def custom_action(self, **kwargs):
        """
        Custom action that can be called via execute_command.
        
        Args:
            **kwargs: Action parameters
        """
        print(f"[{self.name}] Custom action called with: {kwargs}")
        
        self.emitter.notify(
            "Custom action executed!",
            severity="success"
        )
        
        return {"status": "completed", "kwargs": kwargs}
