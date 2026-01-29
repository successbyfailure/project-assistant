import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.models.task import Task, Deliverable

logger = logging.getLogger(__name__)

class ResearchEngine:
    def __init__(self, base_artifact_path: str):
        self.base_artifact_path = base_artifact_path
        os.makedirs(base_artifact_path, exist_ok=True)

    def get_task_artifact_path(self, task_id: str) -> str:
        path = os.path.join(self.base_artifact_path, task_id)
        os.makedirs(path, exist_ok=True)
        return path

    def save_artifact(self, task_id: str, name: str, content: Any, format: str = "json"):
        path = self.get_task_artifact_path(task_id)
        file_path = os.path.join(path, f"{name}.{format}")
        
        with open(file_path, "w") as f:
            if format == "json":
                json.dump(content, f, indent=2)
            else:
                f.write(str(content))
        
        logger.info(f"Saved artifact {name} for task {task_id} at {file_path}")
        return file_path

    def list_artifacts(self, task_id: str) -> List[str]:
        path = self.get_task_artifact_path(task_id)
        return os.listdir(path)

    def generate_report(self, task: Task) -> str:
        """Generates a markdown report summarizing all artifacts for a task."""
        path = self.get_task_artifact_path(task.id)
        artifacts = self.list_artifacts(task.id)
        
        report = [
            f"# Research Report: {task.title}",
            f"**Task ID**: {task.id}",
            f"**Status**: {task.status}",
            f"**Description**: {task.description or 'No description provided.'}",
            "\n## Deliverables Status"
        ]
        
        for d in task.deliverables:
            report.append(f"- [{ 'x' if task.status == 'done' else ' ' }] {d.description or d.type} ({d.format})")
            
        report.append("\n## Artifacts Found")
        for art in artifacts:
            report.append(f"- {art}")
            
        report_path = os.path.join(path, "report.md")
        with open(report_path, "w") as f:
            f.write("\n".join(report))
            
        return "\n".join(report)
