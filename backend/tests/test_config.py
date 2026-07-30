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
    )
    assert (
        Settings(
            _env_file=None,
            database_url="postgresql://postgres:secret@pooler.example:6543/postgres",
        ).sqlalchemy_database_url
        == "postgresql+psycopg://postgres:secret@pooler.example:6543/postgres"
    )
    assert (
        Settings(
            _env_file=None,
            database_url="postgresql+psycopg://postgres:secret@pooler.example/postgres",
        ).sqlalchemy_database_url
        == "postgresql+psycopg://postgres:secret@pooler.example/postgres"
    )
    assert (
        Settings(_env_file=None, database_url="sqlite:///./data/daybook.db").sqlalchemy_database_url
        == "sqlite:///./data/daybook.db"
    )


def test_vercel_rejects_ephemeral_sqlite() -> None:
    with pytest.raises(ValueError, match="Supabase Postgres"):
        Settings(_env_file=None, vercel=True).sqlalchemy_database_url


def test_migration_url_preserves_percent_encoded_passwords() -> None:
    database_url = "postgresql+psycopg://postgres:p%40ss@pooler.example:6543/postgres"
    with (
        patch.object(db, "database_url", database_url),
        patch.object(db.command, "upgrade") as upgrade,
    ):
        db.run_migrations()

    config = upgrade.call_args.args[0]
    assert config.get_main_option("sqlalchemy.url") == database_url
