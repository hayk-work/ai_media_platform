from common.logging import configure_logging
from fastapi import FastAPI

from app.routers import auth, health, media, notifications, uploads

configure_logging()

app = FastAPI(
    title="AI Media Platform API",
    version="0.1.0",
    description="Local foundation API for the AI Media Processing Platform.",
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(uploads.router)
app.include_router(media.router)
app.include_router(notifications.router)
