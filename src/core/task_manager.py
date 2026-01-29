import uuid
from typing import List, Optional, Dict
from datetime import datetime
from src.models.task import Task, TaskStatus
from src.storage.db import TaskStorage
from src.clients.github_client import GitHubMCPClient

class TaskManager:
    def __init__(self, storage: TaskStorage, github_client: Optional[GitHubMCPClient] = None):
        self.storage = storage
        self.github_client = github_client

    async def create_task(self, project_name: str, title: str, task_data: Optional[Dict] = None, create_github_issue: bool = False) -> Task:
        task_id = str(uuid.uuid4())[:8]
        data = task_data or {}
        
        task = Task(
            id=task_id,
            project_name=project_name,
            title=title,
            **data
        )
        
        if create_github_issue and self.github_client:
            # Need owner/repo. This logic probably belongs elsewhere or we need more context.
            # For now, let's assume we can't do it without owner/repo known.
            pass
            
        return self.storage.create_task(task)

    async def update_task_status(self, task_id: str, new_status: TaskStatus) -> Task:
        task = self.storage.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.status = new_status
        task.updated_at = datetime.now()
        if new_status == TaskStatus.DONE:
            task.completed_at = datetime.now()
            
        return self.storage.update_task(task)

    async def link_github_issue(self, task_id: str, issue_number: int) -> Task:
        task = self.storage.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
            
        task.github_issue_number = issue_number
        return self.storage.update_task(task)

    async def get_tasks_for_project(self, project_name: str) -> List[Task]:
        return self.storage.list_tasks(project_name=project_name)
