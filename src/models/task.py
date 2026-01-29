from enum import Enum
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class TaskType(str, Enum):
    STANDARD = "standard"
    RESEARCH = "research"
    DEVELOPMENT = "development"

class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Deliverable(BaseModel):
    type: str  # "report", "data", "code"
    format: str  # "markdown", "json", "python"
    description: Optional[str] = None

class Task(BaseModel):
    id: str
    user_id: str
    project_name: str
    type: TaskType
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    assigned_to: Optional[str] = None
    deliverables: List[Deliverable] = []
    context_files: List[str] = []
    approval_required: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    github_issue_number: Optional[int] = None
    tags: List[str] = []
    artifact_path: Optional[str] = None
