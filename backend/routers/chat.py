# backend/routers/chat.py
# POST /api/conversation  — 세션 시작 시 대화 생성
# POST /api/respond       — 유저 발화 처리 → 피드백 + 다음 대화

import json
import re
import random
from typing import Optional

import anthropic
from fastapi import APIRouter
from pydantic import BaseModel

from backend.config import settings

router = APIRouter()
claude = anthropic.Anthropic(api_key=settings.anthropic_api_key)


# ── 요청/응답 모델 ─────────────────────────────────────────────────

class ConversationRequest(BaseModel):
    sentences: list[dict]   # 클라이언트가 보내는 문장 목록 (랜덤 선택된 것들)
    topic: str


class Turn(BaseModel):
    role: str               # "ai" | "user"
    text: str


class RespondRequest(BaseModel):
    conversation: list[dict]        # 지금까지의 대화 흐름 [{role, text}, ...]
    user_answer: str                # STT로 변환된 유저 발화
    target_sentence: str            # 이번 턴에서 유도하려는 문장
    attempt_count: int              # 현재 문장에서 몇 번째 시도인지
    topic: str


# ── 대화 생성 ──────────────────────────────────────────────────────

def _build_conversation_prompt(sentences: list[dict], topic: str) -> str:
    sentence_list = "\n".join(f"- {s['sentence']}" for s in sentences)
    return f"""You are a friendly English conversation partner practicing business English with a Korean learner.

Your task: Create a SHORT, NATURAL 2-3 turn conversation script that naturally incorporates the following English sentences.

TOPIC: {topic}
TARGET SENTENCES TO INCLUDE:
{sentence_list}

Rules:
1. Write a realistic, flowing dialogue between "AI" and "USER"
2. Each target sentence must appear EXACTLY as written in the USER's turns
3. The AI's lines should naturally prompt the user to say those sentences
4. Keep it conversational and practical — like a real workplace exchange
5. 2-3 turns total (AI speaks → User responds → AI responds → User responds...)

Respond with ONLY a JSON array, no explanation:
[
  {{"role": "ai", "text": "AI's opening line"}},
  {{"role": "user", "text": "User's response using a target sentence"}},
  {{"role": "ai", "text": "AI's follow-up"}},
  {{"role": "user", "text": "User's response using another target sentence"}}
]"""


async def generate_conversation(sentences: list[dict], topic: str) -> list[dict]:
    message = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        messages=[{"role": "user", "content": _build_conversation_prompt(sentences, topic)}],
    )
    raw = message.content[0].text.strip()
    match = re.search(r"\[[\s\S]*\]", raw)
    return json.loads(match.group() if match else raw)


@router.post("/conversation")
async def create_conversation(body: ConversationRequest):
    """세션 시작 시 선택된 문장들로 대화 흐름 생성"""
    # 문장당 2~3개씩 묶어서 하나의 대화 생성
    turns = await generate_conversation(body.sentences, body.topic)
    return {"turns": turns}


# ── 유저 응답 처리 ─────────────────────────────────────────────────

def _build_respond_prompt(
    conversation: list[dict],
    user_answer: str,
    target_sentence: str,
    attempt_count: int,
    topic: str,
) -> str:
    history = "\n".join(
        f"{'AI' if t['role'] == 'ai' else 'USER'}: {t['text']}"
        for t in conversation
    )
    return f"""You are a friendly English conversation coach practicing with a Korean learner.

TOPIC: {topic}
CONVERSATION SO FAR:
{history}

The learner was supposed to say (target):
"{target_sentence}"

What the learner actually said:
"{user_answer}"

This is attempt #{attempt_count} for this sentence.

Evaluate and respond in JSON only:
{{
  "quality": "good" | "poor",
  "ai_response": "<your natural spoken reply IN ENGLISH — if good, continue the conversation naturally; if poor, gently give a hint or model the correct phrase>",
  "hint": "<ONLY if quality is poor: the correct sentence or a close version, in English. Empty string if good.>"
}}

Quality guide:
- "good": the learner conveyed the target meaning clearly, even if not word-for-word perfect
- "poor": unclear, off-topic, very incomplete, or silent

If poor and attempt >= 3, include the full target sentence in ai_response as a natural model.
Keep ai_response SHORT (1-2 sentences). Sound warm and encouraging, never robotic.
Respond with valid JSON only."""


@router.post("/respond")
async def process_response(body: RespondRequest):
    """유저 발화를 받아 good/poor 판정 + AI 다음 대화 반환"""
    message = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[
            {
                "role": "user",
                "content": _build_respond_prompt(
                    body.conversation,
                    body.user_answer,
                    body.target_sentence,
                    body.attempt_count,
                    body.topic,
                ),
            }
        ],
    )
    raw = message.content[0].text.strip()
    match = re.search(r"\{[\s\S]*\}", raw)
    try:
        result = json.loads(match.group() if match else raw)
    except Exception:
        result = {
            "quality": "poor",
            "ai_response": "Could you try saying that again? Take your time.",
            "hint": target_sentence if body.attempt_count >= 3 else "",
        }

    return result
