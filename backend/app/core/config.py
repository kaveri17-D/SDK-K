from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    PROJECT_NAME: str = "Clipper-X Node Registry"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/clipper_x",
        description="Async PostgreSQL connection URL",
    )
    SYNC_DATABASE_URL: Optional[str] = None

    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for runtime state",
    )

    # Security
    NODE_TOKEN_SECRET: str = Field(
        default="clipper-x-super-secret-key-production-change-me",
        description="Secret key for signing/verifying node tokens",
    )

    # Heartbeat & Telemetry thresholds
    HEARTBEAT_INTERVAL_SECONDS: int = 30
    STALE_AFTER_SECONDS: int = 90
    OFFLINE_AFTER_SECONDS: int = 180
    OFFLINE_CHECK_INTERVAL_SECONDS: int = 10

    # Bandwidth measurement settings
    BANDWIDTH_TEST_SIZE_MB: int = Field(default=5, ge=1, le=50)
    BANDWIDTH_MAX_UPLOAD_MB: int = Field(default=10, ge=1, le=50)

    # Reverse proxy security
    TRUSTED_PROXIES: str = Field(
        default="127.0.0.1,::1",
        description="Comma-separated list of trusted reverse proxy IPs or CIDRs",
    )

    # Logging
    LOG_LEVEL: str = "INFO"

    @property
    def sync_database_url(self) -> str:
        if self.SYNC_DATABASE_URL:
            return self.SYNC_DATABASE_URL
        url = self.DATABASE_URL
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql://", 1)
        if url.startswith("sqlite+aiosqlite://"):
            return url.replace("sqlite+aiosqlite://", "sqlite://", 1)
        return url

    @property
    def trusted_proxies_list(self) -> List[str]:
        if not self.TRUSTED_PROXIES:
            return []
        return [p.strip() for p in self.TRUSTED_PROXIES.split(",") if p.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
