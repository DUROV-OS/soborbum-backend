"""OAuth2 client-credentials token acquisition for the MCP knowledge-base
connector. Claude's MCP connector (see engine._call_claude) just wants a
bearer token in `authorization_token` - it doesn't do the OAuth exchange
itself, so we fetch and cache one here.
"""

import time

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

_cached_token: str | None = None
_cached_expires_at: float = 0.0
_EXPIRY_SAFETY_MARGIN_SECONDS = 30


def get_access_token() -> str:
    global _cached_token, _cached_expires_at

    if _cached_token and time.time() < _cached_expires_at - _EXPIRY_SAFETY_MARGIN_SECONDS:
        return _cached_token

    try:
        response = httpx.post(
            settings.mcp_oauth_token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": settings.mcp_oauth_client_id,
                "client_secret": settings.mcp_oauth_client_secret,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        payload = response.json()
        token = payload["access_token"]
    except (httpx.HTTPError, KeyError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Не удалось получить токен для MCP-сервера базы знаний: {e}",
        ) from e

    _cached_token = token
    _cached_expires_at = time.time() + float(payload.get("expires_in", 3600))
    return token
