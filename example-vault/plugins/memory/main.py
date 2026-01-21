import json
import time
import uuid
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
    # Data Management (V3 Schema - Split-on-Branch)
    # =========================================================================

    def _load_chat_file(self, chat_file: Path) -> Dict[str, Any]:
        """Load raw chat file content."""
        if not chat_file.exists():
            return self._create_empty_chat()
            
        try:
            with open(chat_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Migration check: If list (V1) or V2 schema, nuke or migrate?
            # User said "remove old chats", so if version mismatch, reset.
            if isinstance(data, list) or data.get("version") != 3:
                self.logger.warning(f"Version mismatch for {chat_file.name}, resetting to V3")
                return self._create_empty_chat()
            
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
            
            # Emit event to notify frontend that chat is saved (syncs UUIDs)
            # Extract chat_id from chat_file name
            chat_id = chat_file.stem
            self.emit("memory:chat_saved", {"chat_id": chat_id})
        except Exception as e:
            self.logger.error(f"Failed to save chat {chat_file}: {e}")

    def _create_empty_chat(self) -> Dict[str, Any]:
        """Create a new empty chat structure (V3)."""
        root_id = uuid.uuid4().hex[:8]
        return {
            "version": 3,
            "created_at": datetime.now().isoformat(),
            "active_branch": root_id,
            "branches": {
                root_id: {
                    "display_name": "Main",
                    "parent_branch": None,
                    "messages": []
                }
            }
        }

    def _get_chat_path(self, chat_id: str) -> Path:
        """Get safe path for chat ID."""
        safe_id = "".join(x for x in chat_id if x.isalnum() or x in "-_")
        return self.memory_dir / f"{safe_id}.json"

    # =========================================================================
    # Commands
    # =========================================================================

    async def create_branch(self, chat_id: str = "", message_id: str = "", name: str = None, **kwargs) -> Dict[str, Any]:
        """
        Create a new branch from a specific message ID.
        Implements Split-on-Branch logic.
        """
        if not chat_id:
            p = kwargs.get("p") or kwargs.get("params", {})
            chat_id = p.get("chat_id")
            message_id = p.get("message_id") or p.get("parent_message_id", message_id)
            name = p.get("name", name)
            
        if not chat_id:
            return {"status": "error", "error": "chat_id required"}
            
        chat_file = self._get_chat_path(chat_id)
        if not chat_file.exists():
            return {"status": "error", "error": "Chat not found"}
            
        data = self._load_chat_file(chat_file)
        
        # 1. Locate the branch containing message_id
        target_branch_id = None
        target_index = -1
        
        # Search all branches for the message
        # Optimization: Start with active branch?
        # For V3, the message exists in exactly ONE branch.
        for bid, branch in data["branches"].items():
            for idx, msg in enumerate(branch["messages"]):
                if msg.get("id") == message_id:
                    target_branch_id = bid
                    target_index = idx
                    break
            if target_branch_id:
                break
                
        if not target_branch_id:
             # Fallback: if message_id not provided, use end of active branch
            if not message_id:
                target_branch_id = data.get("active_branch")
                # Fallback to ANY branch if active is somehow missing (rare)
                if not target_branch_id and data["branches"]:
                    target_branch_id = list(data["branches"].keys())[0]

                target_index = len(data["branches"][target_branch_id]["messages"]) - 1
                message_id = data["branches"][target_branch_id]["messages"][-1]["id"] if target_index >= 0 else None
            else:
                 return {"status": "error", "error": f"Message ID '{message_id}' not found"}

        parent_branch = data["branches"][target_branch_id]
        
        # 2. Determine if Split is needed
        # Split needed if target_index is NOT the last message
        is_split = target_index < (len(parent_branch["messages"]) - 1)

        if is_split:
            # === SPLIT LOGIC ===
            # Trunk: [0 ... target_index]
            # Tail: [target_index+1 ... end]
            
            trunk_messages = parent_branch["messages"][:target_index+1]
            tail_messages = parent_branch["messages"][target_index+1:]
            
            # Create Continuation Branch (The Tail)
            # Use short UUID for clean names
            continuation_id = uuid.uuid4().hex[:8]
            data["branches"][continuation_id] = {
                "display_name": parent_branch.get("display_name"),
                "parent_branch": target_branch_id,
                # parent_message_id removed (implicit)
                "messages": tail_messages
            }
            
            # Truncate Original Branch
            parent_branch["messages"] = trunk_messages
            
            # Reparent Operations:
            # All existing children of the original branch must now point to the continuation
            # because the continuation represents the original path after the split point.
            for bid, branch in list(data["branches"].items()):
                if branch.get("parent_branch") == target_branch_id:
                     branch["parent_branch"] = continuation_id
                     self.logger.info(f"Reparented branch {bid} to {continuation_id}")

        # 3. Create the New Branch (Divergence)
        new_branch_name = name or uuid.uuid4().hex[:8]
        if new_branch_name in data["branches"]:
             new_branch_name = f"{new_branch_name}_{uuid.uuid4().hex[:4]}"
             
        data["branches"][new_branch_name] = {
             "display_name": name, 
             "parent_branch": target_branch_id,
             # parent_message_id removed (implicit)
             "messages": []
        }
        
        data["active_branch"] = new_branch_name
        
        self._save_chat_file(chat_file, data)
        self.logger.info(f"Created branch '{new_branch_name}' (Split: {is_split})")
        
        # Return full reconstructed history
        history = self._reconstruct_history(data, new_branch_name)
        
        return {
            "status": "success",
            "branch": new_branch_name,
            "history": history
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
        
        history = self._reconstruct_history(data, branch)
        
        return {
            "status": "success",
            "branch": branch,
            "history": history
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
        
        target_branch = branch or data.get("active_branch")
        if not target_branch and data["branches"]:
             target_branch = list(data["branches"].keys())[0]
             
        history = self._reconstruct_history(data, target_branch)
        
        branches_meta = {}
        for bid, b in data["branches"].items():
            branches_meta[bid] = {
                "id": bid,
                "display_name": b.get("display_name"),
                "parent_branch": b.get("parent_branch")
            }
        
        return {
            "status": "success",
            "chat_id": chat_id,
            "history": history,
            "active_branch": target_branch,
            "branches": branches_meta
        }

    def _reconstruct_history(self, data: Dict[str, Any], branch_id: str) -> List[Dict[str, Any]]:
        """Recursively build history from linked branches."""
        if branch_id not in data["branches"]:
            return []
            
        branch = data["branches"][branch_id]
        # Create copies of messages with source_branch tag for UI
        current_messages = [{**msg, "source_branch": branch_id} for msg in branch["messages"]]
        
        # Base case: Root branch (no parent)
        if not branch.get("parent_branch"):
            return current_messages
            
        # Recursive step: Get parent history
        parent_history = self._reconstruct_history(data, branch["parent_branch"])
        
        return parent_history + current_messages

    async def list_branches(self, chat_id: str = "", **kwargs) -> Dict[str, Any]:
        """List all branches for a chat."""
        if not chat_id:
             p = kwargs.get("p") or kwargs.get("params", {})
             chat_id = p.get("chat_id")
             
        chat_file = self._get_chat_path(chat_id)
        if not chat_file.exists():
            return {"status": "error", "error": "Chat not found"}
            
        data = self._load_chat_file(chat_file)
        
        branches_meta = {}
        for bid, b in data["branches"].items():
            branches_meta[bid] = {
                "id": bid,
                "display_name": b.get("display_name"),
                "parent_branch": b.get("parent_branch")
            }
            
        return {
            "status": "success",
            "active_branch": data.get("active_branch"),
            "branches": branches_meta
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
        data = self._load_chat_file(chat_file)
        
        active_branch_id = data.get("active_branch")
        if not active_branch_id or active_branch_id not in data["branches"]:
             # Init root if missing
             root_id = uuid.uuid4().hex[:8]
             active_branch_id = root_id
             data["active_branch"] = root_id
             data["branches"][root_id] = {
                 "display_name": "Main",
                 "parent_branch": None,
                 "messages": []
             }
            
        branch = data["branches"][active_branch_id]
        
        # Create message entries with clean UUIDs
        time_marker = str(time.time())
        
        # User Message
        user_msg = {
            "id": uuid.uuid4().hex[:8],
            "role": "user", 
            "content": ctx.message, 
            "time_marker": time_marker
        }
        
        # Assistant Message
        assistant_msg = {
            "id": uuid.uuid4().hex[:8],
            "role": "assistant", 
            "content": ctx.response, 
            "time_marker": time_marker
        }
        
        branch["messages"].append(user_msg)
        branch["messages"].append(assistant_msg)
        
        self._save_chat_file(chat_file, data)
        self.logger.info(f"Saved interaction to {chat_file.name} (branch: {active_branch_id})")
        
        # Store generated IDs in metadata so VaultBrain can return them
        ctx.metadata["generated_ids"] = {
            "user_message_id": user_msg["id"],
            "assistant_message_id": assistant_msg["id"],
            "chat_id": chat_id,
            "branch_id": active_branch_id
        }
