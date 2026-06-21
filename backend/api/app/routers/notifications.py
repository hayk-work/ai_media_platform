from common.db import get_db_session
from common.models import User
from common.notifications import get_or_create_notification_preferences
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.schemas import (
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> NotificationPreferencesResponse:
    preferences = await get_or_create_notification_preferences(db, current_user.id)
    return NotificationPreferencesResponse(
        email_enabled=preferences.email_enabled,
        sms_enabled=preferences.sms_enabled,
    )


@router.put("/preferences", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    payload: NotificationPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> NotificationPreferencesResponse:
    preferences = await get_or_create_notification_preferences(db, current_user.id)
    preferences.email_enabled = payload.email_enabled
    preferences.sms_enabled = payload.sms_enabled
    await db.commit()
    await db.refresh(preferences)
    return NotificationPreferencesResponse(
        email_enabled=preferences.email_enabled,
        sms_enabled=preferences.sms_enabled,
    )
