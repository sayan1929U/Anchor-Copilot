from fastapi import APIRouter
from app.api.v1.endpoints import chat, audit, auth, analytics

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
