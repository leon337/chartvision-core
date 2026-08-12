"""create Phase 7 outcome evaluation policies

Revision ID: 0007_create_outcome_policies
Revises: 0006_session_exposure
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_create_outcome_policies"
down_revision = "0006_session_exposure"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outcome_evaluation_policies",
        sa.Column("policy_id", sa.String(length=255), nullable=False),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("horizon_closed_candles", sa.Integer(), nullable=False),
        sa.Column("realized_return_threshold", sa.Numeric(78, 38), nullable=False),
        sa.Column("bound_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "char_length(trim(policy_id)) > 0",
            name="ck_outcome_policies_policy_id_not_blank",
        ),
        sa.CheckConstraint(
            "char_length(trim(session_id)) > 0",
            name="ck_outcome_policies_session_id_not_blank",
        ),
        sa.CheckConstraint(
            "horizon_closed_candles >= 1",
            name="ck_outcome_policies_horizon_positive",
        ),
        sa.CheckConstraint(
            "realized_return_threshold >= 0",
            name="ck_outcome_policies_threshold_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["sessions.session_id"],
            name="fk_outcome_policies_session_id_sessions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("policy_id"),
        sa.UniqueConstraint("session_id", name="uq_outcome_policies_session_id"),
    )


def downgrade() -> None:
    op.drop_table("outcome_evaluation_policies")
