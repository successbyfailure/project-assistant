from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.storage.postgres import get_db
from src.api.middleware.auth import get_current_user
from src.models.user import UserDB, AccountDB
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.future import select
import uuid

router = APIRouter(prefix="/accounts", tags=["accounts"])

class LLMConfigCreate(BaseModel):
    provider: str = "openai"
    name: Optional[str] = None
    api_key: Optional[str] = None  # Optional for Ollama self-hosted
    api_endpoint: Optional[str] = "https://api.openai.com/v1"
    model_name: Optional[str] = None  # Will be configured in PM settings
    is_global: bool = False # Only admins should be able to set this

class AccountResponse(BaseModel):
    id: str
    provider: str
    name: Optional[str]
    api_endpoint: Optional[str]
    model_name: Optional[str]
    is_global: bool

    class Config:
        from_attributes = True

class LLMConfigUpdate(BaseModel):
    name: Optional[str] = None

@router.post("/llm", response_model=AccountResponse)
async def configure_llm(
    config: LLMConfigCreate,
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # In a real app, restrict is_global to admins
    account_id = str(uuid.uuid4())
    db_account = AccountDB(
        id=account_id,
        user_id=current_user.id,
        provider=config.provider,
        name=(config.name or config.provider.upper()),
        access_token=config.api_key or None, # Store securely in production!
        api_endpoint=config.api_endpoint,
        model_name=config.model_name,
        is_global=config.is_global
    )
    db.add(db_account)
    await db.commit()
    await db.refresh(db_account)
    return db_account

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
        )
    )
    return result.scalars().all()

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

    await db.commit()
    await db.refresh(account)
    return account
