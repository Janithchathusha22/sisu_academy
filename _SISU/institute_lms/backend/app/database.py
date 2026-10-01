from supabase import Client, ClientOptions, create_client
from .config import get_settings


def user_client(token: str) -> Client:
    settings = get_settings()
    client = create_client(settings.supabase_url, settings.supabase_publishable_key,
                           options=ClientOptions(auto_refresh_token=False, persist_session=False))
    client.postgrest.auth(token)
    return client


def service_client() -> Client:
    settings = get_settings()
    settings.require_auth()
    return create_client(settings.supabase_url, settings.supabase_service_role_key,
                         options=ClientOptions(auto_refresh_token=False, persist_session=False))
