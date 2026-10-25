import uuid
from datetime import datetime, timedelta


DEFAULT_START = "16:00"
DEFAULT_END = "17:00"
MAX_NAME = 80


# ============================================================
# CLEANING
# ============================================================

def _day(value):
    try:
        return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        return None


def _clock(value):
    try:
        return datetime.strptime(str(value).strip()[:5], "%H:%M").strftime("%H:%M")
    except ValueError:
        return None


def _minutes(value):
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def normalize_event(event):
    if not isinstance(event, dict):
        return None
    day = _day(event.get("date"))
    if not day:
        return None

    start = _clock(event.get("start")) or DEFAULT_START
    end = _clock(event.get("end")) or DEFAULT_END
    if _minutes(end) <= _minutes(start):
        end_minutes = min(_minutes(start) + 60, 23 * 60 + 59)
        end = f"{end_minutes // 60:02d}:{end_minutes % 60:02d}"

    return {
        "id": str(event.get("id") or uuid.uuid4().hex),
        "name": " ".join(str(event.get("name") or "").split())[:MAX_NAME] or "Busy",
        "date": day,
        "start": start,
        "end": end,
        "all_day": bool(event.get("all_day"))
    }


def normalize_events(events):
    cleaned = [event for event in (normalize_event(item) for item in events or []) if event]
    return sorted(cleaned, key=lambda event: (event["date"], "" if event["all_day"] else event["start"]))


def new_event(name, date, start=DEFAULT_START, end=DEFAULT_END, all_day=False):
    return normalize_event({
        "id": uuid.uuid4().hex,
        "name": name,
        "date": date,
        "start": start,
        "end": end,
        "all_day": all_day
    })


def upcoming(events, today, days_back=1):
    first = (today - timedelta(days=days_back)).strftime("%Y-%m-%d")
    return [event for event in events if event["date"] >= first]


# ============================================================
# PLANNING
# ============================================================

def as_busy_blocks(events):
    return [
        {
            "date": event["date"],
            "start": "00:00" if event["all_day"] else event["start"],
            "end": "23:59" if event["all_day"] else event["end"]
        }
        for event in events
    ]


def overlapping_sessions(event, sessions):
    start = 0 if event["all_day"] else _minutes(event["start"])
    end = 24 * 60 if event["all_day"] else _minutes(event["end"])
    found = []
    for session in sessions or []:
        if not isinstance(session, dict) or session.get("done") or session.get("date") != event["date"]:
            continue
        session_start = _clock(session.get("start_time"))
        session_end = _clock(session.get("end_time"))
        if not session_start or not session_end:
            continue
        if _minutes(session_start) < end and _minutes(session_end) > start:
            found.append(session)
    return found
