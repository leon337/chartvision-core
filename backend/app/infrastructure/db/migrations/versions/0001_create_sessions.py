"""create sessions table

Revision ID: 0001_create_sessions
Revises:
Create Date: 2026-08-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0001_create_sessions"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=False),
        sa.Column("asset", sa.String(length=128), nullable=False),
        sa.Column("timeframe", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "char_length(trim(session_id)) > 0",
            name="ck_sessions_session_id_not_blank",
        ),
        sa.CheckConstraint(
            "char_length(trim(source_id)) > 0",
            name="ck_sessions_source_id_not_blank",
        ),
        sa.CheckConstraint(
            "char_length(trim(asset)) > 0",
            name="ck_sessions_asset_not_blank",
        ),
        sa.CheckConstraint(
            "char_length(trim(timeframe)) > 0",
            name="ck_sessions_timeframe_not_blank",
        ),
        sa.CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at",
            name="ck_sessions_ended_at_not_before_started_at",
        ),
        sa.PrimaryKeyConstraint("session_id"),
    )


def downgrade() -> None:
    op.drop_table("sessions")
