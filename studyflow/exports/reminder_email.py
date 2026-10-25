import html
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from zoneinfo import ZoneInfo

from studyflow.planning import ab_calendar


DEFAULT_ZONE = "America/New_York"
DEFAULT_TIME = "07:00"
DUE_SOON_DAYS = 3
GMAIL_HOST = "smtp.gmail.com"
GMAIL_PORT = 465


# ============================================================
# TIME HELPERS
# ============================================================

def reminder_time(reminders):
    value = str(reminders.get("time") or "").strip()
    try:
        moment = datetime.strptime(value[:5], "%H:%M")
        return f"{moment.hour:02d}:{moment.minute:02d}"
    except ValueError:
        pass
    try:
        return f"{int(reminders.get('hour', 7)) % 24:02d}:00"
    except (TypeError, ValueError):
        return DEFAULT_TIME


def minutes_of_day(value):
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def clock_label(value):
    try:
        moment = datetime.strptime(str(value).strip()[:5], "%H:%M")
    except ValueError:
        return str(value or "")
    shown = moment.hour % 12 or 12
    return f"{shown}:{moment.minute:02d} {'AM' if moment.hour < 12 else 'PM'}"


def student_today(student):
    zone_name = (student.get("profile") or {}).get("timezone") or DEFAULT_ZONE
    try:
        zone = ZoneInfo(zone_name)
    except Exception:
        zone = ZoneInfo(DEFAULT_ZONE)
    return datetime.now(zone)


def _parse_day(value):
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _day_note(day, profile):
    if not profile.get("ab_calendar", True) or day.weekday() >= 5:
        return ""
    return ab_calendar.describe_day(day)


# ============================================================
# BUILD THE EMAIL
# ============================================================

def todays_summary(student, today):
    profile = student.get("profile") or {}
    plan = student.get("study_plan") or {}

    sessions = [
        session for session in plan.get("study_sessions", [])
        if isinstance(session, dict) and session.get("date") == today.isoformat()
    ]
    sessions.sort(key=lambda session: str(session.get("start_time")))

    due_soon = []
    for assignment in student.get("assignments") or []:
        if not isinstance(assignment, dict):
            continue
        due = _parse_day(assignment.get("due_date"))
        if due and today <= due <= today + timedelta(days=DUE_SOON_DAYS):
            due_soon.append((due, assignment))
    due_soon.sort(key=lambda item: item[0])

    return {
        "name": (profile.get("name") or "").split(" ")[0],
        "day_note": _day_note(today, profile),
        "sessions": sessions,
        "due_soon": due_soon
    }


def _due_label(due, today):
    if due == today:
        return "today"
    if due == today + timedelta(days=1):
        return "tomorrow"
    return f"{due:%A}"


def build_email(student, today, app_url, unsubscribe_url):
    summary = todays_summary(student, today)
    sessions = summary["sessions"]
    due_soon = summary["due_soon"]

    if not sessions and not due_soon:
        return None

    parts = []
    if sessions:
        parts.append(f"{len(sessions)} study session{'s' if len(sessions) != 1 else ''} today")
    if due_soon:
        first_due, first = due_soon[0]
        parts.append(f"{first.get('name') or 'Assignment'} due {_due_label(first_due, today)}")
    subject = "StudyFlow: " + " · ".join(parts)

    greeting = f"Hi {summary['name']}," if summary["name"] else "Hi,"
    date_line = f"{today:%A, %B} {today.day}" + (f" ({summary['day_note']})" if summary["day_note"] else "")

    text = [greeting, "", f"Here's your plan for {date_line}.", ""]
    rows_html = []

    if sessions:
        text.append("TODAY'S STUDY SESSIONS")
        for session in sessions:
            time_range = f"{clock_label(session.get('start_time'))} - {clock_label(session.get('end_time'))}"
            title = " · ".join(part for part in (session.get("course"), session.get("assignment")) if part)
            task = session.get("task") or ""
            text.append(f"- {time_range}: {title}")
            if task:
                text.append(f"  {task}")
            rows_html.append(
                "<tr>"
                f"<td style='padding:8px 12px;color:#0F766E;white-space:nowrap;vertical-align:top'>{html.escape(time_range)}</td>"
                f"<td style='padding:8px 12px'><strong>{html.escape(title)}</strong>"
                + (f"<br><span style='color:#475569'>{html.escape(task)}</span>" if task else "")
                + "</td></tr>"
            )
        text.append("")

    due_html = []
    if due_soon:
        text.append("COMING UP")
        for due, assignment in due_soon:
            name = assignment.get("name") or "Assignment"
            course = assignment.get("course") or ""
            line = f"{name}" + (f" ({course})" if course else "") + f", due {_due_label(due, today)}"
            text.append(f"- {line}")
            due_html.append(f"<li style='margin-bottom:4px'>{html.escape(line)}</li>")
        text.append("")

    text += [
        f"Open StudyFlow: {app_url}",
        "",
        "You're getting this because you turned on daily reminders in StudyFlow AI.",
        f"Turn off reminders: {unsubscribe_url}"
    ]

    body_html = (
        "<div style='font-family:Arial,Helvetica,sans-serif;max-width:560px;margin:0 auto;color:#0F172A'>"
        "<h2 style='color:#0F766E;margin-bottom:4px'>StudyFlow AI</h2>"
        f"<p style='margin-top:0'>{html.escape(greeting)}<br>Here's your plan for <strong>{html.escape(date_line)}</strong>.</p>"
    )
    if rows_html:
        body_html += (
            "<h3 style='margin-bottom:4px'>Today's study sessions</h3>"
            "<table style='border-collapse:collapse;width:100%;background:#F0FDFA;border-radius:8px'>"
            + "".join(rows_html)
            + "</table>"
        )
    if due_html:
        body_html += "<h3 style='margin-bottom:4px'>Coming up</h3><ul style='padding-left:20px'>" + "".join(due_html) + "</ul>"
    body_html += (
        f"<p><a href='{html.escape(app_url)}' style='background:#0F766E;color:#FFFFFF;padding:10px 16px;"
        "border-radius:8px;text-decoration:none;display:inline-block'>Open StudyFlow</a></p>"
        "<p style='font-size:12px;color:#64748B'>You're getting this because you turned on daily reminders in StudyFlow AI. "
        f"<a href='{html.escape(unsubscribe_url)}' style='color:#64748B'>Turn off reminders</a></p>"
        "</div>"
    )

    return subject, "\n".join(text), body_html


def unsubscribe_link(app_url, token):
    return f"{app_url.rstrip('/')}/?unsubscribe={token}"


# ============================================================
# SEND
# ============================================================

def send_email(sender, app_password, to, subject, text, body_html, unsubscribe_url=None):
    message = EmailMessage()
    message["From"] = f"StudyFlow AI <{sender}>"
    message["To"] = to
    message["Subject"] = subject
    if unsubscribe_url:
        message["List-Unsubscribe"] = f"<{unsubscribe_url}>"
    message.set_content(text)
    message.add_alternative(body_html, subtype="html")

    with smtplib.SMTP_SSL(GMAIL_HOST, GMAIL_PORT, timeout=30) as server:
        server.login(sender, app_password.replace(" ", ""))
        server.send_message(message)
