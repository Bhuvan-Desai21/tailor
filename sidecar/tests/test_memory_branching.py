import pytest
import asyncio
import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

from sidecar.vault_brain import VaultBrain
from sidecar.services.llm_service import LLMService

@pytest.mark.asyncio
async def test_memory_branching():
    # Setup paths
    vault_path = Path("/home/arc/Dev/tailor/example-vault")
    memory_dir = vault_path / ".memory"
    chat_id = "chat_branch_test"
    memory_file = memory_dir / f"{chat_id}.json"
    
    # Clean up
    if memory_dir.exists():
        shutil.rmtree(memory_dir)
        
    # Reset Singleton
    if VaultBrain._instance:
        VaultBrain._instance = None
    
    # Initialize
    brain = VaultBrain(vault_path, MagicMock())
    
    # Mock LLM
    mock_llm = MagicMock(spec=LLMService)
    mock_llm.complete = AsyncMock()
    # Responses:
    # 1. Main branch response
    # 2. Side branch response
    mock_llm.complete.side_effect = [
        MagicMock(content="Response 1", model="test", usage={}),
        MagicMock(content="Response 2", model="test", usage={})
    ]
    
    await brain.initialize()
    brain._llm_service = mock_llm
    # Patch the module level service if needed (depending on implementation)
    import sidecar.services.llm_service as llm_module
    llm_module._llm_service = mock_llm
    
    # 1. Start Chat (Main Branch)
    # User: Msg 1 -> Assistant: Response 1
    await brain.chat_send(message="Msg 1", chat_id=chat_id)
    
    # Verify file
    with open(memory_file, "r") as f:
        data = json.load(f)
    
    root_id = data["active_branch"]
    root_branch = data["branches"][root_id]
    
    assert root_branch["display_name"] == "Main"
    assert len(root_branch["messages"]) == 2
    
    msg1_id = root_branch["messages"][0]["id"]
    
    # 2. Create Branch from msg1 (The User Message at index 0)
    # This should split the root branch after msg1 (truncating Response 1)
    # But wait, msg1 is index 0. Response 1 is index 1.
    # If we branch from msg1, we keep msg1. Response 1 is 'future'.
    # V3 Logic:
    # Root becomes [Msg 1].
    # Continuation becomes [Response 1] (parented to Root).
    # New Branch becomes [] (parented to Root).
    
    result = await brain.execute_command("memory.create_branch", 
        chat_id=chat_id, 
        message_id=msg1_id, 
        name="experiment_a"
    )
    
    assert result["status"] == "success"
    new_branch_id = result["branch"]
    
    # Verify file updated
    with open(memory_file, "r") as f:
        data = json.load(f)
        
    assert data["active_branch"] == new_branch_id
    
    # Verify Root Split
    root_branch = data["branches"][root_id]
    assert len(root_branch["messages"]) == 1 # Just Msg 1
    assert root_branch["messages"][0]["id"] == msg1_id
    
    # Verify New Branch
    new_branch = data["branches"][new_branch_id]
    assert new_branch["display_name"] == "experiment_a"
    assert new_branch["parent_branch"] == root_id
    assert len(new_branch["messages"]) == 0
    
    # Verify Continuation Branch (Implicitly created)
    # Search for branch with parent=root_id and NOT new_branch
    continuation_branch = None
    for bid, b in data["branches"].items():
        if b["parent_branch"] == root_id and bid != new_branch_id:
            continuation_branch = b
            break
            
    assert continuation_branch is not None
    assert len(continuation_branch["messages"]) == 1
    assert continuation_branch["messages"][0]["content"] == "Response 1"
    
    # 3. Continue Chat on New Branch
    # User sends Msg 2
    await brain.chat_send(message="Msg 2", chat_id=chat_id)
    
    # Verify file
    with open(memory_file, "r") as f:
        data = json.load(f)
        
    new_branch = data["branches"][new_branch_id]
    # Should have: Msg 2, Response 2
    assert len(new_branch["messages"]) == 2
    assert new_branch["messages"][0]["content"] == "Msg 2"
    assert new_branch["messages"][1]["content"] == "Response 2"
    
    # Cleanup
    await brain.shutdown()
    if memory_dir.exists():
        shutil.rmtree(memory_dir)
