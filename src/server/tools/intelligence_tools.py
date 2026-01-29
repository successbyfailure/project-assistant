import json
import os
from typing import Optional, List, Dict, Any
from mcp.server.fastmcp import FastMCP
from src.config.coder import CoderSettings
from src.storage.db import TaskStorage
from src.core.research_engine import ResearchEngine
from src.models.task import TaskStatus

def register_intelligence_tools(mcp: FastMCP, coder_settings: CoderSettings, storage: TaskStorage, research_engine: ResearchEngine):
    
    @mcp.tool()
    async def project_analyze_codebase(project_name: str) -> str:
        """Deep code analysis to detect project type, structure and dependencies."""
        project_path = os.path.join(coder_settings.projects_root, project_name)
        if not os.path.exists(project_path):
            return json.dumps({"error": f"Project {project_name} not found"})
        
        analysis = {
            "project": project_name,
            "type": "unknown",
            "structure": [],
            "dependencies": []
        }
        
        # Detect project type
        files = os.listdir(project_path)
        if "pyproject.toml" in files or "requirements.txt" in files or "setup.py" in files:
            analysis["type"] = "Python"
        elif "package.json" in files:
            analysis["type"] = "Node.js"
        elif "go.mod" in files:
            analysis["type"] = "Go"
            
        # Basic structure
        for item in files:
            if os.path.isdir(os.path.join(project_path, item)) and not item.startswith("."):
                analysis["structure"].append(item)
                
        # Basic dependencies (Python example)
        if "pyproject.toml" in files:
            try:
                with open(os.path.join(project_path, "pyproject.toml"), "r") as f:
                    content = f.read()
                    # Basic parser for dependencies
                    if "dependencies =" in content:
                        deps_block = content.split("dependencies = [")[1].split("]")[0]
                        analysis["dependencies"] = [d.strip().strip('"').strip("'") for d in deps_block.split(",") if d.strip()]
            except Exception:
                pass
                
        return json.dumps(analysis, indent=2)

    @mcp.tool()
    async def tasks_save_artifact(task_id: str, artifact_name: str, content: str, format: str = "json") -> str:
        """Saves a research artifact for a specific task."""
        task = storage.get_task(task_id)
        if not task:
            return json.dumps({"error": f"Task {task_id} not found"})
            
        try:
            # If format is json, try to parse content
            if format == "json":
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    data = content
            else:
                data = content
                
            file_path = research_engine.save_artifact(task_id, artifact_name, data, format)
            
            # Update task with artifact_path if not set
            if not task.artifact_path:
                task.artifact_path = os.path.dirname(file_path)
                storage.update_task(task)
                
            return json.dumps({"success": True, "path": file_path})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.tool()
    async def tasks_generate_research_report(task_id: str) -> str:
        """Generates a summary research report for a task based on its artifacts."""
        task = storage.get_task(task_id)
        if not task:
            return json.dumps({"error": f"Task {task_id} not found"})
            
        report = research_engine.generate_report(task)
        return json.dumps({"report": report})

    @mcp.tool()
    async def project_health_check(project_name: str) -> str:
        """Comprehensive health report for a project."""
        from src.core.project_context import ProjectContext
        ctx = ProjectContext(project_name, coder_settings, storage)
        try:
            await ctx.initialize()
            status = await ctx.get_status(include_suggestions=True)
            
            # Codebase analysis
            # We call the function directly since we are in the same module logic
            # but for a real health check we want to enrich it
            project_path = os.path.join(coder_settings.projects_root, project_name)
            has_tests = os.path.exists(os.path.join(project_path, "tests")) or os.path.exists(os.path.join(project_path, "test"))
            has_readme = os.path.exists(os.path.join(project_path, "README.md"))
            
            health = {
                "project": project_name,
                "overall_score": 0,
                "checks": {
                    "git_is_clean": not status.git.is_dirty,
                    "has_recent_commits": len(status.git.last_commit) > 0,
                    "has_open_issues": len(status.github.issues),
                    "has_stale_branches": any("stale" in s.description.lower() for s in status.suggestions),
                    "has_tests": has_tests,
                    "has_readme": has_readme,
                    "task_completion": 0 if status.tasks.total == 0 else (status.tasks.by_status.get("done", 0) / status.tasks.total * 100)
                }
            }
            
            # Simple scoring
            score = 100
            if status.git.is_dirty: score -= 20
            if not has_tests: score -= 20
            if not has_readme: score -= 10
            if len(status.github.issues) > 10: score -= 10
            
            health["overall_score"] = max(0, score)
            
            return json.dumps(health, indent=2)
        finally:
            await ctx.close()
