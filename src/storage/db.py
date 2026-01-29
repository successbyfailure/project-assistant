from sqlalchemy import Column, String, Integer, Boolean, DateTime, Enum as SQLEnum, JSON, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json
import os
from typing import List, Optional
from src.models.task import Task, TaskType, TaskStatus, TaskPriority, Deliverable

Base = declarative_base()

class TaskDB(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True)
    project_name = Column(String, nullable=False, index=True)
    type = Column(SQLEnum(TaskType))
    title = Column(String, nullable=False)
    description = Column(String)
    status = Column(SQLEnum(TaskStatus), index=True)
    priority = Column(SQLEnum(TaskPriority))
    assigned_to = Column(String)
    deliverables = Column(JSON)
    context_files = Column(JSON)
    approval_required = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    github_issue_number = Column(Integer, nullable=True)
    tags = Column(JSON)
    artifact_path = Column(String)

class TaskStorage:
    def __init__(self, db_path: str):
        self.db_path = db_path
        engine_url = f"sqlite:///{db_path}"
        self.engine = create_engine(engine_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def _to_pydantic(self, db_task: TaskDB) -> Task:
        return Task(
            id=db_task.id,
            project_name=db_task.project_name,
            type=db_task.type,
            title=db_task.title,
            description=db_task.description,
            status=db_task.status,
            priority=db_task.priority,
            assigned_to=db_task.assigned_to,
            deliverables=[Deliverable(**d) for d in (db_task.deliverables or [])],
            context_files=db_task.context_files or [],
            approval_required=db_task.approval_required,
            created_at=db_task.created_at,
            updated_at=db_task.updated_at,
            completed_at=db_task.completed_at,
            github_issue_number=db_task.github_issue_number,
            tags=db_task.tags or [],
            artifact_path=db_task.artifact_path
        )

    def _to_db(self, task: Task) -> TaskDB:
        return TaskDB(
            id=task.id,
            project_name=task.project_name,
            type=task.type,
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            assigned_to=task.assigned_to,
            deliverables=[d.model_dump() for d in task.deliverables],
            context_files=task.context_files,
            approval_required=task.approval_required,
            created_at=task.created_at,
            updated_at=task.updated_at,
            completed_at=task.completed_at,
            github_issue_number=task.github_issue_number,
            tags=task.tags,
            artifact_path=task.artifact_path
        )

    def create_task(self, task: Task) -> Task:
        with self.Session() as session:
            db_task = self._to_db(task)
            session.add(db_task)
            session.commit()
            return task

    def get_task(self, task_id: str) -> Optional[Task]:
        with self.Session() as session:
            db_task = session.get(TaskDB, task_id)
            if db_task:
                return self._to_pydantic(db_task)
            return None

    def list_tasks(self, project_name: Optional[str] = None, 
                   status: Optional[TaskStatus] = None) -> List[Task]:
        with self.Session() as session:
            query = session.query(TaskDB)
            if project_name:
                query = query.filter(TaskDB.project_name == project_name)
            if status:
                query = query.filter(TaskDB.status == status)
            
            return [self._to_pydantic(db_t) for db_t in query.all()]

    def update_task(self, task: Task) -> Task:
        with self.Session() as session:
            db_task = session.get(TaskDB, task.id)
            if not db_task:
                raise ValueError(f"Task {task.id} not found")
            
            # Simple update by merging
            updated_db_task = self._to_db(task)
            for column in TaskDB.__table__.columns:
                if column.name != 'id':
                    setattr(db_task, column.name, getattr(updated_db_task, column.name))
            
            session.commit()
            return task

    def delete_task(self, task_id: str) -> bool:
        with self.Session() as session:
            db_task = session.get(TaskDB, task_id)
            if db_task:
                session.delete(db_task)
                session.commit()
                return True
            return False
