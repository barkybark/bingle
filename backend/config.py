# backend/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    allowed_origin: str = "*"

    # Supabase
    supabase_url: str
    supabase_service_role_key: str

    # 학습 제한
    daily_limit: int = 30           # 하루 최대 시도 횟수

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
