from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]

MODEL_FLAGSHIP = "claude-fable-5"
MODEL_STANDARD = "claude-sonnet-4-6"
MODEL_LIGHT = "claude-haiku-4-5-20251001"
POSTGRES_SCHEMES = ("postgres://", "postgresql://", "postgresql+psycopg://")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Daybook"
    app_environment: str = "development"
    anthropic_api_key: str = ""
    alpaca_api_key_id: str = ""
    alpaca_api_secret_key: str = ""
    tastytrade_client_id: str = ""
    tastytrade_client_secret: str = ""
    tastytrade_env: str = "sandbox"
    finnhub_api_key: str = ""
    daybook_daily_chat_cap: int = Field(default=300, ge=1)
    database_url: str = "sqlite:///./data/daybook.db"
    secret_key: str = ""
    daybook_api_token: str = ""
    daybook_demo_mode: bool = False
    vercel: bool = False

    @property
    def is_deployed(self) -> bool:
        return self.vercel or self.app_environment.casefold() == "production"

    @property
    def uses_postgres(self) -> bool:
        return self.database_url.startswith(POSTGRES_SCHEMES)

    @property
    def requires_api_token(self) -> bool:
        if self.daybook_demo_mode:
            return False
        # Supabase-backed local runs are protected too, so a missing optional
        # Vercel system variable cannot expose the production API.
        return bool(self.daybook_api_token) or self.is_deployed or self.uses_postgres

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.daybook_demo_mode:
            if self.uses_postgres:
                raise ValueError(
                    "Disable DAYBOOK_DEMO_MODE before connecting Supabase Postgres."
                )
            if self.is_deployed:
                return "sqlite:////tmp/daybook-demo.db"
        if self.is_deployed and not self.uses_postgres:
            raise ValueError("DATABASE_URL must use Supabase Postgres in production.")
        database_url = self.database_url
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
        elif database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        if not database_url.startswith("postgresql+psycopg://"):
            return database_url

        parsed = urlsplit(database_url)
        if self.is_deployed and parsed.port != 6543:
            raise ValueError(
                "DATABASE_URL must use the Supabase transaction pooler on port 6543 "
                "in production."
            )
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        sslmode = query.get("sslmode", "").lower()
        if sslmode and sslmode not in {"require", "verify-ca", "verify-full"}:
            raise ValueError("PostgreSQL DATABASE_URL must enforce TLS.")
        query["sslmode"] = sslmode or "require"
        return urlunsplit(parsed._replace(query=urlencode(query)))

    @property
    def anthropic_configured(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def alpaca_configured(self) -> bool:
        return bool(self.alpaca_api_key_id and self.alpaca_api_secret_key)

    @property
    def tastytrade_configured(self) -> bool:
        return bool(self.tastytrade_client_id and self.tastytrade_client_secret)

    @property
    def finnhub_configured(self) -> bool:
        return bool(self.finnhub_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
