"""Configuration management with .env support."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env_file() -> str | None:
    """Find .env file in priority order: CWD > home directory."""
    candidates = [
        Path.cwd() / ".env",
        Path.home() / ".confluence_2_md.env",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_find_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    CONFLUENCE_BASE_URL: str = ""
    CONFLUENCE_USERNAME: str = ""
    CONFLUENCE_TOKEN: str = ""

    def validate_required(self) -> None:
        """Raise if required fields are missing."""
        missing = []
        if not self.CONFLUENCE_BASE_URL:
            missing.append("CONFLUENCE_BASE_URL")
        if not self.CONFLUENCE_USERNAME:
            missing.append("CONFLUENCE_USERNAME")
        if not self.CONFLUENCE_TOKEN:
            missing.append("CONFLUENCE_TOKEN")
        if missing:
            raise ValueError(
                f"Missing required configuration: {', '.join(missing)}. "
                f"Set via environment variables or .env file."
            )


def load_settings(
    base_url: str | None = None,
    username: str | None = None,
    token: str | None = None,
) -> Settings:
    """Load settings with optional CLI overrides."""
    settings = Settings()
    if base_url:
        settings.CONFLUENCE_BASE_URL = base_url
    if username:
        settings.CONFLUENCE_USERNAME = username
    if token:
        settings.CONFLUENCE_TOKEN = token
    # Ensure base_url has no trailing slash
    settings.CONFLUENCE_BASE_URL = settings.CONFLUENCE_BASE_URL.rstrip("/")
    return settings
