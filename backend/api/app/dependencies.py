import uuid

from common.db import get_db_session
from common.models import User
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_current_user(
    authorization: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    user_id_raw = None
    if authorization and authorization.startswith("Bearer "):
        user_id_raw = authorization.removeprefix("Bearer ").strip()
    elif x_user_id:
        user_id_raw = x_user_id.strip()

    if not user_id_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication. Use Authorization: Bearer <user_id> or X-User-Id.",
        )

    try:
        user_id = uuid.UUID(user_id_raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identifier.",
        ) from exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )
    return user
