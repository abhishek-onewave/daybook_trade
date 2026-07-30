"""Protect Daybook tables from Supabase's public Data API.

Revision ID: 0002_supabase_rls
Revises: 0001_phase_0
Create Date: 2026-07-29
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_supabase_rls"
down_revision: str | None = "0001_phase_0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "alembic_version",
    "conversations",
    "messages",
    "watchlist",
    "news_items",
    "quotes_cache",
    "tt_tokens",
    "portfolio_snapshots",
    "settings",
    "usage_log",
)


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
