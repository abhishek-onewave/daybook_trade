from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from backend.app.config import get_settings
from backend.app.db import SessionLocal

router = APIRouter(prefix="/api", tags=["health"])


class IntegrationStatus(BaseModel):
    anthropic_configured: bool
    alpaca_configured: bool
    tastytrade_configured: bool
    finnhub_configured: bool


class DatabaseStatus(BaseModel):
    configured: bool
    connected: bool


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    mode: Literal["demo", "live"]
    as_of: datetime
    database: DatabaseStatus
    integrations: IntegrationStatus
    tastytrade_environment: str


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    database_connected = False
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        database_connected = True
    except Exception:
        database_connected = False

    return HealthResponse(
        status="ok" if database_connected else "degraded",
        mode="demo" if settings.daybook_demo_mode else "live",
        as_of=datetime.now(UTC),
        database=DatabaseStatus(
            configured=bool(settings.database_url),
            connected=database_connected,
        ),
        integrations=IntegrationStatus(
            anthropic_configured=settings.anthropic_configured,
            alpaca_configured=settings.alpaca_configured,
            tastytrade_configured=settings.tastytrade_configured,
            finnhub_configured=settings.finnhub_configured,
        ),
        tastytrade_environment=settings.tastytrade_env,
    )
