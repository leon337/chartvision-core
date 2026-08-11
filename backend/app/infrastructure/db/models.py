from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
)
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
        UniqueConstraint("frame_id", "session_id", name="uq_frames_frame_id_session_id"),
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


class ObservationRecord(Base):
    __tablename__ = "observations"
    __table_args__ = (
        CheckConstraint(
            "char_length(trim(observation_id)) > 0",
            name="ck_observations_observation_id_not_blank",
        ),
        CheckConstraint(
            "char_length(trim(session_id)) > 0",
            name="ck_observations_session_id_not_blank",
        ),
        CheckConstraint(
            "char_length(trim(frame_id)) > 0",
            name="ck_observations_frame_id_not_blank",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_observations_confidence_range",
        ),
        CheckConstraint(
            "visual_quality >= 0 AND visual_quality <= 1",
            name="ck_observations_visual_quality_range",
        ),
        ForeignKeyConstraint(
            ["session_id"],
            ["sessions.session_id"],
            name="fk_observations_session_id_sessions",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["frame_id", "session_id"],
            ["frames.frame_id", "frames.session_id"],
            name="fk_observations_frame_session_frames",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "observation_id",
            "session_id",
            name="uq_observations_observation_id_session_id",
        ),
    )

    observation_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    frame_id: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    visual_quality: Mapped[float] = mapped_column(Float, nullable=False)


class CandleRecord(Base):
    __tablename__ = "candles"
    __table_args__ = (
        CheckConstraint(
            "char_length(trim(session_id)) > 0",
            name="ck_candles_session_id_not_blank",
        ),
        CheckConstraint(
            "char_length(trim(source_id)) > 0",
            name="ck_candles_source_id_not_blank",
        ),
        CheckConstraint(
            "char_length(trim(asset)) > 0",
            name="ck_candles_asset_not_blank",
        ),
        CheckConstraint(
            "char_length(trim(timeframe)) > 0",
            name="ck_candles_timeframe_not_blank",
        ),
        CheckConstraint("close_time > open_time", name="ck_candles_time_order"),
        CheckConstraint("high >= open", name="ck_candles_high_ge_open"),
        CheckConstraint("high >= close", name="ck_candles_high_ge_close"),
        CheckConstraint("low <= open", name="ck_candles_low_le_open"),
        CheckConstraint("low <= close", name="ck_candles_low_le_close"),
        CheckConstraint("low <= high", name="ck_candles_low_le_high"),
        CheckConstraint(
            "vision_confidence IS NULL OR (vision_confidence >= 0 AND vision_confidence <= 1)",
            name="ck_candles_vision_confidence_range",
        ),
        CheckConstraint(
            "source_confidence IS NULL OR (source_confidence >= 0 AND source_confidence <= 1)",
            name="ck_candles_source_confidence_range",
        ),
        ForeignKeyConstraint(
            ["session_id"],
            ["sessions.session_id"],
            name="fk_candles_session_id_sessions",
            ondelete="RESTRICT",
        ),
        PrimaryKeyConstraint("session_id", "open_time"),
    )

    session_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    asset: Mapped[str] = mapped_column(String(128), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(32), nullable=False)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    vision_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)


class CandleSnapshotRecord(Base):
    __tablename__ = "candle_snapshots"
    __table_args__ = (
        CheckConstraint(
            "char_length(trim(observation_id)) > 0",
            name="ck_candle_snapshots_observation_id_not_blank",
        ),
        CheckConstraint(
            "char_length(trim(session_id)) > 0",
            name="ck_candle_snapshots_session_id_not_blank",
        ),
        CheckConstraint(
            "char_length(trim(source_id)) > 0",
            name="ck_candle_snapshots_source_id_not_blank",
        ),
        CheckConstraint(
            "char_length(trim(asset)) > 0",
            name="ck_candle_snapshots_asset_not_blank",
        ),
        CheckConstraint(
            "char_length(trim(timeframe)) > 0",
            name="ck_candle_snapshots_timeframe_not_blank",
        ),
        CheckConstraint(
            "close_time > open_time",
            name="ck_candle_snapshots_time_order",
        ),
        CheckConstraint("high >= open", name="ck_candle_snapshots_high_ge_open"),
        CheckConstraint("high >= close", name="ck_candle_snapshots_high_ge_close"),
        CheckConstraint("low <= open", name="ck_candle_snapshots_low_le_open"),
        CheckConstraint("low <= close", name="ck_candle_snapshots_low_le_close"),
        CheckConstraint("low <= high", name="ck_candle_snapshots_low_le_high"),
        CheckConstraint(
            "vision_confidence IS NULL OR (vision_confidence >= 0 AND vision_confidence <= 1)",
            name="ck_candle_snapshots_vision_confidence_range",
        ),
        CheckConstraint(
            "source_confidence IS NULL OR (source_confidence >= 0 AND source_confidence <= 1)",
            name="ck_candle_snapshots_source_confidence_range",
        ),
        ForeignKeyConstraint(
            ["observation_id", "session_id"],
            ["observations.observation_id", "observations.session_id"],
            name="fk_candle_snapshots_observation_session",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["session_id", "open_time"],
            ["candles.session_id", "candles.open_time"],
            name="fk_candle_snapshots_candle_identity",
            ondelete="RESTRICT",
        ),
        PrimaryKeyConstraint("observation_id", "session_id", "open_time"),
    )

    observation_id: Mapped[str] = mapped_column(String(255), nullable=False)
    session_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    asset: Mapped[str] = mapped_column(String(128), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(32), nullable=False)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    vision_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)


class AnalysisRecord(Base):
    __tablename__ = "analyses"
    __table_args__ = (
        CheckConstraint(
            "char_length(trim(analysis_id)) > 0",
            name="ck_analyses_analysis_id_not_blank",
        ),
        CheckConstraint(
            "char_length(trim(session_id)) > 0",
            name="ck_analyses_session_id_not_blank",
        ),
        CheckConstraint(
            "market_state IN ('UP', 'DOWN', 'SIDEWAYS', 'UNCERTAIN')",
            name="ck_analyses_market_state",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_analyses_confidence_range",
        ),
        CheckConstraint(
            "data_quality IS NULL OR (data_quality >= 0 AND data_quality <= 1)",
            name="ck_analyses_data_quality_range",
        ),
    )

    analysis_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("sessions.session_id", ondelete="RESTRICT"),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    market_state: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    data_quality: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence: Mapped[list[str]] = mapped_column(JSON, nullable=False)
