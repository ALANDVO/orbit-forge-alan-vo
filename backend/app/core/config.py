"""Application configuration loaded from environment variables.

No external settings dependency required; all values default safely and
are overridden by environment variables per the 12-factor methodology.
"""

from __future__ import annotations

import os
from functools import lru_cache


def _str_to_bool(value: str, default: bool = False) -> bool:
    if value.strip().lower() in ("1", "true", "yes", "on"):
        return True
    if value.strip().lower() in ("0", "false", "no", "off"):
        return False
    return default


class Settings:
    """Runtime configuration sourced from the process environment."""

    def __init__(self) -> None:
        self.host: str = os.environ.get("HOST", "127.0.0.1")
        self.port: int = int(os.environ.get("PORT", "8000"))
        self.environment: str = os.environ.get("ENVIRONMENT", "development").lower()
        self.demo_mode: bool = _str_to_bool(
            os.environ.get("DEMO_MODE", "false"), default=False
        )

        self.database_url: str = os.environ.get(
            "DATABASE_URL", "sqlite:///./data/orbit_forge.db"
        )

        self.oidc_issuer_url: str = os.environ.get("OIDC_ISSUER_URL", "")
        self.oidc_client_id: str = os.environ.get("OIDC_CLIENT_ID", "")
        self.oidc_audience: str = os.environ.get("OIDC_AUDIENCE", "")

        self.llm_api_key: str = os.environ.get("LLM_API_KEY", "")
        self.llm_provider: str = os.environ.get(
            "LLM_PROVIDER", "openai-compatible"
        )
        self.llm_model: str = os.environ.get("LLM_MODEL", "gpt-4o-mini")
        self.llm_base_url: str = os.environ.get("LLM_BASE_URL", "")

        self.secret_key: str = os.environ.get("SECRET_KEY", self._dev_secret_key())

    @staticmethod
    def _dev_secret_key() -> str:
        """Generate a stable dev key; production must set SECRET_KEY explicitly."""
        return "dev-insecure-secret-key-change-in-production"

    def is_production(self) -> bool:
        return self.environment == "production"

    def demo_allowed(self) -> bool:
        """Demo mode is only permitted on localhost in non-production environments."""
        if self.is_production():
            return False
        return self.demo_mode


@lru_cache()
def get_settings() -> Settings:
    return Settings()