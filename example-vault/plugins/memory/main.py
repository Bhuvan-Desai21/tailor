import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from sidecar.api.plugin_base import PluginBase
from sidecar.pipeline.events import PipelineEvents
from sidecar.pipeline.types import PipelineContext
from sidecar import utils

class Plugin(PluginBase):
    """
    Memory Plugin
    
    Stores conversation history and retrieves relevant context for the LLM.
    Supports chat branching.
    """
    
    def __init__(self, plugin_dir: Path, vault_path: Path, config: Dict[str, Any] = None):
        super().__init__(plugin_dir, vault_path, config)
        self.memory_dir = vault_path / ".memory"

    def register_commands(self) -> None:
        """Register memory commands."""
        self.brain.register_command("memory.create_branch", self.create_branch, self.name)
        self.brain.register_command("memory.switch_branch", self.switch_branch, self.name)
        self.brain.register_command("memory.get_chat_history", self.get_chat_history, self.name)
        self.brain.register_command("memory.list_branches", self.list_branches, self.name)
        
    async def on_load(self) -> None:
        """Load memory and subscribe to pipeline events."""
        await super().on_load()
        if not self.memory_dir.exists():
            self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.subscribe(PipelineEvents.OUTPUT, self.save_interaction, priority=10)
        
        self.logger.info("Memory Plugin loaded.")

    # =========================================================================
    # Data Management (V2 Schema)
    # =========================================================================

    def _load_chat_file(self, chat_file: Path) -> Dict[str, Any]:
        """Load raw chat file content."""
        if not chat_file.exists():
            return self._create_empty_chat()
            
        try:
            with open(chat_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Migration check: If list, convert to V2
            if isinstance(data, list):
                return self._migrate_to_v2(data)
            
            return data
        except Exception as e:
            self.logger.error(f"Failed to load chat {chat_file}: {e}")
            return self._create_empty_chat()

    def _save_chat_file(self, chat_file: Path, data: Dict[str, Any]) -> None:
        """Save chat file content."""
        try:
            if not self.memory_dir.exists():
                self.memory_dir.mkdir(parents=True, exist_ok=True)
                
            with open(chat_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save chat {chat_file}: {e}")

    def _create_empty_chat(self) -> Dict[str, Any]:
        """Create a new empty chat structure (V2)."""
        return {
            "version": 2,
            "created_at": datetime.now().isoformat(),
            "active_branch": "main",
            "branches": {
                "main": []
            }
        }

    def _migrate_to_v2(self, old_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert V1 list format to V2 dict format."""
        return {
            "version": 2,
            "created_at": datetime.now().isoformat(),
            "active_branch": "main",
            "branches": {
                "main": old_data
            }
        }

    def _get_chat_path(self, chat_id: str) -> Path:
        """Get safe path for chat ID."""
        safe_id = "".join(x for x in chat_id if x.isalnum() or x in "-_")
        return self.memory_dir / f"{safe_id}.json"

    # =========================================================================
    # Commands
    # =========================================================================

    async def create_branch(self, chat_id: str = "", message_index: int = -1, name: str = None, **kwargs) -> Dict[str, Any]:
        """
        Create a new branch from a specific point in the active branch.
        """
        if not chat_id:
            p = kwargs.get("p") or kwargs.get("params", {})
            chat_id = p.get("chat_id")
            message_index = p.get("message_index", message_index)
            name = p.get("name", name)
            
        if not chat_id:
            return {"status": "error", "error": "chat_id required"}
            
        chat_file = self._get_chat_path(chat_id)
        if not chat_file.exists():
            return {"status": "error", "error": "Chat not found"}
            
        data = self._load_chat_file(chat_file)
        active_branch = data.get("active_branch", "main")
        current_history = data["branches"].get(active_branch, [])
        
        # Validate index
        if message_index < 0 or message_index >= len(current_history):
            # If invalid index, simplify: assume last? No, error is safer.
            # Actually, frontend might pass a message ID. Currently logic uses index.
            # If -1, maybe branch from end? But that's just a copy.
            if message_index != -1: # -1 could mean "current state"
                return {"status": "error", "error": f"Invalid message index: {message_index}"}
                
        # Slice history (inclusive of the message at index)
        # If index is 2, we want items 0, 1, 2. So slice 0:3.
        new_history = current_history[:message_index+1]
        
        # Generate new branch name
        if not name:
            name = f"branch_{int(time.time())}"
        
        if name in data["branches"]:
           name = f"{name}_{int(time.time())}" 
            
        # Create branch
        data["branches"][name] = new_history
        data["active_branch"] = name
        
        self._save_chat_file(chat_file, data)
        self.logger.info(f"Created branch '{name}' for chat {chat_id}")
        
        return {
            "status": "success",
            "branch": name,
            "history": new_history
        }

    async def switch_branch(self, chat_id: str = "", branch: str = "", **kwargs) -> Dict[str, Any]:
        """Switch to an existing branch."""
        if not chat_id:
            p = kwargs.get("p") or kwargs.get("params", {})
            chat_id = p.get("chat_id")
            branch = p.get("branch", branch)
            
        chat_file = self._get_chat_path(chat_id)
        data = self._load_chat_file(chat_file)
        
        if branch not in data["branches"]:
            return {"status": "error", "error": f"Branch '{branch}' not found"}
            
        data["active_branch"] = branch
        self._save_chat_file(chat_file, data)
        
        return {
            "status": "success",
            "branch": branch,
            "history": data["branches"][branch]
        }

    async def get_chat_history(self, chat_id: str = "", branch: str = None, **kwargs) -> Dict[str, Any]:
        """Get history for a chat (active or specific branch)."""
        if not chat_id:
            p = kwargs.get("p") or kwargs.get("params", {})
            chat_id = p.get("chat_id")
            branch = p.get("branch", branch)
            
        if not chat_id:
            return {"status": "error", "error": "chat_id required"}
            
        chat_file = self._get_chat_path(chat_id)
        if not chat_file.exists():
            return {"status": "success", "history": [], "branches": []}
            
        data = self._load_chat_file(chat_file)
        
        target_branch = branch or data.get("active_branch", "main")
        history = data["branches"].get(target_branch, [])
        
        return {
            "status": "success",
            "chat_id": chat_id,
            "history": history,
            "active_branch": target_branch,
            "branches": list(data["branches"].keys())
        }

    async def list_branches(self, chat_id: str = "", **kwargs) -> Dict[str, Any]:
        """List all branches for a chat."""
        if not chat_id:
             p = kwargs.get("p") or kwargs.get("params", {})
             chat_id = p.get("chat_id")
             
        chat_file = self._get_chat_path(chat_id)
        if not chat_file.exists():
            return {"status": "error", "error": "Chat not found"}
            
        data = self._load_chat_file(chat_file)
        
        return {
            "status": "success",
            "active_branch": data.get("active_branch"),
            "branches": list(data["branches"].keys())
        }

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
            
        if ctx.metadata.get("save_to_memory") is False:
            return
            
        chat_id = ctx.metadata.get("chat_id")
        if not chat_id:
            chat_id = f"chat_{int(time.time())}"
            ctx.metadata["chat_id"] = chat_id
            
        chat_file = self._get_chat_path(chat_id)
        
        # Load existing data
        data = self._load_chat_file(chat_file)
        
        active_branch = data.get("active_branch", "main")
        if active_branch not in data["branches"]:
            # Should not happen unless corrupted, fallback to create it
            data["branches"][active_branch] = []
            
        history = data["branches"][active_branch]
        
        # Create message entries
        time_marker = str(time.time())
        user_msg = {"role": "user", "content": ctx.message, "time_marker": time_marker}
        assistant_msg = {"role": "assistant", "content": ctx.response, "time_marker": time_marker}
        
        history.append(user_msg)
        history.append(assistant_msg)
        
        self._save_chat_file(chat_file, data)
        self.logger.info(f"Saved interaction to {chat_file.name} (branch: {active_branch})")
