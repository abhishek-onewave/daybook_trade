"""Create the initial Daybook schema and seed local defaults.

Revision ID: 0001_phase_0
Revises:
Create Date: 2026-07-29
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "0001_phase_0"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "news_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tickers_json", sa.Text(), nullable=False),
        sa.Column("sentiment", sa.String(length=20), nullable=True),
        sa.Column("why", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )
    op.create_table(
        "portfolio_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("balances_json", sa.Text(), nullable=False),
        sa.Column("positions_json", sa.Text(), nullable=False),
        sa.Column("metrics_json", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "quotes_cache",
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("last", sa.String(length=32), nullable=True),
        sa.Column("change_abs", sa.String(length=32), nullable=True),
        sa.Column("change_pct", sa.String(length=32), nullable=True),
        sa.Column("volume", sa.Integer(), nullable=True),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("symbol"),
    )
    op.create_table(
        "settings",
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("value_json", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_table(
        "tt_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("access_token_enc", sa.Text(), nullable=False),
        sa.Column("refresh_token_enc", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "usage_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("chat_turns", sa.Integer(), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False),
        sa.Column("tokens_out", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_usage_log_day"), "usage_log", ["day"], unique=False)
    op.create_table(
        "watchlist",
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("symbol"),
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations_json", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    now = datetime.now(UTC)
    watchlist = sa.table(
        "watchlist",
        sa.column("symbol", sa.String),
        sa.column("name", sa.String),
        sa.column("added_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        watchlist,
        [
            {"symbol": "NVDA", "name": "NVIDIA", "added_at": now},
            {"symbol": "AAPL", "name": "Apple", "added_at": now},
            {"symbol": "MSFT", "name": "Microsoft", "added_at": now},
            {"symbol": "TSLA", "name": "Tesla", "added_at": now},
            {"symbol": "AMD", "name": "Advanced Micro Devices", "added_at": now},
        ],
    )

    settings = sa.table(
        "settings",
        sa.column("key", sa.String),
        sa.column("value_json", sa.Text),
    )
    op.bulk_insert(
        settings,
        [
            {"key": "name", "value_json": '"Tracy"'},
            {"key": "answer_depth", "value_json": '"standard"'},
            {"key": "refresh_cadence", "value_json": "15"},
        ],
    )


def downgrade() -> None:
    op.drop_table("messages")
    op.drop_table("watchlist")
    op.drop_index(op.f("ix_usage_log_day"), table_name="usage_log")
    op.drop_table("usage_log")
    op.drop_table("tt_tokens")
    op.drop_table("settings")
    op.drop_table("quotes_cache")
    op.drop_table("portfolio_snapshots")
    op.drop_table("news_items")
    op.drop_table("conversations")

