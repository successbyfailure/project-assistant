from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Enum as SQLEnum, JSON
from datetime import datetime
import os
from src.storage.base import Base
from src.models.user import UserDB, AccountDB, ProjectDB
from src.models.task import TaskType, TaskStatus, TaskPriority

class TaskDB(Base):
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    github_issue_number = Column(Integer, nullable=True)
    tags = Column(JSON)
    artifact_path = Column(String)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/fulcrum")

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        # Warning: This creates tables but doesn't handle migrations well. 
        # In a real app, use Alembic.
        await conn.run_sync(Base.metadata.create_all)
