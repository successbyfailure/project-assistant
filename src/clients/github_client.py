import json
import os
import subprocess
from typing import List, Optional, Dict, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import logging

logger = logging.getLogger(__name__)

class GitHubMCPClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token or self._get_gh_token()
        # Using npx to run the server as it's more portable than docker in some local envs
        # unless docker is specifically preferred. 
        # The official server is @modelcontextprotocol/server-github
        # or the github/github-mcp-server docker image.
        # Let's try to use the docker image as suggested in IMPLEMENTATION_PLAN.md
        self.server_params = StdioServerParameters(
            command="docker",
            args=[
                "run", "--rm", "-i", 
                "-e", f"GITHUB_TOKEN={self.token}", 
                "ghcr.io/modelcontextprotocol/server-github"
            ],
            env={**os.environ, "GITHUB_TOKEN": self.token} if self.token else os.environ
        )
        self.session: Optional[ClientSession] = None
        self._client_context = None

    def _get_gh_token(self) -> str:
        """Attempts to get token from gh CLI."""
        try:
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except Exception as e:
            logger.warning(f"Could not get GitHub token from gh CLI: {e}")
            return os.getenv("GITHUB_TOKEN", "")

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def connect(self):
        """Connects to the github-mcp-server."""
        if not self.token:
            raise RuntimeError("GitHub token not found. Please set GITHUB_TOKEN or authenticate with 'gh auth login'.")
        
        self._client_context = stdio_client(self.server_params)
        read_stream, write_stream = await self._client_context.__aenter__()
        self.session = ClientSession(read_stream, write_stream)
        await self.session.__aenter__()
        await self.session.initialize()
        logger.info("Connected to github-mcp-server")

    async def disconnect(self):
        """Disconnects from the github-mcp-server."""
        if self.session:
            await self.session.__aexit__(None, None, None)
            self.session = None
        if self._client_context:
            await self._client_context.__aexit__(None, None, None)
            self._client_context = None
        logger.info("Disconnected from github-mcp-server")

    async def _call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        if not self.session:
            raise RuntimeError("Not connected to github-mcp-server")
        
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

    async def list_issues(self, owner: str, repo: str, state: str = "open") -> List[Dict[str, Any]]:
        """Lists issues from a GitHub repo."""
        return await self._call_tool("list_issues", {
            "owner": owner,
            "repo": repo,
            "state": state
        })

    async def get_issue(self, owner: str, repo: str, number: int) -> Dict[str, Any]:
        """Gets a single issue."""
        return await self._call_tool("get_issue", {
            "owner": owner,
            "repo": repo,
            "issue_number": number
        })

    async def create_issue(self, owner: str, repo: str, title: str, body: str = "", labels: List[str] = []) -> Dict[str, Any]:
        """Creates an issue."""
        return await self._call_tool("create_issue", {
            "owner": owner,
            "repo": repo,
            "title": title,
            "body": body,
            "labels": labels
        })

    async def list_pull_requests(self, owner: str, repo: str, state: str = "open") -> List[Dict[str, Any]]:
        """Lists pull requests."""
        return await self._call_tool("list_pull_requests", {
            "owner": owner,
            "repo": repo,
            "state": state
        })

    async def create_pull_request(self, owner: str, repo: str, title: str, head: str, base: str = "main", body: str = "") -> Dict[str, Any]:
        """Creates a pull request."""
        return await self._call_tool("create_pull_request", {
            "owner": owner,
            "repo": repo,
            "title": title,
            "head": head,
            "base": base,
            "body": body
        })
