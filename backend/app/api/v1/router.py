from fastapi import APIRouter

from .endpoints.auth import router as auth_router
from .endpoints.chat import router as chat_router
from .endpoints.checklist import router as checklist_router
from .endpoints.training import router as training_router
from .endpoints.upload import router as upload_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(checklist_router)
api_v1_router.include_router(training_router)
api_v1_router.include_router(upload_router)
