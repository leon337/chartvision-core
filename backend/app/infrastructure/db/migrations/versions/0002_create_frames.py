"""create frames table

Revision ID: 0002_create_frames
Revises: 0001_create_sessions
Create Date: 2026-08-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0002_create_frames"
down_revision: str | Sequence[str] | None = "0001_create_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "frames",
        sa.Column("frame_id", sa.String(length=255), nullable=False),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("image_hash", sa.String(length=128), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("changed_since_previous", sa.Boolean(), nullable=False),
        sa.Column("storage_reference", sa.String(length=1024), nullable=True),
        sa.CheckConstraint(
            "char_length(trim(frame_id)) > 0",
            name="ck_frames_frame_id_not_blank",
        ),
        sa.CheckConstraint(
            "char_length(trim(session_id)) > 0",
            name="ck_frames_session_id_not_blank",
        ),
        sa.CheckConstraint(
            "char_length(trim(image_hash)) > 0",
            name="ck_frames_image_hash_not_blank",
        ),
        sa.CheckConstraint("width > 0", name="ck_frames_width_positive"),
        sa.CheckConstraint("height > 0", name="ck_frames_height_positive"),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["sessions.session_id"],
            name="fk_frames_session_id_sessions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("frame_id"),
    )


def downgrade() -> None:
    op.drop_table("frames")
