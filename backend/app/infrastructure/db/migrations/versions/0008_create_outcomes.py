"""create Phase 7 outcomes

Revision ID: 0008_create_outcomes
Revises: 0007_create_outcome_policies
"""

from alembic import op
import sqlalchemy as sa

revision = "0008_create_outcomes"
down_revision = "0007_create_outcome_policies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outcomes",
        sa.Column("analysis_id", sa.String(length=255), nullable=False),
        sa.Column("policy_id", sa.String(length=255), nullable=False),
        sa.Column("evaluation_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reference_candle_open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reference_candle_close_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reference_close", sa.Numeric(78, 38), nullable=False),
        sa.Column("final_candle_open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("final_candle_close_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("final_close", sa.Numeric(78, 38), nullable=False),
        sa.Column("horizon_closed_candles", sa.Integer(), nullable=False),
        sa.Column("realized_return_threshold", sa.Numeric(78, 38), nullable=False),
        sa.Column("realized_return", sa.Numeric(78, 38), nullable=False),
        sa.Column("realized_state", sa.String(length=32), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.CheckConstraint("horizon_closed_candles >= 1", name="ck_outcomes_horizon_positive"),
        sa.CheckConstraint(
            "realized_return_threshold >= 0",
            name="ck_outcomes_threshold_nonnegative",
        ),
        sa.CheckConstraint("reference_close <> 0", name="ck_outcomes_reference_close_nonzero"),
        sa.CheckConstraint(
            "final_candle_close_time > reference_candle_close_time",
            name="ck_outcomes_final_after_reference",
        ),
        sa.CheckConstraint(
            "realized_state IN ('UP', 'DOWN', 'SIDEWAYS')",
            name="ck_outcomes_realized_state",
        ),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["analyses.analysis_id"],
            name="fk_outcomes_analysis_id_analyses",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["policy_id"],
            ["outcome_evaluation_policies.policy_id"],
            name="fk_outcomes_policy_id_outcome_policies",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("analysis_id"),
    )


def downgrade() -> None:
    op.drop_table("outcomes")
