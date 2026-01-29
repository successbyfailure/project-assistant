import pytest
from unittest.mock import AsyncMock, patch
from src.clients.github_client import GitHubMCPClient

@pytest.mark.asyncio
async def test_github_client_list_issues():
    with patch("src.clients.github_client.stdio_client") as mock_stdio:
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_stdio.return_value.__aenter__.return_value = (mock_read, mock_write)
        
        with patch("src.clients.github_client.ClientSession") as mock_session_cls:
            mock_session = mock_session_cls.return_value
            mock_session.initialize = AsyncMock()
            mock_session.call_tool = AsyncMock()
            
            mock_content = AsyncMock()
            mock_content.text = '[{"number": 1, "title": "Test Issue"}]'
            mock_response = AsyncMock()
            mock_response.content = [mock_content]
            mock_response.is_error = False
            mock_session.call_tool.return_value = mock_response
            
            # Use a dummy token to avoid subprocess call
            client = GitHubMCPClient(token="fake_token")
            await client.connect()
            
            issues = await client.list_issues("owner", "repo")
            
            assert len(issues) == 1
            assert issues[0]["title"] == "Test Issue"
            mock_session.call_tool.assert_called_once_with("list_issues", {
                "owner": "owner",
                "repo": "repo",
                "state": "open"
            })
            
            await client.disconnect()

@pytest.mark.asyncio
async def test_github_client_create_issue():
    with patch("src.clients.github_client.stdio_client") as mock_stdio:
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_stdio.return_value.__aenter__.return_value = (mock_read, mock_write)
        
        with patch("src.clients.github_client.ClientSession") as mock_session_cls:
            mock_session = mock_session_cls.return_value
            mock_session.initialize = AsyncMock()
            mock_session.call_tool = AsyncMock()
            
            mock_content = AsyncMock()
            mock_content.text = '{"number": 2, "title": "New Issue"}'
            mock_response = AsyncMock()
            mock_response.content = [mock_content]
            mock_response.is_error = False
            mock_session.call_tool.return_value = mock_response
            
            client = GitHubMCPClient(token="fake_token")
            await client.connect()
            
            issue = await client.create_issue("owner", "repo", "New Issue", "Body")
            
            assert issue["number"] == 2
            mock_session.call_tool.assert_called_once_with("create_issue", {
                "owner": "owner",
                "repo": "repo",
                "title": "New Issue",
                "body": "Body",
                "labels": []
            })
            
            await client.disconnect()
