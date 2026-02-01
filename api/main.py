from fastapi import APIRouter
from api.v1.tts_router import router as tts_router

api_router = APIRouter()
api_router.include_router(tts_router, prefix="/tts", tags=["TTS"])