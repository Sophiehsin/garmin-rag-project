"""Generate anonymised demo data from real Garmin sample files.

Removes / replaces all personal identifiers:
  - userProfileId / userProfilePk  → fake ID 10000001
  - activityId                     → sequential fake IDs starting at 10000001
  - deviceId                       → fake ID 20000001
  - uuidMsb / uuidLsb              → zeroed
  - startLongitude / startLatitude → removed
  - activity name                  → generic "<Type> Session" + ordinal
  - locationName                   → generic region bucket

Output: data/demo/summarizedActivities.json
        data/demo/sleepData.json
        data/demo/personalRecord.json
        data/demo/garmin_demo.zip   ← ready to upload

Usage:
    python scripts/generate_demo_data.py
"""

import json
import random
import zipfile
from collections import defaultdict
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
FAKE_USER_ID    = 10000001
FAKE_DEVICE_ID  = 20000001
TARGET_RUNNING  = 70
TARGET_CYCLING  = 20
TARGET_OTHER    = 10   # any remaining types
TARGET_SLEEP    = 30   # sleep records to include

SAMPLES_DIR = Path("data/samples")
OUTPUT_DIR  = Path("data/demo")

# Generic location buckets (replace specific Taiwanese district names)
LOCATION_MAP = {
    "新店區": "Mountain Trail Area",
    "台北市": "City Centre",
    "新北市": "Riverside Route",
    "板橋區": "Park Loop",
    "中和區": "Urban Route",
    "永和區": "Riverside Route",
    "三峽區": "Mountain Trail Area",
    "烏來區": "Mountain Trail Area",
    "石碇區": "Mountain Trail Area",
    "坪林區": "Mountain Trail Area",
}

def _generic_location(original: str | None) -> str | None:
    if not original:
        return None
    for key, val in LOCATION_MAP.items():
        if key in original:
            return val
    # Keep if already looks generic (ASCII)
    if all(ord(c) < 128 for c in original):
        return original
    return "Training Route"


def _generic_name(activity_type: str, idx: int) -> str:
    labels = {
        "running":          "Morning Run",
        "treadmill_running":"Treadmill Run",
        "cycling":          "Cycling Session",
        "indoor_cycling":   "Indoor Ride",
        "swimming":         "Swim Session",
        "hiking":           "Hiking",
        "other":            "Workout",
    }
    label = labels.get(activity_type, "Activity")
    return f"{label} #{idx}"


def anonymise_activity(record: dict, fake_id: int, ordinal: int) -> dict:
    r = dict(record)
    r["activityId"]    = fake_id
    r["uuidMsb"]       = 0
    r["uuidLsb"]       = 0
    r["userProfileId"] = FAKE_USER_ID
    r["deviceId"]      = FAKE_DEVICE_ID
    r.pop("startLongitude", None)
    r.pop("startLatitude",  None)
    r["name"]         = _generic_name(r.get("activityType", "other"), ordinal)
    r["locationName"] = _generic_location(r.get("locationName"))
    return r


def anonymise_sleep(record: dict) -> dict:
    r = dict(record)
    spo2 = dict(r.get("spo2SleepSummary") or {})
    spo2.pop("userProfilePk", None)
    spo2["deviceId"] = FAKE_DEVICE_ID
    r["spo2SleepSummary"] = spo2
    return r


def anonymise_pr(record: dict, fake_id: int) -> dict:
    r = dict(record)
    r["personalRecordId"] = fake_id
    r["activityId"] = 0   # unlink from real activity
    return r


def main() -> None:
    random.seed(42)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Activities ─────────────────────────────────────────────────────────────
    with open(SAMPLES_DIR / "summarizedActivities.json") as f:
        raw_acts = json.load(f)

    all_acts = raw_acts[0]["summarizedActivitiesExport"]

    # Bucket by type
    by_type: dict[str, list] = defaultdict(list)
    for a in all_acts:
        by_type[a["activityType"]].append(a)

    running  = random.sample(by_type["running"],  min(TARGET_RUNNING, len(by_type["running"])))
    cycling  = random.sample(by_type["cycling"],  min(TARGET_CYCLING, len(by_type["cycling"])))

    other_pool = [a for t, acts in by_type.items()
                  if t not in ("running", "cycling")
                  for a in acts]
    other = random.sample(other_pool, min(TARGET_OTHER, len(other_pool)))

    selected = running + cycling + other
    # Sort chronologically
    selected.sort(key=lambda a: a.get("beginTimestamp", 0))

    fake_id = 10000001
    anonymised_acts = []
    for i, act in enumerate(selected, start=1):
        anonymised_acts.append(anonymise_activity(act, fake_id, i))
        fake_id += 1

    activities_out = [{"summarizedActivitiesExport": anonymised_acts}]
    with open(OUTPUT_DIR / "summarizedActivities.json", "w") as f:
        json.dump(activities_out, f, ensure_ascii=False, indent=2)
    print(f"Activities: {len(anonymised_acts)} "
          f"(running={sum(1 for a in anonymised_acts if a['activityType']=='running')}, "
          f"cycling={sum(1 for a in anonymised_acts if a['activityType']=='cycling')}, "
          f"other={sum(1 for a in anonymised_acts if a['activityType'] not in ('running','cycling'))})")

    # ── Sleep ──────────────────────────────────────────────────────────────────
    with open(SAMPLES_DIR / "sleepData.json") as f:
        raw_sleep = json.load(f)

    selected_sleep = random.sample(raw_sleep, min(TARGET_SLEEP, len(raw_sleep)))
    selected_sleep.sort(key=lambda s: s.get("calendarDate", ""))
    anonymised_sleep = [anonymise_sleep(s) for s in selected_sleep]

    with open(OUTPUT_DIR / "sleepData.json", "w") as f:
        json.dump(anonymised_sleep, f, ensure_ascii=False, indent=2)
    print(f"Sleep records: {len(anonymised_sleep)}")

    # ── Personal Records ───────────────────────────────────────────────────────
    with open(SAMPLES_DIR / "personalRecord.json") as f:
        raw_pr = json.load(f)

    prs = raw_pr[0]["personalRecords"]
    fake_pr_id = 30000001
    anonymised_prs = []
    for pr in prs:
        anonymised_prs.append(anonymise_pr(pr, fake_pr_id))
        fake_pr_id += 1

    pr_out = [{"personalRecords": anonymised_prs}]
    with open(OUTPUT_DIR / "personalRecord.json", "w") as f:
        json.dump(pr_out, f, ensure_ascii=False, indent=2)
    print(f"Personal records: {len(anonymised_prs)}")

    # ── ZIP ────────────────────────────────────────────────────────────────────
    zip_path = OUTPUT_DIR / "garmin_demo.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(OUTPUT_DIR / "summarizedActivities.json", "summarizedActivities.json")
        zf.write(OUTPUT_DIR / "sleepData.json",            "sleepData.json")
        zf.write(OUTPUT_DIR / "personalRecord.json",       "personalRecord.json")
    print(f"\nDemo ZIP written to: {zip_path}")
    print("Upload this file to POST /api/v1/upload to test the system.")


if __name__ == "__main__":
    main()
