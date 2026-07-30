import asyncio
from contextlib import asynccontextmanager
from secrets import compare_digest

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.config import get_settings
from backend.app.db import run_migrations
from backend.app.routers import health, prices
from backend.app.services.alpaca import AlpacaClient, run_quote_poller


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if not settings.is_deployed or settings.daybook_demo_mode:
        run_migrations()

    app.state.alpaca_client = None
    app.state.quote_refresh_lock = asyncio.Lock()
    app.state.quote_poller_stop = asyncio.Event()
    app.state.quote_poller_task = None

    if (
        settings.alpaca_configured
        and not settings.is_deployed
        and not settings.daybook_demo_mode
    ):
        client = AlpacaClient(settings)
        app.state.alpaca_client = client
        app.state.quote_poller_task = asyncio.create_task(
            run_quote_poller(
                client,
                app.state.quote_poller_stop,
                refresh_lock=app.state.quote_refresh_lock,
            ),
            name="daybook-alpaca-quote-poller",
        )

    try:
        yield
    finally:
        app.state.quote_poller_stop.set()
        poller_task = app.state.quote_poller_task
        client = app.state.alpaca_client
        try:
            if poller_task is not None:
                await poller_task
        finally:
            if client is not None:
                await client.aclose()


app = FastAPI(
    title="Daybook API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


@app.middleware("http")
async def require_api_token(request: Request, call_next):
    settings = get_settings()
    if not settings.requires_api_token:
        return await call_next(request)
    if len(settings.daybook_api_token) < 32:
        return JSONResponse(
            status_code=503,
            content={"detail": "DAYBOOK_API_TOKEN is not securely configured."},
        )
    presented = request.headers.get("x-daybook-api-token", "")
    if not compare_digest(
        presented.encode("utf-8"),
        settings.daybook_api_token.encode("utf-8"),
    ):
        return JSONResponse(status_code=401, content={"detail": "Unauthorized."})
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health.router)
app.include_router(prices.router)
