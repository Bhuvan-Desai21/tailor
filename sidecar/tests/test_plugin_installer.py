
import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from sidecar.plugin_installer import PluginInstaller, InstallStatus

@pytest.fixture
def mock_vault_path(tmp_path):
    # Create valid vault structure
    (tmp_path / "plugins").mkdir()
    return tmp_path

@pytest.fixture
def plugin_installer(mock_vault_path):
    return PluginInstaller(mock_vault_path)

@pytest.mark.asyncio
async def test_install_from_git_success(plugin_installer, mock_vault_path):
    # Mock subprocess for git clone
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        # Mock process
        process_mock = AsyncMock()
        process_mock.communicate.return_value = (b"", b"")
        process_mock.returncode = 0
        
        # Side effect to create dir when git clone is "run"
        plugin_id = "test_plugin"
        plugin_dir = mock_vault_path / "plugins" / plugin_id
        
        async def mock_subprocess_side_effect(*args, **kwargs):
            plugin_dir.mkdir(parents=True, exist_ok=True)
            return process_mock
            
        mock_exec.side_effect = mock_subprocess_side_effect

        # Mock validate to pass
        with patch.object(plugin_installer, "validate", new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = MagicMock(valid=True, manifest={"name": "test", "version": "1.0.0"})
            
            # Execute
            result = await plugin_installer.install("https://github.com/user/repo", plugin_id)
            
            assert result.status == InstallStatus.SUCCESS
            assert result.plugin_id == plugin_id
            assert plugin_dir.exists()

@pytest.mark.asyncio
async def test_install_from_git_failure(plugin_installer):
    # Mock subprocess failure
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        process_mock = AsyncMock()
        process_mock.communicate.return_value = (b"", b"Critical Error")
        process_mock.returncode = 128
        mock_exec.return_value = process_mock

        result = await plugin_installer.install("https://github.com/user/repo", "test_failure")
        
        assert result.status == InstallStatus.CLONE_FAILED
        assert "Critical Error" in result.message

@pytest.mark.asyncio
async def test_install_from_url(plugin_installer, mock_vault_path):
    # Mock httpx and zipfile
    download_url = "http://example.com/plugin.zip"
    plugin_id = "zip_plugin"
    
    with patch("httpx.AsyncClient") as MockClient, \
         patch("zipfile.ZipFile") as MockZip, \
         patch("shutil.copytree") as MockCopy:
        
        # Mock HTTP response
        client_instance = AsyncMock()
        response_mock = AsyncMock()
        response_mock.content = b"fakezipcontent"
        response_mock.raise_for_status = MagicMock()
        client_instance.__aenter__.return_value = client_instance
        client_instance.get.return_value = response_mock
        MockClient.return_value = client_instance

        # Simulate copytree side effect (create the destination dir)
        def side_effect_copytree(src, dst):
            Path(dst).mkdir(exist_ok=True)
        MockCopy.side_effect = side_effect_copytree
        
        # Mock validate
        with patch.object(plugin_installer, "validate", new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = MagicMock(valid=True, manifest={})
            
            result = await plugin_installer.install_from_url(download_url, plugin_id)
            
            assert result.status == InstallStatus.SUCCESS
            # Verify httpx was used
            client_instance.get.assert_called_with(download_url, follow_redirects=True)

@pytest.mark.asyncio
async def test_uninstall(plugin_installer, mock_vault_path):
    # Create dummy plugin dir
    plugin_dir = mock_vault_path / "plugins" / "to_delete"
    plugin_dir.mkdir()
    
    success = await plugin_installer.uninstall("to_delete")
    assert success is True
    assert not plugin_dir.exists()

@pytest.mark.asyncio
async def test_update_success(plugin_installer, mock_vault_path):
    plugin_id = "existing_plugin"
    plugin_dir = mock_vault_path / "plugins" / plugin_id
    plugin_dir.mkdir()
    
    with patch("asyncio.create_subprocess_exec") as mock_exec, \
         patch.object(plugin_installer, "validate", new_callable=AsyncMock) as mock_validate:
         
        process_mock = AsyncMock()
        process_mock.communicate.return_value = (b"Updated", b"")
        process_mock.returncode = 0
        mock_exec.return_value = process_mock
        
        mock_validate.return_value = MagicMock(valid=True)
        
        result = await plugin_installer.update(plugin_id)
        assert result.status == InstallStatus.SUCCESS

