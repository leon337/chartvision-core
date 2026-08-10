from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SessionRecord(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint(
            "char_length(trim(session_id)) > 0",
            name="ck_sessions_session_id_not_blank",
        ),
        CheckConstraint(
            "char_length(trim(source_id)) > 0",
            name="ck_sessions_source_id_not_blank",
        ),
        CheckConstraint(
            "char_length(trim(asset)) > 0",
            name="ck_sessions_asset_not_blank",
        ),
        CheckConstraint(
            "char_length(trim(timeframe)) > 0",
            name="ck_sessions_timeframe_not_blank",
        ),
        CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at",
            name="ck_sessions_ended_at_not_before_started_at",
        ),
    )

    session_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    asset: Mapped[str] = mapped_column(String(128), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
