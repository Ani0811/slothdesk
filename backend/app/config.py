"""Configuration settings for SlothDesk backend."""

from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration with validation and sensible defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    SLOTHDESK_ROOT: str = "./test_downloads"
    SLOTHDESK_DATA_DIR: str = "./.slothdesk_data"
    LM_STUDIO_BASE_URL: str = "http://localhost:1234/v1"
    LM_STUDIO_MODEL: str = "qwen2.5-7b-instruct"
    PLAN_EXPIRY_SECONDS: int = 900  # 15 minutes
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:3000",
    ]

    @property
    def root_path(self) -> Path:
        """Returns the canonical Path object for the configured root directory."""
        path = Path(self.SLOTHDESK_ROOT).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def data_path(self) -> Path:
        """Returns the canonical Path object for persistent application data."""
        path = Path(self.SLOTHDESK_DATA_DIR).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def manifests_path(self) -> Path:
        """Returns the directory where execution manifests are saved."""
        p = self.data_path / "manifests"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def plans_path(self) -> Path:
        """Returns the directory where active plans are cached."""
        p = self.data_path / "plans"
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
