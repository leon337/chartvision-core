from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String
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


class FrameRecord(Base):
    __tablename__ = "frames"
    __table_args__ = (
        CheckConstraint(
            "char_length(trim(frame_id)) > 0",
            name="ck_frames_frame_id_not_blank",
        ),
        CheckConstraint(
            "char_length(trim(session_id)) > 0",
            name="ck_frames_session_id_not_blank",
        ),
        CheckConstraint(
            "char_length(trim(image_hash)) > 0",
            name="ck_frames_image_hash_not_blank",
        ),
        CheckConstraint("width > 0", name="ck_frames_width_positive"),
        CheckConstraint("height > 0", name="ck_frames_height_positive"),
    )

    frame_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("sessions.session_id", ondelete="RESTRICT"),
        nullable=False,
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    image_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    changed_since_previous: Mapped[bool] = mapped_column(Boolean, nullable=False)
    storage_reference: Mapped[str | None] = mapped_column(String(1024), nullable=True)
