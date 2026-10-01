"""Supabase client factories.

Request handlers use the caller's JWT with the publishable client so PostgreSQL
RLS remains active. The secret client is intentionally a separate factory for
trusted server jobs and is never returned to the browser.
"""

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


def admin_client(settings: Settings | None = None) -> Client:
    current = settings or get_settings()
    return create_client(
        str(current.supabase_url),
        current.supabase_secret_key,
        options=ClientOptions(auto_refresh_token=False, persist_session=False),
    )


def service_client() -> Client:
    settings = get_settings()
    settings.require_auth()
    return admin_client(settings)


def service_client() -> Client:
    settings = get_settings()
    settings.require_auth()
    return admin_client(settings)
