from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://soborbum:soborbum@db:5432/soborbum"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12

    storage_dir: str = "/app/storage"

    admin_email: str = "admin@soborbum.local"
    admin_password: str = "admin123"
    admin_full_name: str = "Administrator"

    # Comma-separated list of origins the frontend is served from, e.g.
    # "http://localhost:5173,http://localhost:3000". "*" allows any origin.
    cors_allowed_origins: str = "*"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    # --- AI assistant (app/ai) ---
    anthropic_api_key: str = ""
    ai_model: str = "claude-sonnet-5"
    # Remote MCP connector to the knowledge base - OAuth2 client-credentials
    # (the server hands out its own access tokens, we exchange client_id +
    # client_secret for one via mcp_oauth_token_url, see app/ai/mcp_auth.py).
    # Empty mcp_server_url means "no MCP server attached".
    mcp_server_url: str = ""
    mcp_oauth_token_url: str = ""
    mcp_oauth_client_id: str = ""
    mcp_oauth_client_secret: str = ""

    @property
    def mcp_configured(self) -> bool:
        return bool(
            self.mcp_server_url and self.mcp_oauth_token_url and self.mcp_oauth_client_id and self.mcp_oauth_client_secret
        )


settings = Settings()
