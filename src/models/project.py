from typing import List, Optional, Dict
from pydantic import BaseModel

class GitInfo(BaseModel):
    branch: str
    is_dirty: bool
    ahead: int
    behind: int
    last_commit: Dict[str, str]
    modified_files: List[str]
    untracked_files: List[str]
    branches: List[Dict[str, Any]] = []

class GitHubInfo(BaseModel):
    owner: Optional[str] = None
    repo: Optional[str] = None
    issues: List[Dict] = []

class TaskSummary(BaseModel):
    total: int
    by_status: Dict[str, int]
    recent: List[Dict]

class Suggestion(BaseModel):
    priority: str
    action: str
    description: str
    can_automate: bool = False
    files: List[str] = []
    issue_number: Optional[int] = None

class ProjectStatus(BaseModel):
    project: str
    path: str
    git: GitInfo
    github: GitHubInfo
    tasks: TaskSummary
    suggestions: List[Suggestion] = []
