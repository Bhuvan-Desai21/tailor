"""
Vault Brain - LangGraph orchestrator for vault-specific AI operations

Manages plugins, memory, and LangGraph execution for a single vault.
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional
import importlib.util

from event_emitter import EventEmitter


class VaultBrain:
    """
    LangGraph orchestrator that manages vault-specific operations.
    
    Responsibilities:
    - Load vault-specific plugins
    - Initialize memory storage
    - Create isolated LangGraph instance
    - Run periodic tick loop for plugins
    """
    
    def __init__(self, vault_path: Path, emitter: EventEmitter, ws_server):
        """
        Initialize VaultBrain.
        
        Args:
            vault_path: Path to vault directory
            emitter: EventEmitter for plugins
            ws_server: WebSocket server instance
        """
        self.vault_path = vault_path
        self.emitter = emitter
        self.ws_server = ws_server
        self.plugins = {}
        self.memory = None
        self.graph = None
        
        # Load vault configuration
        self.config = self._load_config()
        
        # Initialize components
        self._init_memory()
        self._load_plugins()
        self._build_langgraph()
        self._register_commands()
        
        print(f"VaultBrain initialized for: {vault_path}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load vault configuration from .vault.json."""
        config_file = self.vault_path / ".vault.json"
        
        if config_file.exists():
            with open(config_file, "r") as f:
                return json.load(f)
        
        # Default configuration
        return {
            "id": str(self.vault_path),
            "name": self.vault_path.name,
            "version": "1.0.0",
            "plugins": {
                "enabled": [],
            }
        }
    
    def _init_memory(self):
        """Initialize memory storage."""
        memory_dir = self.vault_path / ".memory"
        memory_dir.mkdir(exist_ok=True)
        
        print(f"Memory directory: {memory_dir}")
        
        # In a full implementation, initialize a proper memory system
        # For now, just store the path
        self.memory = {
            "path": memory_dir,
            "conversations": [],
        }
    
    def _load_plugins(self):
        """Load and initialize vault-specific plugins."""
        plugins_dir = self.vault_path / "plugins"
        
        if not plugins_dir.exists():
            print("No plugins directory found")
            return
        
        # Discover Python files in plugins directory
        for plugin_file in plugins_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue
            
            try:
                plugin_name = plugin_file.stem
                print(f"Loading plugin: {plugin_name}")
                
                # Load plugin module
                spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Initialize plugin with emitter
                if hasattr(module, "Plugin"):
                    plugin = module.Plugin(emitter=self.emitter)
                    self.plugins[plugin_name] = plugin
                    print(f"Plugin loaded: {plugin_name}")
                else:
                    print(f"No Plugin class found in {plugin_name}")
            
            except Exception as e:
                print(f"Failed to load plugin {plugin_file.name}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"Loaded {len(self.plugins)} plugin(s)")
    
    def _build_langgraph(self):
        """Build LangGraph instance with vault configuration."""
        # In a full implementation, build a proper LangGraph
        # For now, create a placeholder
        self.graph = {
            "vault_id": self.config.get("id"),
            "nodes": [],
        }
        print("LangGraph initialized (placeholder)")
    
    def _register_commands(self):
        """Register command handlers with WebSocket server."""
        
        async def handle_chat(params: Dict[str, Any]) -> Dict[str, Any]:
            """Handle chat.send_message command."""
            message = params.get("message", "")
            print(f"Received chat message: {message}")
            
            # In a full implementation, process with LangGraph
            # For now, echo back
            return {
                "response": f"Echo: {message}",
                "status": "success",
            }
        
        async def handle_execute(params: Dict[str, Any]) -> Dict[str, Any]:
            """Handle generic execute command."""
            command = params.get("command", "")
            args = params.get("args", {})
            
            print(f"Executing command: {command} with args: {args}")
            
            # Call plugin if available
            plugin_name, method_name = command.split(".", 1) if "." in command else (command, "execute")
            
            if plugin_name in self.plugins:
                plugin = self.plugins[plugin_name]
                if hasattr(plugin, method_name):
                    result = await getattr(plugin, method_name)(**args)
                    return {"result": result, "status": "success"}
            
            return {"error": "Command not found", "status": "error"}
        
        # Register handlers
        self.ws_server.register_handler("chat.send_message", handle_chat)
        self.ws_server.register_handler("execute_command", handle_execute)
    
    async def tick_loop(self):
        """
        Periodic tick loop for plugins.
        Runs every 5 seconds, allowing plugins to emit events.
        """
        print("Starting tick loop...")
        
        while True:
            await asyncio.sleep(5)
            
            # Call on_tick for each plugin
            for plugin_name, plugin in self.plugins.items():
                if hasattr(plugin, "on_tick"):
                    try:
                        await plugin.on_tick(self.emitter)
                    except Exception as e:
                        print(f"Plugin {plugin_name} tick error: {e}")
                        import traceback
                        traceback.print_exc()
