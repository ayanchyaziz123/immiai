from collections.abc import AsyncGenerator

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .database import AsyncSessionLocal
from .security import decode_token


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_optional_user(
    access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Returns the authenticated User or None for guests. Never raises."""
    if not access_token:
        return None
    user_id = decode_token(access_token)
    if not user_id:
        return None
    from ..repositories.user_repository import UserRepository
    user = await UserRepository(db).get_by_id(user_id)
    return user if (user and user.is_active) else None


async def get_current_user(user=Depends(get_optional_user)):
    """Returns the authenticated User, or raises 401 for guests."""
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
