"""Application settings, read from environment with development defaults."""

import os
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    app_name: str = "Reelfit"
    secret_key: str = field(
        default_factory=lambda: os.getenv("REELFIT_SECRET_KEY", "dev-insecure-secret")
    )
    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./reelfit.db")
    )
    debug: bool = field(
        default_factory=lambda: os.getenv("REELFIT_DEBUG", "0") == "1"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
