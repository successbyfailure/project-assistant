from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, String, DateTime, Boolean, JSON
from src.storage.base import Base

class UserDB(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)  # Null if only using OAuth
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AccountDB(Base):
    __tablename__ = "accounts"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    provider = Column(String, nullable=False)  # "github", "coder", "openai", "azure", "anthropic"
    name = Column(String)  # User-friendly label for display
    provider_user_id = Column(String)
    access_token = Column(String, nullable=True)  # Map to encrypted storage in production
    refresh_token = Column(String)
    expires_at = Column(DateTime)
    api_endpoint = Column(String)  # For custom OpenAI-compatible endpoints
    model_name = Column(String)    # Preferred model for this account
    is_global = Column(Boolean, default=False) # Admin-provided global credentials
    extra_metadata = Column(JSON)

class ProjectDB(Base):
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    source_type = Column(String) # "local", "github", "coder"
    remote_url = Column(String)
    github_repo = Column(String)
    workspace_id = Column(String)
    workspace_name = Column(String)
    workspace_path = Column(String)
    workspace_ref = Column(String)
    production_url = Column(String)
    testing_url = Column(String)
    thumbnail_url = Column(String)
    codespace_id = Column(String)
    codespace_name = Column(String)
    codespace_url = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    extra_metadata = Column(JSON)
