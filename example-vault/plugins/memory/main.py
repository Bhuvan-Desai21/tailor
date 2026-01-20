import json
import time
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
        self.memory_file = self.memory_dir / "memory.json"
        self.memories: List[Dict[str, Any]] = []

    def register_commands(self) -> None:
        """Register commands (none for now)."""
        pass
        
    async def on_load(self) -> None:
        """Load memory and subscribe to pipeline events."""
        await super().on_load()
        self._ensure_memory_storage()
        self._load_memory()
        
        # Subscribe to pipeline events
        # Priority 10 to run before other context providers if any (or after? Higher is earlier)
        # We want to inject context EARLY so others can see it? Or LATE?
        # Usually Context phase is for gathering. Let's say Priority 10.
        self.subscribe(PipelineEvents.CONTEXT, self.inject_context, priority=10)
        
        # Capture output to save memory
        self.subscribe(PipelineEvents.OUTPUT, self.save_interaction, priority=10)
        
        self.logger.info("Memory Plugin loaded and subscribed to pipeline.")

    def _ensure_memory_storage(self) -> None:
        """Ensure .memory directory exists."""
        if not self.memory_dir.exists():
            self.memory_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created memory directory: {self.memory_dir}")
            
    def _load_memory(self) -> None:
        """Load memories from JSON file."""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    self.memories = json.load(f)
                self.logger.info(f"Loaded {len(self.memories)} memories.")
            except Exception as e:
                self.logger.error(f"Failed to load memory: {e}")
                self.memories = []
        else:
            self.memories = []

    def _save_memory(self) -> None:
        """Save memories to JSON file."""
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.memories, f, indent=2)
            self.logger.debug("Memory saved.")
        except Exception as e:
            self.logger.error(f"Failed to save memory: {e}")

    # =========================================================================
    # Event Handlers
    # =========================================================================

    async def inject_context(self, ctx: PipelineContext) -> None:
        """
        Pipeline Handler: CONTEXT
        Retrieve relevant memories and inject into RAG context.
        """
        self.logger.debug(f"Injecting context for: {ctx.message[:50]}...")
        
        # Simple retrieval: Get last 5 interactions (excluding current)
        # In a real system, we'd do vector search here.
        # For now, let's just create a formatted string of recent history
        # that IS NOT already in ctx.history (ctx.history handles immediate session)
        # Actually, "Long Term Memory" might be older stuff.
        # Let's just grab the last 5 entries from stored memory.
        
        recent_memories = self.memories[-5:]
        if not recent_memories:
            return
            
        context_str = "Long-term Memory:\n"
        for mem in recent_memories:
            user = mem.get("user_input", "")
            ai = mem.get("ai_response", "")
            context_str += f"- User: {user}\n  AI: {ai}\n"
            
        if "rag_context" not in ctx.metadata:
            ctx.metadata["rag_context"] = []
            
        ctx.metadata["rag_context"].append(context_str)
        self.logger.debug("Injected long-term memory context.")

    async def save_interaction(self, ctx: PipelineContext) -> None:
        """
        Pipeline Handler: OUTPUT
        Save the interaction to memory.
        """
        if not ctx.response:
            return
            
        new_memory = {
            "timestamp": time.time(),
            "user_input": ctx.message,
            "ai_response": ctx.response
        }
        
        self.memories.append(new_memory)
        self._save_memory()
        self.logger.info("Saved new interaction to memory.")
