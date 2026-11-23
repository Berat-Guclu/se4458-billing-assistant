from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import SessionLocal, init_db
from .routers import auth, bills, usage
from .seed import seed_if_empty

logger = logging.getLogger("billing")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("SEED_ON_STARTUP", "false").lower() in {"1", "true", "yes"}:
        init_db()
        db = SessionLocal()
        try:
            seed_if_empty(db)
            logger.info("Billing database is ready")
        finally:
            db.close()
    yield


app = FastAPI(
    title="Mobile Provider Billing API",
    version="1.0.0",
    description=(
        "Versioned billing operations for the SE4458 Group 2 assistant. "
        "Call these routes through the API gateway. "
        "Money is simulated USD. 1 GB = 1,000 MB. "
        "Phone: the first 1,000 minutes are free, then $10 per started 1,000-minute block. "
        "Internet: $50 up to 20 GB, then $10 per started additional 10 GB block."
    ),
    servers=[
        {
            "url": "/",
            "description": "This host. Graded calls use the AWS API Gateway invoke URL.",
        },
    ],
    lifespan=lifespan,
    redirect_slashes=False,
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(usage.router, prefix="/api/v1")
app.include_router(bills.router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
def health() -> dict:
    return {"status": "ok", "service": "billing-api", "version": "v1"}
