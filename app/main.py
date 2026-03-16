from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import reco_router
from app.api import image_router
from app.api import nearby_router
from app.api.chat_router import router as chat_router
from app.api.admin_router import router as admin_router
from app.api import biz_router
from app.api.moderation_router import router as moderation_router

app = FastAPI(title="MOHAENG AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 로컬 테스트용이므로 전부 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reco_router.router)
app.include_router(image_router.router)
app.include_router(chat_router)

app.include_router(admin_router)
app.include_router(moderation_router)
app.include_router(nearby_router.router)
app.include_router(biz_router.router)
