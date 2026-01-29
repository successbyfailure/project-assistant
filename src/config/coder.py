import os
import subprocess
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class CoderSettings(BaseSettings):
    workspace_name: Optional[str] = Field(default=None, env="CODER_WORKSPACE_NAME")
    projects_root: str = Field(default="/home/coder/Projects", env="PROJECTS_ROOT")
    
    @property
    def is_coder_workspace(self) -> bool:
        """Detects if running inside a Coder workspace."""
        return self.workspace_name is not None or os.getenv("CODER") == "true"

    def get_available_projects(self) -> List[str]:
        """Lists all git repositories in the projects root."""
        if not os.path.exists(self.projects_root):
            return []
        
        projects = []
        for d in os.listdir(self.projects_root):
            path = os.path.join(self.projects_root, d)
            if os.path.isdir(path) and os.path.exists(os.path.join(path, ".git")):
                projects.append(d)
        return sorted(projects)

    def verify_gh_auth(self) -> bool:
        """Checks if gh CLI is authenticated."""
        try:
            result = subprocess.run(
                ["gh", "auth", "status"], 
                capture_output=True, 
                text=True, 
                check=False
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

settings = CoderSettings()
