import json
import logging
import os
from typing import Optional, Dict, Any, List

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client

logger = logging.getLogger(__name__)


class CoderMCPClient:
    def __init__(self, base_url: str, access_token: str):
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token
        self.session: Optional[ClientSession] = None
        self._client_context = None
        self._http_client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def connect(self):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        self._http_client = create_mcp_http_client(headers=headers)
        self._client_context = streamable_http_client(
            f"{self.base_url}/api/experimental/mcp/http",
            http_client=self._http_client,
        )
        read_stream, write_stream, _ = await self._client_context.__aenter__()
        self.session = ClientSession(read_stream, write_stream)
        await self.session.__aenter__()
        await self.session.initialize()
        logger.info("Connected to Coder MCP server")

    async def disconnect(self):
        if self.session:
            await self.session.__aexit__(None, None, None)
            self.session = None
        if self._client_context:
            await self._client_context.__aexit__(None, None, None)
            self._client_context = None
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        logger.info("Disconnected from Coder MCP server")

    async def _call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        if not self.session:
            raise RuntimeError("Not connected to Coder MCP server")

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

    async def list_tools(self) -> List[Dict[str, Any]]:
        if not self.session:
            raise RuntimeError("Not connected to Coder MCP server")
        result = await self.session.list_tools()
        tools = []
        for tool in getattr(result, "tools", []) or []:
            tools.append({"name": tool.name, "description": tool.description})
        return tools

    async def list_directory(self, workspace: str, path: str) -> List[Dict[str, Any]]:
        return await self._call_tool("coder_workspace_ls", {"workspace": workspace, "path": path})

    async def get_workspace(self, workspace: str) -> Dict[str, Any]:
        return await self._call_tool("coder_get_workspace", {"workspace": workspace})
