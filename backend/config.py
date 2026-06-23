# backend/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    allowed_origin: str = "*"
    session_max_minutes: int = 30     # 세션 최대 지속 시간
    poor_repeat_min: int = 5          # 못했을 때 최소 반복
    poor_repeat_max: int = 8          # 못했을 때 최대 반복

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
