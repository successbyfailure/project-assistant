import os
import logging
from mcp.server.fastmcp import FastMCP
from src.config.coder import CoderSettings
from src.storage.db import TaskStorage
from src.server.tools.project_tools import register_project_tools
from src.server.tools.task_tools import register_task_tools
from src.server.tools.intelligence_tools import register_intelligence_tools
from src.core.research_engine import ResearchEngine

logger = logging.getLogger(__name__)

class ProjectAssistantServer:
    def __init__(self, coder_settings: CoderSettings):
        self.coder_settings = coder_settings
        self.mcp = FastMCP("Project Assistant")
        
        db_path = os.getenv("PROJECT_ASSISTANT_DB", os.path.expanduser("~/.project-assistant/db.sqlite"))
        self.storage = TaskStorage(db_path)
        
        artifact_path = os.getenv("PROJECT_ASSISTANT_ARTIFACTS", os.path.expanduser("~/.project-assistant/artifacts"))
        self.research_engine = ResearchEngine(artifact_path)
        
        self._register_tools()

    def _register_tools(self):
        register_project_tools(self.mcp, self.coder_settings, self.storage)
        register_task_tools(self.mcp, self.storage)
        register_intelligence_tools(self.mcp, self.coder_settings, self.storage, self.research_engine)

    async def run(self):
        """Starts the STDIO server."""
        logger.info("Starting Project Assistant MCP Server...")
        await self.mcp.run_stdio_async()
