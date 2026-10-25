import re
import uuid
from datetime import time

import streamlit as st

import fcps_courses


DAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

DAY_FULL = {
    "Monday": "Mon",
    "Tuesday": "Tue",
    "Wednesday": "Wed",
    "Thursday": "Thu",
    "Friday": "Fri",
    "Saturday": "Sat",
    "Sunday": "Sun"
}

GRADES = ["7th", "8th", "9th", "10th", "11th", "12th"]

OLD_GRADE_NAMES = {
    "Freshman": "9th",
    "Sophomore": "10th",
    "Junior": "11th",
    "Senior": "12th"
}

BLOCK_DAYS = ["A day", "B day"]

TIME_ZONES = {
    "Eastern (New York)": "America/New_York",
    "Central (Chicago)": "America/Chicago",
    "Mountain (Denver)": "America/Denver",
    "Arizona (Phoenix)": "America/Phoenix",
    "Pacific (Los Angeles)": "America/Los_Angeles",
    "Alaska (Anchorage)": "America/Anchorage",
    "Hawaii (Honolulu)": "Pacific/Honolulu"
}

FCPS_SCHOOLS = [
    "Annandale High School",
    "Centreville High School",
    "Chantilly High School",
    "Edison High School",
    "Fairfax High School",
    "Falls Church High School",
    "Herndon High School",
    "John R. Lewis High School",
    "Justice High School",
    "Langley High School",
    "Madison High School",
    "Marshall High School",
    "McLean High School",
    "Mount Vernon High School",
    "Oakton High School",
    "Skyview High School",
    "South County High School",
    "South Lakes High School",
    "Thomas Jefferson High School for Science and Technology",
    "West Potomac High School",
    "West Springfield High School",
    "Westfield High School",
    "Woodson High School",
    "Hayfield Secondary School",
    "Lake Braddock Secondary School",
    "Robinson Secondary School",
    "Bryant High School",
    "Mountain View High School",
    "Carson Middle School",
    "Cooper Middle School",
    "Franklin Middle School",
    "Frost Middle School",
    "Glasgow Middle School",
    "Herndon Middle School",
    "Holmes Middle School",
    "Hughes Middle School",
    "Irving Middle School",
    "Jackson Middle School",
    "Katherine Johnson Middle School",
    "Key Middle School",
    "Kilmer Middle School",
    "Liberty Middle School",
    "Longfellow Middle School",
    "Poe Middle School",
    "Rocky Run Middle School",
    "Sandburg Middle School",
    "South County Middle School",
    "Stone Middle School",
    "Thoreau Middle School",
    "Twain Middle School",
    "Whitman Middle School"
]

STUDY_STYLES = ["Short sessions", "Long focused blocks", "A mix of both"]

PEAK_TIMES = ["Morning", "Afternoon", "Evening", "Night"]

DEFAULT_PROFILE = {
    "name": "",
    "grade": "9th",
    "school": "",
    "timezone": "America/New_York",
    "region": "Virginia",
    "ab_calendar": True,
    "onboarded": False
}

DEFAULT_STUDY_STYLE = {
    "wake": "07:00",
    "bed": "22:30",
    "dinner": "18:00",
    "homework_start": "16:00",
    "weekends": True,
    "lighter_fridays": True,
    "sunday_catchup": False,
    "session_length": 45,
    "max_per_day": 180,
    "break_length": 10,
    "pomodoro": 25,
    "style": "Short sessions",
    "peak": "Evening",
    "hardest": "",
    "favorite": ""
}

SETUP_PREFIXES = ("setup_", "settings_")

REGIONS = [
    "Alabama",
    "Alaska",
    "American Samoa",
    "Arizona",
    "Arkansas",
    "California",
    "Colorado",
    "Connecticut",
    "Delaware",
    "District of Columbia",
    "Florida",
    "Georgia",
    "Guam",
    "Hawaii",
    "Idaho",
    "Illinois",
    "Indiana",
    "Iowa",
    "Kansas",
    "Kentucky",
    "Louisiana",
    "Maine",
    "Maryland",
    "Massachusetts",
    "Michigan",
    "Minnesota",
    "Mississippi",
    "Missouri",
    "Montana",
    "Nebraska",
    "Nevada",
    "New Hampshire",
    "New Jersey",
    "New Mexico",
    "New York",
    "North Carolina",
    "North Dakota",
    "Northern Mariana Islands",
    "Ohio",
    "Oklahoma",
    "Oregon",
    "Pennsylvania",
    "Puerto Rico",
    "Rhode Island",
    "South Carolina",
    "South Dakota",
    "Tennessee",
    "Texas",
    "U.S. Virgin Islands",
    "Utah",
    "Vermont",
    "Virginia",
    "Washington",
    "West Virginia",
    "Wisconsin",
    "Wyoming",
]


# ============================================================
# TIME HELPERS
# ============================================================

def to_time(value):
    if isinstance(value, time):
        return value
    if not value:
        return None
    try:
        hours, minutes = str(value).split(":")[:2]
        return time(int(hours), int(minutes))
    except (ValueError, TypeError):
        return None


def from_time(value):
    return value.strftime("%H:%M") if value else None


def pretty_time(value):
    value = to_time(value)
    if value is None:
        return "not set"
    hour = value.hour % 12 or 12
    suffix = "AM" if value.hour < 12 else "PM"
    return f"{hour}:{value.minute:02d} {suffix}"


def _parse_clock(text):
    match = re.match(r"\s*(\d{1,2})(?::(\d{2}))?\s*([ap]\.?m\.?)?", text or "", re.I)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    meridiem = (match.group(3) or "").lower()
    if meridiem.startswith("p") and hour < 12:
        hour += 12
    if meridiem.startswith("a") and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        return None
    return f"{hour:02d}:{minute:02d}"


def _parse_range(text):
    parts = re.split(r"\s*(?:-|–|to)\s*", text or "", maxsplit=1)
    if len(parts) != 2:
        return None, None
    return _parse_clock(parts[0]), _parse_clock(parts[1])


# ============================================================
# SAVED DATA
# ============================================================

def new_id():
    return uuid.uuid4().hex[:8]


def new_course(name=""):
    return {
        "id": new_id(),
        "name": name,
        "teacher": "",
        "blocks": []
    }


def new_activity():
    return {
        "id": new_id(),
        "name": "",
        "start": "15:30",
        "end": "17:00",
        "location": "",
        "days": []
    }


def normalize_courses(courses):
    cleaned = []
    for course in courses or []:
        if isinstance(course, str):
            course = new_course(course)
        elif isinstance(course, dict):
            course = {**new_course(), **course}
            course["id"] = course.get("id") or new_id()
        else:
            continue
        for old_field in ("start", "end", "days", "room"):
            course.pop(old_field, None)
        course["blocks"] = [block for block in course.get("blocks") or [] if block in ("A", "B")]
        cleaned.append(course)
    return cleaned


def normalize_activities(activities):
    cleaned = []
    for activity in activities or []:
        if not isinstance(activity, dict):
            continue
        result = {**new_activity(), **activity}
        result["id"] = activity.get("id") or new_id()

        if "day" in activity and "days" not in activity:
            day = DAY_FULL.get(activity.get("day"), activity.get("day"))
            result["days"] = [day] if day in DAY_SHORT else []
            start, end = _parse_range(activity.get("time", ""))
            result["start"], result["end"] = start, end

        result.pop("day", None)
        result.pop("time", None)
        result["days"] = [day for day in result.get("days") or [] if day in DAY_SHORT]
        cleaned.append(result)
    return cleaned


def complete_profile(profile):
    profile = {**DEFAULT_PROFILE, **(profile or {})}
    profile["grade"] = OLD_GRADE_NAMES.get(profile["grade"], profile["grade"])
    return profile


def complete_study_style(study_style):
    return {**DEFAULT_STUDY_STYLE, **(study_style or {})}


def reset_form_state():
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith(SETUP_PREFIXES):
            del st.session_state[key]


# ============================================================
# FORM HELPERS
# ============================================================

def _index(options, value, default=0):
    return options.index(value) if value in options else default


def _number(value, default, low, high):
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(low, min(high, number))


def _current_name(prefix, course):
    typed = st.session_state.get(f"{prefix}_course_{course['id']}_name")
    return (typed if typed is not None else course["name"]).strip().lower()


def _timezone_label(zone):
    for label, value in TIME_ZONES.items():
        if value == zone:
            return label
    return "Eastern (New York)"


# ============================================================
# PROFILE
# ============================================================

def profile_form(prefix, profile, suggested_name=""):
    profile = complete_profile(profile)

    name = st.text_input(
        "Name",
        value=profile["name"] or suggested_name,
        placeholder="Your name",
        key=f"{prefix}_profile_name"
    )

    grade_column, school_column = st.columns(2)

    with grade_column:
        grade = st.selectbox(
            "Grade",
            GRADES,
            index=_index(GRADES, profile["grade"]),
            key=f"{prefix}_profile_grade"
        )

    with school_column:
        schools = list(FCPS_SCHOOLS)
        if profile["school"] and profile["school"] not in schools:
            schools.append(profile["school"])

        school = st.selectbox(
            "School",
            schools,
            index=schools.index(profile["school"]) if profile["school"] in schools else None,
            placeholder="Choose or type your school",
            accept_new_options=True,
            key=f"{prefix}_profile_school"
        )

    zone_labels = list(TIME_ZONES)
    zone_label = st.selectbox(
        "Time zone",
        zone_labels,
        index=_index(zone_labels, _timezone_label(profile["timezone"])),
        key=f"{prefix}_profile_timezone"
    )

    region = st.selectbox(
        "Region",
        REGIONS,
        index=REGIONS.index('Virginia'),
        key=f"{prefix}_profile_region"
    )

    st.caption("Region data is used to determine school curriculum and not for any other purpose.")

    ab_calendar = st.toggle(
        "My school follows the FCPS A/B day calendar",
        value=bool(profile["ab_calendar"]),
        key=f"{prefix}_profile_ab"
    )

    st.caption("Course suggestions and A/B days are based on Fairfax County Public Schools (FCPS).")

    return {
        **profile,
        "name": name.strip(),
        "grade": grade,
        "school": (school or "").strip(),
        "timezone": TIME_ZONES[zone_label],
        "region": region,
        "ab_calendar": ab_calendar
    }


# ============================================================
# COURSES
# ============================================================

def _courses_draft(prefix, courses):
    draft_key = f"{prefix}_courses_draft"
    if draft_key not in st.session_state:
        st.session_state[draft_key] = [dict(course) for course in normalize_courses(courses)]
    return draft_key


def _quick_add_course(prefix):
    pick_key = f"{prefix}_courses_quick"
    name = st.session_state.get(pick_key)
    draft = st.session_state[f"{prefix}_courses_draft"]

    if name and name.lower() not in {_current_name(prefix, course) for course in draft}:
        draft.append(new_course(name))

    st.session_state[pick_key] = None


def _remove(prefix, kind, item_id):
    draft_key = f"{prefix}_{kind}_draft"
    st.session_state[draft_key] = [
        item for item in st.session_state[draft_key] if item["id"] != item_id
    ]


def _add_blank(prefix, kind):
    draft_key = f"{prefix}_{kind}_draft"
    blank = new_course() if kind == "courses" else new_activity()
    st.session_state[draft_key].append(blank)


def courses_editor(prefix, courses, grade=None):
    draft_key = _courses_draft(prefix, courses)
    draft = st.session_state[draft_key]

    catalog = fcps_courses.for_grade(grade)
    level = fcps_courses.level_for_grade(grade)
    taken = {_current_name(prefix, course) for course in draft}
    remaining = [name for name in catalog if name.lower() not in taken]

    st.selectbox(
        "Add a course",
        remaining,
        index=None,
        placeholder=f"Search {len(catalog)} FCPS {level + ' ' if level else ''}courses",
        format_func=lambda name: f"{name}  ·  {catalog[name]}",
        key=f"{prefix}_courses_quick",
        on_change=_quick_add_course,
        args=(prefix,)
    )

    st.caption("Not on the list? Use :material/add: Add a course below and type it in.")

    if draft:
        st.caption("For each course, pick A day, B day, or both if it meets every day.")

    updated = []

    for course in draft:
        course_id = course["id"]
        base = f"{prefix}_course_{course_id}"

        with st.container(border=True):
            name_column, teacher_column, delete_column = st.columns(
                [5, 5, 1],
                vertical_alignment="bottom"
            )

            with name_column:
                name = st.text_input(
                    "Course name",
                    value=course["name"],
                    placeholder="e.g. Biology 1",
                    key=f"{base}_name"
                )

            with teacher_column:
                teacher = st.text_input(
                    "Teacher (optional)",
                    value=course.get("teacher", ""),
                    key=f"{base}_teacher"
                )

            with delete_column:
                st.button(
                    ":material/delete:",
                    key=f"{base}_delete",
                    help="Remove this course",
                    on_click=_remove,
                    args=(prefix, "courses", course_id)
                )

            blocks = st.pills(
                "Meets on",
                BLOCK_DAYS,
                selection_mode="multi",
                default=[f"{block} day" for block in course.get("blocks", [])],
                key=f"{base}_blocks"
            )

        updated.append({
            "id": course_id,
            "name": name.strip(),
            "teacher": teacher.strip(),
            "blocks": [label[0] for label in BLOCK_DAYS if label in (blocks or [])]
        })

    st.button(
        ":material/add: Add a course",
        key=f"{prefix}_courses_add",
        on_click=_add_blank,
        args=(prefix, "courses")
    )

    return updated


# ============================================================
# ACTIVITIES
# ============================================================

def activities_editor(prefix, activities):
    draft_key = f"{prefix}_activities_draft"
    if draft_key not in st.session_state:
        st.session_state[draft_key] = [dict(item) for item in normalize_activities(activities)]
    draft = st.session_state[draft_key]

    if not draft:
        st.caption("No activities yet. Add sports, clubs, a job, or anything else that takes up time.")

    updated = []

    for activity in draft:
        activity_id = activity["id"]
        base = f"{prefix}_activity_{activity_id}"

        with st.container(border=True):
            name_column, delete_column = st.columns([10, 1], vertical_alignment="bottom")

            with name_column:
                name = st.text_input(
                    "Activity name",
                    value=activity["name"],
                    placeholder="e.g. Soccer practice",
                    key=f"{base}_name"
                )

            with delete_column:
                st.button(
                    ":material/delete:",
                    key=f"{base}_delete",
                    help="Remove this activity",
                    on_click=_remove,
                    args=(prefix, "activities", activity_id)
                )

            start_column, end_column, location_column = st.columns(3)

            with start_column:
                start = st.time_input(
                    "Starts",
                    value=to_time(activity.get("start")),
                    step=300,
                    format="12h",
                    key=f"{base}_start"
                )

            with end_column:
                end = st.time_input(
                    "Ends",
                    value=to_time(activity.get("end")),
                    step=300,
                    format="12h",
                    key=f"{base}_end"
                )

            with location_column:
                location = st.text_input(
                    "Location (optional)",
                    value=activity.get("location", ""),
                    key=f"{base}_location"
                )

            days = st.pills(
                "Days",
                DAY_SHORT,
                selection_mode="multi",
                default=activity.get("days", []),
                key=f"{base}_days"
            )

            if name.strip() and start and end and end <= start:
                st.caption(":material/warning: The end time is before the start time.")
            elif name.strip() and not days:
                st.caption(":material/warning: Pick at least one day so your plan can work around it.")

        updated.append({
            "id": activity_id,
            "name": name.strip(),
            "start": from_time(start),
            "end": from_time(end),
            "location": location.strip(),
            "days": [day for day in DAY_SHORT if day in (days or [])]
        })

    st.button(
        ":material/add: Add an activity",
        key=f"{prefix}_activities_add",
        on_click=_add_blank,
        args=(prefix, "activities")
    )

    return updated


# ============================================================
# DAILY ROUTINE
# ============================================================

def routine_form(prefix, study_style):
    style = complete_study_style(study_style)

    wake_column, bed_column = st.columns(2)

    with wake_column:
        wake = st.time_input("Wake up", value=to_time(style["wake"]), step=300, format="12h", key=f"{prefix}_routine_wake")

    with bed_column:
        bed = st.time_input("Bedtime", value=to_time(style["bed"]), step=300, format="12h", key=f"{prefix}_routine_bed")

    dinner_column, homework_column = st.columns(2)

    with dinner_column:
        dinner = st.time_input("Dinner", value=to_time(style["dinner"]), step=300, format="12h", key=f"{prefix}_routine_dinner")

    with homework_column:
        homework = st.time_input(
            "Homework start",
            value=to_time(style["homework_start"]),
            step=300,
            format="12h",
            key=f"{prefix}_routine_homework"
        )

    if homework and bed and wake and wake < bed <= homework:
        st.caption(":material/warning: Homework starts after bedtime, so there's no time left to study on school days.")

    weekends = st.toggle("Use weekends for study", value=style["weekends"], key=f"{prefix}_routine_weekends")
    lighter = st.toggle("Lighter Fridays", value=style["lighter_fridays"], key=f"{prefix}_routine_fridays")
    catchup = st.toggle("Sunday catch-up day", value=style["sunday_catchup"], key=f"{prefix}_routine_sunday")

    return {
        "wake": from_time(wake),
        "bed": from_time(bed),
        "dinner": from_time(dinner),
        "homework_start": from_time(homework),
        "weekends": weekends,
        "lighter_fridays": lighter,
        "sunday_catchup": catchup
    }


# ============================================================
# STUDY PREFERENCES
# ============================================================

def _subject_picker(label, value, options, placeholder, key):
    choices = list(options)
    if value and value not in choices:
        choices.append(value)
    picked = st.selectbox(
        label,
        choices,
        index=choices.index(value) if value in choices else None,
        placeholder=placeholder,
        accept_new_options=True,
        key=key
    )
    return (picked or "").strip()


def preferences_form(prefix, study_style, courses=None):
    style = complete_study_style(study_style)

    session_column, max_column = st.columns(2)

    with session_column:
        session_length = st.number_input(
            "Session length (min)",
            min_value=10,
            max_value=90,
            step=5,
            value=_number(style["session_length"], 45, 10, 90),
            key=f"{prefix}_prefs_session"
        )

    with max_column:
        max_per_day = st.number_input(
            "Max study per day (min)",
            min_value=30,
            max_value=600,
            step=15,
            value=_number(style["max_per_day"], 180, 30, 600),
            key=f"{prefix}_prefs_max"
        )

    break_column, pomodoro_column = st.columns(2)

    with break_column:
        break_length = st.number_input(
            "Break length (min)",
            min_value=0,
            max_value=60,
            step=5,
            value=_number(style["break_length"], 10, 0, 60),
            key=f"{prefix}_prefs_break"
        )

    with pomodoro_column:
        pomodoro = st.number_input(
            "Pomodoro (min)",
            min_value=10,
            max_value=60,
            step=5,
            value=_number(style["pomodoro"], 25, 10, 60),
            key=f"{prefix}_prefs_pomodoro"
        )

    style_column, peak_column = st.columns(2)

    with style_column:
        study_type = st.selectbox(
            "Study style",
            STUDY_STYLES,
            index=_index(STUDY_STYLES, style["style"]),
            key=f"{prefix}_prefs_style"
        )

    with peak_column:
        peak = st.selectbox(
            "Peak productivity",
            PEAK_TIMES,
            index=_index(PEAK_TIMES, style["peak"], 2),
            key=f"{prefix}_prefs_peak"
        )

    names = course_names(courses)
    hardest_column, favorite_column = st.columns(2)

    with hardest_column:
        hardest = _subject_picker(
            "Hardest subject",
            style["hardest"],
            names,
            "Pick a course or type a subject",
            f"{prefix}_prefs_hardest"
        )

    with favorite_column:
        favorite = _subject_picker(
            "Favorite subject",
            style["favorite"],
            names,
            "Pick a course or type a subject",
            f"{prefix}_prefs_favorite"
        )

    return {
        "session_length": int(session_length),
        "max_per_day": int(max_per_day),
        "break_length": int(break_length),
        "pomodoro": int(pomodoro),
        "style": study_type,
        "peak": peak,
        "hardest": hardest,
        "favorite": favorite
    }


# ============================================================
# SUMMARIES FOR THE AI
# ============================================================

def course_names(courses):
    return [course["name"] for course in normalize_courses(courses) if course["name"]]


def describe_for_ai(profile, courses, activities, study_style):
    profile = complete_profile(profile)
    style = complete_study_style(study_style)

    lines = []

    if profile["name"]:
        lines.append(f"Student: {profile['name']}, {profile['grade']}" + (f" at {profile['school']}" if profile["school"] else ""))

    course_lines = []
    schedule_note = "the school uses an A/B day block schedule" if profile["ab_calendar"] else "class days not tracked"
    for course in normalize_courses(courses):
        if not course["name"]:
            continue
        blocks = course["blocks"]
        when = ""
        if blocks == ["A", "B"]:
            when = " (meets every day)"
        elif blocks:
            when = f" (meets on {blocks[0]} days)"
        course_lines.append(f"- {course['name']}{when}")
    lines.append(f"Courses ({schedule_note}):\n" + ("\n".join(course_lines) if course_lines else "- none listed"))

    activity_lines = []
    for activity in normalize_activities(activities):
        if not activity["name"]:
            continue
        days = ", ".join(activity["days"]) or "days not set"
        activity_lines.append(
            f"- {activity['name']}: {pretty_time(activity['start'])}-{pretty_time(activity['end'])} on {days}"
        )
    lines.append("Activities (do not schedule study during these):\n" + ("\n".join(activity_lines) if activity_lines else "- none listed"))

    lines.append(
        "Daily routine:\n"
        f"- Wakes up {pretty_time(style['wake'])}, bedtime {pretty_time(style['bed'])}\n"
        f"- Dinner around {pretty_time(style['dinner'])} (about 45 minutes, no studying)\n"
        f"- Starts homework at {pretty_time(style['homework_start'])} on school days\n"
        f"- Study on weekends: {'yes' if style['weekends'] else 'no'}\n"
        f"- Lighter Fridays: {'yes' if style['lighter_fridays'] else 'no'}\n"
        f"- Sunday catch-up day: {'yes' if style['sunday_catchup'] else 'no'}"
    )

    lines.append(
        "Study preferences:\n"
        f"- Session length: {style['session_length']} minutes, breaks of {style['break_length']} minutes\n"
        f"- Maximum study per day: {style['max_per_day']} minutes\n"
        f"- Pomodoro length: {style['pomodoro']} minutes\n"
        f"- Prefers: {style['style']}; most productive in the {style['peak'].lower()}\n"
        f"- Hardest subject: {style['hardest'] or 'not given'}; favorite subject: {style['favorite'] or 'not given'}"
    )

    return "\n\n".join(lines)
