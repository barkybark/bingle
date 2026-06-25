# main.py 
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.routers import auth, practice

app = FastAPI(title="Bingle API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.allowed_origin, "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(practice.router, prefix="/api")


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Bingle API v3"}


# 프론트엔드 정적 파일 서빙 (반드시 맨 마지막에 위치해야 함)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

# test