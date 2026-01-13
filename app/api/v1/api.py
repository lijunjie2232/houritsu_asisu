from fastapi import APIRouter

from app.api.v1.chat import router as chat_router

api_router = APIRouter()

# Include all API routes
api_router.include_router(chat_router)
