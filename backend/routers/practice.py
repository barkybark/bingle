# backend/routers/practice.py
# POST /api/practice/check — 발화 판정 + 사용 기록

import re
from datetime import datetime, timezone
from difflib import SequenceMatcher

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import settings
from backend.utils.database import get_db

router = APIRouter()

SIMILARITY_THRESHOLD = 0.6   # 이 이상이면 "통과"로 판정


class CheckRequest(BaseModel):
    token: str
    card_id: int
    user_answer: str
    target_sentence: str


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


@router.post("/practice/check")
async def check_answer(body: CheckRequest):
    db = get_db()

    user_result = (
        db.table("users")
        .select("id, is_active")
        .eq("access_token", body.token)
        .single()
        .execute()
    )
    user = user_result.data
    if not user or not user["is_active"]:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")

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
            detail=f"오늘 연습 횟수({settings.daily_limit}회)를 모두 사용했습니다.",
        )

    score = _similarity(body.user_answer, body.target_sentence)
    passed = score >= SIMILARITY_THRESHOLD

    db.table("usage_logs").insert(
        {
            "user_id": user["id"],
            "card_id": body.card_id,
            "user_answer": body.user_answer,
            "passed": passed,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()

    return {
        "passed": passed,
        "similarity": round(score, 2),
        "used_today": used_today + 1,
        "limit": settings.daily_limit,
        "remaining": settings.daily_limit - (used_today + 1),
    }

#push 