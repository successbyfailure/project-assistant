import json
from typing import Optional, List
from mcp.server.fastmcp import FastMCP
from src.storage.db import TaskStorage
from src.core.task_manager import TaskManager
from src.models.task import TaskStatus, TaskType, TaskPriority

def register_task_tools(mcp: FastMCP, storage: TaskStorage):
    task_manager = TaskManager(storage)

    @mcp.tool()
    async def tasks_list(project_name: Optional[str] = None, status: Optional[str] = None) -> str:
        """Lists tasks with optional filtering by project and status."""
        task_status = TaskStatus(status) if status else None
        tasks = storage.list_tasks(project_name=project_name, status=task_status)
        return json.dumps([t.model_dump() for t in tasks], indent=2, default=str)

    @mcp.tool()
    async def tasks_create(
        project_name: str, 
        title: str, 
        description: Optional[str] = None,
        task_type: str = "standard",
        priority: str = "medium"
    ) -> str:
        """Creates a new task."""
        data = {
            "description": description,
            "type": TaskType(task_type),
            "priority": TaskPriority(priority)
        }
        task = await task_manager.create_task(project_name, title, data)
        return task.model_dump_json(indent=2)

    @mcp.tool()
    async def tasks_update(task_id: str, status: str) -> str:
        """Updates a task status."""
        task = await task_manager.update_task_status(task_id, TaskStatus(status))
        return task.model_dump_json(indent=2)

    @mcp.tool()
    async def tasks_get(task_id: str) -> str:
        """Gets detailed information about a single task."""
        task = storage.get_task(task_id)
        if not task:
            return json.dumps({"error": f"Task {task_id} not found"})
        return task.model_dump_json(indent=2)
