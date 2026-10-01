"""Supabase Auth transport. Never log request bodies or provider responses."""
import httpx
from fastapi import HTTPException
from .config import get_settings


def auth_request(method, path, body=None, token=None, params=None):
    settings = get_settings()
    headers = {'apikey': settings.supabase_publishable_key}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    try:
        response = httpx.request(method, settings.supabase_url.rstrip('/') + '/auth/v1/' + path,
                                 headers=headers, json=body, params=params, timeout=15)
    except httpx.HTTPError:
        raise HTTPException(503, 'Authentication service is unavailable. Please try again.') from None
    if response.is_error:
        if response.status_code == 429:
            raise HTTPException(429, 'Too many attempts. Please wait before trying again.')
        if response.status_code >= 500:
            raise HTTPException(503, 'Authentication service is unavailable. Please try again.')
        raise HTTPException(401 if path in {'token', 'user'} else 400,
                            'Authentication failed. Check your details and email verification.')
    return response.json() if response.content else {}
