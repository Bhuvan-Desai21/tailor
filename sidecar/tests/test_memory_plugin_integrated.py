import pytest
import asyncio
import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

from sidecar.vault_brain import VaultBrain
from sidecar.services.llm_service import LLMService

@pytest.mark.asyncio
async def test_memory_plugin_integrated():
    # Setup paths
    vault_path = Path("/home/arc/Dev/tailor/example-vault")
    memory_dir = vault_path / ".memory"
    memory_file = memory_dir / "chat_default.json"
    
    # Clean up previous memory
    if memory_dir.exists():
        shutil.rmtree(memory_dir)
        
    # Initialize Brain
    # Force singleton reset if needed (though pytest runs usually isolate or we can patch)
    if VaultBrain._instance:
        VaultBrain._instance = None
    
    # Mock WebSocket
    ws_mock = MagicMock()
    brain = VaultBrain(vault_path, ws_mock)
    
    # Mock LLM Service to capture prompts and return specific responses
    mock_llm = MagicMock(spec=LLMService)
    mock_llm.complete = AsyncMock()
    
    # First response (simple ack)
    # Second response (answer)
    mock_llm.complete.side_effect = [
        MagicMock(content="Hello AutoTest", model="test-model", usage={}),
        MagicMock(content="Your name is AutoTest", model="test-model", usage={})
    ]
    
    # Start Brain (loads plugins)
    await brain.initialize()
    
    # Inject mock LLM AFTER initialization (overwriting real service)
    brain._llm_service = mock_llm
    
    # Update global singleton so Pipeline picks it up
    import sidecar.services.llm_service as llm_module
    llm_module._llm_service = mock_llm
    
    # Verify plugin loaded
    assert "memory" in brain.plugins
    assert brain.plugins["memory"].is_loaded
    
    # 1. Send first message
    response1 = await brain.chat_send(message="Msg A", chat_id="chat_v3_test")
    assert response1["status"] == "success"
    
    # 2. Send second message
    response2 = await brain.chat_send(message="Msg B", chat_id="chat_v3_test")
    
    # 3. Send third message
    response3 = await brain.chat_send(message="Msg C", chat_id="chat_v3_test")

    # Verify ID existence in file
    chat_file = memory_dir / "chat_v3_test.json"
    with open(chat_file, "r") as f:
        data = json.load(f)
        
    main_branch_id = data["active_branch"]
    main_branch = data["branches"][main_branch_id]
    msgs = main_branch["messages"]
    assert len(msgs) == 6 # 3 user + 3 assistant
    msg_b_id = msgs[3]["id"] # 0=A_user, 1=A_asst, 2=B_user, 3=B_asst (This is B)
    
    # 4. Branch from B (Assistant response) - effectively splitting before C
    # Message Index 3 is B_assistant.
    # Total len is 6. Index 3 is middle.
    
    branch_res = await brain.execute_command("memory.create_branch", chat_id="chat_v3_test", message_id=msg_b_id, name="split_branch")
    assert branch_res["status"] == "success"
    
    # Reload file to check Split
    with open(chat_file, "r") as f:
        data_split = json.load(f)
        
    # MAIN BRANCH (The Root): Should be truncated up to B_asst
    main_msgs = data_split["branches"][main_branch_id]["messages"]
    assert len(main_msgs) == 4
    assert main_msgs[-1]["id"] == msg_b_id
    
    # CONTINUATION BRANCH: Should have [C_user, C_asst]
    # Find the branch that has parent=main_branch_id and parent_msg_id=msg_b_id AND has messages
    continuation = None
    for bid, b in data_split["branches"].items():
        if b.get("parent_branch") == main_branch_id and b.get("parent_message_id") == msg_b_id and len(b["messages"]) > 0:
            continuation = b
            break
            
    assert continuation is not None
    assert len(continuation["messages"]) == 2 # C_user, C_asst
    
    # NEW BRANCH: Should be empty
    new_branch = data_split["branches"]["split_branch"]
    assert len(new_branch["messages"]) == 0
    assert new_branch["parent_branch"] == main_branch_id
    assert new_branch["parent_message_id"] == msg_b_id

    # Cleanup
    await brain.shutdown()
    if memory_dir.exists():
        shutil.rmtree(memory_dir)
