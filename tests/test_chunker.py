"""Tests for app/services/chunker.py"""

import json
import pytest
from pathlib import Path

from langchain_core.documents import Document

from app.services.chunker import (
    format_activity_as_text,
    format_sleep_as_text,
    format_record_as_text,
    build_metadata,
    chunk_garmin_data,
)

# ---------------------------------------------------------------------------
# Fixtures — minimal snake_case dicts matching normalized Garmin data
# ---------------------------------------------------------------------------

CYCLING_ACTIVITY = {
    "activity_id": 4667415185,
    "activity_type": "cycling",
    "user_profile_id": 74303376,
    "begin_timestamp": 1584405978000,
    "duration": 1944574.95,   # ms (~32 min)
    "distance": 791093.99,    # cm (~7.91 km)
    "avg_speed": 0.4068,      # dm/s (~14.65 km/h)
    "max_speed": 0.7035,      # dm/s (~25.3 km/h)
    "calories": 913.4,
    "elevation_gain": 781.4,
    "lap_count": 2,
    "pr": False,
    "location_name": "New Taipei City",
}

RUNNING_ACTIVITY = {
    "activity_id": 4650566228,
    "activity_type": "running",
    "user_profile_id": 74303376,
    "begin_timestamp": 1584091751000,
    "duration": 2405402.1,   # ms (~40 min)
    "distance": 801229.98,   # cm (~8.01 km)
    "avg_speed": 0.3331,     # dm/s (~5:00/km pace)
    "max_speed": 0.3686,
    "calories": 620.0,
    "elevation_gain": 120.0,
    "lap_count": 1,
    "pr": False,
}

SLEEP_RECORD = {
    "calendar_date": "2024-05-15",
    "sleep_start_timestamp_gmt": "2024-05-14T15:41:04.0",
    "sleep_end_timestamp_gmt": "2024-05-14T22:01:04.0",
    "deep_sleep_seconds": 6720,
    "light_sleep_seconds": 11460,
    "rem_sleep_seconds": 1920,
    "awake_sleep_seconds": 2700,
    "unmeasurable_seconds": 0,
    "spo2_sleep_summary": {
        "user_profile_pk": 74303376,
        "average_spo2": 97.0,
        "average_hr": 49.0,
        "lowest_spo2": 93,
    },
    "sleep_scores": {
        "overall_score": 64,
        "quality_score": 74,
    },
}

PERSONAL_RECORD = {
    "personal_record_id": 1369841692,
    "activity_id": 0,
    "value": 13.0,
    "pr_start_time_gmt": "Sat Apr 11 16:00:00 GMT 2026",
    "personal_record_type": "Current Goal Streak",
    "current": True,
    "confirmed": True,
}

HISTORICAL_RECORD = {
    "personal_record_id": 1369841700,
    "activity_id": 4650566228,
    "value": 42.195,
    "pr_start_time_gmt": "May 15, 2024",
    "personal_record_type": "Best Marathon",
    "current": False,
    "confirmed": True,
}


# ---------------------------------------------------------------------------
# Activity formatting tests
# ---------------------------------------------------------------------------

def test_format_activity_cycling_shows_speed_kmh():
    text = format_activity_as_text(CYCLING_ACTIVITY)
    assert "km/h" in text
    # Should NOT show pace format for cycling
    assert "/km" not in text.replace("km/h", "")


def test_format_activity_running_shows_pace():
    text = format_activity_as_text(RUNNING_ACTIVITY)
    # Should show pace in min:ss/km format, not km/h
    assert "/km" in text
    assert "km/h" not in text


def test_format_activity_uses_natural_prose():
    text = format_activity_as_text(CYCLING_ACTIVITY)
    # Natural prose: starts with "You" and contains full sentences
    assert text.startswith("You completed")
    assert "covering" in text
    # No pipe-delimited metric format
    assert " | " not in text


def test_format_activity_contains_key_fields():
    text = format_activity_as_text(CYCLING_ACTIVITY)
    # Distance (7.91 km from 791093.99 cm / 100000)
    assert "7.91 km" in text
    # Calories
    assert "913" in text
    # Duration (~32 min)
    assert "32" in text


def test_format_activity_handles_none_speed():
    activity = {**CYCLING_ACTIVITY, "avg_speed": None, "max_speed": None}
    text = format_activity_as_text(activity)
    assert "You completed" in text
    assert "km/h" not in text


def test_format_activity_handles_pr_flag():
    activity = {**CYCLING_ACTIVITY, "pr": True}
    text = format_activity_as_text(activity)
    assert "personal record" in text.lower()


# ---------------------------------------------------------------------------
# Sleep formatting tests
# ---------------------------------------------------------------------------

def test_format_sleep_normal():
    text = format_sleep_as_text(SLEEP_RECORD)
    assert "2024-05-15" in text
    # Should contain sleep stage percentages
    assert "%" in text
    assert "deep sleep" in text
    assert "REM" in text


def test_format_sleep_uses_natural_prose():
    text = format_sleep_as_text(SLEEP_RECORD)
    assert text.startswith("On the night of")
    assert "you slept for" in text
    assert " | " not in text


def test_format_sleep_contains_hr_and_spo2():
    text = format_sleep_as_text(SLEEP_RECORD)
    assert "49" in text   # avg HR
    assert "97" in text   # avg SpO2


def test_format_sleep_contains_score():
    text = format_sleep_as_text(SLEEP_RECORD)
    assert "64" in text   # overall_score


def test_format_sleep_zero_total_seconds():
    record = {**SLEEP_RECORD, "deep_sleep_seconds": 0, "light_sleep_seconds": 0,
              "rem_sleep_seconds": 0, "awake_sleep_seconds": 0}
    # Must not raise ZeroDivisionError
    text = format_sleep_as_text(record)
    assert "unavailable" in text.lower()


def test_format_sleep_none_total_seconds():
    record = {**SLEEP_RECORD, "deep_sleep_seconds": None, "light_sleep_seconds": None,
              "rem_sleep_seconds": None, "awake_sleep_seconds": None}
    # Must not raise TypeError or ZeroDivisionError
    text = format_sleep_as_text(record)
    assert "unavailable" in text.lower()


# ---------------------------------------------------------------------------
# Personal record formatting tests
# ---------------------------------------------------------------------------

def test_format_record_text_contains_record_type():
    text = format_record_as_text(PERSONAL_RECORD)
    assert "Current Goal Streak" in text


def test_format_record_uses_natural_prose():
    text = format_record_as_text(PERSONAL_RECORD)
    assert text.startswith("You set a personal record")
    assert " | " not in text


def test_format_record_current_flag():
    current_text = format_record_as_text(PERSONAL_RECORD)
    historical_text = format_record_as_text(HISTORICAL_RECORD)
    assert "current all-time best" in current_text
    assert "previous personal record" in historical_text


# ---------------------------------------------------------------------------
# Metadata tests
# ---------------------------------------------------------------------------

def test_build_metadata_activity_data_type():
    meta = build_metadata("activity", CYCLING_ACTIVITY, user_id="test_user")
    assert meta["data_type"] == "activity"
    assert meta["activity_type"] == "cycling"
    assert meta["record_id"] == 4667415185
    assert meta["is_current_pr"] is None
    assert meta["user_id"] == "test_user"


def test_build_metadata_activity_has_date():
    meta = build_metadata("activity", CYCLING_ACTIVITY, user_id="test_user")
    assert meta["date"] is not None
    # Should be ISO date format YYYY-MM-DD
    assert len(meta["date"]) == 10
    assert meta["date"].count("-") == 2


def test_build_metadata_personal_record_has_is_current_pr():
    meta_current = build_metadata("personal_record", PERSONAL_RECORD, user_id="test_user")
    meta_historical = build_metadata("personal_record", HISTORICAL_RECORD, user_id="test_user")
    assert meta_current["is_current_pr"] is True
    assert meta_historical["is_current_pr"] is False


def test_build_metadata_activity_is_current_pr_is_none():
    meta = build_metadata("activity", CYCLING_ACTIVITY, user_id="test_user")
    assert meta["is_current_pr"] is None


def test_build_metadata_sleep_data_type():
    meta = build_metadata("sleep", SLEEP_RECORD, user_id="test_user")
    assert meta["data_type"] == "sleep"
    assert meta["activity_type"] is None
    assert meta["is_current_pr"] is None


# ---------------------------------------------------------------------------
# Integration test with real sample data
# ---------------------------------------------------------------------------

SAMPLES_DIR = Path(__file__).parent.parent / "data" / "samples"


@pytest.mark.skipif(
    not (SAMPLES_DIR / "summarizedActivities.json").exists(),
    reason="Real sample data not available",
)
def test_chunk_garmin_data_with_real_samples():
    from app.services.parser import normalize_json_keys

    with open(SAMPLES_DIR / "summarizedActivities.json") as f:
        activities_raw = normalize_json_keys(json.load(f))
    with open(SAMPLES_DIR / "sleepData.json") as f:
        sleep_raw = normalize_json_keys(json.load(f))
    with open(SAMPLES_DIR / "personalRecord.json") as f:
        records_raw = normalize_json_keys(json.load(f))

    parsed = {
        "summarizedActivities": activities_raw,
        "sleepData": sleep_raw,
        "personalRecords": records_raw,
    }

    docs = chunk_garmin_data(parsed, user_id="test_user")

    assert len(docs) > 0
    for doc in docs:
        assert isinstance(doc, Document)
        assert len(doc.page_content) > 20
        assert "data_type" in doc.metadata
        assert doc.metadata["data_type"] in ("activity", "sleep", "personal_record")
        assert "source" in doc.metadata
        assert doc.metadata["source"] == "garmin_zip"

    # Check we got all three types
    types = {doc.metadata["data_type"] for doc in docs}
    assert "activity" in types
    assert "sleep" in types
    assert "personal_record" in types
