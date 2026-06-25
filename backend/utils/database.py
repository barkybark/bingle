# backend/utils/database.py
from supabase import create_client, Client
from backend.config import settings

_client: Client | None = None


def get_db() -> Client:
    """Supabase 클라이언트 싱글톤 반환"""
    global _client
    if _client is None:
        _client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )
    return _client