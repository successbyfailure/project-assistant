import os
import json
import pytest
from unittest.mock import MagicMock
from src.core.research_engine import ResearchEngine
from src.models.task import Task, TaskType

def test_research_engine_save_artifact(tmp_path):
    engine = ResearchEngine(str(tmp_path))
    task_id = "test-task"
    
    file_path = engine.save_artifact(task_id, "data", {"result": 42}, "json")
    
    assert os.path.exists(file_path)
    with open(file_path, "r") as f:
        data = json.load(f)
        assert data["result"] == 42

def test_research_engine_generate_report(tmp_path):
    engine = ResearchEngine(str(tmp_path))
    task = Task(id="t1", title="Research Task", project_name="p1", type=TaskType.RESEARCH)
    
    engine.save_artifact(task.id, "observation", "Found something", "txt")
    report = engine.generate_report(task)
    
    assert "Research Report: Research Task" in report
    assert "observation.txt" in report

@pytest.mark.asyncio
async def test_project_analyze_codebase(tmp_path):
    # Setup mock project
    proj_dir = tmp_path / "myproj"
    proj_dir.mkdir()
    (proj_dir / "pyproject.toml").write_text('dependencies = ["mcp", "pydantic"]')
    (proj_dir / "src").mkdir()
    
    from src.server.tools.intelligence_tools import register_intelligence_tools
    from mcp.server.fastmcp import FastMCP
    from src.config.coder import CoderSettings
    
    mcp = FastMCP("test")
    coder_settings = CoderSettings(projects_root=str(tmp_path))
    storage = MagicMock()
    engine = ResearchEngine(str(tmp_path / "artifacts"))
    
    register_intelligence_tools(mcp, coder_settings, storage, engine)
    
    # FastMCP tool run uses arguments
    result_json, _ = await mcp.call_tool("project_analyze_codebase", {"project_name": "myproj"})
    
    analysis = json.loads(result_json[0].text)
    assert analysis["type"] == "Python"
    assert "src" in analysis["structure"]
    assert "mcp" in analysis["dependencies"]
