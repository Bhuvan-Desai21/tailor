import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from sidecar.api.plugin_base import PluginBase
from sidecar.pipeline.events import PipelineEvents
from sidecar.pipeline.types import PipelineContext

class Plugin(PluginBase):
    """
    Memory Plugin
    
    Stores conversation history and retrieves relevant context for the LLM.
    """
    
    def __init__(self, plugin_dir: Path, vault_path: Path, config: Dict[str, Any] = None):
        super().__init__(plugin_dir, vault_path, config)
        self.memory_dir = vault_path / ".memory"

    def register_commands(self) -> None:
        """Register commands (none for now)."""
        pass
        
    async def on_load(self) -> None:
        """Load memory and subscribe to pipeline events."""
        await super().on_load()
        if not self.memory_dir.exists():
            self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.subscribe(PipelineEvents.OUTPUT, self.save_interaction, priority=10)
        
        self.logger.info("Memory Plugin loaded.")

    def _load_chat_memory(self, chat_file: Path) -> List[Dict[str, Any]]:
        """Load memories from a specific chat file."""
        if chat_file.exists():
            try:
                with open(chat_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load memory file {chat_file}: {e}")
        return []

    def _save_chat_memory(self, chat_file: Path, memories: List[Dict[str, Any]]) -> None:
        """Save memories to a specific chat file."""
        try:
            # Ensure directory exists
            if not self.memory_dir.exists():
                self.memory_dir.mkdir(parents=True, exist_ok=True)
                
            with open(chat_file, "w", encoding="utf-8") as f:
                json.dump(memories, f, indent=2)
            self.logger.debug(f"Memory saved to {chat_file.name}.")
        except Exception as e:
            self.logger.error(f"Failed to save memory: {e}")

    # =========================================================================
    # Event Handlers
    # =========================================================================

    async def save_interaction(self, ctx: PipelineContext) -> None:
        """
        Pipeline Handler: OUTPUT
        Save the interaction to memory.
        """
        if not ctx.response:
            return
            
        chat_id = ctx.metadata.get("chat_id")
        if not chat_id:
            chat_id = f"chat_{int(time.time())}"
            ctx.metadata["chat_id"] = chat_id
        safe_chat_id = "".join(x for x in chat_id if x.isalnum() or x in "-_")
        chat_filename = f"{safe_chat_id}.json"
        chat_file = self.memory_dir / chat_filename
            
        # Store the whole history as it is in the memory object
        # This aligns with the standard List[Dict[str, str]] format
        full_history = []
        if ctx.history:
            full_history.extend(ctx.history)
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M")
        time_marker = time.time()
        full_history.append({"role": "user", "content": ctx.message, "timestamp": timestamp, "time_marker": time_marker})
        full_history.append({"role": "assistant", "content": ctx.response, "timestamp": timestamp, "time_marker": time_marker})
        
        self._save_chat_memory(chat_file, full_history)
        
        self.logger.info(f"Saved interaction to {chat_filename}.")
