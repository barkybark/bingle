# backend/routers/auth.py
# POST /api/auth — 토큰 검증 + 오늘 사용량 확인

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import settings
from backend.utils.database import get_db

router = APIRouter()


class AuthRequest(BaseModel):
    token: str


@router.post("/auth")
async def verify_token(body: AuthRequest):
    db = get_db()
    token = body.token.strip()

    result = (
        db.table("users")
        .select("id, name, is_active")
        .eq("access_token", token)
        .single()
        .execute()
    )

    user = result.data
    if not user:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="비활성화된 계정입니다.")

    today = datetime.now(timezone.utc).date().isoformat()

    usage_result = (
        db.table("usage_logs")
        .select("id", count="exact")
        .eq("user_id", user["id"])
        .gte("created_at", f"{today}T00:00:00+00:00")
        .execute()
    )
    used_today = usage_result.count or 0

    if used_today >= settings.daily_limit:
        raise HTTPException(
            status_code=429,
            detail=f"오늘 연습 횟수({settings.daily_limit}회)를 모두 사용했습니다. 내일 다시 도전하세요! 🌟",
        )

    return {
        "success": True,
        "user": {"id": user["id"], "name": user["name"]},
        "usage": {
            "used": used_today,
            "limit": settings.daily_limit,
            "remaining": settings.daily_limit - used_today,
        },
    }

#push
