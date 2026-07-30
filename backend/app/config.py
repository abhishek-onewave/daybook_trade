from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]

MODEL_FLAGSHIP = "claude-fable-5"
MODEL_STANDARD = "claude-sonnet-4-6"
MODEL_LIGHT = "claude-haiku-4-5-20251001"


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
    vercel: bool = False

    @property
    def sqlalchemy_database_url(self) -> str:
        postgres_schemes = ("postgres://", "postgresql://", "postgresql+psycopg://")
        if self.vercel and not self.database_url.startswith(postgres_schemes):
            raise ValueError("DATABASE_URL must use Supabase Postgres on Vercel.")
        if self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql+psycopg://", 1)
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self.database_url

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
