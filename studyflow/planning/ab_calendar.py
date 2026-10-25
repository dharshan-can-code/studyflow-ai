from datetime import date, timedelta


FIRST_DAY = date(2026, 8, 24)
LAST_DAY = date(2027, 6, 16)
SCHOOL_YEAR = "2026-27"


# ============================================================
# DAYS WITH NO SCHOOL FOR STUDENTS
# ============================================================

def _span(start, end, reason):
    days = {}
    day = start
    while day <= end:
        days[day] = reason
        day += timedelta(days=1)
    return days


NO_SCHOOL = {
    date(2026, 9, 4): "Labor Day break",
    date(2026, 9, 7): "Labor Day",
    date(2026, 9, 21): "Yom Kippur",
    date(2026, 10, 12): "Indigenous Peoples' Day",
    date(2026, 11, 2): "student holiday",
    date(2026, 11, 3): "Election Day",
    **_span(date(2026, 11, 25), date(2026, 11, 27), "Thanksgiving break"),
    **_span(date(2026, 12, 21), date(2027, 1, 1), "winter break"),
    date(2027, 1, 18): "Martin Luther King Jr. Day",
    date(2027, 1, 29): "student holiday",
    date(2027, 2, 1): "student holiday",
    date(2027, 2, 15): "Presidents' Day",
    date(2027, 3, 9): "Eid al-Fitr",
    **_span(date(2027, 3, 22), date(2027, 3, 26), "spring break"),
    date(2027, 4, 19): "student holiday",
    date(2027, 4, 20): "student holiday",
    date(2027, 5, 17): "Eid al-Adha",
    date(2027, 5, 31): "Memorial Day"
}

ALL_CLASSES_DAYS = {
    LAST_DAY: "last day of school, all classes meet"
}

EARLY_RELEASE = {
    date(2026, 10, 30): "2-hour early release, end of quarter 1",
    date(2027, 1, 28): "2-hour early release, end of quarter 2",
    date(2027, 4, 16): "2-hour early release, end of quarter 3",
    LAST_DAY: "2-hour early release"
}


# ============================================================
# A/B ROTATION
# ============================================================

def _build_rotation():
    rotation = {}
    letter = "A"
    day = FIRST_DAY
    while day <= LAST_DAY:
        if day.weekday() < 5 and day not in NO_SCHOOL:
            if day in ALL_CLASSES_DAYS:
                rotation[day] = "All"
            else:
                rotation[day] = letter
                letter = "B" if letter == "A" else "A"
        day += timedelta(days=1)
    return rotation


ROTATION = _build_rotation()


def in_school_year(day):
    return FIRST_DAY <= day <= LAST_DAY


def day_type(day):
    return ROTATION.get(day)


def short_label(day):
    kind = day_type(day)
    if kind == "All":
        return "All classes"
    if kind:
        return f"{kind} day"
    return ""


def describe_day(day):
    kind = day_type(day)
    if kind is None:
        return f"no school, {NO_SCHOOL[day]}" if day in NO_SCHOOL else "no school"
    text = ALL_CLASSES_DAYS[day] if kind == "All" else f"{kind} day"
    if day in EARLY_RELEASE:
        text += f", {EARLY_RELEASE[day]}"
    return text
