from datetime import datetime

from app.models.sql_models import (
    PersonalRecordDB,
    SleepDataDB,
    SummarizedActivityDB,
    User,
)


def test_user_model_has_expected_fields():
    user = User(email="test@example.com")

    assert user.email == "test@example.com"
    assert user.id is None
    assert "email" in User.model_fields
    assert "id" in User.model_fields


def test_summarized_activity_db_defaults_and_required_fields():
    activity = SummarizedActivityDB(
        user_id=1,
        activity_id=123456,
        activity_type="cycling",
        start_time_in_seconds=1715904000000,
        duration=3600,
        distance=10000,
        avg_moving_speed=5.0,
        max_moving_speed=12.0,
    )

    assert activity.user_id == 1
    assert activity.activity_type == "cycling"
    assert activity.distance == 10000
    assert activity.calories == 0
    assert isinstance(activity.created_at, datetime)
    assert isinstance(activity.updated_at, datetime)
    assert SummarizedActivityDB.__tablename__ == "summarized_activities"
    assert activity.id is None


def test_sleep_data_db_defaults_and_required_fields():
    sleep = SleepDataDB(
        user_id=1,
        calendar_date="2024-05-15",
        sleep_start_timestamp_gmt="2024-05-14T22:30:00.0Z",
        sleep_end_timestamp_gmt="2024-05-15T06:30:00.0Z",
        deep_sleep_seconds=7200,
        light_sleep_seconds=10800,
        rem_sleep_seconds=1800,
        awake_sleep_seconds=1800,
    )

    assert sleep.user_id == 1
    assert sleep.calendar_date == "2024-05-15"
    assert sleep.unmeasurable_seconds == 0
    assert sleep.avg_sleep_stress is None
    assert SleepDataDB.__tablename__ == "sleep_data"
    assert sleep.id is None


def test_personal_record_db_fields_and_metadata():
    record = PersonalRecordDB(
        user_id=1,
        personal_record_id=1,
        personal_record_type="fastest_5k_time",
        value=1500.0,
        record_unit="second",
        record_date="May 15, 2024",
    )

    assert record.user_id == 1
    assert record.personal_record_type == "fastest_5k_time"
    assert record.record_unit == "second"
    assert PersonalRecordDB.__tablename__ == "personal_records"
    assert record.id is None
