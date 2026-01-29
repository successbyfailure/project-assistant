import json
import os
from typing import List, Optional, Dict, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import logging

logger = logging.getLogger(__name__)

class FileSystemMCPClient:
    def __init__(self, root_path: str):
        self.root_path = root_path
        self.server_params = StdioServerParameters(
            command="uvx",
            args=["mcp-server-filesystem", root_path],
        )
        self.session: Optional[ClientSession] = None
        self._client_context = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def connect(self):
        """Connects to the mcp-server-filesystem."""
        self._client_context = stdio_client(self.server_params)
        read_stream, write_stream = await self._client_context.__aenter__()
        self.session = ClientSession(read_stream, write_stream)
        await self.session.__aenter__()
        await self.session.initialize()
        logger.info(f"Connected to mcp-server-filesystem for {self.root_path}")

    async def disconnect(self):
        """Disconnects from the mcp-server-filesystem."""
        if self.session:
            await self.session.__aexit__(None, None, None)
            self.session = None
        if self._client_context:
            await self._client_context.__aexit__(None, None, None)
            self._client_context = None
        logger.info(f"Disconnected from mcp-server-filesystem for {self.root_path}")

    async def _call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        if not self.session:
            raise RuntimeError("Not connected to mcp-server-filesystem")
        
        result = await self.session.call_tool(name, arguments)
        if hasattr(result, "is_error") and result.is_error:
            raise RuntimeError(f"Tool {name} failed: {result.content}")
        
        if isinstance(result.content, list) and len(result.content) > 0:
            text = result.content[0].text
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
        return result.content

    async def list_directory(self, path: str = ".") -> List[Dict[str, Any]]:
        return await self._call_tool("list_directory", {"path": path})

    async def read_file(self, path: str) -> str:
        return await self._call_tool("read_file", {"path": path})

    async def write_file(self, path: str, content: str) -> Dict[str, Any]:
        return await self._call_tool("write_file", {"path": path, "content": content})

    async def search_files(self, path: str, pattern: str) -> List[str]:
        return await self._call_tool("search_files", {"path": path, "pattern": pattern})
