"""Supabase clients that always preserve the verified caller's RLS context."""

from supabase import Client, ClientOptions, create_client

from .config import Settings, get_settings


def public_client(settings: Settings | None = None) -> Client:
    current = settings or get_settings()
    return create_client(
        str(current.supabase_url),
        current.supabase_publishable_key,
        options=ClientOptions(auto_refresh_token=False, persist_session=False),
    )


def user_client(token: str, settings: Settings | None = None) -> Client:
    client = public_client(settings)
    client.postgrest.auth(token)
    return client
