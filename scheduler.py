from datetime import datetime, timedelta


DAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
PRIORITY_RANK = {"High": 0, "Medium": 1, "Low": 2}
PEAK_HOURS = {
    "Morning": (6 * 60, 12 * 60),
    "Afternoon": (12 * 60, 17 * 60),
    "Evening": (17 * 60, 21 * 60),
    "Night": (21 * 60, 24 * 60)
}
DINNER_MINUTES = 45
BEDTIME_BUFFER = 30
SLOT_STEP = 15
MIN_CHUNK = 15
MAX_SESSION = 90
WEEKEND_START = 10 * 60
UNDATED_DAYS = 14


# ============================================================
# TIME HELPERS
# ============================================================

def _minutes(value, default=None):
    try:
        hours, minutes = str(value).split(":")[:2]
        return int(hours) * 60 + int(minutes)
    except (ValueError, TypeError, AttributeError):
        return default


def _clock(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _round_up(minutes):
    return -(-minutes // SLOT_STEP) * SLOT_STEP


def _parse_day(value):
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _number(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ============================================================
# DAYS AND FREE TIME
# ============================================================

def _day_window(day, is_school_day, style):
    wake = _minutes(style.get("wake"), 7 * 60)
    bed = _minutes(style.get("bed"), 22 * 60 + 30)
    if bed <= wake:
        bed = 24 * 60
    end = min(bed - BEDTIME_BUFFER, 24 * 60 - 1)

    if is_school_day(day):
        start = _minutes(style.get("homework_start"), 16 * 60)
    else:
        start = max(WEEKEND_START, wake + 60)

    return start, end


def _blocked(day, style, activities):
    blocks = []
    dinner = _minutes(style.get("dinner"))
    if dinner is not None:
        blocks.append((dinner, dinner + DINNER_MINUTES))

    weekday = DAY_SHORT[day.weekday()]
    for activity in activities or []:
        if weekday not in (activity.get("days") or []):
            continue
        start = _minutes(activity.get("start"))
        end = _minutes(activity.get("end"))
        if start is not None and end is not None and end > start:
            blocks.append((start, end))

    return blocks


def _day_capacity(day, is_school_day, style):
    max_per_day = max(15, _number(style.get("max_per_day"), 180))
    weekday = day.weekday()

    if not is_school_day(day) and not style.get("weekends", True):
        return 0
    if weekday == 6 and style.get("sunday_catchup"):
        return 0
    if weekday == 4 and style.get("lighter_fridays", True):
        return max_per_day // 2
    return max_per_day


def _free_slot(day_plan, length, style, prefer=None):
    gap = day_plan["break"]
    taken = day_plan["blocked"] + [(item["start"] - gap, item["end"] + gap) for item in day_plan["sessions"]]
    candidates = []
    start = day_plan["start"]

    while start + length <= day_plan["end"]:
        clash = next((block for block in taken if start < block[1] and start + length > block[0]), None)
        if clash:
            start = _round_up(clash[1])
            continue
        candidates.append(start)
        start += SLOT_STEP

    if not candidates:
        return None
    if prefer:
        low, high = prefer
        preferred = [slot for slot in candidates if low <= slot < high]
        if preferred:
            return preferred[0]
    return candidates[0]


# ============================================================
# SPLITTING WORK INTO SESSIONS
# ============================================================

def _chunks(total, session_length):
    session_length = max(MIN_CHUNK, min(MAX_SESSION, session_length))
    total = max(MIN_CHUNK, total)
    count = -(-total // session_length)
    size = max(MIN_CHUNK, _round_to_five(total / count))
    pieces = [size] * count
    pieces[-1] = max(MIN_CHUNK, total - size * (count - 1))
    return pieces


def _round_to_five(value):
    return int(round(value / 5.0)) * 5


def _target_index(index, count, window_size, test):
    if window_size <= 1:
        return 0
    if count == 1:
        return window_size - 1 if test else 0
    return round(index * (window_size - 1) / (count - 1))


def _sorted_assignments(assignments, today):
    def key(item):
        due = _parse_day(item.get("due_date")) or today + timedelta(days=UNDATED_DAYS)
        return (
            due,
            PRIORITY_RANK.get(item.get("priority"), 1),
            -_number(item.get("difficulty"), 3)
        )
    return sorted(assignments, key=key)


# ============================================================
# BUILD THE PLAN
# ============================================================

def build_plan(assignments, style, activities, now, is_school_day):
    today = now.date()
    now_minutes = now.hour * 60 + now.minute
    session_length = _number(style.get("session_length"), 45)
    break_length = max(0, _number(style.get("break_length"), 10))
    peak = PEAK_HOURS.get(style.get("peak"))
    hardest = str(style.get("hardest") or "").strip().lower()

    days = {}

    def day_plan(day):
        if day not in days:
            start, end = _day_window(day, is_school_day, style)
            if day == today:
                start = max(start, _round_up(now_minutes + 15))
            days[day] = {
                "start": start,
                "end": end,
                "blocked": _blocked(day, style, activities),
                "capacity": _day_capacity(day, is_school_day, style),
                "used": 0,
                "break": break_length,
                "sessions": []
            }
        return days[day]

    sessions = []
    unscheduled = []

    for assignment in _sorted_assignments(assignments, today):
        due = _parse_day(assignment.get("due_date"))
        last_day = (due - timedelta(days=1)) if due else today + timedelta(days=UNDATED_DAYS)
        name = assignment.get("name") or "Assignment"
        course = assignment.get("course") or ""

        if last_day < today:
            unscheduled.append({"assignment": name, "minutes": _number(assignment.get("estimated_minutes"), 60), "reason": "due today or already past"})
            continue

        pieces = _chunks(_number(assignment.get("estimated_minutes"), 60), session_length)
        full_window = [today + timedelta(days=offset) for offset in range((last_day - today).days + 1)]
        hard = _number(assignment.get("difficulty"), 3) >= 4 or bool(
            hardest and course and (hardest in course.lower() or course.lower() in hardest)
        )
        test = is_test(name)
        placed = []

        def place(pieces, window):
            for per_day_limit in range(1, 5):
                if not pieces:
                    break
                remaining = []
                for index, length in enumerate(pieces):
                    target = _target_index(index, len(pieces), len(window), test)
                    order = sorted(range(len(window)), key=lambda i: (abs(i - target), i))
                    for position in order:
                        day = window[position]
                        plan = day_plan(day)
                        if sum(1 for item in placed if item["day"] == day) >= per_day_limit:
                            continue
                        if plan["used"] + length > plan["capacity"]:
                            continue
                        start = _free_slot(plan, length, style, peak if hard else None)
                        if start is None:
                            continue
                        session = {"day": day, "start": start, "end": start + length, "minutes": length}
                        plan["sessions"].append(session)
                        plan["used"] += length
                        placed.append(session)
                        break
                    else:
                        remaining.append(length)
                pieces = remaining
            return pieces

        pieces = place(pieces, full_window[-max(len(pieces) * 2, 7):])
        pieces = place(pieces, full_window)
        for smaller in (30, MIN_CHUNK):
            if pieces:
                pieces = place(_chunks(sum(pieces), smaller), full_window)

        if pieces:
            unscheduled.append({"assignment": name, "minutes": sum(pieces), "reason": "not enough free time left before it's due"})

        placed.sort(key=lambda item: (item["day"], item["start"]))
        for index, session in enumerate(placed, start=1):
            sessions.append({
                "date": session["day"].isoformat(),
                "start_time": _clock(session["start"]),
                "end_time": _clock(session["end"]),
                "course": course,
                "assignment": name,
                "task": "",
                "minutes": session["minutes"],
                "part": index,
                "parts": len(placed),
                "description": assignment.get("description") or "",
                "due_date": assignment.get("due_date") or ""
            })

    sessions.sort(key=lambda item: (item["date"], item["start_time"]))
    return sessions, unscheduled


# ============================================================
# DEFAULT TASKS
# ============================================================

TEST_WORDS = {"test", "tests", "quiz", "quizzes", "exam", "exams", "final", "finals", "midterm", "sol", "sols"}


def is_test(name):
    words = "".join(ch if ch.isalnum() else " " for ch in str(name or "").lower()).split()
    return any(word in TEST_WORDS for word in words)


def default_task(session):
    part = session.get("part", 1)
    parts = session.get("parts", 1)

    if is_test(session.get("assignment")):
        if parts == 1:
            return "Review your notes, then do practice questions and check your answers"
        if part == 1:
            return "Go through your notes and make a list of topics you're unsure about"
        if part == parts:
            return "Final review: quiz yourself on every topic and redo missed questions"
        return "Do practice problems on your weakest topics and check every answer"

    if parts == 1:
        return "Read the instructions, do the work, and check it before you finish"
    if part == 1:
        return "Read the instructions carefully and plan or outline your work"
    if part == parts:
        return "Finish the remaining work, then proofread and check everything"
    return "Keep working through the main part of the assignment"


def public_session(session):
    return {
        key: session[key]
        for key in ("date", "start_time", "end_time", "course", "assignment", "task", "minutes")
    }
