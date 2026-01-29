import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from src.server.mcp_server import ProjectAssistantServer
from src.config.coder import CoderSettings

@pytest.fixture
def coder_settings():
    settings = CoderSettings()
    settings.projects_root = "/tmp/projects"
    settings.workspace_name = "test-workspace"
    return settings

@pytest.mark.asyncio
async def test_project_list_available_tool(coder_settings, tmp_path):
    # Setup mock projects
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    (projects_dir / "proj1").mkdir()
    (projects_dir / "proj1" / ".git").mkdir()
    (projects_dir / "proj2").mkdir()
    (projects_dir / "proj2" / ".git").mkdir()
    
    coder_settings.projects_root = str(projects_dir)
    
    server = ProjectAssistantServer(coder_settings)
    
    # Use call_tool to run the tool
    result = await server.mcp.call_tool("project_list_available", {})
    
    # FastMCP call_tool returns a tuple (content_list, extra)
    contents, _ = result
    data = json.loads(contents[0].text)
    assert "proj1" in data["projects"]
    assert "proj2" in data["projects"]
    assert data["total"] == 2

@pytest.mark.asyncio
async def test_tasks_create_tool(coder_settings, tmp_path):
    db_path = tmp_path / "test.db"
    import os
    os.environ["PROJECT_ASSISTANT_DB"] = str(db_path)
    
    server = ProjectAssistantServer(coder_settings)
    
    result = await server.mcp.call_tool("tasks_create", {
        "project_name": "test-proj", 
        "title": "New Task"
    })
    
    contents, _ = result
    task = json.loads(contents[0].text)
    assert task["title"] == "New Task"
    assert task["project_name"] == "test-proj"
    
    # Verify it's in DB
    list_result = await server.mcp.call_tool("tasks_list", {"project_name": "test-proj"})
    list_contents, _ = list_result
    tasks = json.loads(list_contents[0].text)
    assert len(tasks) == 1
    assert tasks[0]["title"] == "New Task"
