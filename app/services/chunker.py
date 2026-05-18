"""Garmin data chunker — converts parsed Garmin records into LangChain Documents.

Raw Garmin unit notes (from data/samples analysis):
  - distance: stored in centimeters (cm); divide by 100_000 to get km
  - avg_speed / max_speed: stored in dm/s; multiply by 36 to get km/h, ×10 for m/s
  - duration: stored in milliseconds; divide by 1000 for seconds
  - timestamps (begin_timestamp, start_time_gmt): Unix milliseconds
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from langchain_core.documents import Document

from app.services.parser import normalize_timestamp


# ---------------------------------------------------------------------------
# Internal unit helpers (work with raw Garmin cm / dm/s / ms values)
# ---------------------------------------------------------------------------

def _cm_to_km(cm: Optional[float]) -> Optional[float]:
    if cm is None:
        return None
    try:
        return float(cm) / 100_000.0
    except (TypeError, ValueError):
        return None


def _dms_to_kmh(dms: Optional[float]) -> Optional[float]:
    """dm/s → km/h"""
    if dms is None:
        return None
    try:
        return float(dms) * 36.0
    except (TypeError, ValueError):
        return None


def _dms_to_ms(dms: Optional[float]) -> Optional[float]:
    """dm/s → m/s"""
    if dms is None:
        return None
    try:
        return float(dms) * 10.0
    except (TypeError, ValueError):
        return None


def _ms_to_hms(ms: Optional[float]) -> str:
    """Milliseconds → human-readable duration string."""
    if not ms:
        return "unknown duration"
    try:
        total_sec = int(float(ms) / 1000)
        hours, remainder = divmod(total_sec, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours}h {minutes}min {seconds}sec"
        return f"{minutes}min {seconds}sec"
    except (TypeError, ValueError):
        return "unknown duration"


def _pace_str(raw_speed_dms: Optional[float]) -> Optional[str]:
    """dm/s → 'mm:ss/km' running pace string."""
    if not raw_speed_dms:
        return None
    try:
        pace_sec = 100.0 / float(raw_speed_dms)  # sec/km (raw units: 100 / dms = s/km)
        mins = int(pace_sec // 60)
        secs = int(pace_sec % 60)
        return f"{mins}:{secs:02d}/km"
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _timestamp_to_date(ts: Any) -> str:
    """Return 'YYYY-MM-DD' from any Garmin timestamp value, or 'unknown date'."""
    dt = normalize_timestamp(ts)
    if dt is None:
        return "unknown date"
    return dt.strftime("%B %-d, %Y")


def _timestamp_to_iso_date(ts: Any) -> Optional[str]:
    """Return ISO date string 'YYYY-MM-DD' for metadata filtering."""
    dt = normalize_timestamp(ts)
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Text formatters
# ---------------------------------------------------------------------------

def format_activity_as_text(activity: dict) -> str:
    """Convert a normalized (snake_case) activity dict to natural-language prose."""
    activity_type = (activity.get("activity_type") or "activity").lower()
    date_str = _timestamp_to_date(activity.get("begin_timestamp") or activity.get("start_time_gmt"))

    dist_km = _cm_to_km(activity.get("distance"))
    dist_str = f"{dist_km:.2f} km" if dist_km is not None else "unknown distance"

    dur_str = _ms_to_hms(activity.get("duration"))

    cal = activity.get("calories")
    cal_str = f"{cal:.0f} calories" if cal is not None else None

    elev_gain = activity.get("elevation_gain")
    elev_str = f"{elev_gain:.0f} m of elevation gain" if elev_gain is not None else None

    lap_count = activity.get("lap_count")
    lap_str = f"{lap_count} lap{'s' if lap_count != 1 else ''}" if lap_count is not None else None

    is_pr = activity.get("pr")

    # Speed / pace — activity-type-specific
    raw_speed = activity.get("avg_speed")
    raw_max_speed = activity.get("max_speed")

    if activity_type == "running":
        avg_pace = _pace_str(raw_speed)
        max_pace = _pace_str(raw_max_speed)
        speed_sentence = ""
        if avg_pace:
            speed_sentence = f"Your average pace was {avg_pace}"
            if max_pace:
                speed_sentence += f" with a best pace of {max_pace}"
            speed_sentence += "."
    else:
        avg_kmh = _dms_to_kmh(raw_speed)
        max_kmh = _dms_to_kmh(raw_max_speed)
        speed_sentence = ""
        if avg_kmh is not None:
            speed_sentence = f"Your average speed was {avg_kmh:.1f} km/h"
            if max_kmh is not None:
                speed_sentence += f" with a maximum of {max_kmh:.1f} km/h"
            speed_sentence += "."

    parts = [
        f"You completed a {activity_type} session on {date_str},",
        f"covering {dist_str} in {dur_str}.",
    ]
    if speed_sentence:
        parts.append(speed_sentence)
    if cal_str:
        parts.append(f"You burned {cal_str}.")
    if elev_str:
        parts.append(f"You accumulated {elev_str}.")
    if lap_str:
        parts.append(f"The session consisted of {lap_str}.")
    if is_pr:
        parts.append("This session included a personal record achievement.")

    return " ".join(parts)


def format_sleep_as_text(sleep: dict) -> str:
    """Convert a normalized sleep record dict to natural-language prose."""
    date_str = sleep.get("calendar_date", "unknown date")

    deep = sleep.get("deep_sleep_seconds") or 0
    light = sleep.get("light_sleep_seconds") or 0
    rem = sleep.get("rem_sleep_seconds") or 0
    awake = sleep.get("awake_sleep_seconds") or 0
    total = deep + light + rem + awake

    total_hours = total // 3600
    total_mins = (total % 3600) // 60
    duration_str = f"{total_hours} hour{'s' if total_hours != 1 else ''} and {total_mins} minute{'s' if total_mins != 1 else ''}"

    parts = [f"On the night of {date_str}, you slept for {duration_str}."]

    if total > 0:
        deep_pct = round(deep / total * 100)
        light_pct = round(light / total * 100)
        rem_pct = round(rem / total * 100)
        awake_pct = round(awake / total * 100)
        parts.append(
            f"Your sleep was composed of {deep_pct}% deep sleep, {rem_pct}% REM sleep, "
            f"{light_pct}% light sleep, and {awake_pct}% awake time."
        )
    else:
        parts.append("Sleep stage breakdown unavailable for this night.")

    # SpO2 / HR from nested spo2_sleep_summary
    spo2_summary = sleep.get("spo2_sleep_summary") or {}
    avg_hr = spo2_summary.get("average_hr") or spo2_summary.get("average_h_r")
    avg_spo2 = spo2_summary.get("average_spo2") or spo2_summary.get("average_sp_o2")

    if avg_hr is not None or avg_spo2 is not None:
        health_parts = []
        if avg_hr is not None:
            health_parts.append(f"average heart rate of {avg_hr:.0f} bpm")
        if avg_spo2 is not None:
            health_parts.append(f"average SpO2 of {avg_spo2:.0f}%")
        parts.append(f"During sleep, your {' and '.join(health_parts)}.")

    # Sleep score
    sleep_scores = sleep.get("sleep_scores") or {}
    overall = sleep_scores.get("overall_score")
    if overall is not None:
        parts.append(f"Your overall sleep score was {overall} out of 100.")

    return " ".join(parts)


def format_record_as_text(record: dict) -> str:
    """Convert a normalized personal record dict to natural-language prose."""
    record_type = record.get("personal_record_type") or "Personal Record"
    value = record.get("value")
    date_str = _timestamp_to_date(record.get("pr_start_time_gmt"))
    is_current = record.get("current", False)
    activity_id = record.get("activity_id")

    status = "your current all-time best" if is_current else "a previous personal record"

    parts = [f"You set a personal record for {record_type} on {date_str}."]

    if value is not None:
        parts.append(f"The recorded value was {value}.")

    parts.append(f"This is {status}.")

    if activity_id and int(activity_id) > 0:
        parts.append(f"It was achieved during activity ID {activity_id}.")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Metadata builders
# ---------------------------------------------------------------------------

def build_metadata(data_type: str, record: dict) -> dict:
    """Build a metadata dict for a chunk, used for retrieval filtering."""
    meta: dict[str, Any] = {
        "data_type": data_type,
        "source": "garmin_zip",
    }

    if data_type == "activity":
        meta["record_id"] = record.get("activity_id")
        meta["activity_type"] = (record.get("activity_type") or "").lower()
        meta["user_id"] = record.get("user_profile_id")
        meta["date"] = _timestamp_to_iso_date(
            record.get("begin_timestamp") or record.get("start_time_gmt")
        )
        meta["is_current_pr"] = None

    elif data_type == "sleep":
        meta["record_id"] = None
        meta["activity_type"] = None
        meta["user_id"] = (record.get("spo2_sleep_summary") or {}).get("user_profile_pk")
        meta["date"] = record.get("calendar_date")
        meta["is_current_pr"] = None

    elif data_type == "personal_record":
        meta["record_id"] = record.get("personal_record_id")
        meta["activity_type"] = None
        meta["user_id"] = None
        meta["date"] = _timestamp_to_iso_date(record.get("pr_start_time_gmt"))
        meta["is_current_pr"] = bool(record.get("current", False))

    return meta


# ---------------------------------------------------------------------------
# Per-type chunkers
# ---------------------------------------------------------------------------

def chunk_activities(activities: list[dict]) -> list[Document]:
    """Convert a list of normalized activity dicts to LangChain Documents."""
    docs = []
    for activity in activities:
        text = format_activity_as_text(activity)
        metadata = build_metadata("activity", activity)
        docs.append(Document(page_content=text, metadata=metadata))
    return docs


def chunk_sleep(sleep_records: list[dict]) -> list[Document]:
    """Convert a list of normalized sleep record dicts to LangChain Documents.

    Skips records that have no calendar_date AND zero total sleep seconds —
    these are corrupt/empty Garmin log entries with no useful RAG content.
    """
    docs = []
    for record in sleep_records:
        has_date = bool(record.get("calendar_date"))
        total_sleep = (
            (record.get("deep_sleep_seconds") or 0)
            + (record.get("light_sleep_seconds") or 0)
            + (record.get("rem_sleep_seconds") or 0)
            + (record.get("awake_sleep_seconds") or 0)
        )
        if not has_date and total_sleep == 0:
            continue  # skip corrupt empty record
        text = format_sleep_as_text(record)
        metadata = build_metadata("sleep", record)
        docs.append(Document(page_content=text, metadata=metadata))
    return docs


def chunk_personal_records(records: list[dict]) -> list[Document]:
    """Convert a list of normalized personal record dicts to LangChain Documents."""
    # personalRecord.json wraps records in a 'personal_records' key
    flat: list[dict] = []
    for item in records:
        if isinstance(item, dict) and "personal_records" in item:
            flat.extend(item["personal_records"])
        else:
            flat.append(item)

    docs = []
    for record in flat:
        text = format_record_as_text(record)
        metadata = build_metadata("personal_record", record)
        docs.append(Document(page_content=text, metadata=metadata))
    return docs


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def chunk_garmin_data(parsed: dict) -> list[Document]:
    """Convert the output of parse_garmin_zip() into a list of LangChain Documents.

    Args:
        parsed: dict returned by parse_garmin_zip() with keys:
            'summarizedActivities', 'sleepData', 'personalRecords'

    Returns:
        Combined list of Documents from all three data types.
    """
    docs: list[Document] = []

    raw_activities = parsed.get("summarizedActivities", [])
    # summarizedActivities.json is a list of {summarizedActivitiesExport: [...]}
    flat_activities: list[dict] = []
    for item in raw_activities:
        if isinstance(item, dict) and "summarized_activities_export" in item:
            flat_activities.extend(item["summarized_activities_export"])
        elif isinstance(item, dict):
            flat_activities.append(item)
    docs.extend(chunk_activities(flat_activities))

    raw_sleep = parsed.get("sleepData", [])
    if isinstance(raw_sleep, list):
        docs.extend(chunk_sleep(raw_sleep))

    raw_records = parsed.get("personalRecords", [])
    if isinstance(raw_records, list):
        docs.extend(chunk_personal_records(raw_records))

    return docs
