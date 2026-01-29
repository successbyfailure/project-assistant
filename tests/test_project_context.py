import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.core.project_context import ProjectContext
from src.config.coder import CoderSettings
from src.models.task import Task

@pytest.fixture
def mock_storage():
    storage = MagicMock()
    storage.list_tasks.return_value = []
    return storage

@pytest.fixture
def coder_settings():
    settings = CoderSettings()
    settings.projects_root = "/tmp/projects"
    return settings

@pytest.mark.asyncio
async def test_project_context_get_status():
    with patch("src.core.project_context.GitMCPClient") as mock_git_cls, \
         patch("src.core.project_context.GitHubMCPClient") as mock_github_cls:
        
        mock_git = mock_git_cls.return_value
        mock_git.connect = AsyncMock()
        mock_git.disconnect = AsyncMock()
        mock_git.get_status = AsyncMock(return_value={
            "branch": "main",
            "is_dirty": True,
            "modified_files": ["README.md"]
        })
        mock_git._call_tool = AsyncMock(return_value=[{"name": "origin", "url": "https://github.com/owner/repo.git"}])
        
        mock_github = mock_github_cls.return_value
        mock_github.connect = AsyncMock()
        mock_github.disconnect = AsyncMock()
        mock_github.list_issues = AsyncMock(return_value=[])
        
        storage = MagicMock()
        storage.list_tasks.return_value = [
            Task(id="1", project_name="test", title="Task 1", type="standard")
        ]
        
        ctx = ProjectContext("test", CoderSettings(projects_root="/tmp"), storage)
        await ctx.initialize()
        
        status = await ctx.get_status()
        
        assert status.project == "test"
        assert status.git.branch == "main"
        assert status.git.is_dirty is True
        assert len(status.tasks.recent) == 1
        assert len(status.suggestions) > 0 # Should have commit suggestion
        
        await ctx.close()
