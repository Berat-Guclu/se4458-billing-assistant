from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    jwt_secret: str
    jwt_issuer: str
    jwt_ttl_seconds: int


def load_settings() -> Settings:
    return Settings(
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://billing:billing@localhost:5432/billing",
        ),
        jwt_secret=os.getenv("JWT_SECRET", "billing-demo-secret-key-please-change"),
        jwt_issuer=os.getenv("JWT_ISSUER", "billing-key"),
        jwt_ttl_seconds=int(os.getenv("JWT_TTL_SECONDS", "28800")),
    )


settings = load_settings()
