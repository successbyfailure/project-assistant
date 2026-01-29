import json
import logging
from mcp.server.fastmcp import FastMCP
from src.config.coder import CoderSettings
from src.core.project_context import ProjectContext
from src.storage.db import TaskStorage

logger = logging.getLogger(__name__)

def register_project_tools(mcp: FastMCP, coder_settings: CoderSettings, storage: TaskStorage):
    
    @mcp.tool()
    async def project_list_available() -> str:
        """Lists all projects available in the /Projects directory."""
        projects = coder_settings.get_available_projects()
        return json.dumps({
            "projects": projects,
            "total": len(projects),
            "location": coder_settings.projects_root
        }, indent=2)

    @mcp.tool()
    async def project_status(project_name: str, include_suggestions: bool = True) -> str:
        """Gets a comprehensive status of a project including Git, GitHub and Tasks."""
        ctx = ProjectContext(project_name, coder_settings, storage)
        try:
            await ctx.initialize()
            status = await ctx.get_status(include_suggestions=include_suggestions)
            return status.model_dump_json(indent=2)
        finally:
            await ctx.close()

    @mcp.tool()
    async def project_suggest_next_steps(project_name: str) -> str:
        """Gets AI-powered suggestions based on current project state."""
        ctx = ProjectContext(project_name, coder_settings, storage)
        try:
            await ctx.initialize()
            status = await ctx.get_status(include_suggestions=True)
            return json.dumps({"suggestions": [s.model_dump() for s in status.suggestions]}, indent=2)
        finally:
            await ctx.close()
