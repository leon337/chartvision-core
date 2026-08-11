"""create immutable analyses

Revision ID: 0005_create_analyses
Revises: 0004_create_candles
Create Date: 2026-08-11
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0005_create_analyses"
down_revision: str | Sequence[str] | None = "0004_create_candles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analyses",
        sa.Column("analysis_id", sa.String(length=255), nullable=False),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("market_state", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("data_quality", sa.Float(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "char_length(trim(analysis_id)) > 0",
            name="ck_analyses_analysis_id_not_blank",
        ),
        sa.CheckConstraint(
            "char_length(trim(session_id)) > 0",
            name="ck_analyses_session_id_not_blank",
        ),
        sa.CheckConstraint(
            "market_state IN ('UP', 'DOWN', 'SIDEWAYS', 'UNCERTAIN')",
            name="ck_analyses_market_state",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_analyses_confidence_range",
        ),
        sa.CheckConstraint(
            "data_quality IS NULL OR (data_quality >= 0 AND data_quality <= 1)",
            name="ck_analyses_data_quality_range",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["sessions.session_id"],
            name="fk_analyses_session_id_sessions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("analysis_id"),
    )


def downgrade() -> None:
    op.drop_table("analyses")
