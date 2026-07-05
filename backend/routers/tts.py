# backend/routers/tts.py
# POST /api/tts — 텍스트를 OpenAI TTS로 변환해서 mp3로 반환

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import OpenAI

from backend.config import settings
from backend.utils.database import get_db

router = APIRouter()
openai_client = OpenAI(api_key=settings.openai_api_key)

VOICES = {
    "female": "nova",    # 자연스러운 여성 목소리
    "male": "onyx",      # 깊고 자연스러운 남성 목소리
}
# OpenAI TTS 음성 옵션: alloy, echo, fable, onyx, nova, shimmer


class TTSRequest(BaseModel):
    token: str
    text: str
    gender: str = "female"   # "female" | "male"


@router.post("/tts")
async def text_to_speech(body: TTSRequest):
    # 토큰 인증
    db = get_db()
    result = (
        db.table("users")
        .select("id, is_active")
        .eq("access_token", body.token)
        .single()
        .execute()
    )
    user = result.data
    if not user or not user["is_active"]:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")

    # 텍스트 길이 제한 (비용 방어)
    text = body.text.strip()[:500]
    if not text:
        raise HTTPException(status_code=400, detail="텍스트가 비어있습니다.")

    voice = VOICES.get(body.gender, "nova")

    try:
        response = openai_client.audio.speech.create(
            model="tts-1",          # tts-1 (빠름/저렴) 또는 tts-1-hd (고품질)
            voice=voice,
            input=text,
            response_format="mp3",
            speed=0.95,             # 약간 천천히 (0.25~4.0)
        )
        audio_data = response.content

        return StreamingResponse(
            iter([audio_data]),
            media_type="audio/mpeg",
            headers={"Cache-Control": "no-cache"},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS 오류: {str(e)}")