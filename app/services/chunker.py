"""Garmin data chunker — converts parsed Garmin records into LangChain Documents.

Raw Garmin unit notes (from data/samples analysis):
  - distance: stored in centimeters (cm); divide by 100_000 to get km
  - avg_speed / max_speed: stored in dm/s; multiply by 36 to get km/h, ×10 for m/s
  - duration: stored in milliseconds; divide by 1000 for seconds
  - timestamps (begin_timestamp, start_time_gmt): Unix milliseconds
"""

from __future__ import annotations

from collections import Counter
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
        pace_sec = 100.0 / float(raw_speed_dms)
        mins = int(pace_sec // 60)
        secs = int(pace_sec % 60)
        return f"{mins}:{secs:02d}/km"
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _timestamp_to_date(ts: Any) -> str:
    """Return 'Month D, YYYY' from any Garmin timestamp value, or 'unknown date'."""
    dt = normalize_timestamp(ts)
    if dt is None:
        return "unknown date"
    return dt.strftime("%B %-d, %Y")


def _timestamp_to_iso_date(ts: Any) -> Optional[str]:
    """Return 'YYYY-MM-DD' for metadata filtering."""
    dt = normalize_timestamp(ts)
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Sport-specific text formatters (Task 3)
# ---------------------------------------------------------------------------

def _append_pr(activity: dict, parts: list) -> None:
    """Append a PR note if the activity has pr=True."""
    if activity.get("pr"):
        parts.append("This session included a personal record achievement.")


def _format_running(activity: dict) -> str:
    date_str = _timestamp_to_date(activity.get("begin_timestamp") or activity.get("start_time_gmt"))
    name = activity.get("name") or "Running"
    dist_km = _cm_to_km(activity.get("distance"))
    dist_str = f"{dist_km:.2f} km" if dist_km is not None else "unknown distance"
    dur_str = _ms_to_hms(activity.get("duration"))
    avg_pace = _pace_str(activity.get("avg_speed"))
    max_pace = _pace_str(activity.get("max_speed"))
    avg_hr = activity.get("avg_heart_rate")
    max_hr = activity.get("max_heart_rate")
    cadence = activity.get("avg_running_cadence") or activity.get("avg_cadence")
    cal = activity.get("calories")
    elev_gain = activity.get("elevation_gain")

    parts = [f"You completed a running session ({name}) on {date_str}, covering {dist_str} in {dur_str}."]
    if avg_pace:
        pace_line = f"Your average pace was {avg_pace}"
        if max_pace:
            pace_line += f" with a best pace of {max_pace}"
        parts.append(pace_line + ".")
    if avg_hr is not None:
        hr_line = f"Average heart rate: {avg_hr:.0f} bpm"
        if max_hr is not None:
            hr_line += f", max: {max_hr:.0f} bpm"
        parts.append(hr_line + ".")
    if cadence is not None:
        parts.append(f"Average cadence: {cadence:.0f} spm.")
    if cal is not None:
        parts.append(f"You burned {cal:.0f} calories.")
    if elev_gain is not None and float(elev_gain) > 0:
        parts.append(f"Elevation gain: {elev_gain:.0f} m.")
    _append_pr(activity, parts)
    return " ".join(parts)


def _format_cycling(activity: dict) -> str:
    date_str = _timestamp_to_date(activity.get("begin_timestamp") or activity.get("start_time_gmt"))
    name = activity.get("name") or "Cycling"
    dist_km = _cm_to_km(activity.get("distance"))
    dist_str = f"{dist_km:.2f} km" if dist_km is not None else "unknown distance"
    dur_str = _ms_to_hms(activity.get("duration"))
    avg_kmh = _dms_to_kmh(activity.get("avg_speed"))
    max_kmh = _dms_to_kmh(activity.get("max_speed"))
    elev_gain = activity.get("elevation_gain")
    elev_loss = activity.get("elevation_loss")
    cal = activity.get("calories")
    location = activity.get("location_name")

    parts = [f"You completed a cycling session ({name}) on {date_str}, covering {dist_str} in {dur_str}."]
    if avg_kmh is not None:
        speed_line = f"Average speed: {avg_kmh:.1f} km/h"
        if max_kmh is not None:
            speed_line += f", max: {max_kmh:.1f} km/h"
        parts.append(speed_line + ".")
    if elev_gain is not None and float(elev_gain) > 0:
        elev_line = f"Elevation gain: {elev_gain:.0f} m"
        if elev_loss is not None:
            elev_line += f", loss: {elev_loss:.0f} m"
        parts.append(elev_line + ".")
    if cal is not None:
        parts.append(f"You burned {cal:.0f} calories.")
    if location:
        parts.append(f"Location: {location}.")
    _append_pr(activity, parts)
    return " ".join(parts)


def _format_swimming(activity: dict) -> str:
    date_str = _timestamp_to_date(activity.get("begin_timestamp") or activity.get("start_time_gmt"))
    dist_km = _cm_to_km(activity.get("distance"))
    dur_str = _ms_to_hms(activity.get("duration"))
    cal = activity.get("calories")
    laps = activity.get("lap_count")

    if dist_km and dist_km > 0:
        dist_str = f"{dist_km:.3f} km"
    elif laps:
        dist_str = f"{laps} lap{'s' if laps != 1 else ''}"
    else:
        dist_str = "unknown distance"

    parts = [f"You completed a swimming session on {date_str}, covering {dist_str} in {dur_str}."]
    if cal is not None:
        parts.append(f"You burned {cal:.0f} calories.")
    _append_pr(activity, parts)
    return " ".join(parts)


def _format_triathlon(activity: dict) -> str:
    date_str = _timestamp_to_date(activity.get("begin_timestamp") or activity.get("start_time_gmt"))
    dur_str = _ms_to_hms(activity.get("duration"))
    dist_km = _cm_to_km(activity.get("distance"))
    dist_str = f"{dist_km:.2f} km" if dist_km and dist_km > 0 else "unknown distance"
    cal = activity.get("calories")
    laps = activity.get("lap_count")

    parts = [f"You completed a triathlon on {date_str}, total distance {dist_str} in {dur_str}."]
    if laps:
        parts.append(f"The race had {laps} leg{'s' if laps != 1 else ''} recorded.")
    if cal is not None:
        parts.append(f"You burned {cal:.0f} calories.")
    _append_pr(activity, parts)
    return " ".join(parts)


def _format_strength(activity: dict) -> str:
    date_str = _timestamp_to_date(activity.get("begin_timestamp") or activity.get("start_time_gmt"))
    name = activity.get("name") or "Strength Training"
    dur_str = _ms_to_hms(activity.get("duration"))
    cal = activity.get("calories")

    parts = [f"You completed a strength training session ({name}) on {date_str}, lasting {dur_str}."]
    if cal is not None:
        parts.append(f"You burned {cal:.0f} calories.")
    _append_pr(activity, parts)
    return " ".join(parts)


def _format_hiking(activity: dict) -> str:
    date_str = _timestamp_to_date(activity.get("begin_timestamp") or activity.get("start_time_gmt"))
    name = activity.get("name") or "Hiking"
    dist_km = _cm_to_km(activity.get("distance"))
    dist_str = f"{dist_km:.2f} km" if dist_km is not None else "unknown distance"
    dur_str = _ms_to_hms(activity.get("duration"))
    elev_gain = activity.get("elevation_gain")
    elev_loss = activity.get("elevation_loss")
    cal = activity.get("calories")
    location = activity.get("location_name")

    parts = [f"You went hiking ({name}) on {date_str}, covering {dist_str} in {dur_str}."]
    if elev_gain is not None and float(elev_gain) > 0:
        elev_line = f"Elevation gain: {elev_gain:.0f} m"
        if elev_loss is not None:
            elev_line += f", loss: {elev_loss:.0f} m"
        parts.append(elev_line + ".")
    if cal is not None:
        parts.append(f"You burned {cal:.0f} calories.")
    if location:
        parts.append(f"Location: {location}.")
    _append_pr(activity, parts)
    return " ".join(parts)


def _format_mountaineering(activity: dict) -> str:
    date_str = _timestamp_to_date(activity.get("begin_timestamp") or activity.get("start_time_gmt"))
    name = activity.get("name") or "Mountaineering"
    dur_str = _ms_to_hms(activity.get("duration"))
    elev_gain = activity.get("elevation_gain")
    elev_loss = activity.get("elevation_loss")
    max_elev = activity.get("max_elevation")
    min_elev = activity.get("min_elevation")
    cal = activity.get("calories")
    location = activity.get("location_name")

    parts = [f"You went mountaineering ({name}) on {date_str}, lasting {dur_str}."]
    if elev_gain is not None and float(elev_gain) > 0:
        elev_line = f"Elevation gain: {elev_gain:.0f} m"
        if elev_loss is not None:
            elev_line += f", loss: {elev_loss:.0f} m"
        parts.append(elev_line + ".")
    if max_elev is not None:
        elev_range = f"Max elevation: {max_elev:.0f} m"
        if min_elev is not None:
            elev_range += f", min: {min_elev:.0f} m"
        parts.append(elev_range + ".")
    if cal is not None:
        parts.append(f"You burned {cal:.0f} calories.")
    if location:
        parts.append(f"Location: {location}.")
    _append_pr(activity, parts)
    return " ".join(parts)


def _format_generic(activity: dict) -> str:
    activity_type = (activity.get("activity_type") or "activity").lower()
    date_str = _timestamp_to_date(activity.get("begin_timestamp") or activity.get("start_time_gmt"))
    name = activity.get("name") or activity_type.replace("_", " ").title()
    dur_str = _ms_to_hms(activity.get("duration"))
    dist_km = _cm_to_km(activity.get("distance"))
    cal = activity.get("calories")

    parts = [f"You completed a {activity_type} session ({name}) on {date_str}, lasting {dur_str}."]
    if dist_km and dist_km > 0:
        parts.append(f"Distance covered: {dist_km:.2f} km.")
    if cal is not None:
        parts.append(f"You burned {cal:.0f} calories.")
    _append_pr(activity, parts)
    return " ".join(parts)


SPORT_FORMATTERS = {
    "running":             _format_running,
    "treadmill_running":   _format_running,
    "cycling":             _format_cycling,
    "indoor_cycling":      _format_cycling,
    "virtual_ride":        _format_cycling,
    "swimming":            _format_swimming,
    "open_water_swimming": _format_swimming,
    "triathlon":           _format_triathlon,
    "strength_training":   _format_strength,
    "fitness_equipment":   _format_strength,
    "hiking":              _format_hiking,
    "mountaineering":      _format_mountaineering,
}


def format_activity_as_text(activity: dict) -> str:
    """Dispatcher: select the right formatter based on activity_type."""
    key = (activity.get("activity_type") or "").lower()
    formatter = SPORT_FORMATTERS.get(key, _format_generic)
    return formatter(activity)


# ---------------------------------------------------------------------------
# Sleep and personal record text formatters (unchanged logic)
# ---------------------------------------------------------------------------

def format_sleep_as_text(sleep: dict) -> str:
    date_str = sleep.get("calendar_date", "unknown date")

    deep = sleep.get("deep_sleep_seconds") or 0
    light = sleep.get("light_sleep_seconds") or 0
    rem = sleep.get("rem_sleep_seconds") or 0
    awake = sleep.get("awake_sleep_seconds") or 0
    total = deep + light + rem + awake

    total_hours = total // 3600
    total_mins = (total % 3600) // 60
    duration_str = (
        f"{total_hours} hour{'s' if total_hours != 1 else ''} "
        f"and {total_mins} minute{'s' if total_mins != 1 else ''}"
    )

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

    sleep_scores = sleep.get("sleep_scores") or {}
    overall = sleep_scores.get("overall_score")
    if overall is not None:
        parts.append(f"Your overall sleep score was {overall} out of 100.")

    return " ".join(parts)


def format_record_as_text(record: dict) -> str:
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
# Metadata builder — user_id is now a required parameter (Task 1)
# ---------------------------------------------------------------------------

def build_metadata(data_type: str, record: dict, user_id: str) -> dict:
    """Build metadata dict. user_id is injected from the authenticated caller —
    never read from the record itself (prevents cross-user spoofing)."""
    meta: dict[str, Any] = {
        "user_id":   user_id,
        "data_type": data_type,
        "source":    "garmin_zip",
    }

    if data_type == "activity":
        meta["record_id"] = record.get("activity_id")
        meta["activity_type"] = (record.get("activity_type") or "").lower()
        meta["date"] = _timestamp_to_iso_date(
            record.get("begin_timestamp") or record.get("start_time_gmt")
        )
        meta["is_current_pr"] = None

    elif data_type == "sleep":
        meta["record_id"] = None
        meta["activity_type"] = None
        meta["date"] = record.get("calendar_date")
        meta["is_current_pr"] = None

    elif data_type == "personal_record":
        meta["record_id"] = record.get("personal_record_id")
        meta["activity_type"] = None
        meta["date"] = _timestamp_to_iso_date(record.get("pr_start_time_gmt"))
        meta["is_current_pr"] = bool(record.get("current", False))

    return meta


# ---------------------------------------------------------------------------
# Per-type chunkers — all require user_id now
# ---------------------------------------------------------------------------

def chunk_activities(activities: list[dict], user_id: str) -> list[Document]:
    """Convert activity dicts to Documents. Tags each with analysis_ready based
    on whether its sport type has >= 10 records in this upload."""
    sport_counts: Counter = Counter(
        (a.get("activity_type") or "other").lower() for a in activities
    )

    docs = []
    for activity in activities:
        sport = (activity.get("activity_type") or "other").lower()
        text = format_activity_as_text(activity)
        metadata = build_metadata("activity", activity, user_id)
        metadata["analysis_ready"] = sport_counts[sport] >= 10
        docs.append(Document(page_content=text, metadata=metadata))
    return docs


def chunk_sleep(sleep_records: list[dict], user_id: str) -> list[Document]:
    """Convert sleep record dicts to Documents. Skips corrupt empty records."""
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
            continue
        text = format_sleep_as_text(record)
        metadata = build_metadata("sleep", record, user_id)
        metadata["analysis_ready"] = True
        docs.append(Document(page_content=text, metadata=metadata))
    return docs


def chunk_personal_records(records: list[dict], user_id: str) -> list[Document]:
    """Convert personal record dicts to Documents."""
    flat: list[dict] = []
    for item in records:
        if isinstance(item, dict) and "personal_records" in item:
            flat.extend(item["personal_records"])
        else:
            flat.append(item)

    docs = []
    for record in flat:
        text = format_record_as_text(record)
        metadata = build_metadata("personal_record", record, user_id)
        metadata["analysis_ready"] = True
        docs.append(Document(page_content=text, metadata=metadata))
    return docs


# ---------------------------------------------------------------------------
# Main entry point — user_id is now required (Task 1)
# ---------------------------------------------------------------------------

def chunk_garmin_data(parsed: dict, user_id: str) -> list[Document]:
    """Convert the output of parse_garmin_zip() into a list of LangChain Documents.

    Args:
        parsed:  dict from parse_garmin_zip() with keys
                 'summarizedActivities', 'sleepData', 'personalRecords'
        user_id: authenticated user's ID — injected into every chunk's metadata

    Returns:
        Combined list of Documents from all three data types.
    """
    docs: list[Document] = []

    raw_activities = parsed.get("summarizedActivities", [])
    flat_activities: list[dict] = []
    for item in raw_activities:
        if isinstance(item, dict) and "summarized_activities_export" in item:
            flat_activities.extend(item["summarized_activities_export"])
        elif isinstance(item, dict):
            flat_activities.append(item)
    docs.extend(chunk_activities(flat_activities, user_id))

    raw_sleep = parsed.get("sleepData", [])
    if isinstance(raw_sleep, list):
        docs.extend(chunk_sleep(raw_sleep, user_id))

    raw_records = parsed.get("personalRecords", [])
    if isinstance(raw_records, list):
        docs.extend(chunk_personal_records(raw_records, user_id))

    return docs
