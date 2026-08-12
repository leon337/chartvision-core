"""add Phase 7 session exposure provenance

Revision ID: 0006_add_session_exposure_tracking
Revises: 0005_create_analyses
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_add_session_exposure_tracking"
down_revision = "0005_create_analyses"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column(
            "exposure_tracking_state",
            sa.String(length=32),
            nullable=False,
            server_default="LEGACY_UNKNOWN",
        ),
    )
    op.add_column(
        "sessions",
        sa.Column("session_origin_time", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sessions",
        sa.Column("session_exposure_watermark", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_sessions_exposure_tracking_state",
        "sessions",
        "exposure_tracking_state IN ('TRACKED', 'LEGACY_UNKNOWN')",
    )
    op.create_check_constraint(
        "ck_sessions_exposure_provenance",
        "sessions",
        "((exposure_tracking_state = 'LEGACY_UNKNOWN' "
        "AND session_origin_time IS NULL "
        "AND session_exposure_watermark IS NULL) "
        "OR (exposure_tracking_state = 'TRACKED' "
        "AND session_origin_time IS NOT NULL "
        "AND session_exposure_watermark IS NOT NULL "
        "AND session_exposure_watermark >= session_origin_time))",
    )


def downgrade() -> None:
    op.drop_constraint("ck_sessions_exposure_provenance", "sessions", type_="check")
    op.drop_constraint("ck_sessions_exposure_tracking_state", "sessions", type_="check")
    op.drop_column("sessions", "session_exposure_watermark")
    op.drop_column("sessions", "session_origin_time")
    op.drop_column("sessions", "exposure_tracking_state")
