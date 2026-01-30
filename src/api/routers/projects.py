from fastapi import APIRouter, Depends, HTTPException
from src.api.middleware.auth import get_current_user
from src.core.agents.pm_agent import FulcrumPMAgent
from src.models.user import UserDB, ProjectDB
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.storage.postgres import get_db
from sqlalchemy.future import select
import uuid

router = APIRouter(prefix="/projects", tags=["projects"])

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    source_type: str = "local"
    remote_url: Optional[str] = None
    workspace_id: Optional[str] = None
    workspace_name: Optional[str] = None
    workspace_path: Optional[str] = None
    production_url: Optional[str] = None
    testing_url: Optional[str] = None
    thumbnail_url: Optional[str] = None

class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    source_type: str
    remote_url: Optional[str] = None
    workspace_id: Optional[str] = None
    workspace_name: Optional[str] = None
    workspace_path: Optional[str] = None
    production_url: Optional[str] = None
    testing_url: Optional[str] = None
    thumbnail_url: Optional[str] = None

    class Config:
        from_attributes = True

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    source_type: Optional[str] = None
    remote_url: Optional[str] = None
    workspace_id: Optional[str] = None
    workspace_name: Optional[str] = None
    workspace_path: Optional[str] = None
    production_url: Optional[str] = None
    testing_url: Optional[str] = None
    thumbnail_url: Optional[str] = None

@router.post("", response_model=ProjectResponse)
@router.post("/", response_model=ProjectResponse, include_in_schema=False)
async def create_project(
    project_in: ProjectCreate, 
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    print(f"DEBUG: Creating project for user {current_user.id}: {project_in.model_dump()}")
    try:
        project_id = str(uuid.uuid4())
        db_project = ProjectDB(
            id=project_id,
            user_id=current_user.id,
            **project_in.model_dump()
        )
        db.add(db_project)
        await db.commit()
        await db.refresh(db_project)
        print(f"DEBUG: Project created successfully: {project_id}")
        return db_project
    except Exception as e:
        print(f"DEBUG: Error creating project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=List[ProjectResponse])
@router.get("/", response_model=List[ProjectResponse], include_in_schema=False)
async def list_projects(
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(ProjectDB).where(ProjectDB.user_id == current_user.id))
    return result.scalars().all()

@router.get("/overview")
async def get_overview(
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    agent = FulcrumPMAgent(current_user.id, db)
    return await agent.get_global_overview()

@router.get("/{project_id}/status")
async def get_project_status(
    project_id: str, 
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify project ownership
    result = await db.execute(
        select(ProjectDB).where(ProjectDB.id == project_id, ProjectDB.user_id == current_user.id)
    )
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    agent = FulcrumPMAgent(current_user.id, db)
    return {"project": project.name, "status": "Local metadata only (Phase 1)"}

@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_in: ProjectUpdate,
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ProjectDB).where(ProjectDB.id == project_id, ProjectDB.user_id == current_user.id)
    )
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    updates = project_in.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(project, key, value)

    await db.commit()
    await db.refresh(project)
    return project
