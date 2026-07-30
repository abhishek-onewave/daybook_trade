from unittest.mock import patch

import pytest
from backend.app import db
from backend.app.config import Settings


def test_database_urls_select_psycopg_only_for_plain_postgres_schemes() -> None:
    assert (
        Settings(
            _env_file=None,
            database_url="postgres://postgres:secret@pooler.example:6543/postgres",
        ).sqlalchemy_database_url
        == "postgresql+psycopg://postgres:secret@pooler.example:6543/postgres"
        "?sslmode=require"
    )
    assert (
        Settings(
            _env_file=None,
            database_url="postgresql://postgres:secret@pooler.example:6543/postgres",
        ).sqlalchemy_database_url
        == "postgresql+psycopg://postgres:secret@pooler.example:6543/postgres"
        "?sslmode=require"
    )
    assert (
        Settings(
            _env_file=None,
            database_url="postgresql+psycopg://postgres:secret@pooler.example/postgres",
        ).sqlalchemy_database_url
        == "postgresql+psycopg://postgres:secret@pooler.example/postgres"
        "?sslmode=require"
    )
    assert (
        Settings(_env_file=None, database_url="sqlite:///./data/daybook.db").sqlalchemy_database_url
        == "sqlite:///./data/daybook.db"
    )


def test_vercel_rejects_ephemeral_sqlite() -> None:
    with pytest.raises(ValueError, match="Supabase Postgres"):
        Settings(_env_file=None, vercel=True).sqlalchemy_database_url


def test_vercel_demo_uses_ephemeral_sqlite_without_an_api_token() -> None:
    settings = Settings(_env_file=None, vercel=True, daybook_demo_mode=True)

    assert settings.sqlalchemy_database_url == "sqlite:////tmp/daybook-demo.db"
    assert settings.requires_api_token is False


def test_demo_mode_refuses_to_connect_to_postgres() -> None:
    settings = Settings(
        _env_file=None,
        vercel=True,
        daybook_demo_mode=True,
        database_url="postgresql://postgres:secret@pooler.example:6543/postgres",
    )

    with pytest.raises(ValueError, match="Disable DAYBOOK_DEMO_MODE"):
        settings.sqlalchemy_database_url


def test_vercel_database_url_enforces_tls() -> None:
    secure = Settings(
        _env_file=None,
        vercel=True,
        database_url="postgresql://postgres:secret@pooler.example:6543/postgres",
    )
    assert secure.sqlalchemy_database_url.endswith("?sslmode=require")

    with pytest.raises(ValueError, match="TLS"):
        Settings(
            _env_file=None,
            vercel=True,
            database_url=(
                "postgresql://postgres:secret@pooler.example:6543/postgres?sslmode=disable"
            ),
        ).sqlalchemy_database_url


def test_all_postgres_connections_reject_optional_tls() -> None:
    with pytest.raises(ValueError, match="TLS"):
        Settings(
            _env_file=None,
            database_url=(
                "postgresql://postgres:secret@db.example:5432/postgres?sslmode=prefer"
            ),
        ).sqlalchemy_database_url


def test_production_marker_enforces_serverless_database_contract() -> None:
    secure = Settings(
        _env_file=None,
        app_environment="production",
        database_url="postgresql://postgres:secret@pooler.example:6543/postgres",
    )
    assert secure.is_deployed is True
    assert secure.requires_api_token is True
    assert secure.sqlalchemy_database_url.endswith("?sslmode=require")

    with pytest.raises(ValueError, match="port 6543"):
        Settings(
            _env_file=None,
            app_environment="production",
            database_url="postgresql://postgres:secret@db.example:5432/postgres",
        ).sqlalchemy_database_url


def test_migration_url_preserves_percent_encoded_passwords() -> None:
    database_url = "postgresql+psycopg://postgres:p%40ss@pooler.example:6543/postgres"
    with (
        patch.object(db, "database_url", database_url),
        patch.object(db.command, "upgrade") as upgrade,
    ):
        db.run_migrations()

    config = upgrade.call_args.args[0]
    assert config.get_main_option("sqlalchemy.url") == database_url
