"""SQLModel database models for Garmin Garmin RAG Task 3.

This module contains the SQLModel schema definitions that map Garmin data
into relational tables suitable for PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, Index, SQLModel


class User(SQLModel, table=True):
    """Minimal user table used for foreign key relationships."""

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(default="", index=True)


class SummarizedActivityDB(SQLModel, table=True):
    """SQLModel for Garmin summarized activity records."""

    __tablename__ = "summarized_activities"
    __table_args__ = (
        Index("idx_activity_user_start", "user_id", "start_time_in_seconds"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    activity_id: int = Field(..., description="Garmin activity identifier", ge=1)
    activity_type: str = Field(..., description="Activity type key", min_length=1)
    start_time_in_seconds: int = Field(
        ..., description="Start time in milliseconds (Unix epoch)", ge=0, index=True
    )
    duration: int = Field(..., description="Duration in seconds", gt=0)
    distance: int = Field(..., description="Distance in meters", ge=0)
    elevation_gain: Optional[int] = Field(default=None, description="Elevation gain in meters", ge=0)
    avg_moving_speed: float = Field(..., description="Average moving speed in m/s", ge=0.0)
    max_moving_speed: float = Field(..., description="Maximum moving speed in m/s", ge=0.0)
    calories: int = Field(default=0, description="Calories burned", ge=0)
    sport_type: Optional[str] = Field(default=None, description="Sport type")
    avg_heart_rate: Optional[int] = Field(default=None, description="Average heart rate", ge=0)
    max_heart_rate: Optional[int] = Field(default=None, description="Maximum heart rate", ge=0)
    steps: Optional[int] = Field(default=None, description="Step count", ge=0)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SleepDataDB(SQLModel, table=True):
    """SQLModel for Garmin sleep records."""

    __tablename__ = "sleep_data"
    __table_args__ = (
        Index("idx_sleep_user_date", "user_id", "calendar_date"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    calendar_date: str = Field(..., description="Calendar date in YYYY-MM-DD format", min_length=10)
    sleep_start_timestamp_gmt: str = Field(..., description="Sleep start timestamp in ISO 8601 format")
    sleep_end_timestamp_gmt: str = Field(..., description="Sleep end timestamp in ISO 8601 format")
    deep_sleep_seconds: int = Field(..., description="Deep sleep seconds", ge=0)
    light_sleep_seconds: int = Field(..., description="Light sleep seconds", ge=0)
    rem_sleep_seconds: int = Field(..., description="REM sleep seconds", ge=0)
    awake_sleep_seconds: int = Field(..., description="Awake sleep seconds", ge=0)
    unmeasurable_seconds: int = Field(default=0, description="Unmeasurable sleep seconds", ge=0)
    average_heart_rate: Optional[float] = Field(default=None, description="Average heart rate during sleep", ge=0.0)
    max_heart_rate: Optional[float] = Field(default=None, description="Maximum heart rate during sleep", ge=0.0)
    min_heart_rate: Optional[float] = Field(default=None, description="Minimum heart rate during sleep", ge=0.0)
    average_respiration: Optional[float] = Field(default=None, description="Average respiration rate during sleep", ge=0.0)
    highest_respiration: Optional[float] = Field(default=None, description="Highest respiration rate during sleep", ge=0.0)
    lowest_respiration: Optional[float] = Field(default=None, description="Lowest respiration rate during sleep", ge=0.0)
    average_spo2: Optional[float] = Field(default=None, description="Average SpO2", ge=0.0, le=100.0)
    lowest_spo2: Optional[float] = Field(default=None, description="Lowest SpO2", ge=0.0, le=100.0)
    sleep_window_confirmation_type: Optional[str] = Field(default=None, description="Sleep window confirmation type")
    retro: Optional[bool] = Field(default=False, description="Retro sleep record flag")
    awake_count: Optional[int] = Field(default=0, description="Number of awakenings during sleep", ge=0)
    avg_sleep_stress: Optional[float] = Field(default=None, description="Average sleep stress", ge=0.0, le=100.0)
    overall_sleep_score: Optional[int] = Field(default=None, description="Overall sleep score", ge=0, le=100)
    sleep_quality_score: Optional[int] = Field(default=None, description="Sleep quality score", ge=0, le=100)
    sleep_recovery_score: Optional[int] = Field(default=None, description="Sleep recovery score", ge=0, le=100)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PersonalRecordDB(SQLModel, table=True):
    """SQLModel for Garmin personal record entries."""

    __tablename__ = "personal_records"
    __table_args__ = (
        Index("idx_personal_record_user_type", "user_id", "personal_record_type"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    personal_record_id: int = Field(..., description="Garmin personal record identifier", ge=1)
    personal_record_type: str = Field(..., description="Personal record type", min_length=1)
    value: float = Field(..., description="Record value", gt=0.0)
    record_unit: str = Field(..., description="Record unit (meter, second, etc.)", min_length=1)
    record_date: str = Field(..., description="Date record was achieved", min_length=1)
    create_date: Optional[str] = Field(default=None, description="Record creation timestamp")
    linked_activity_id: Optional[int] = Field(default=None, description="Linked activity ID", ge=0)
    activity_type: Optional[str] = Field(default=None, description="Related activity type")
    display_order: Optional[int] = Field(default=None, description="Display order", ge=0)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
