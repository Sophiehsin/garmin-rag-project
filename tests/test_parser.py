import json
import zipfile
from pathlib import Path
from datetime import datetime
import pytest
import zoneinfo

from app.services.parser import (
    DEFAULT_GARMIN_TARGETS,
    get_garmin_json_names,
    normalize_json_keys,
    parse_garmin_zip,
    normalize_timestamp,
    convert_distance_meters_to_km,
    convert_speed_ms_to_kmh,
    convert_distance_km_to_meters,
    convert_speed_kmh_to_ms,
    convert_elevation_feet_to_meters,
    convert_elevation_meters_to_feet,
)
from datetime import datetime, timezone

def test_normalize_json_keys_converts_camel_case():
    sample = {
        "activityId": 123,
        "activityType": "cycling",
        "nestedData": {
            "startTimeInSeconds": 1600000000000,
            "heartRate": 150,
        },
        "lapMetrics": [
            {"lapTimeSeconds": 60},
            {"lapTimeSeconds": 65},
        ],
    }

    normalized = normalize_json_keys(sample)

    assert normalized["activity_id"] == 123
    assert normalized["activity_type"] == "cycling"
    assert normalized["nested_data"]["start_time_in_seconds"] == 1600000000000
    assert normalized["nested_data"]["heart_rate"] == 150
    assert normalized["lap_metrics"][0]["lap_time_seconds"] == 60


def test_parse_garmin_zip_extracts_three_core_files(tmp_path: Path):
    archive_path = tmp_path / "garmin_export.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "DI_CONNECT/DI-Connect-Fitness/a850132a@gmail.com_4004_summarizedActivities.json",
            json.dumps({"activityId": 123, "distance": 10000}),
        )
        archive.writestr(
            "DI_CONNECT/DI-Connect-Wellness/2024-05-15_2024-08-23_74303376_sleepData.json",
            json.dumps({"calendarDate": "2024-05-15", "deepSleepSeconds": 7200}),
        )
        archive.writestr(
            "DI_CONNECT/DI-Connect-Fitness/a850132a@gmail.com_personalRecord.json",
            json.dumps({"personalRecordId": 1, "value": 1500.0}),
        )
        archive.writestr("README.txt", "This is not a Garmin JSON file")

    result = parse_garmin_zip(str(archive_path))

    assert set(result.keys()) == set(DEFAULT_GARMIN_TARGETS)
    assert result["summarizedActivities"]["activity_id"] == 123
    assert result["sleepData"]["calendar_date"] == "2024-05-15"
    assert result["personalRecords"]["personal_record_id"] == 1


def test_get_garmin_json_names_finds_core_files(tmp_path: Path):
    archive_path = tmp_path / "garmin_export.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("DI_CONNECT/test/sleepData.json", json.dumps({"calendarDate": "2024-05-15"}))
        archive.writestr("DI_CONNECT/test/randomFile.json", json.dumps({"foo": "bar"}))

    names = get_garmin_json_names(str(archive_path))
    assert names == ["sleepData"]


def test_parse_garmin_zip_raises_when_missing_core_file(tmp_path: Path):
    archive_path = tmp_path / "partial_export.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "DI_CONNECT/DI-Connect-Fitness/a850132a@gmail.com_4004_summarizedActivities.json",
            json.dumps({"activityId": 123}),
        )

    with pytest.raises(KeyError) as exc_info:
        parse_garmin_zip(str(archive_path))

    assert "Missing Garmin JSON files" in str(exc_info.value)


def test_normalize_timestamp_unix_milliseconds():
    timestamp = 1715904000000  # May 17, 2024 00:00:00 GMT
    normalized = normalize_timestamp(timestamp)
    assert normalized == datetime(2024, 5, 17, 0, 0, 0, tzinfo=timezone.utc)


def test_normalize_timestamp_iso_8601_z():
    timestamp = "2024-05-14T15:41:04.0Z"
    normalized = normalize_timestamp(timestamp)
    assert normalized == datetime(2024, 5, 14, 15, 41, 4, tzinfo=timezone.utc)


def test_normalize_timestamp_iso_8601_no_z():
    timestamp = "2024-05-14T15:41:04.0"
    normalized = normalize_timestamp(timestamp)
    assert normalized == datetime(2024, 5, 14, 15, 41, 4, tzinfo=timezone.utc)


def test_normalize_timestamp_text_date_month_day_year():
    timestamp = "May 15, 2024"
    normalized = normalize_timestamp(timestamp)
    assert normalized == datetime(2024, 5, 15, 0, 0, 0, tzinfo=timezone.utc)


def test_normalize_timestamp_text_date_day_month_year():
    timestamp = "15-May-2024"
    normalized = normalize_timestamp(timestamp)
    assert normalized == datetime(2024, 5, 15, 0, 0, 0, tzinfo=timezone.utc)


def test_normalize_timestamp_text_date_full_gmt():
    # Note: strptime for %Z does not handle 'GMT' directly as a timezone object unless explicitly defined.
    # We assume UTC for these text formats.
    timestamp = "Sat Apr 11 16:00:00 GMT 2026"
    normalized = normalize_timestamp(timestamp)
    assert normalized == datetime(2026, 4, 11, 16, 0, 0, tzinfo=timezone.utc)


def test_normalize_timestamp_invalid_format():
    timestamp = "invalid-date-format"
    normalized = normalize_timestamp(timestamp)
    assert normalized is None


def test_normalize_timestamp_none_input():
    timestamp = None
    normalized = normalize_timestamp(timestamp)
    assert normalized is None


# --- Task 6: Unit Conversion Tests ---
def test_convert_distance_meters_to_km():
    assert convert_distance_meters_to_km(1000) == 1.0
    assert convert_distance_meters_to_km(5000) == 5.0
    assert convert_distance_meters_to_km(0) == 0.0
    assert convert_distance_meters_to_km(1500) == 1.5
    assert convert_distance_meters_to_km(None) is None
    assert convert_distance_meters_to_km("invalid") is None


def test_convert_speed_ms_to_kmh():
    assert convert_speed_ms_to_kmh(1) == 3.6
    assert convert_speed_ms_to_kmh(5) == 18.0
    assert convert_speed_ms_to_kmh(10) == 36.0
    assert convert_speed_ms_to_kmh(0) == 0.0
    assert convert_speed_ms_to_kmh(None) is None
    assert convert_speed_ms_to_kmh("invalid") is None


def test_convert_distance_km_to_meters():
    assert convert_distance_km_to_meters(1) == 1000.0
    assert convert_distance_km_to_meters(5) == 5000.0
    assert convert_distance_km_to_meters(1.5) == 1500.0
    assert convert_distance_km_to_meters(0) == 0.0
    assert convert_distance_km_to_meters(None) is None
    assert convert_distance_km_to_meters("invalid") is None


def test_convert_speed_kmh_to_ms():
    assert convert_speed_kmh_to_ms(3.6) == 1.0
    assert convert_speed_kmh_to_ms(18) == 5.0
    assert convert_speed_kmh_to_ms(36) == 10.0
    assert convert_speed_kmh_to_ms(0) == 0.0
    assert convert_speed_kmh_to_ms(None) is None
    assert convert_speed_kmh_to_ms("invalid") is None


def test_convert_elevation_feet_to_meters():
    # 1 foot = 0.3048 meters
    assert abs(convert_elevation_feet_to_meters(1) - 0.3048) < 1e-4
    assert abs(convert_elevation_feet_to_meters(100) - 30.48) < 1e-4
    assert abs(convert_elevation_feet_to_meters(1000) - 304.8) < 1e-4
    assert convert_elevation_feet_to_meters(0) == 0.0
    assert convert_elevation_feet_to_meters(None) is None
    assert convert_elevation_feet_to_meters("invalid") is None


def test_convert_elevation_meters_to_feet():
    # 1 meter = 3.28084 feet
    assert abs(convert_elevation_meters_to_feet(1) - 3.28084) < 1e-4
    assert abs(convert_elevation_meters_to_feet(100) - 328.084) < 1e-4
    assert abs(convert_elevation_meters_to_feet(304.8) - 1000) < 1e-4
    assert convert_elevation_meters_to_feet(0) == 0.0
    assert convert_elevation_meters_to_feet(None) is None
    assert convert_elevation_meters_to_feet("invalid") is None


def test_unit_conversion_round_trip():
    """Test that converting back and forth returns approximately the original value."""
    # Distance round trip
    original_meters = 5000
    converted_km = convert_distance_meters_to_km(original_meters)
    back_to_meters = convert_distance_km_to_meters(converted_km)
    assert abs(back_to_meters - original_meters) < 1e-10

    # Speed round trip
    original_ms = 10
    converted_kmh = convert_speed_ms_to_kmh(original_ms)
    back_to_ms = convert_speed_kmh_to_ms(converted_kmh)
    assert abs(back_to_ms - original_ms) < 1e-10

    # Elevation round trip
    original_feet = 1000
    converted_meters = convert_elevation_feet_to_meters(original_feet)
    back_to_feet = convert_elevation_meters_to_feet(converted_meters)
    assert abs(back_to_feet - original_feet) < 1e-10
