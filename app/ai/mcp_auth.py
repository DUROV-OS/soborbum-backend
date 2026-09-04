"""Interactive OAuth2 (authorization_code + PKCE) for the MCP knowledge-base
connector, and access-token refresh once that's done.

Claude's MCP connector (see engine._call_claude) just wants a bearer token
in `authorization_token` - it doesn't do the OAuth exchange itself. This
particular provider's .well-known/oauth-authorization-server only lists
`authorization_code` and `refresh_token` grants (no client_credentials), so
an admin has to complete a one-time browser authorization once
(GET /api/ai/mcp/authorize -> approve -> GET /callback) before the
assistant can use the knowledge base; from then on get_access_token()
refreshes automatically using the stored refresh_token.
"""

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.ai.models import McpCredential
from app.core.config import settings

# state -> code_verifier, for the short window between /authorize and /callback.
_pending_pkce: dict[str, str] = {}

_cached_metadata: dict | None = None


def _discover_metadata() -> dict:
    global _cached_metadata
    if _cached_metadata:
        return _cached_metadata

    parsed = urlparse(settings.mcp_server_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    candidates = []
    if parsed.path and parsed.path != "/":
        candidates.append(f"{origin}/.well-known/oauth-authorization-server{parsed.path}")
    candidates.append(f"{origin}/.well-known/oauth-authorization-server")

    for url in candidates:
        try:
            response = httpx.get(url, timeout=10.0)
            if response.status_code == 200:
                _cached_metadata = response.json()
                return _cached_metadata
        except httpx.HTTPError:
            continue

    # No discovery document - assume the bare server URL doubles as both endpoints.
    _cached_metadata = {
        "authorization_endpoint": settings.mcp_server_url,
        "token_endpoint": settings.mcp_server_url,
    }
    return _cached_metadata


def _generate_pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def build_authorize_url() -> str:
    if not settings.mcp_configured:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MCP не настроен: заполните MCP_SERVER_URL, MCP_OAUTH_CLIENT_ID, MCP_OAUTH_CLIENT_SECRET",
        )

    metadata = _discover_metadata()
    verifier, challenge = _generate_pkce_pair()
    state = secrets.token_urlsafe(24)
    _pending_pkce[state] = verifier

    params = {
        "response_type": "code",
        "client_id": settings.mcp_oauth_client_id,
        "redirect_uri": settings.mcp_redirect_uri,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return f"{metadata['authorization_endpoint']}?{urlencode(params)}"


def exchange_code_for_tokens(db: Session, code: str, state: str) -> McpCredential:
    verifier = _pending_pkce.pop(state, None)
    if verifier is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неизвестный или устаревший state - начните авторизацию заново через /api/ai/mcp/authorize",
        )

    metadata = _discover_metadata()
    try:
        response = httpx.post(
            metadata["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.mcp_redirect_uri,
                "client_id": settings.mcp_oauth_client_id,
                "client_secret": settings.mcp_oauth_client_secret,
                "code_verifier": verifier,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Не удалось обменять код авторизации на токен MCP: {e}",
        ) from e

    return _store_tokens(db, payload)


def _store_tokens(db: Session, payload: dict) -> McpCredential:
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=float(payload.get("expires_in", 3600)))
    credential = db.get(McpCredential, 1)
    if credential is None:
        credential = McpCredential(id=1, access_token=payload["access_token"], expires_at=expires_at)
        db.add(credential)
    else:
        credential.access_token = payload["access_token"]
        credential.expires_at = expires_at
    # Some providers only send a refresh_token on the very first grant.
    if payload.get("refresh_token"):
        credential.refresh_token = payload["refresh_token"]
    db.commit()
    db.refresh(credential)
    return credential


def get_access_token(db: Session) -> str:
    credential = db.get(McpCredential, 1)
    if credential is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MCP ещё не авторизован. Администратор должен один раз пройти "
            "GET /api/ai/mcp/authorize в браузере.",
        )

    if credential.expires_at > datetime.now(timezone.utc) + timedelta(seconds=30):
        return credential.access_token

    if not credential.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Токен MCP истёк и обновить его нечем (нет refresh_token) - "
            "повторите авторизацию через GET /api/ai/mcp/authorize.",
        )

    metadata = _discover_metadata()
    try:
        response = httpx.post(
            metadata["token_endpoint"],
            data={
                "grant_type": "refresh_token",
                "refresh_token": credential.refresh_token,
                "client_id": settings.mcp_oauth_client_id,
                "client_secret": settings.mcp_oauth_client_secret,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Не удалось обновить токен MCP - возможно нужна повторная авторизация "
            f"через GET /api/ai/mcp/authorize: {e}",
        ) from e

    return _store_tokens(db, payload).access_token
