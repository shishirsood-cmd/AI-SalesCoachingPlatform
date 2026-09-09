from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://coach:coach@localhost:5432/salescoach"
    jwt_secret: str = "change-me-in-env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12
    cors_origins: list[str] = ["http://localhost:3000"]
    storage_root: str = "./storage"
    max_upload_bytes: int = 20 * 1024 * 1024
    anthropic_api_key: str | None = None
    claude_model: str = "claude-sonnet-5"
    rag_top_k: int = 4
    deepgram_api_key: str | None = None
    elevenlabs_api_key: str | None = None
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"

    @property
    def async_database_url(self) -> str:
        """Normalize whatever scheme the host gives us (e.g. Render's plain
        `postgres://`/`postgresql://`) to the asyncpg driver URL SQLAlchemy needs."""
        url = self.database_url
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        if url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://") :]
        return url


settings = Settings()
