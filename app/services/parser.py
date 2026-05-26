"""Garmin JSON 過濾與解析服務

本模組負責：
1. ZIP 檔案解壓與核心 Garmin JSON 提取
2. JSON 資料驗證與正規化
3. 將 Garmin camelCase 欄位轉為 snake_case 供內部模型使用

目前實作重點：Task 4 - ZIP 解析與資料正規化
"""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from datetime import datetime, timezone


CORE_JSON_SUFFIXES: Dict[str, str] = {
    "summarizedActivities": "summarizedActivities.json",
    "sleepData": "sleepData.json",
    "personalRecords": "personalRecord.json",
}

DEFAULT_GARMIN_TARGETS: List[str] = list(CORE_JSON_SUFFIXES.keys())


def camel_to_snake(value: str) -> str:
    """Convert camelCase / PascalCase keys to snake_case."""
    if not isinstance(value, str):
        return value
    value = value.replace("-", "_").replace(" ", "_")
    value = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return value.lower()


def normalize_json_keys(value: Any) -> Any:
    """Recursively normalize dictionary keys from camelCase to snake_case."""
    if isinstance(value, dict):
        return {camel_to_snake(k): normalize_json_keys(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize_json_keys(item) for item in value]
    return value


def _match_core_key(file_name: str, target_keys: Iterable[str]) -> Optional[str]:
    normalized_file_name = file_name.replace("\\", "/").lower()
    for key in target_keys:
        suffix = CORE_JSON_SUFFIXES.get(key, "").lower()
        if suffix and normalized_file_name.endswith(suffix):
            return key
    return None


def parse_garmin_zip(
    zip_path: str,
    target_jsons: Optional[List[str]] = None,
) -> Dict[str, List[Any]]:
    """Parse Garmin ZIP and extract core Garmin JSON files.

    Merges ALL files matching each target type into a single list, so that
    split exports (e.g. 5 summarizedActivities files, 25 sleepData files)
    are fully ingested rather than truncated to the first file found.

    Args:
        zip_path: Path to the Garmin ZIP archive.
        target_jsons: Optional list of target keys to extract.
            Defaults to the 3 core Garmin JSON files.

    Returns:
        A dict keyed by Garmin target name with normalized JSON content.

    Raises:
        FileNotFoundError: if the ZIP archive does not exist.
        zipfile.BadZipFile: if the archive is invalid or corrupted.
        KeyError: if one of the required target JSON files is missing.
        json.JSONDecodeError: if an extracted file is not valid JSON.
    """
    path = Path(zip_path)
    if not path.exists():
        raise FileNotFoundError(f"ZIP not found: {zip_path}")

    if target_jsons is None:
        target_jsons = DEFAULT_GARMIN_TARGETS

    selected_targets = [key for key in target_jsons if key in CORE_JSON_SUFFIXES]
    if not selected_targets:
        raise ValueError("No valid target_jsons provided")

    extracted: Dict[str, List[Any]] = {}

    with zipfile.ZipFile(path, "r") as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue

            core_key = _match_core_key(member.filename, selected_targets)
            if core_key is None:
                continue

            with archive.open(member, "r") as file_obj:
                payload = normalize_json_keys(json.loads(file_obj.read().decode("utf-8")))

            if core_key not in extracted:
                extracted[core_key] = []

            # Merge: if the file contains a list, extend; otherwise append
            if isinstance(payload, list):
                extracted[core_key].extend(payload)
            else:
                extracted[core_key].append(payload)

    missing = [key for key in selected_targets if key not in extracted]
    if missing:
        raise KeyError(f"Missing Garmin JSON files in ZIP: {missing}")

    return extracted


def get_garmin_json_names(zip_path: str) -> List[str]:
    """Return the list of recognized Garmin core JSON files found in the ZIP."""
    path = Path(zip_path)
    if not path.exists():
        raise FileNotFoundError(f"ZIP not found: {zip_path}")

    found: List[str] = []
    with zipfile.ZipFile(path, "r") as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            core_key = _match_core_key(member.filename, CORE_JSON_SUFFIXES.keys())
            if core_key and core_key not in found:
                found.append(core_key)
    return found


# --- Task 5: Timestamp Normalization ---
def normalize_timestamp(timestamp_value: Any) -> Optional[datetime]:
    """
    Normalize various Garmin timestamp formats to a standard UTC datetime object.

    Handles:
    1. Unix milliseconds (int or str) -> datetime
    2. ISO 8601 strings (e.g., "2024-05-14T15:41:04.0Z", "2024-05-14T22:30:00.0") -> datetime
    3. Text date strings (e.g., "May 15, 2024", "Sat Apr 11 16:00:00 GMT 2026") -> datetime

    Args:
        timestamp_value: The raw timestamp value from Garmin data.

    Returns:
        A datetime object in UTC, or None if parsing fails.
    """
    if timestamp_value is None:
        return None

    # 1. Handle Unix milliseconds (Activities)
    if isinstance(timestamp_value, (int, float)):
        try:
            # Assume milliseconds
            return datetime.fromtimestamp(timestamp_value / 1000, tz=timezone.utc)
        except (ValueError, TypeError):
            pass  # Try other formats

    if isinstance(timestamp_value, str):
        # 2. Handle ISO 8601 strings (Sleep)
        try:
            # Handle ISO format with potential '.0' at the end
            if timestamp_value.endswith('.0'):
                # Convert to "2024-05-14T15:41:04" for fromisoformat
                iso_str = timestamp_value[:-2]
            else:
                iso_str = timestamp_value
            
            # Handle 'Z' for UTC explicitly
            if iso_str.endswith('Z'):
                return datetime.fromisoformat(iso_str[:-1] + '+00:00')
            else:
                # Assume UTC if no timezone info, then explicitly set it
                return datetime.fromisoformat(iso_str).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            pass # Try other formats

        # 3. Handle Text date strings (Personal Records)
        text_date_formats = [
            '%B %d, %Y',  # "May 15, 2024"
            '%Y-%m-%d',   # "2024-05-15"
            '%a %b %d %H:%M:%S %Z %Y', # "Sat Apr 11 16:00:00 GMT 2026"
            '%m/%d/%Y',   # "05/15/2024"
            '%d-%b-%Y',   # "15-May-2024"
        ]
        for fmt in text_date_formats:
            try:
                # For text dates, assume local timezone for simplicity if no timezone specified
                # Then convert to UTC
                dt = datetime.strptime(timestamp_value, fmt)
                # If the parsed datetime object doesn't have timezone information, assume UTC.
                # If the string specified a timezone, it would be handled by fromisoformat for ISO8601.
                # For strptime, a specified timezone like 'GMT' is parsed into a tzinfo object.
                # However, if it's just 'GMT 2026', strptime usually doesn't create a tzinfo object.
                # So we explicitly set tzinfo=timezone.utc here to ensure UTC consistency.
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

    return None


# --- Task 6: Unit Conversion ---
def convert_distance_meters_to_km(distance_m: Optional[float]) -> Optional[float]:
    """
    Convert distance from meters to kilometers.

    Args:
        distance_m: Distance in meters.

    Returns:
        Distance in kilometers, or None if input is None.
    """
    if distance_m is None:
        return None
    try:
        return float(distance_m) / 1000.0
    except (ValueError, TypeError):
        return None


def convert_speed_ms_to_kmh(speed_ms: Optional[float]) -> Optional[float]:
    """
    Convert speed from meters per second to kilometers per hour.

    Args:
        speed_ms: Speed in meters per second (m/s).

    Returns:
        Speed in kilometers per hour (km/h), or None if input is None.
    """
    if speed_ms is None:
        return None
    try:
        return float(speed_ms) * 3.6  # 1 m/s = 3.6 km/h
    except (ValueError, TypeError):
        return None


def convert_distance_km_to_meters(distance_km: Optional[float]) -> Optional[float]:
    """
    Convert distance from kilometers to meters.

    Args:
        distance_km: Distance in kilometers.

    Returns:
        Distance in meters, or None if input is None.
    """
    if distance_km is None:
        return None
    try:
        return float(distance_km) * 1000.0
    except (ValueError, TypeError):
        return None


def convert_speed_kmh_to_ms(speed_kmh: Optional[float]) -> Optional[float]:
    """
    Convert speed from kilometers per hour to meters per second.

    Args:
        speed_kmh: Speed in kilometers per hour (km/h).

    Returns:
        Speed in meters per second (m/s), or None if input is None.
    """
    if speed_kmh is None:
        return None
    try:
        return float(speed_kmh) / 3.6  # 1 km/h = 0.2778 m/s
    except (ValueError, TypeError):
        return None


def convert_elevation_feet_to_meters(elevation_ft: Optional[float]) -> Optional[float]:
    """
    Convert elevation from feet to meters.

    Args:
        elevation_ft: Elevation in feet.

    Returns:
        Elevation in meters, or None if input is None.
    """
    if elevation_ft is None:
        return None
    try:
        return float(elevation_ft) * 0.3048  # 1 foot = 0.3048 meters
    except (ValueError, TypeError):
        return None


def convert_elevation_meters_to_feet(elevation_m: Optional[float]) -> Optional[float]:
    """
    Convert elevation from meters to feet.

    Args:
        elevation_m: Elevation in meters.

    Returns:
        Elevation in feet, or None if input is None.
    """
    if elevation_m is None:
        return None
    try:
        return float(elevation_m) / 0.3048  # 1 meter = 3.28084 feet
    except (ValueError, TypeError):
        return None
