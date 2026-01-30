from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from src.storage.postgres import get_db
from src.api.services import user_service
from src.core.auth import security
from pydantic import BaseModel, EmailStr
from jose import jwt, JWTError
import os
import httpx
import uuid
from sqlalchemy.future import select

from src.models.user import AccountDB

router = APIRouter(prefix="/auth", tags=["auth"])

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str = None

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/register", response_model=Token)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    user = await user_service.get_user_by_email(db, user_in.email)
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = await user_service.create_user(
        db, email=user_in.email, password=user_in.password, full_name=user_in.full_name
    )
    
    access_token = security.create_access_token(user.id)
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await user_service.get_user_by_email(db, form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = security.create_access_token(user.id)
    return {"access_token": access_token, "token_type": "bearer"}


def _base_domain() -> str:
    base = os.getenv("BASE_DOMAIN", "http://localhost:8000")
    return base.rstrip("/")


def _github_redirect_uri() -> str:
    return f"{_base_domain()}/auth/github/callback"


def _coder_redirect_uri() -> str:
    return f"{_base_domain()}/auth/coder/callback"


@router.get("/github/callback", include_in_schema=False)
async def github_callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(state, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        if payload.get("typ") != "github_oauth":
            raise HTTPException(status_code=400, detail="Invalid OAuth state.")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid OAuth state.")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid OAuth state.")

    client_id = os.getenv("GITHUB_CLIENT_ID")
    client_secret = os.getenv("GITHUB_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured.")

    async with httpx.AsyncClient(timeout=10.0) as client:
        token_res = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": _github_redirect_uri(),
            },
        )
        token_data = token_res.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="GitHub OAuth failed.")

        user_res = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_data = user_res.json()

    result = await db.execute(
        select(AccountDB).where(
            (AccountDB.user_id == user_id) & (AccountDB.provider == "github")
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        account = AccountDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            provider="github",
            name=user_data.get("login"),
            provider_user_id=str(user_data.get("id")),
            access_token=access_token,
        )
        db.add(account)
    else:
        account.access_token = access_token
        account.provider_user_id = str(user_data.get("id"))
        account.name = user_data.get("login")

    await db.commit()
    return RedirectResponse(f"{_base_domain()}/?#github=connected")


@router.get("/coder/callback", include_in_schema=False)
async def coder_callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(state, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        if payload.get("typ") != "coder_oauth":
            raise HTTPException(status_code=400, detail="Invalid OAuth state.")
        user_id = payload.get("sub")
        issuer = payload.get("iss")
        token_endpoint = payload.get("token_endpoint")
        if not user_id or not issuer or not token_endpoint:
            raise HTTPException(status_code=400, detail="Invalid OAuth state.")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid OAuth state.")

    client_id = os.getenv("CODER_OAUTH_CLIENT_ID")
    client_secret = os.getenv("CODER_OAUTH_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="Coder OAuth not configured.")

    async with httpx.AsyncClient(timeout=10.0) as client:
        token_res = await client.post(
            token_endpoint,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": _coder_redirect_uri(),
            },
        )
        token_data = token_res.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Coder OAuth failed.")

        user_res = await client.get(
            f"{issuer}/api/v2/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Coder OAuth user lookup failed.")
        user_data = user_res.json()

    result = await db.execute(
        select(AccountDB).where(
            (AccountDB.user_id == user_id) & (AccountDB.provider == "coder") & (AccountDB.api_endpoint == issuer)
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        account = AccountDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            provider="coder",
            name=f"Coder ({issuer})",
            provider_user_id=str(user_data.get("id")),
            access_token=access_token,
            api_endpoint=issuer,
            extra_metadata={"auth_type": "bearer"},
        )
        db.add(account)
    else:
        account.access_token = access_token
        account.provider_user_id = str(user_data.get("id"))
        account.name = account.name or f"Coder ({issuer})"
        account.extra_metadata = {**(account.extra_metadata or {}), "auth_type": "bearer"}

    await db.commit()
    return RedirectResponse(f"{_base_domain()}/?#coder=connected")
