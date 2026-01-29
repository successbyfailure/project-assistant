from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models.user import UserDB
from src.core.auth.security import get_password_hash
import uuid

async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(UserDB).where(UserDB.email == email))
    return result.scalars().first()

async def create_user(db: AsyncSession, email: str, password: str, full_name: str = None):
    # Check if this is the first user
    result = await db.execute(select(UserDB).limit(1))
    first_user = result.scalars().first()
    is_admin = first_user is None

    user_id = str(uuid.uuid4())
    db_user = UserDB(
        id=user_id,
        email=email,
        hashed_password=get_password_hash(password),
        full_name=full_name,
        is_admin=is_admin
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user
