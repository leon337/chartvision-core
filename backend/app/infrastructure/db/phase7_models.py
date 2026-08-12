from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
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
