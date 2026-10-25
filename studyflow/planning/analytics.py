from datetime import datetime, timedelta


DIFFICULTY_LABELS = {
    1: "Very easy",
    2: "Easy",
    3: "Medium",
    4: "Hard",
    5: "Very hard"
}


# ============================================================
# HELPERS
# ============================================================

def _day(value):
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _minutes(session):
    try:
        return max(0, int(session.get("minutes") or 0))
    except (TypeError, ValueError):
        return 0


def _finished_day(session):
    return _day(session.get("done_on")) or _day(session.get("date"))


def pretty_minutes(minutes):
    hours, minutes = divmod(int(minutes), 60)
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes} min"


# ============================================================
# STUDY SESSIONS
# ============================================================

def totals(sessions):
    done = [session for session in sessions if session.get("done")]
    return {
        "done": len(done),
        "total": len(sessions),
        "done_minutes": sum(_minutes(session) for session in done),
        "total_minutes": sum(_minutes(session) for session in sessions)
    }


def average_minutes(sessions):
    if not sessions:
        return 0
    return round(sum(_minutes(session) for session in sessions) / len(sessions))


def course_load(sessions, course_names=()):
    courses = {}

    def row(name):
        return courses.setdefault(name, {
            "course": name,
            "done": 0,
            "total": 0,
            "done_minutes": 0,
            "total_minutes": 0
        })

    for name in course_names:
        row(name)

    for session in sessions:
        course = row(session.get("course") or "General")
        minutes = _minutes(session)
        course["total"] += 1
        course["total_minutes"] += minutes
        if session.get("done"):
            course["done"] += 1
            course["done_minutes"] += minutes

    return sorted(courses.values(), key=lambda course: (-course["total"], course["course"]))


def streak(sessions, today):
    days = {_finished_day(session) for session in sessions if session.get("done")}
    days.discard(None)

    day = today if today in days else today - timedelta(days=1)
    count = 0
    while day in days:
        count += 1
        day -= timedelta(days=1)
    return count


def missed(sessions, today):
    return [
        session for session in sessions
        if not session.get("done") and (_day(session.get("date")) or today) < today
    ]


def minutes_by_day(sessions, today, days=7):
    """Minutes checked off on each of the last `days` days, ending today."""
    start = today - timedelta(days=days - 1)
    rows = {start + timedelta(days=offset): 0 for offset in range(days)}
    for session in sessions:
        day = _finished_day(session)
        if session.get("done") and day in rows:
            rows[day] += _minutes(session)
    return [{"day": day, "minutes": minutes} for day, minutes in rows.items()]


# ============================================================
# ASSIGNMENTS
# ============================================================

def assignments_by_subject(assignments):
    counts = {}
    for assignment in assignments:
        course = assignment.get("course") or "General"
        counts[course] = counts.get(course, 0) + 1
    return sorted(
        ({"course": course, "count": count} for course, count in counts.items()),
        key=lambda row: (-row["count"], row["course"])
    )


def difficulty_breakdown(assignments):
    counts = {level: 0 for level in DIFFICULTY_LABELS}
    for assignment in assignments:
        try:
            level = min(5, max(1, int(assignment.get("difficulty") or 3)))
        except (TypeError, ValueError):
            level = 3
        counts[level] += 1
    return [
        {"level": level, "label": f"{level} · {DIFFICULTY_LABELS[level]}", "count": count}
        for level, count in counts.items()
    ]


def upcoming_deadlines(assignments, today, days=7):
    upcoming = []
    for assignment in assignments:
        due = _day(assignment.get("due_date"))
        if due is not None and today <= due <= today + timedelta(days=days):
            upcoming.append({**assignment, "days_left": (due - today).days})
    return sorted(upcoming, key=lambda assignment: (assignment["days_left"], assignment.get("name", "")))
