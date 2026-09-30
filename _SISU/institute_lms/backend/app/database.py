from supabase import Client, create_client
from .config import get_settings


def user_client(token: str) -> Client:
    settings = get_settings()
    client = create_client(settings.supabase_url, settings.supabase_publishable_key)
    client.postgrest.auth(token)
    return client


def service_client() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_secret_key)
