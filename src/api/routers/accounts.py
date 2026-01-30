from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.storage.postgres import get_db
from src.api.middleware.auth import get_current_user
from src.models.user import UserDB, AccountDB
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.future import select
import uuid
import httpx

router = APIRouter(prefix="/accounts", tags=["accounts"])

OLLAMA_PROVIDERS = {"ollama", "ollama-local"}

def normalize_ollama_endpoint(provider: str, endpoint: Optional[str]) -> Optional[str]:
    if provider not in OLLAMA_PROVIDERS or not endpoint:
        return endpoint
    trimmed = endpoint.rstrip("/")
    return trimmed if trimmed.endswith("/v1") else f"{trimmed}/v1"

class LLMConfigCreate(BaseModel):
    provider: str = "openai"
    name: Optional[str] = None
    api_key: Optional[str] = None  # Optional for Ollama self-hosted
    api_endpoint: Optional[str] = "https://api.openai.com/v1"
    model_name: Optional[str] = None  # Will be configured in PM settings
    is_global: bool = False # Only admins should be able to set this
    enabled_models: Optional[List[str]] = None

class AccountResponse(BaseModel):
    id: str
    provider: str
    name: Optional[str]
    api_endpoint: Optional[str]
    model_name: Optional[str]
    is_global: bool
    enabled_models: Optional[List[str]]

    class Config:
        from_attributes = True

class LLMConfigUpdate(BaseModel):
    name: Optional[str] = None
    api_endpoint: Optional[str] = None
    model_name: Optional[str] = None
    enabled_models: Optional[List[str]] = None

class LLMModelQuery(BaseModel):
    provider: str
    api_endpoint: Optional[str]
    api_key: Optional[str] = None

def account_to_response(account: AccountDB) -> dict:
    enabled_models = None
    if account.extra_metadata and isinstance(account.extra_metadata, dict):
        enabled_models = account.extra_metadata.get("enabled_models")
    return {
        "id": account.id,
        "provider": account.provider,
        "name": account.name,
        "api_endpoint": account.api_endpoint,
        "model_name": account.model_name,
        "is_global": account.is_global,
        "enabled_models": enabled_models
    }

@router.post("/llm", response_model=AccountResponse)
async def configure_llm(
    config: LLMConfigCreate,
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # In a real app, restrict is_global to admins
    account_id = str(uuid.uuid4())
    normalized_endpoint = normalize_ollama_endpoint(config.provider, config.api_endpoint)
    model_name = config.model_name
    if not model_name and config.enabled_models and "*" not in config.enabled_models:
        model_name = config.enabled_models[0] if config.enabled_models else None
    db_account = AccountDB(
        id=account_id,
        user_id=current_user.id,
        provider=config.provider,
        name=(config.name or config.provider.upper()),
        access_token=config.api_key or None, # Store securely in production!
        api_endpoint=normalized_endpoint,
        model_name=model_name,
        is_global=config.is_global,
        extra_metadata={"enabled_models": config.enabled_models} if config.enabled_models else None
    )
    db.add(db_account)
    await db.commit()
    await db.refresh(db_account)
    return account_to_response(db_account)

@router.get("", response_model=List[AccountResponse])
@router.get("/", response_model=List[AccountResponse], include_in_schema=False)
async def list_accounts(
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Fetch user specific and global accounts
    result = await db.execute(
        select(AccountDB).where(
            (AccountDB.user_id == current_user.id) | (AccountDB.is_global == True)
        ).where(AccountDB.provider.in_(["openai", "azure", "anthropic", "ollama", "ollama-local"]))
    )
    return [account_to_response(acc) for acc in result.scalars().all()]

@router.delete("/{account_id}")
async def delete_account(
    account_id: str,
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Fetch the account
    result = await db.execute(
        select(AccountDB).where(AccountDB.id == account_id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Only allow deletion if user owns it or is admin
    if account.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this account")
    
    await db.delete(account)
    await db.commit()
    
    return {"message": "Account deleted successfully"}

@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: str,
    config: LLMConfigUpdate,
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(AccountDB).where(AccountDB.id == account_id)
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if account.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to edit this account")

    if config.name is not None:
        account.name = config.name or None
    if config.api_endpoint is not None:
        account.api_endpoint = normalize_ollama_endpoint(account.provider, config.api_endpoint or None)
    if config.model_name is not None:
        account.model_name = config.model_name or None
    if config.enabled_models is not None:
        account.extra_metadata = account.extra_metadata or {}
        account.extra_metadata["enabled_models"] = config.enabled_models

    await db.commit()
    await db.refresh(account)
    return account_to_response(account)

@router.get("/{account_id}/models")
async def list_models_for_account(
    account_id: str,
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(AccountDB).where(AccountDB.id == account_id)
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if account.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to access this account")

    endpoint = normalize_ollama_endpoint(
        account.provider,
        account.api_endpoint or "https://api.openai.com/v1"
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {}
            if account.access_token:
                headers["Authorization"] = f"Bearer {account.access_token}"
            response = await client.get(f"{endpoint}/models", headers=headers)

            if response.status_code == 200:
                data = response.json()
                models = [m["id"] for m in data.get("data", [])]
                if models:
                    return {"models": sorted(models)}

            raise HTTPException(
                status_code=502,
                detail=f"Could not retrieve models from {endpoint}. Status: {response.status_code}. Please verify your API endpoint and credentials."
            )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"Timeout connecting to {endpoint}. Please verify the endpoint is accessible."
        )
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error connecting to {endpoint}: {str(e)}. Please verify your API endpoint and credentials."
        )

@router.post("/llm/models")
async def list_models_for_endpoint(
    query: LLMModelQuery,
    current_user: UserDB = Depends(get_current_user)
):
    endpoint = normalize_ollama_endpoint(
        query.provider,
        query.api_endpoint or "https://api.openai.com/v1"
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {}
            if query.api_key:
                headers["Authorization"] = f"Bearer {query.api_key}"
            response = await client.get(f"{endpoint}/models", headers=headers)

            if response.status_code == 200:
                data = response.json()
                models = [m["id"] for m in data.get("data", [])]
                if models:
                    return {"models": sorted(models)}

            raise HTTPException(
                status_code=502,
                detail=f"Could not retrieve models from {endpoint}. Status: {response.status_code}. Please verify your API endpoint and credentials."
            )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"Timeout connecting to {endpoint}. Please verify the endpoint is accessible."
        )
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error connecting to {endpoint}: {str(e)}. Please verify your API endpoint and credentials."
        )
