import hashlib
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from zoneinfo import ZoneInfo


PRODUCT_ID = "-//StudyFlow AI//Study Plan//EN"
REMINDER_MINUTES = 10


# ============================================================
# HELPERS
# ============================================================

def _zone(name):
    try:
        return ZoneInfo(name or "America/New_York")
    except Exception:
        return ZoneInfo("America/New_York")


def _parse_date(value):
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_clock(value):
    try:
        return datetime.strptime(str(value).strip()[:5], "%H:%M").time()
    except ValueError:
        return None


def _utc_stamp(moment):
    return moment.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _escape(text):
    text = str(text or "")
    for old, new in (("\\", "\\\\"), (";", "\\;"), (",", "\\,"), ("\r\n", "\\n"), ("\n", "\\n")):
        text = text.replace(old, new)
    return text


def _fold(line):
    encoded = line.encode("utf-8")
    if len(encoded) <= 75:
        return [line]
    parts = []
    current = ""
    limit = 75
    for character in line:
        if len((current + character).encode("utf-8")) > limit:
            parts.append(current)
            current = " " + character
            limit = 75
        else:
            current += character
    parts.append(current)
    return parts


def _uid(*pieces):
    digest = hashlib.sha1("|".join(str(piece) for piece in pieces).encode("utf-8")).hexdigest()
    return f"{digest[:20]}@studyflow-ai"


# ============================================================
# EVENTS
# ============================================================

def session_times(session, zone_name):
    day = _parse_date(session.get("date"))
    start = _parse_clock(session.get("start_time"))
    end = _parse_clock(session.get("end_time"))
    if not day or not start:
        return None, None

    zone = _zone(zone_name)
    start_at = datetime.combine(day, start, tzinfo=zone)

    if end:
        end_at = datetime.combine(day, end, tzinfo=zone)
        if end_at <= start_at:
            end_at += timedelta(days=1)
    else:
        try:
            minutes = int(session.get("minutes") or 60)
        except (TypeError, ValueError):
            minutes = 60
        end_at = start_at + timedelta(minutes=max(5, minutes))

    return start_at, end_at


def session_title(session):
    course = str(session.get("course") or "").strip()
    assignment = str(session.get("assignment") or "").strip()
    label = " · ".join(part for part in (course, assignment) if part)
    return f"📚 Study: {label}" if label else "📚 Study session"


def session_details(session):
    lines = []
    if session.get("task"):
        lines.append(f"Task: {session['task']}")
    if session.get("assignment"):
        lines.append(f"Assignment: {session['assignment']}")
    if session.get("minutes"):
        lines.append(f"Planned time: {session['minutes']} minutes")
    lines.append("Planned by StudyFlow AI")
    return "\n".join(lines)


def _session_event(session, zone_name, stamp):
    start_at, end_at = session_times(session, zone_name)
    if not start_at:
        return []

    return [
        "BEGIN:VEVENT",
        f"UID:{_uid('session', session.get('date'), session.get('start_time'), session.get('course'), session.get('assignment'))}",
        f"DTSTAMP:{stamp}",
        f"DTSTART:{_utc_stamp(start_at)}",
        f"DTEND:{_utc_stamp(end_at)}",
        f"SUMMARY:{_escape(session_title(session))}",
        f"DESCRIPTION:{_escape(session_details(session))}",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        f"DESCRIPTION:{_escape(session_title(session))}",
        f"TRIGGER:-PT{REMINDER_MINUTES}M",
        "END:VALARM",
        "END:VEVENT"
    ]


def _due_event(assignment, stamp):
    day = _parse_date(assignment.get("due_date"))
    if not day:
        return []

    name = str(assignment.get("name") or "Assignment").strip()
    course = str(assignment.get("course") or "").strip()
    details = [f"Course: {course}"] if course else []
    if assignment.get("description"):
        details.append(str(assignment["description"]))
    details.append("Added by StudyFlow AI")

    return [
        "BEGIN:VEVENT",
        f"UID:{_uid('due', name, course, assignment.get('due_date'))}",
        f"DTSTAMP:{stamp}",
        f"DTSTART;VALUE=DATE:{day:%Y%m%d}",
        f"DTEND;VALUE=DATE:{day + timedelta(days=1):%Y%m%d}",
        f"SUMMARY:{_escape(f'📌 Due: {name}' + (f' ({course})' if course else ''))}",
        f"DESCRIPTION:{_escape(chr(10).join(details))}",
        "TRANSP:TRANSPARENT",
        "END:VEVENT"
    ]


# ============================================================
# FILE AND LINKS
# ============================================================

def build_ics(sessions, assignments, zone_name, include_due_dates=True):
    stamp = _utc_stamp(datetime.now(timezone.utc))
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODUCT_ID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:StudyFlow Study Plan"
    ]

    for session in sessions or []:
        if isinstance(session, dict):
            lines.extend(_session_event(session, zone_name, stamp))

    if include_due_dates:
        for assignment in assignments or []:
            if isinstance(assignment, dict):
                lines.extend(_due_event(assignment, stamp))

    lines.append("END:VCALENDAR")

    folded = []
    for line in lines:
        folded.extend(_fold(line))
    return ("\r\n".join(folded) + "\r\n").encode("utf-8")


def count_events(sessions, assignments, include_due_dates=True):
    session_count = sum(
        1 for session in sessions or []
        if isinstance(session, dict) and session_times(session, None)[0]
    )
    due_count = sum(
        1 for assignment in assignments or []
        if isinstance(assignment, dict) and _parse_date(assignment.get("due_date"))
    ) if include_due_dates else 0
    return session_count, due_count


def google_calendar_link(session, zone_name):
    start_at, end_at = session_times(session, zone_name)
    if not start_at:
        return None

    query = urlencode({
        "action": "TEMPLATE",
        "text": session_title(session),
        "dates": f"{_utc_stamp(start_at)}/{_utc_stamp(end_at)}",
        "details": session_details(session)
    })
    return f"https://calendar.google.com/calendar/render?{query}"
