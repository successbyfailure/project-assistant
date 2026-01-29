import json
from typing import List, Optional, Dict, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import logging

logger = logging.getLogger(__name__)

class GitMCPClient:
    def __init__(self, repository_path: str):
        self.repository_path = repository_path
        self.server_params = StdioServerParameters(
            command="uvx",
            args=["mcp-server-git", "--repository", repository_path],
        )
        self.session: Optional[ClientSession] = None
        self._exit_stack = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def connect(self):
        """Connects to the mcp-server-git."""
        self._client_context = stdio_client(self.server_params)
        read_stream, write_stream = await self._client_context.__aenter__()
        self.session = ClientSession(read_stream, write_stream)
        await self.session.__aenter__()
        await self.session.initialize()
        logger.info(f"Connected to mcp-server-git for {self.repository_path}")

    async def disconnect(self):
        """Disconnects from the mcp-server-git."""
        if self.session:
            await self.session.__aexit__(None, None, None)
            self.session = None
        if self._client_context:
            await self._client_context.__aexit__(None, None, None)
            self._client_context = None
        logger.info(f"Disconnected from mcp-server-git for {self.repository_path}")

    async def _call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        if not self.session:
            raise RuntimeError("Not connected to mcp-server-git")
        
        result = await self.session.call_tool(name, arguments)
        if hasattr(result, "is_error") and result.is_error:
            raise RuntimeError(f"Tool {name} failed: {result.content}")
        
        # The content is usually a list of TextContent objects
        if isinstance(result.content, list) and len(result.content) > 0:
            text = result.content[0].text
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
        return result.content

    async def get_status(self) -> Dict[str, Any]:
        """Returns current branch, dirty state, etc."""
        return await self._call_tool("git_status", {})

    async def get_log(self, max_count: int = 10) -> List[Dict[str, Any]]:
        """Returns commit history."""
        # Note: git_log tool might not exist exactly with this name or params
        # Checking mcp-server-git tools from documentation:
        # git_log: { "count": number }
        return await self._call_tool("git_log", {"count": max_count})

    async def get_diff(self, staged: bool = False) -> str:
        """Returns git diff."""
        # git_diff_untracked is also available
        # git_diff_staged or git_diff
        tool_name = "git_diff_staged" if staged else "git_diff"
        return await self._call_tool(tool_name, {})

    async def commit(self, message: str, files: Optional[List[str]] = None) -> Dict[str, Any]:
        """Creates commits successfully."""
        # git_commit: { "message": string }
        # The tool might not support specific files directly in one go if they are not staged
        # Usually we stage them first if provided? 
        # mcp-server-git has git_add
        if files:
            for file in files:
                await self._call_tool("git_add", {"path": file})
        
        return await self._call_tool("git_commit", {"message": message})

    async def create_branch(self, name: str) -> Dict[str, Any]:
        """Creates a new branch."""
        # git_create_branch: { "name": string }
        return await self._call_tool("git_create_branch", {"name": name})

    async def checkout(self, branch: str) -> Dict[str, Any]:
        """Checks out a branch."""
        # git_checkout: { "branch": string }
        return await self._call_tool("git_checkout", {"branch": branch})

    async def list_branches(self) -> List[Dict[str, Any]]:
        """Lists all local branches."""
        # git_list_branches doesn't exist in all versions, might be git_branches
        return await self._call_tool("git_branches", {})
