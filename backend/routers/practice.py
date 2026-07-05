# backend/routers/practice.py
# POST /api/practice/check   — 유사도 판정만 (암기카드 모드)
# POST /api/practice/complete — 카드 1장 완료 기록 (테스트 모드, 카드당 1회 차감)
# POST /api/conversation/prompt — AI가 대화 질문 생성
# POST /api/conversation/evaluate — 학생 답변 1~10점 평가

import re
import json
from datetime import datetime, timezone
from difflib import SequenceMatcher

import anthropic
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import settings
from backend.utils.database import get_db

router = APIRouter()
claude = anthropic.Anthropic(api_key=settings.anthropic_api_key)

SIMILARITY_THRESHOLD = 0.6


# ── 공통 유틸 ──────────────────────────────────────────────────────

class CheckRequest(BaseModel):
    token: str
    card_id: int
    user_answer: str
    target_sentence: str


class CompleteRequest(BaseModel):
    token: str
    card_id: int
    passed: bool


class PromptRequest(BaseModel):
    token: str
    target_sentence: str
    topic: str


class EvaluateRequest(BaseModel):
    token: str
    target_sentence: str
    topic: str
    user_answer: str   # STT로 변환된 학생 발화


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def _get_active_user(db, token: str):
    result = (
        db.table("users")
        .select("id, is_active")
        .eq("access_token", token)
        .single()
        .execute()
    )
    user = result.data
    if not user or not user["is_active"]:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    return user


def _count_today(db, user_id: str) -> int:
    today = datetime.now(timezone.utc).date().isoformat()
    result = (
        db.table("usage_logs")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .gte("created_at", f"{today}T00:00:00+00:00")
        .execute()
    )
    return result.count or 0


# ── 암기카드 모드 ──────────────────────────────────────────────────

@router.post("/practice/check")
async def check_answer(body: CheckRequest):
    """유사도 판정만 — DB 기록 없음 (암기카드 모드 재시도 자유)"""
    db = get_db()
    _get_active_user(db, body.token)
    score = _similarity(body.user_answer, body.target_sentence)
    return {"passed": score >= SIMILARITY_THRESHOLD, "similarity": round(score, 2)}


@router.post("/practice/complete")
async def complete_card(body: CompleteRequest):
    """카드 1장 완료 시 호출 — 대화하기 모드에서 하루 10회 차감"""
    db = get_db()
    user = _get_active_user(db, body.token)
    used_today = _count_today(db, user["id"])

    if used_today >= settings.daily_limit:
        raise HTTPException(
            status_code=429,
            detail=f"오늘 대화하기 횟수({settings.daily_limit}회)를 모두 사용했습니다. 내일 다시 도전하세요! 🌟",
        )

    db.table("usage_logs").insert({
        "user_id": user["id"],
        "card_id": body.card_id,
        "passed": body.passed,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    return {
        "used_today": used_today + 1,
        "limit": settings.daily_limit,
        "remaining": settings.daily_limit - (used_today + 1),
    }


# ── 대화하기 모드 ──────────────────────────────────────────────────

@router.post("/conversation/prompt")
async def generate_prompt(body: PromptRequest):
    """학생이 target_sentence를 자연스럽게 말할 수 있도록 AI가 영어로 질문 생성"""
    db = get_db()
    _get_active_user(db, body.token)

    message = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": f"""You are a friendly English conversation partner practicing with a Korean business English learner.

Topic: {body.topic}
Target expression the student should use: "{body.target_sentence}"

Write ONE short, natural English question or prompt (1-2 sentences) that would naturally lead the student to respond using the target expression above. The question should feel like real conversation, not a drill.

Reply with ONLY the question — no labels, no explanation, no quotes."""
        }]
    )
    prompt_text = message.content[0].text.strip()
    return {"prompt": prompt_text}


@router.post("/conversation/evaluate")
async def evaluate_answer(body: EvaluateRequest):
    """학생 답변을 1~10점으로 평가 — 유창성/문법/의미 전달 종합"""
    db = get_db()
    _get_active_user(db, body.token)

    message = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{
            "role": "user",
            "content": f"""You are a friendly English speaking coach for Korean learners.

The student just studied this flashcard:
Target expression: "{body.target_sentence}"
Topic: {body.topic}

The student's spoken answer (transcribed): "{body.user_answer}"

Evaluate and respond with ONLY valid JSON in this exact format:
{{
  "level": <integer 1-4>,
  "score": <integer 1-10>,
  "score_reason": "<one sentence in Korean>",
  "model_answer": "{body.target_sentence}",
  "coach_comment": "<1-2 sentences in Korean>",
  "retry_flashcard": <true|false>
}}

Level guide (pick exactly one):
- Level 4 (score 9-10): Student said it almost exactly as memorized. → coach_comment: 외운 대로 완벽하게 말했어요! 정말 잘했어요 🌟, retry_flashcard: false
- Level 3 (score 7-8): Student didn't say it exactly, but creatively used the idea correctly. → coach_comment: 외운 표현을 응용해서 자연스럽게 말했어요! 훌륭해요 👍, retry_flashcard: false
- Level 2 (score 5-6): Answer makes sense in context, but missed the target expression. → coach_comment: 의미는 통했어요! 조금만 더 연습하면 완벽해질 거예요 💪, retry_flashcard: false
- Level 1 (score 1-4): Answer is off-topic, incomprehensible, or too incomplete. → coach_comment: 암기카드로 돌아가서 표현을 다시 익혀봐요! 할 수 있어요 🔄, retry_flashcard: true

Be generous for Level 2 and 3 — reward communication even if imperfect."""
        }]
    )

    raw = message.content[0].text.strip()
    match = re.search(r"\{[\s\S]*\}", raw)
    try:
        result = json.loads(match.group() if match else raw)
    except Exception:
        result = {
            "score": 5,
            "score_reason": "평가 중 오류가 발생했습니다.",
            "model_answer": body.target_sentence,
            "coach_comment": "다시 한번 도전해보세요!"
        }

    return result