import json
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st
from streamlit_calendar import calendar

from studyflow.planning import ab_calendar


STYLE_FILE = Path(__file__).resolve().parents[2] / "assets" / "styles" / "calendar.css"
COURSE_COLORS = ["#0F766E", "#1D4ED8", "#7C3AED", "#B45309", "#BE185D", "#15803D", "#C2410C", "#4338CA"]
DUE_COLOR = "#9F1239"
CALLBACKS = ["eventClick", "eventChange", "select"]
DAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WEEKS_AHEAD = 6


# ============================================================
# HELPERS
# ============================================================

def _parse_day(value):
    try:
        return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_clock(value):
    try:
        return datetime.strptime(str(value).strip()[:5], "%H:%M").time()
    except ValueError:
        return None


def _stamp(day, clock):
    return f"{day:%Y-%m-%d}T{clock:%H:%M}:00"


def course_colors(courses, sessions, assignments):
    names = []
    for name in list(courses) + [s.get("course") for s in sessions] + [a.get("course") for a in assignments]:
        if name and name not in names:
            names.append(name)
    return {name: COURSE_COLORS[index % len(COURSE_COLORS)] for index, name in enumerate(names)}


# ============================================================
# EVENTS
# ============================================================

def _session_events(sessions, colors):
    events = []
    for index, session in enumerate(sessions):
        if not isinstance(session, dict):
            continue
        day = _parse_day(session.get("date"))
        start = _parse_clock(session.get("start_time"))
        end = _parse_clock(session.get("end_time"))
        if not day or not start:
            continue
        start_at = datetime.combine(day, start)
        end_at = datetime.combine(day, end) if end else start_at + timedelta(minutes=int(session.get("minutes") or 45))
        if end_at <= start_at:
            end_at += timedelta(days=1)

        color = colors.get(session.get("course"), COURSE_COLORS[0])
        events.append({
            "id": f"session-{index}",
            "title": session.get("assignment") or session.get("course") or "Study session",
            "start": f"{start_at:%Y-%m-%dT%H:%M:%S}",
            "end": f"{end_at:%Y-%m-%dT%H:%M:%S}",
            "backgroundColor": color,
            "borderColor": color,
            "classNames": ["sf-session", "sf-done"] if session.get("done") else ["sf-session"],
            "extendedProps": {"kind": "session", "index": index}
        })
    return events


def _due_events(assignments):
    events = []
    for index, assignment in enumerate(assignments):
        day = _parse_day(assignment.get("due_date"))
        if not day:
            continue
        kind = (assignment.get("type") or "").title()
        label = kind if kind in ("Test", "Quiz", "Presentation") else "Due"
        events.append({
            "id": f"due-{index}",
            "title": f"{label}: {assignment.get('name') or 'Assignment'}",
            "start": f"{day:%Y-%m-%d}",
            "allDay": True,
            "editable": False,
            "backgroundColor": DUE_COLOR,
            "borderColor": DUE_COLOR,
            "classNames": ["sf-due"],
            "extendedProps": {"kind": "due", "index": index}
        })
    return events


def _activity_events(activities, first, last):
    events = []
    day = first
    while day <= last:
        weekday = DAY_SHORT[day.weekday()]
        for activity in activities:
            start = _parse_clock(activity.get("start"))
            end = _parse_clock(activity.get("end"))
            if weekday not in (activity.get("days") or []) or not start or not end or end <= start:
                continue
            events.append({
                "id": f"activity-{activity.get('id')}-{day:%Y%m%d}",
                "title": activity.get("name") or "Activity",
                "start": _stamp(day, start),
                "end": _stamp(day, end),
                "editable": False,
                "classNames": ["sf-busy"],
                "extendedProps": {"kind": "activity"}
            })
        day += timedelta(days=1)
    return events


def _one_time_events(one_time):
    events = []
    for item in one_time:
        event = {
            "id": f"event-{item['id']}",
            "title": item["name"],
            "classNames": ["sf-event"],
            "extendedProps": {"kind": "event", "event_id": item["id"]}
        }
        if item["all_day"]:
            event.update({"start": item["date"], "allDay": True})
        else:
            event.update({"start": f"{item['date']}T{item['start']}:00", "end": f"{item['date']}T{item['end']}:00"})
        events.append(event)
    return events


def _ab_events(first, last):
    events = []
    day = first
    while day <= last:
        label = ab_calendar.short_label(day)
        if label:
            events.append({
                "id": f"ab-{day:%Y%m%d}",
                "title": label,
                "start": f"{day:%Y-%m-%d}",
                "allDay": True,
                "editable": False,
                "classNames": ["sf-ab"],
                "extendedProps": {"kind": "ab"}
            })
        day += timedelta(days=1)
    return events


def build_events(sessions, assignments, activities, courses, today, use_ab, one_time=()):
    colors = course_colors(courses, sessions, assignments)
    days = [_parse_day(s.get("date")) for s in sessions if isinstance(s, dict)]
    days = [day for day in days if day]
    first = min(days + [today]) - timedelta(days=7)
    last = max(days + [today + timedelta(weeks=WEEKS_AHEAD)]) + timedelta(days=7)

    events = (
        _session_events(sessions, colors)
        + _due_events(assignments)
        + _activity_events(activities, first, last)
        + _one_time_events(one_time)
    )
    if use_ab:
        events += _ab_events(first, last)
    return events


# ============================================================
# CALENDAR
# ============================================================

def _options(now, study_style, mobile, first_session):
    homework = _parse_clock(study_style.get("homework_start")) or _parse_clock("16:00")
    scroll = (datetime.combine(now.date(), homework) - timedelta(hours=1)).time()
    start_day = first_session if first_session and first_session > now.date() else now.date()

    if mobile:
        toolbar = {"left": "prev,next", "center": "title", "right": "timeGridDay,listWeek"}
    else:
        toolbar = {"left": "prev,next today", "center": "title", "right": "timeGridDay,timeGridWeek,dayGridMonth,listWeek"}

    return {
        "initialView": "timeGridDay" if mobile else "timeGridWeek",
        "initialDate": f"{start_day:%Y-%m-%d}",
        "headerToolbar": toolbar,
        "buttonText": {"today": "Today", "day": "Day", "week": "Week", "month": "Month", "list": "List"},
        "views": {
            "timeGridDay": {"buttonText": "Day"},
            "timeGridWeek": {"buttonText": "Week"},
            "dayGridMonth": {"buttonText": "Month"},
            "listWeek": {"buttonText": "List"}
        },
        "timeZone": "UTC",
        "now": f"{now:%Y-%m-%dT%H:%M:%S}",
        "nowIndicator": True,
        "editable": True,
        "selectable": True,
        "selectMirror": True,
        "eventStartEditable": True,
        "eventDurationEditable": True,
        "snapDuration": "00:15:00",
        "slotDuration": "00:30:00",
        "slotMinTime": "06:00:00",
        "slotMaxTime": "24:00:00",
        "scrollTime": f"{scroll:%H:%M:%S}",
        "allDaySlot": True,
        "allDayText": "All day",
        "dayMaxEvents": True,
        "expandRows": True,
        "height": 640 if mobile else 720,
        "eventTimeFormat": {"hour": "numeric", "minute": "2-digit", "meridiem": "short"},
        "slotLabelFormat": {"hour": "numeric", "meridiem": "short"},
        "dayHeaderFormat": {"weekday": "short", "month": "numeric", "day": "numeric", "omitCommas": True},
        "firstDay": 0,
        "eventDisplay": "block"
    }


def show(sessions, assignments, activities, courses, study_style, now, use_ab, mobile, revision, one_time=()):
    events = build_events(sessions, assignments, activities, courses, now.date(), use_ab, one_time)
    for event in events:
        event["extendedProps"]["revision"] = revision

    first_days = sorted(
        day for day in (_parse_day(s.get("date")) for s in sessions if isinstance(s, dict) and not s.get("done")) if day
    )
    return calendar(
        events=events,
        options=_options(now, study_style, mobile, first_days[0] if first_days else None),
        custom_css=STYLE_FILE.read_text(encoding="utf-8"),
        callbacks=CALLBACKS,
        key="study_calendar"
    )


# ============================================================
# WHAT THE STUDENT DID
# ============================================================

def _wall_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def read_action(state):
    if not isinstance(state, dict) or not state.get("callback"):
        return None

    signature = json.dumps(state, sort_keys=True, default=str)
    if st.session_state.get("calendar_last_action") == signature:
        return None
    st.session_state.calendar_last_action = signature

    if state["callback"] == "eventClick":
        event = (state.get("eventClick") or {}).get("event") or {}
        props = event.get("extendedProps") or {}
        if props.get("kind") in ("session", "due"):
            return {"type": "select", "kind": props["kind"], "index": props.get("index")}
        if props.get("kind") == "event":
            return {"type": "select", "kind": "event", "index": props.get("event_id")}
        return None

    if state["callback"] == "select":
        picked = state.get("select") or {}
        start = _wall_time(picked.get("start"))
        end = _wall_time(picked.get("end"))
        if not start:
            return None
        if picked.get("allDay"):
            return {"type": "new_event", "date": start.date(), "start": None, "end": None, "all_day": True}
        if not end or end <= start:
            end = start + timedelta(hours=1)
        if end.date() != start.date():
            end = datetime.combine(start.date(), datetime.max.time()).replace(second=0, microsecond=0)
        return {"type": "new_event", "date": start.date(), "start": start, "end": end, "all_day": False}

    if state["callback"] == "eventChange":
        event = (state.get("eventChange") or {}).get("event") or {}
        props = event.get("extendedProps") or {}
        if props.get("kind") == "event":
            start = _wall_time(event.get("start"))
            end = _wall_time(event.get("end"))
            if not start:
                return {"type": "revert"}
            if event.get("allDay"):
                return {"type": "move_event", "id": props.get("event_id"), "date": start.date(), "start": None, "end": None, "all_day": True}
            if not end or end <= start:
                end = start + timedelta(hours=1)
            return {"type": "move_event", "id": props.get("event_id"), "date": start.date(), "start": start, "end": end, "all_day": False}
        if props.get("kind") != "session":
            return {"type": "revert"}
        start = _wall_time(event.get("start"))
        end = _wall_time(event.get("end"))
        if event.get("allDay") or not start:
            return {"type": "revert", "index": props.get("index"), "reason": "all_day"}
        if not end or end <= start:
            end = start + timedelta(minutes=45)
        return {"type": "move", "index": props.get("index"), "start": start, "end": end}

    return None


def move_session(session, start, end):
    if end.date() != start.date():
        end = datetime.combine(start.date(), datetime.max.time()).replace(second=0, microsecond=0)
    session["date"] = f"{start:%Y-%m-%d}"
    session["start_time"] = f"{start:%H:%M}"
    session["end_time"] = f"{end:%H:%M}"
    session["minutes"] = max(5, int((end - start).total_seconds() // 60))
