from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://soborbum:soborbum@db:5432/soborbum"

    environment: Literal["development", "production", "test"] = "production"
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12

    storage_dir: str = "/app/storage"

    admin_email: str = "admin@soborbum.local"
    admin_password: str = ""
    admin_full_name: str = "Administrator"

    # Comma-separated list of origins the frontend is served from, e.g.
    # "http://localhost:5173,http://localhost:3000". "*" allows any origin.
    cors_allowed_origins: str = "http://localhost:5173"

    @model_validator(mode="after")
    def validate_secrets(self):
        if len(self.jwt_secret) < 32 or self.jwt_secret == "change-me-in-production":
            raise ValueError("JWT_SECRET must be a unique secret of at least 32 characters")
        if self.admin_password and (len(self.admin_password) < 12 or len(self.admin_password.encode("utf-8")) > 72):
            raise ValueError("ADMIN_PASSWORD must contain at least 12 characters and at most 72 UTF-8 bytes")
        if self.environment == "production" and "*" in self.cors_origins:
            raise ValueError("Set explicit CORS_ALLOWED_ORIGINS in production")
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    # --- AI assistant (app/ai) ---
    anthropic_api_key: str = ""
    ai_model: str = "claude-sonnet-5"

    # Remote MCP connector to the knowledge base. The provider advertises
    # only the authorization_code grant (no client_credentials), but issues
    # the code without a consent screen, so app/ai/mcp_auth.py runs that
    # grant headlessly and keeps the token fresh with no human involved.
    # mcp_redirect_uri is never fetched in that flow, but is still sent and
    # validated, so it must match a redirect URI registered for this OAuth
    # client with the provider.
    mcp_server_url: str = ""
    mcp_oauth_client_id: str = ""
    mcp_oauth_client_secret: str = ""
    mcp_redirect_uri: str = "http://127.0.0.1:8000/callback"

    @property
    def mcp_configured(self) -> bool:
        return bool(self.mcp_server_url and self.mcp_oauth_client_id and self.mcp_oauth_client_secret)


settings = Settings()
