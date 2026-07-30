from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from ..config import get_settings
from ..db import SessionLocal

router = APIRouter(prefix="/api", tags=["health"])


class IntegrationStatus(BaseModel):
    anthropic_configured: bool
    alpaca_configured: bool
    tastytrade_configured: bool
    finnhub_configured: bool


class DatabaseStatus(BaseModel):
    configured: bool
    connected: bool
    persistent: bool


CapabilityState = Literal[
    "ready",
    "not_configured",
    "disabled_in_demo",
    "pending_phase",
]


class CapabilityStatus(BaseModel):
    configured: bool
    enabled: bool
    implemented: bool
    state: CapabilityState


class CapabilityStatuses(BaseModel):
    anthropic: CapabilityStatus
    alpaca: CapabilityStatus
    tastytrade: CapabilityStatus
    finnhub: CapabilityStatus


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    mode: Literal["demo", "live"]
    as_of: datetime
    database: DatabaseStatus
    integrations: IntegrationStatus
    capabilities: CapabilityStatuses
    tastytrade_environment: str


def _capability(
    *,
    configured: bool,
    demo_mode: bool,
    implemented: bool,
) -> CapabilityStatus:
    if not configured:
        state: CapabilityState = "not_configured"
    elif demo_mode:
        state = "disabled_in_demo"
    elif not implemented:
        state = "pending_phase"
    else:
        state = "ready"
    return CapabilityStatus(
        configured=configured,
        enabled=state == "ready",
        implemented=implemented,
        state=state,
    )


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
            persistent=settings.uses_postgres and not settings.daybook_demo_mode,
        ),
        integrations=IntegrationStatus(
            anthropic_configured=settings.anthropic_configured,
            alpaca_configured=settings.alpaca_configured,
            tastytrade_configured=settings.tastytrade_configured,
            finnhub_configured=settings.finnhub_configured,
        ),
        capabilities=CapabilityStatuses(
            anthropic=_capability(
                configured=settings.anthropic_configured,
                demo_mode=settings.daybook_demo_mode,
                implemented=False,
            ),
            alpaca=_capability(
                configured=settings.alpaca_configured,
                demo_mode=settings.daybook_demo_mode,
                implemented=True,
            ),
            tastytrade=_capability(
                configured=settings.tastytrade_configured,
                demo_mode=settings.daybook_demo_mode,
                implemented=False,
            ),
            finnhub=_capability(
                configured=settings.finnhub_configured,
                demo_mode=settings.daybook_demo_mode,
                implemented=False,
            ),
        ),
        tastytrade_environment=settings.tastytrade_env,
    )
