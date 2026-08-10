"""create candles and immutable candle snapshots

Revision ID: 0004_create_candles
Revises: 0003_create_observations
Create Date: 2026-08-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0004_create_candles"
down_revision: str | Sequence[str] | None = "0003_create_observations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _candle_checks(prefix: str) -> list[sa.CheckConstraint]:
    return [
        sa.CheckConstraint(
            "char_length(trim(session_id)) > 0",
            name=f"ck_{prefix}_session_id_not_blank",
        ),
        sa.CheckConstraint(
            "char_length(trim(source_id)) > 0",
            name=f"ck_{prefix}_source_id_not_blank",
        ),
        sa.CheckConstraint(
            "char_length(trim(asset)) > 0",
            name=f"ck_{prefix}_asset_not_blank",
        ),
        sa.CheckConstraint(
            "char_length(trim(timeframe)) > 0",
            name=f"ck_{prefix}_timeframe_not_blank",
        ),
        sa.CheckConstraint("close_time > open_time", name=f"ck_{prefix}_time_order"),
        sa.CheckConstraint("high >= open", name=f"ck_{prefix}_high_ge_open"),
        sa.CheckConstraint("high >= close", name=f"ck_{prefix}_high_ge_close"),
        sa.CheckConstraint("low <= open", name=f"ck_{prefix}_low_le_open"),
        sa.CheckConstraint("low <= close", name=f"ck_{prefix}_low_le_close"),
        sa.CheckConstraint("low <= high", name=f"ck_{prefix}_low_le_high"),
        sa.CheckConstraint(
            "vision_confidence IS NULL OR (vision_confidence >= 0 AND vision_confidence <= 1)",
            name=f"ck_{prefix}_vision_confidence_range",
        ),
        sa.CheckConstraint(
            "source_confidence IS NULL OR (source_confidence >= 0 AND source_confidence <= 1)",
            name=f"ck_{prefix}_source_confidence_range",
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "candles",
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=False),
        sa.Column("asset", sa.String(length=128), nullable=False),
        sa.Column("timeframe", sa.String(length=32), nullable=False),
        sa.Column("open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("close_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(38, 18), nullable=False),
        sa.Column("high", sa.Numeric(38, 18), nullable=False),
        sa.Column("low", sa.Numeric(38, 18), nullable=False),
        sa.Column("close", sa.Numeric(38, 18), nullable=False),
        sa.Column("is_closed", sa.Boolean(), nullable=False),
        sa.Column("vision_confidence", sa.Float(), nullable=True),
        sa.Column("source_confidence", sa.Float(), nullable=True),
        *_candle_checks("candles"),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["sessions.session_id"],
            name="fk_candles_session_id_sessions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("session_id", "open_time"),
    )

    op.create_table(
        "candle_snapshots",
        sa.Column("observation_id", sa.String(length=255), nullable=False),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=False),
        sa.Column("asset", sa.String(length=128), nullable=False),
        sa.Column("timeframe", sa.String(length=32), nullable=False),
        sa.Column("open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("close_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(38, 18), nullable=False),
        sa.Column("high", sa.Numeric(38, 18), nullable=False),
        sa.Column("low", sa.Numeric(38, 18), nullable=False),
        sa.Column("close", sa.Numeric(38, 18), nullable=False),
        sa.Column("is_closed", sa.Boolean(), nullable=False),
        sa.Column("vision_confidence", sa.Float(), nullable=True),
        sa.Column("source_confidence", sa.Float(), nullable=True),
        sa.CheckConstraint(
            "char_length(trim(observation_id)) > 0",
            name="ck_candle_snapshots_observation_id_not_blank",
        ),
        *_candle_checks("candle_snapshots"),
        sa.ForeignKeyConstraint(
            ["observation_id", "session_id"],
            ["observations.observation_id", "observations.session_id"],
            name="fk_candle_snapshots_observation_session",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["session_id", "open_time"],
            ["candles.session_id", "candles.open_time"],
            name="fk_candle_snapshots_candle_identity",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("observation_id", "session_id", "open_time"),
    )


def downgrade() -> None:
    op.drop_table("candle_snapshots")
    op.drop_table("candles")
