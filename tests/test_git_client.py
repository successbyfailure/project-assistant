import pytest
from unittest.mock import AsyncMock, patch
from src.clients.git_client import GitMCPClient

@pytest.mark.asyncio
async def test_git_client_get_status():
    with patch("src.clients.git_client.stdio_client") as mock_stdio:
        # Setup mocks
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_stdio.return_value.__aenter__.return_value = (mock_read, mock_write)
        
        with patch("src.clients.git_client.ClientSession") as mock_session_cls:
            mock_session = mock_session_cls.return_value
            mock_session.initialize = AsyncMock()
            mock_session.call_tool = AsyncMock()
            
            # Mock tool response
            mock_content = AsyncMock()
            mock_content.text = '{"branch": "main", "is_dirty": false}'
            mock_response = AsyncMock()
            mock_response.content = [mock_content]
            mock_response.is_error = False
            mock_session.call_tool.return_value = mock_response
            
            client = GitMCPClient("/fake/path")
            await client.connect()
            
            status = await client.get_status()
            
            assert status["branch"] == "main"
            mock_session.call_tool.assert_called_once_with("git_status", {})
            
            await client.disconnect()

@pytest.mark.asyncio
async def test_git_client_commit():
    with patch("src.clients.git_client.stdio_client") as mock_stdio:
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_stdio.return_value.__aenter__.return_value = (mock_read, mock_write)
        
        with patch("src.clients.git_client.ClientSession") as mock_session_cls:
            mock_session = mock_session_cls.return_value
            mock_session.initialize = AsyncMock()
            mock_session.call_tool = AsyncMock()
            
            mock_content = AsyncMock()
            mock_content.text = '{"success": true}'
            mock_response = AsyncMock()
            mock_response.content = [mock_content]
            mock_response.is_error = False
            mock_session.call_tool.return_value = mock_response
            
            client = GitMCPClient("/fake/path")
            await client.connect()
            
            # Test commit with files (should call git_add then git_commit)
            await client.commit("test commit", files=["file1.txt"])
            
            assert mock_session.call_tool.call_count == 2
            mock_session.call_tool.assert_any_call("git_add", {"path": "file1.txt"})
            mock_session.call_tool.assert_any_call("git_commit", {"message": "test commit"})
            
            await client.disconnect()
