from fastapi import APIRouter
from app.api.v1.endpoints import chat, audit

api_router = APIRouter()
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
