from fastapi import APIRouter, Depends, HTTPException
from src.api.middleware.auth import get_current_user
from src.core.agents.pm_agent import FulcrumPMAgent
from src.models.user import UserDB, ProjectDB, AccountDB
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.storage.postgres import get_db
from sqlalchemy.future import select
import httpx
import uuid

router = APIRouter(prefix="/projects", tags=["projects"])

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    source_type: str = "local"
    remote_url: Optional[str] = None
    github_repo: Optional[str] = None
    workspace_id: Optional[str] = None
    workspace_name: Optional[str] = None
    workspace_path: Optional[str] = None
    workspace_ref: Optional[str] = None
    production_url: Optional[str] = None
    testing_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    codespace_id: Optional[str] = None
    codespace_name: Optional[str] = None
    codespace_url: Optional[str] = None

class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    source_type: str
    remote_url: Optional[str] = None
    github_repo: Optional[str] = None
    workspace_id: Optional[str] = None
    workspace_name: Optional[str] = None
    workspace_path: Optional[str] = None
    workspace_ref: Optional[str] = None
    production_url: Optional[str] = None
    testing_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    codespace_id: Optional[str] = None
    codespace_name: Optional[str] = None
    codespace_url: Optional[str] = None

    class Config:
        from_attributes = True

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    source_type: Optional[str] = None
    remote_url: Optional[str] = None
    github_repo: Optional[str] = None
    workspace_id: Optional[str] = None
    workspace_name: Optional[str] = None
    workspace_path: Optional[str] = None
    workspace_ref: Optional[str] = None
    production_url: Optional[str] = None
    testing_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    codespace_id: Optional[str] = None
    codespace_name: Optional[str] = None
    codespace_url: Optional[str] = None

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


@router.get("/{project_id}/github/summary")
async def get_project_github_summary(
    project_id: str,
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ProjectDB).where(ProjectDB.id == project_id, ProjectDB.user_id == current_user.id)
    )
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    repo_full = project.github_repo
    if not repo_full and project.remote_url:
        match = None
        try:
            import re
            match = re.search(r"github\\.com/([^/]+/[^/]+)(?:\\.git)?$", project.remote_url)
        except Exception:
            match = None
        if match:
            repo_full = match.group(1)
    if not repo_full:
        raise HTTPException(status_code=400, detail="GitHub repo not configured for this project.")

    account_res = await db.execute(
        select(AccountDB).where(
            (AccountDB.user_id == current_user.id) & (AccountDB.provider == "github")
        )
    )
    account = account_res.scalar_one_or_none()
    if not account or not account.access_token:
        raise HTTPException(status_code=400, detail="GitHub not connected.")

    owner, repo = repo_full.split("/", 1)
    headers = {"Authorization": f"Bearer {account.access_token}"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            issues_res = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/issues",
                params={"state": "open", "per_page": 5},
                headers=headers,
            )
            pulls_res = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/pulls",
                params={"state": "open", "per_page": 5},
                headers=headers,
            )
        if issues_res.status_code != 200 or pulls_res.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to fetch GitHub data.")
        issues_data = issues_res.json()
        pulls_data = pulls_res.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"GitHub request failed: {str(e)}")

    issues = [
        {"number": i.get("number"), "title": i.get("title"), "url": i.get("html_url")}
        for i in issues_data
        if isinstance(i, dict) and "pull_request" not in i
    ]
    pulls = [
        {"number": p.get("number"), "title": p.get("title"), "url": p.get("html_url")}
        for p in pulls_data
        if isinstance(p, dict)
    ]
    return {"repo": repo_full, "issues": issues, "pull_requests": pulls}

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
