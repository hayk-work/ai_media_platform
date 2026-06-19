from common.db import get_db_session
from common.models import User
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import SessionRequest, SessionResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/session", response_model=SessionResponse)
async def create_session(
    payload: SessionRequest,
    db: AsyncSession = Depends(get_db_session),
) -> SessionResponse:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(email=payload.email)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return SessionResponse(user_id=user.id, token=str(user.id))
