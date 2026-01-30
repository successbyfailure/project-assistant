from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import os
import httpx
from datetime import datetime, timedelta
from jose import jwt
from pydantic import BaseModel
import uuid

from src.storage.postgres import get_db
from src.api.middleware.auth import get_current_user
from src.core.auth import security
from src.clients.coder_mcp_client import CoderMCPClient
from src.models.user import AccountDB, UserDB

router = APIRouter(prefix="/integrations", tags=["integrations"])


class CoderConnectRequest(BaseModel):
    name: str | None = None
    url: str
    token: str

class CoderWorkspaceFiles(BaseModel):
    path: str


def _base_domain() -> str:
    base = os.getenv("BASE_DOMAIN", "http://localhost:8000")
    return base.rstrip("/")


def _github_redirect_uri() -> str:
    return f"{_base_domain()}/auth/github/callback"


def _coder_redirect_uri() -> str:
    return f"{_base_domain()}/auth/coder/callback"


def _coder_auth_headers(account: AccountDB) -> dict:
    extra = account.extra_metadata or {}
    if extra.get("auth_type") == "bearer":
        return {"Authorization": f"Bearer {account.access_token}"}
    return {"Coder-Session-Token": account.access_token}


@router.get("/github/login")
async def github_login(
    current_user: UserDB = Depends(get_current_user),
):
    client_id = os.getenv("GITHUB_CLIENT_ID")
    client_secret = os.getenv("GITHUB_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(status_code=400, detail="GitHub OAuth not configured.")

    state = jwt.encode(
        {
            "sub": current_user.id,
            "typ": "github_oauth",
            "exp": (datetime.utcnow() + timedelta(minutes=10)),
        },
        security.SECRET_KEY,
        algorithm=security.ALGORITHM,
    )

    params = {
        "client_id": client_id,
        "redirect_uri": _github_redirect_uri(),
        "scope": "read:user repo",
        "state": state,
    }
    query = httpx.QueryParams(params)
    return {"url": f"https://github.com/login/oauth/authorize?{query}"}


@router.get("/github/status")
async def github_status(
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    client_id = os.getenv("GITHUB_CLIENT_ID")
    client_secret = os.getenv("GITHUB_CLIENT_SECRET")
    configured = bool(client_id and client_secret)
    result = await db.execute(
        select(AccountDB).where(
            (AccountDB.user_id == current_user.id) & (AccountDB.provider == "github")
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        return {"connected": False, "configured": configured}
    return {"connected": True, "username": account.name, "configured": configured}


@router.get("/github/repos")
async def github_repos(
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(AccountDB).where(
            (AccountDB.user_id == current_user.id) & (AccountDB.provider == "github")
        )
    )
    account = result.scalar_one_or_none()
    if not account or not account.access_token:
        raise HTTPException(status_code=400, detail="GitHub not connected.")

    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(
            "https://api.github.com/user/repos?per_page=100&sort=updated",
            headers={"Authorization": f"Bearer {account.access_token}"},
        )
        if res.status_code != 200:
            raise HTTPException(status_code=502, detail="Failed to fetch GitHub repositories.")
        data = res.json()
    repos = [
        {"id": r.get("id"), "full_name": r.get("full_name"), "description": r.get("description")}
        for r in data
    ]
    return {"repos": repos}


@router.post("/coder/oauth/login")
async def coder_oauth_login(
    current_user: UserDB = Depends(get_current_user),
):
    client_id = os.getenv("CODER_OAUTH_CLIENT_ID")
    client_secret = os.getenv("CODER_OAUTH_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(status_code=400, detail="Coder OAuth not configured.")

    base_url = os.getenv("CODER_BASE_URL")
    if not base_url:
        raise HTTPException(status_code=400, detail="Coder base URL not configured.")
    base_url = base_url.rstrip("/")
    discovery_url = f"{base_url}/.well-known/oauth-authorization-server"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            discovery_res = await client.get(discovery_url)
            if discovery_res.status_code != 200:
                raise HTTPException(status_code=502, detail="Failed to load Coder OAuth discovery.")
            discovery = discovery_res.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Error connecting to Coder: {str(exc)}")

    authorization_endpoint = discovery.get("authorization_endpoint")
    token_endpoint = discovery.get("token_endpoint")
    if not authorization_endpoint or not token_endpoint:
        raise HTTPException(status_code=502, detail="Invalid Coder OAuth discovery response.")

    state = jwt.encode(
        {
            "sub": current_user.id,
            "typ": "coder_oauth",
            "iss": base_url,
            "token_endpoint": token_endpoint,
            "exp": (datetime.utcnow() + timedelta(minutes=10)),
        },
        security.SECRET_KEY,
        algorithm=security.ALGORITHM,
    )

    params = {
        "client_id": client_id,
        "redirect_uri": _coder_redirect_uri(),
        "response_type": "code",
        "state": state,
    }
    scope = os.getenv("CODER_OAUTH_SCOPE")
    if scope:
        params["scope"] = scope

    query = httpx.QueryParams(params)
    return {"url": f"{authorization_endpoint}?{query}"}


@router.get("/coder/accounts")
async def coder_accounts(
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(AccountDB).where(
            (AccountDB.user_id == current_user.id) & (AccountDB.provider == "coder")
        )
    )
    accounts = result.scalars().all()
    return {
        "accounts": [
            {"id": acc.id, "name": acc.name, "api_endpoint": acc.api_endpoint}
            for acc in accounts
        ]
    }


@router.delete("/coder/accounts/{account_id}")
async def delete_coder_account(
    account_id: str,
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(AccountDB).where(AccountDB.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account or account.provider != "coder":
        raise HTTPException(status_code=404, detail="Coder account not found.")
    if account.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this account.")

    await db.delete(account)
    await db.commit()
    return {"ok": True}


@router.post("/coder/connect")
async def coder_connect(
    payload: "CoderConnectRequest",
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    url = payload.url
    token = payload.token
    name = payload.name or None
    if not url or not token:
        raise HTTPException(status_code=400, detail="URL and token are required.")

    base_url = url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(
                f"{base_url}/api/v2/users/me",
                headers={"Coder-Session-Token": token},
            )
            if res.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to validate Coder token. Status: {res.status_code}",
                )
            user_data = res.json()
    except HTTPException:
        raise
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to Coder: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Coder MCP error: {str(e)}")

    result = await db.execute(
        select(AccountDB).where(
            (AccountDB.user_id == current_user.id)
            & (AccountDB.provider == "coder")
            & (AccountDB.api_endpoint == base_url)
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        account = AccountDB(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            provider="coder",
            name=name or user_data.get("username"),
            provider_user_id=str(user_data.get("id")),
            access_token=token,
            api_endpoint=base_url,
            extra_metadata={"auth_type": "session"},
        )
        db.add(account)
    else:
        account.access_token = token
        account.name = name or account.name
        account.provider_user_id = str(user_data.get("id"))
        account.extra_metadata = {**(account.extra_metadata or {}), "auth_type": "session"}

    await db.commit()
    return {"ok": True}


@router.post("/coder/exchange")
async def coder_exchange(
    payload: "CoderConnectRequest",
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    url = payload.url
    session_token = payload.token
    name = payload.name or None
    if not url or not session_token:
        raise HTTPException(status_code=400, detail="URL and session token are required.")

    base_url = url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            me_res = await client.get(
                f"{base_url}/api/v2/users/me",
                headers={"Coder-Session-Token": session_token},
            )
            if me_res.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to validate Coder session token. Status: {me_res.status_code}",
                )
            user_data = me_res.json()

            token_res = await client.post(
                f"{base_url}/api/v2/users/me/keys/tokens",
                headers={"Coder-Session-Token": session_token},
                json={"name": "Fulcrum", "scope": "all"},
            )
            if token_res.status_code != 201 and token_res.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to create Coder API token. Status: {token_res.status_code}",
                )
            token_data = token_res.json()
            api_token = token_data.get("key") or token_data.get("token") or token_data.get("value")
            if not api_token:
                raise HTTPException(status_code=400, detail="Coder API token not returned.")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to Coder: {str(e)}")

    result = await db.execute(
        select(AccountDB).where(
            (AccountDB.user_id == current_user.id)
            & (AccountDB.provider == "coder")
            & (AccountDB.api_endpoint == base_url)
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        account = AccountDB(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            provider="coder",
            name=name or user_data.get("username"),
            provider_user_id=str(user_data.get("id")),
            access_token=api_token,
            api_endpoint=base_url,
            extra_metadata={"auth_type": "session"},
        )
        db.add(account)
    else:
        account.access_token = api_token
        account.name = name or account.name
        account.provider_user_id = str(user_data.get("id"))
        account.extra_metadata = {**(account.extra_metadata or {}), "auth_type": "session"}

    await db.commit()
    return {"ok": True}


@router.get("/coder/workspaces")
async def coder_workspaces(
    account_id: str,
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(AccountDB).where(AccountDB.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Coder account not found.")
    if account.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to access this account.")
    if not account.access_token or not account.api_endpoint:
        raise HTTPException(status_code=400, detail="Coder account is missing credentials.")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(
                f"{account.api_endpoint}/api/v2/workspaces",
                params={"q": "owner:me", "limit": 100},
                headers=_coder_auth_headers(account),
            )
            if res.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to fetch Coder workspaces. Status: {res.status_code}",
                )
            data = res.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to Coder: {str(e)}")

    items = data.get("workspaces") if isinstance(data, dict) else None
    if items is None and isinstance(data, list):
        items = data
    if items is None:
        raise HTTPException(status_code=502, detail="Unexpected Coder workspaces response.")

    workspaces = []
    for w in items:
        if not isinstance(w, dict):
            continue
        latest_build = w.get("latest_build") if isinstance(w.get("latest_build"), dict) else {}
        owner_name = (
            w.get("owner_name")
            or (w.get("owner") or {}).get("username")
            or (w.get("owner") or {}).get("name")
        )
        status = (
            w.get("status")
            or latest_build.get("status")
            or latest_build.get("job_status")
            or latest_build.get("state")
            or latest_build.get("phase")
            or w.get("workspace_status")
        )
        name = w.get("name")
        workspace_ref = f"{owner_name}/{name}" if owner_name and name else None
        workspaces.append(
            {
                "id": w.get("id"),
                "name": name,
                "status": status,
                "owner_name": owner_name,
                "workspace_ref": workspace_ref,
            }
        )
    return {"workspaces": workspaces}


@router.get("/coder/workspaces/files")
async def coder_workspace_files(
    account_id: str,
    workspace_id: str,
    workspace_ref: str | None = None,
    path: str = "/",
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(AccountDB).where(AccountDB.id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Coder account not found.")
    if account.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to access this account.")
    if not account.access_token or not account.api_endpoint:
        raise HTTPException(status_code=400, detail="Coder account is missing credentials.")

    normalized_path = path or "/"
    if not normalized_path.startswith("/"):
        normalized_path = f"/{normalized_path}"

    try:
        extra = account.extra_metadata or {}
        auth_type = extra.get("auth_type")
        if auth_type == "bearer":
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    ws_res = await client.get(
                        f"{account.api_endpoint}/api/v2/workspaces/{workspace_id}",
                        headers=_coder_auth_headers(account),
                    )
                    if ws_res.status_code == 200:
                        ws_data = ws_res.json()
                        latest_build = ws_data.get("latest_build") if isinstance(ws_data, dict) else None
                        resources = None
                        if isinstance(latest_build, dict):
                            resources = latest_build.get("resources")
                        agents = []
                        if isinstance(resources, list):
                            for resource in resources:
                                res_agents = resource.get("agents") if isinstance(resource, dict) else None
                                if isinstance(res_agents, list):
                                    agents.extend(res_agents)
                        agent_status = None
                        lifecycle_state = None
                        if agents:
                            agent_status = agents[0].get("status")
                            lifecycle_state = agents[0].get("lifecycle_state")
                        if agent_status and str(agent_status).lower() != "connected":
                            raise HTTPException(
                                status_code=409,
                                detail=f"Coder workspace agent is {agent_status} (state: {lifecycle_state or 'unknown'}). Start or restart the workspace.",
                            )
                        if lifecycle_state and str(lifecycle_state).lower() in ("shutting_down", "stopped"):
                            raise HTTPException(
                                status_code=409,
                                detail=f"Coder workspace agent is {lifecycle_state}. Start or restart the workspace.",
                            )
            except HTTPException:
                raise
            except httpx.HTTPError:
                pass
            workspace_identifier = workspace_ref or workspace_id
            if not workspace_identifier:
                raise HTTPException(status_code=400, detail="Workspace not specified.")
            async with CoderMCPClient(account.api_endpoint, account.access_token) as mcp_client:
                workspace_identifier = workspace_ref or workspace_id
                if not workspace_ref:
                    ws_meta = await mcp_client.get_workspace(workspace_id)
                    owner_name = ws_meta.get("owner_name") or (ws_meta.get("owner") or {}).get("username")
                    ws_name = ws_meta.get("name")
                    if owner_name and ws_name:
                        workspace_identifier = f"{owner_name}/{ws_name}"
                last_exc = None
                for attempt in range(3):
                    try:
                        data = await mcp_client.list_directory(workspace_identifier, normalized_path)
                        last_exc = None
                        break
                    except Exception as exc:
                        last_exc = exc
                        message = str(exc).lower()
                        if "agent not ready" in message or "shutting down" in message:
                            import asyncio
                            await asyncio.sleep(1.0 + attempt)
                            continue
                        break
                if last_exc:
                    tools = await mcp_client.list_tools()
                    tool_names = [t.get("name") for t in tools if t.get("name")]
                    if "coder_workspace_ls" in tool_names:
                        if "agent not ready" in str(last_exc).lower() or "shutting down" in str(last_exc).lower():
                            raise HTTPException(
                                status_code=409,
                                detail="Coder workspace agent is not ready. Start or restart the workspace and try again.",
                            )
                        raise HTTPException(
                            status_code=502,
                            detail=f"MCP call failed: {last_exc}",
                        )
                    raise HTTPException(
                        status_code=502,
                        detail=f"MCP tool 'coder_workspace_ls' not available. Available tools: {', '.join(tool_names) or 'none'}",
                    )
            entries = data.get("contents") if isinstance(data, dict) else None
            if entries is None and isinstance(data, list):
                entries = data
            if entries is None:
                raise HTTPException(status_code=502, detail="Unexpected MCP response.")
            folders = []
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                if not entry.get("is_dir"):
                    continue
                entry_path = entry.get("path")
                name = os.path.basename(entry_path) if entry_path else entry.get("name")
                if not entry_path:
                    continue
                folders.append({"name": name or entry_path, "path": entry_path})
            return {"path": normalized_path, "folders": folders}

        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(
                f"{account.api_endpoint}/api/v2/workspaces/{workspace_id}/files",
                params={"path": normalized_path},
                headers=_coder_auth_headers(account),
            )
            if res.status_code == 404:
                # Fallback: return agent directories as selectable roots.
                ws_res = await client.get(
                    f"{account.api_endpoint}/api/v2/workspaces/{workspace_id}",
                    headers=_coder_auth_headers(account),
                )
                if ws_res.status_code != 200:
                    raise HTTPException(
                        status_code=502,
                        detail="File browsing is not supported and workspace details could not be loaded.",
                    )
                workspace = ws_res.json()
                resources = None
                if isinstance(workspace, dict):
                    resources = workspace.get("resources")
                    if resources is None:
                        latest_build = workspace.get("latest_build")
                        if isinstance(latest_build, dict):
                            resources = latest_build.get("resources")
                suggestions = []
                if isinstance(resources, list):
                    for resource in resources:
                        agents = resource.get("agents") if isinstance(resource, dict) else None
                        if not isinstance(agents, list):
                            continue
                        for agent in agents:
                            if not isinstance(agent, dict):
                                continue
                            for key in ("expanded_directory", "directory"):
                                candidate = agent.get(key)
                                if candidate and candidate not in suggestions:
                                    suggestions.append(candidate)
                if normalized_path == "/":
                    return {
                        "path": normalized_path,
                        "folders": [{"name": s.split("/")[-1] or s, "path": s} for s in suggestions],
                    }
                return {"path": normalized_path, "folders": []}
            if res.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to fetch workspace files. Status: {res.status_code}",
                )
            data = res.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to Coder: {str(e)}")

    entries = None
    if isinstance(data, dict):
        entries = data.get("entries") or data.get("items") or data.get("data")
    if entries is None and isinstance(data, list):
        entries = data
    if entries is None:
        raise HTTPException(status_code=502, detail="Unexpected Coder files response.")

    folders = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry_type = entry.get("type") or entry.get("kind") or entry.get("file_type")
        is_dir = entry.get("is_dir") or entry.get("isDirectory")
        if entry_type and str(entry_type).lower() not in ("dir", "directory", "folder"):
            if not is_dir:
                continue
        name = entry.get("name") or entry.get("path", "").split("/")[-1]
        entry_path = entry.get("path") or f"{normalized_path.rstrip('/')}/{name}"
        folders.append({"name": name, "path": entry_path})

    return {"path": normalized_path, "folders": folders}
