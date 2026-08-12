from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.models import Base


class OutcomeEvaluationPolicyRecord(Base):
    __tablename__ = "outcome_evaluation_policies"
    __table_args__ = (
        CheckConstraint(
            "char_length(trim(policy_id)) > 0",
            name="ck_outcome_policies_policy_id_not_blank",
        ),
        CheckConstraint(
            "char_length(trim(session_id)) > 0",
            name="ck_outcome_policies_session_id_not_blank",
        ),
        CheckConstraint(
            "horizon_closed_candles >= 1",
            name="ck_outcome_policies_horizon_positive",
        ),
        CheckConstraint(
            "realized_return_threshold >= 0",
            name="ck_outcome_policies_threshold_nonnegative",
        ),
        UniqueConstraint("session_id", name="uq_outcome_policies_session_id"),
    )

    policy_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("sessions.session_id", ondelete="RESTRICT"),
        nullable=False,
    )
    horizon_closed_candles: Mapped[int] = mapped_column(Integer, nullable=False)
    realized_return_threshold: Mapped[Decimal] = mapped_column(Numeric(78, 38), nullable=False)
    bound_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OutcomeRecord(Base):
    __tablename__ = "outcomes"
    __table_args__ = (
        CheckConstraint("horizon_closed_candles >= 1", name="ck_outcomes_horizon_positive"),
        CheckConstraint(
            "realized_return_threshold >= 0",
            name="ck_outcomes_threshold_nonnegative",
        ),
        CheckConstraint("reference_close <> 0", name="ck_outcomes_reference_close_nonzero"),
        CheckConstraint(
            "final_candle_close_time > reference_candle_close_time",
            name="ck_outcomes_final_after_reference",
        ),
        CheckConstraint(
            "realized_state IN ('UP', 'DOWN', 'SIDEWAYS')",
            name="ck_outcomes_realized_state",
        ),
    )

    analysis_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("analyses.analysis_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    policy_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("outcome_evaluation_policies.policy_id", ondelete="RESTRICT"),
        nullable=False,
    )
    evaluation_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reference_candle_open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reference_candle_close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reference_close: Mapped[Decimal] = mapped_column(Numeric(78, 38), nullable=False)
    final_candle_open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    final_candle_close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    final_close: Mapped[Decimal] = mapped_column(Numeric(78, 38), nullable=False)
    horizon_closed_candles: Mapped[int] = mapped_column(Integer, nullable=False)
    realized_return_threshold: Mapped[Decimal] = mapped_column(Numeric(78, 38), nullable=False)
    realized_return: Mapped[Decimal] = mapped_column(Numeric(78, 38), nullable=False)
    realized_state: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence: Mapped[list[str]] = mapped_column(JSON, nullable=False)
