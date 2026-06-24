# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.routers import chat

app = FastAPI(title="Bingle API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.allowed_origin, "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Bingle API v2"}

# 프론트엔드 정적 파일 서빙
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")


