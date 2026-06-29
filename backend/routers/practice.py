# backend/routers/practice.py
# POST /api/practice/check — 발화 판정만 (기록 안 함)
# POST /api/practice/complete — 카드 1장 완료 기록 (재시도와 무관하게 1회만 차감)

import re
from datetime import datetime, timezone
from difflib import SequenceMatcher

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import settings
from backend.utils.database import get_db

router = APIRouter()

SIMILARITY_THRESHOLD = 0.6


class CheckRequest(BaseModel):
    token: str
    card_id: int
    user_answer: str
    target_sentence: str


class CompleteRequest(BaseModel):
    token: str
    card_id: int
    passed: bool


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def _get_active_user(db, token: str):
    user_result = (
        db.table("users")
        .select("id, is_active")
        .eq("access_token", token)
        .single()
        .execute()
    )
    user = user_result.data
    if not user or not user["is_active"]:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    return user


def _count_today(db, user_id: str) -> int:
    today = datetime.now(timezone.utc).date().isoformat()
    usage_result = (
        db.table("usage_logs")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .gte("created_at", f"{today}T00:00:00+00:00")
        .execute()
    )
    return usage_result.count or 0


@router.post("/practice/check")
async def check_answer(body: CheckRequest):
    """발화 판정만 수행 — 사용량 기록은 하지 않음 (재시도 자유)"""
    db = get_db()
    _get_active_user(db, body.token)

    score = _similarity(body.user_answer, body.target_sentence)
    passed = score >= SIMILARITY_THRESHOLD

    return {
        "passed": passed,
        "similarity": round(score, 2),
    }


@router.post("/practice/complete")
async def complete_card(body: CompleteRequest):
    """카드 1장을 떠날 때(통과 또는 포기) 호출 — 테스트 모드에서만 사용량 1회 차감"""
    db = get_db()
    user = _get_active_user(db, body.token)

    used_today = _count_today(db, user["id"])
    if used_today >= settings.daily_limit:
        raise HTTPException(
            status_code=429,
            detail=f"오늘 테스트 횟수({settings.daily_limit}회)를 모두 사용했습니다.",
        )

    db.table("usage_logs").insert(
        {
            "user_id": user["id"],
            "card_id": body.card_id,
            "passed": body.passed,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()

    return {
        "used_today": used_today + 1,
        "limit": settings.daily_limit,
        "remaining": settings.daily_limit - (used_today + 1),
    }