"""create observations table

Revision ID: 0003_create_observations
Revises: 0002_create_frames
Create Date: 2026-08-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0003_create_observations"
down_revision: str | Sequence[str] | None = "0002_create_frames"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_frames_frame_id_session_id",
        "frames",
        ["frame_id", "session_id"],
    )
    op.create_table(
        "observations",
        sa.Column("observation_id", sa.String(length=255), nullable=False),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("frame_id", sa.String(length=255), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("visual_quality", sa.Float(), nullable=False),
        sa.CheckConstraint(
            "char_length(trim(observation_id)) > 0",
            name="ck_observations_observation_id_not_blank",
        ),
        sa.CheckConstraint(
            "char_length(trim(session_id)) > 0",
            name="ck_observations_session_id_not_blank",
        ),
        sa.CheckConstraint(
            "char_length(trim(frame_id)) > 0",
            name="ck_observations_frame_id_not_blank",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_observations_confidence_range",
        ),
        sa.CheckConstraint(
            "visual_quality >= 0 AND visual_quality <= 1",
            name="ck_observations_visual_quality_range",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["sessions.session_id"],
            name="fk_observations_session_id_sessions",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["frame_id", "session_id"],
            ["frames.frame_id", "frames.session_id"],
            name="fk_observations_frame_session_frames",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("observation_id"),
        sa.UniqueConstraint(
            "observation_id",
            "session_id",
            name="uq_observations_observation_id_session_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("observations")
    op.drop_constraint(
        "uq_frames_frame_id_session_id",
        "frames",
        type_="unique",
    )
