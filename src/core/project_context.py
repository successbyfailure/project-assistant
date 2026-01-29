import os
import logging
from typing import List, Tuple, Optional, Dict, Any
from src.clients.git_client import GitMCPClient
from src.clients.github_client import GitHubMCPClient
from src.storage.db import TaskStorage
from src.models.project import ProjectStatus, GitInfo, GitHubInfo, TaskSummary, Suggestion
from src.config.coder import CoderSettings
from src.core.suggestions import SuggestionsEngine

logger = logging.getLogger(__name__)

class ProjectContext:
    def __init__(self, project_name: str, coder_settings: CoderSettings, storage: TaskStorage):
        self.project_name = project_name
        self.coder_settings = coder_settings
        self.storage = storage
        self.project_path = os.path.join(coder_settings.projects_root, project_name)
        self.git_client = GitMCPClient(self.project_path)
        self.github_client: Optional[GitHubMCPClient] = None # Will be initialized if needed
        self.suggestions_engine = SuggestionsEngine()

    async def initialize(self):
        """Connects to MCP clients."""
        await self.git_client.connect()
        # GitHub client connection might need a token, we handle it inside
        try:
            self.github_client = GitHubMCPClient()
            await self.github_client.connect()
        except Exception as e:
            logger.warning(f"Could not connect to GitHub MCP server: {e}")
            self.github_client = None

    async def close(self):
        """Disconnects from MCP clients."""
        await self.git_client.disconnect()
        if self.github_client:
            await self.github_client.disconnect()

    async def get_status(self, include_suggestions: bool = True) -> ProjectStatus:
        """Aggregates data from multi MCP sources."""
        git_info = await self.get_git_info()
        github_info = await self.get_github_info(git_info)
        tasks = self.storage.list_tasks(project_name=self.project_name)
        
        task_summary = self._create_task_summary(tasks)
        
        suggestions = []
        if include_suggestions:
            suggestions = self.suggestions_engine.generate_suggestions(
                git_info=git_info,
                github_info=github_info,
                tasks=tasks
            )

        return ProjectStatus(
            project=self.project_name,
            path=self.project_path,
            git=git_info,
            github=github_info,
            tasks=task_summary,
            suggestions=suggestions
        )

    async def get_git_info(self) -> GitInfo:
        """Fetches git status from GitMCPClient."""
        status = await self.git_client.get_status()
        branches = []
        try:
            branches = await self.git_client.list_branches()
        except Exception:
            logger.debug("Failed to fetch branches")

        return GitInfo(
            branch=status.get("branch", "unknown"),
            is_dirty=status.get("is_dirty", False),
            ahead=status.get("ahead", 0),
            behind=status.get("behind", 0),
            last_commit=status.get("last_commit", {}),
            modified_files=status.get("modified_files", []),
            untracked_files=status.get("untracked_files", []),
            branches=branches
        )

    async def get_github_info(self, git_info: GitInfo) -> GitHubInfo:
        """Fetches GitHub info if possible."""
        if not self.github_client:
            return GitHubInfo()
        
        # Try to parse owner/repo from remote or last commit perhaps?
        # Usually from `git remote -v` but GitMCP doesn't have a direct tool for it?
        # Wait, mcp-server-git might have git_list_remotes
        try:
            remotes = await self.git_client._call_tool("git_list_remotes", {})
            # remotes: [{"name": "origin", "url": "..."}]
            origin = next((r["url"] for r in remotes if r["name"] == "origin"), None)
            if origin:
                owner, repo = self._parse_github_remote(origin)
                issues = await self.github_client.list_issues(owner, repo)
                return GitHubInfo(owner=owner, repo=repo, issues=issues)
        except Exception as e:
            logger.debug(f"Failed to get GitHub info: {e}")
            
        return GitHubInfo()

    def _parse_github_remote(self, url: str) -> Tuple[str, str]:
        """Extracts owner/repo from GitHub URL."""
        # Handles https://github.com/owner/repo.git or git@github.com:owner/repo.git
        if url.endswith(".git"):
            url = url[:-4]
        
        if "github.com" in url:
            if url.startswith("https://"):
                parts = url.split("github.com/")[1].split("/")
            else: # git@github.com:owner/repo
                parts = url.split("github.com:")[1].split("/")
            return parts[0], parts[1]
        
        raise ValueError(f"Not a GitHub URL: {url}")

    def _create_task_summary(self, tasks: List[Any]) -> TaskSummary:
        by_status = {}
        for t in tasks:
            by_status[t.status] = by_status.get(t.status, 0) + 1
        
        recent = [
            {"id": t.id, "title": t.title, "status": t.status}
            for t in sorted(tasks, key=lambda x: x.updated_at, reverse=True)[:5]
        ]
        
        return TaskSummary(
            total=len(tasks),
            by_status=by_status,
            recent=recent
        )
