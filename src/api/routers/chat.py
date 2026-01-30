from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.storage.postgres import get_db
from src.api.middleware.auth import get_current_user
from src.models.user import UserDB
from pydantic import BaseModel
from typing import List, Optional
import httpx
import json

router = APIRouter(prefix="/chat", tags=["chat"])

OLLAMA_PROVIDERS = {"ollama", "ollama-local"}

def normalize_ollama_endpoint(provider: str, endpoint: Optional[str]) -> Optional[str]:
    if provider not in OLLAMA_PROVIDERS or not endpoint:
        return endpoint
    trimmed = endpoint.rstrip("/")
    return trimmed if trimmed.endswith("/v1") else f"{trimmed}/v1"

class ChatMessage(BaseModel):
    message: str
    model_name: Optional[str] = None
    account_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    model_used: str

class PMSettings(BaseModel):
    account_id: str
    model_name: str

@router.post("/pm", response_model=ChatResponse)
async def chat_with_pm(
    msg: ChatMessage,
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Chat with the Project Manager AI"""
    from src.core.agents.pm_agent import FulcrumPMAgent
    from src.models.user import AccountDB
    from sqlalchemy.future import select
    
    if msg.account_id:
        result = await db.execute(
            select(AccountDB).where(AccountDB.id == msg.account_id)
        )
        account = result.scalar_one_or_none()
        if not account:
            raise HTTPException(status_code=404, detail="AI account not found.")
        if account.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to use this AI account.")
    else:
        # Get the first available account (frontend should configure which one to use)
        result = await db.execute(
            select(AccountDB).where(
                (AccountDB.user_id == current_user.id) | (AccountDB.is_global == True)
            ).where(AccountDB.provider.in_(["openai", "azure", "anthropic", "ollama", "ollama-local"]))
            .order_by(AccountDB.is_global.asc())
        )
        account = result.scalars().first()
    
    if not account:
        raise HTTPException(status_code=400, detail="No AI account configured. Please add one in AI Accounts.")
    
    # Get PM overview for context
    agent = FulcrumPMAgent(current_user.id, db)
    overview = await agent.get_global_overview()
    
    # Build context
    projects_info = ', '.join([f"{p['name']} ({p.get('description', 'no description')})" for p in overview['projects']])
    context = f"""You are the Fulcrum Project Manager AI assistant.
User: {current_user.full_name or current_user.email}
Active Projects: {overview['project_count']}
Projects: {projects_info or 'None'}

Answer the user's question helpfully and concisely. Be friendly and professional."""
    
    enabled_models = None
    if account.extra_metadata and isinstance(account.extra_metadata, dict):
        enabled_models = account.extra_metadata.get("enabled_models")

    # Use a default model if none is set
    if msg.model_name:
        model_to_use = msg.model_name
    else:
        model_to_use = account.model_name or get_default_model(account.provider)

    if enabled_models and "*" not in enabled_models:
        if msg.model_name and model_to_use not in enabled_models:
            raise HTTPException(status_code=400, detail="Selected model is not enabled for this account.")
        if model_to_use not in enabled_models:
            model_to_use = enabled_models[0]
    
    # Call the LLM
    try:
        endpoint = normalize_ollama_endpoint(
            account.provider,
            account.api_endpoint or "https://api.openai.com/v1"
        )
        response_text = await call_llm(
            endpoint,
            account.access_token,
            model_to_use,
            context,
            msg.message
        )
        
        return ChatResponse(
            response=response_text,
            model_used=f"{account.provider}:{model_to_use}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calling LLM: {str(e)}")

def get_default_model(provider: str) -> str:
    """Get default model for a provider"""
    defaults = {
        "openai": "gpt-4",
        "anthropic": "claude-3-5-sonnet-20241022",
        "azure": "gpt-4",
        "ollama": "llama3.2",
        "ollama-local": "llama3.2"
    }
    return defaults.get(provider, "gpt-4")

async def call_llm(endpoint: str, api_key: str, model: str, system_prompt: str, user_message: str) -> str:
    """Call OpenAI-compatible API"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Build headers - Authorization is optional for Ollama self-hosted
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            response = await client.post(
                f"{endpoint}/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            raise Exception(f"LLM API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to call LLM: {str(e)}")

@router.get("/models/{account_id}")
async def list_models(
    account_id: str,
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List available models for an account by querying the endpoint"""
    from src.models.user import AccountDB
    from sqlalchemy.future import select
    
    result = await db.execute(
        select(AccountDB).where(AccountDB.id == account_id)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    enabled_models = None
    if account.extra_metadata and isinstance(account.extra_metadata, dict):
        enabled_models = account.extra_metadata.get("enabled_models")

    if enabled_models and "*" not in enabled_models:
        return {"models": sorted(enabled_models)}

    # For OpenAI-compatible endpoints, try to list models
    endpoint = normalize_ollama_endpoint(
        account.provider,
        account.api_endpoint or "https://api.openai.com/v1"
    )
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Build headers - Authorization is optional for Ollama self-hosted
            headers = {}
            if account.access_token:
                headers["Authorization"] = f"Bearer {account.access_token}"
            
            response = await client.get(
                f"{endpoint}/models",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                models = [m["id"] for m in data.get("data", [])]
                if models:
                    return {"models": sorted(models)}
            
            # If we got a response but no models or error, raise
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
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error retrieving models: {str(e)}"
        )
