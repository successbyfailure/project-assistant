import logging
from typing import List, Optional
from src.models.user import ProjectDB, AccountDB
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class FulcrumPMAgent:
    """
    The central Project Manager agent for Fulcrum.
    Maintains global context across all projects for a user.
    """
    
    def __init__(self, user_id: str, db: AsyncSession):
        self.user_id = user_id
        self.db = db
        self.active_project: Optional[str] = None
        
    async def _get_llm_credentials(self) -> Optional[AccountDB]:
        """
        Fetch the best available LLM credentials (user-specific first, then global).
        """
        result = await self.db.execute(
            select(AccountDB)
            .where(
                (AccountDB.user_id == self.user_id) | (AccountDB.is_global == True)
            )
            .where(AccountDB.provider.in_(["openai", "azure", "anthropic", "ollama", "ollama-local"]))
            .order_by(AccountDB.is_global.asc()) # User specific (is_global=False) comes first
        )
        return result.scalars().first()

    async def get_global_overview(self) -> dict:
        """
        Aggregates status across all user projects.
        """
        result = await self.db.execute(
            select(ProjectDB).where(ProjectDB.user_id == self.user_id)
        )
        projects = result.scalars().all()
        
        creds = await self._get_llm_credentials()
        
        if not creds:
            llm_status = "No LLM configured"
        elif creds.is_global:
            llm_status = "Using global credentials"
        else:
            llm_status = "Using user credentials"

        return {
            "user_id": self.user_id,
            "llm_status": llm_status,
            "project_count": len(projects),
            "projects": [{"id": p.id, "name": p.name, "description": p.description} for p in projects]
        }
