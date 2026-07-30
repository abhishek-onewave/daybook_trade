import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import get_settings
from backend.app.db import run_migrations
from backend.app.routers import health, prices
from backend.app.services.alpaca import AlpacaClient, run_quote_poller


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if not settings.vercel:
        run_migrations()

    app.state.alpaca_client = None
    app.state.quote_refresh_lock = asyncio.Lock()
    app.state.quote_poller_stop = asyncio.Event()
    app.state.quote_poller_task = None

    if settings.alpaca_configured and not settings.vercel:
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health.router)
app.include_router(prices.router)
