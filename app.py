import streamlit as st
import altair as alt
import html
import json
import re
import secrets
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from ollama import Client, ResponseError
from streamlit_cookies_controller import CookieController

from studyflow.data import storage, uploads
from studyflow.exports import calendar_export, reminder_email
from studyflow.planning import ab_calendar, analytics, scheduler
from studyflow.planning import events as calendar_events
from studyflow.ui import flashcard_display as fcard
from studyflow.ui import glass_background
from studyflow.ui import plan_calendar
from studyflow.ui import setup_forms as setup

import importlib
import os
import sys


# ============================================================
# KEEP HELPER FILES UP TO DATE
# ============================================================

HELPER_MODULES = [
    "studyflow.data.fcps_courses",
    "studyflow.planning.ab_calendar",
    "studyflow.planning.events",
    "studyflow.data.uploads",
    "studyflow.data.storage",
    "studyflow.planning.scheduler",
    "studyflow.exports.calendar_export",
    "studyflow.exports.reminder_email",
    "studyflow.ui.setup_forms",
    "studyflow.planning.analytics",
    "studyflow.ui.flashcard_display",
    "studyflow.ui.glass_background",
    "studyflow.ui.plan_calendar"
]


@st.cache_resource
def _helper_file_times():
    return {}


def refresh_helper_modules():
    seen = _helper_file_times()
    for name in HELPER_MODULES:
        module = sys.modules.get(name)
        path = getattr(module, "__file__", None)
        if not path:
            continue
        try:
            changed_at = os.path.getmtime(path)
        except OSError:
            continue
        if name in seen and seen[name] != changed_at:
            importlib.reload(module)
        seen[name] = changed_at


refresh_helper_modules()


# ============================================================
# PAGE SETTINGS
# ============================================================

APP_DIR = Path(__file__).parent
ASSETS_DIR = APP_DIR / "assets"
FAVICON_PATH = str(ASSETS_DIR / "images" / "favicon.svg")
LOGO_PATH = str(ASSETS_DIR / "images" / "studyflow_logo.png")
APP_CSS = ASSETS_DIR / "styles" / "app.css"

st.set_page_config(
    page_title="StudyFlow AI",
    page_icon=FAVICON_PATH,
    layout="wide"
)

st.markdown(
    f"<style>{APP_CSS.read_text(encoding='utf-8')}</style>",
    unsafe_allow_html=True
)

glass_background.show()

# ============================================================
# CONNECT TO OLLAMA
# ============================================================

try:
    ollama_api_key = st.secrets["OLLAMA_API_KEY"]
except Exception:
    st.error(
        "OLLAMA_API_KEY was not found. "
        "Add it to .streamlit/secrets.toml."
    )
    st.stop()

AI_TIMEOUT_SECONDS = 90

AI_ATTEMPTS = 2

TASK_TIMEOUT_SECONDS = 45

client = Client(
    host="https://ollama.com",
    headers={
        "Authorization": f"Bearer {ollama_api_key}"
    },
    timeout=AI_TIMEOUT_SECONDS
)

task_client = Client(
    host="https://ollama.com",
    headers={
        "Authorization": f"Bearer {ollama_api_key}"
    },
    timeout=TASK_TIMEOUT_SECONDS
)

MODEL = "gpt-oss:20b-cloud"

VISION_MODEL = "gemma4:31b-cloud"

CHAT_MODEL = "gemma4:31b-cloud"

CHAT_TEMPERATURE = 0.7

AVATAR_PATH = FAVICON_PATH

APP_TIMEZONE = "America/New_York"

REGION = 'Virginia'

MAX_HISTORY_MESSAGES = 50

GUEST_COOKIE = "studyflow_guest_token"

SETUP_STEPS = [
    ("Basic Info", "Tell us about yourself"),
    ("Your Courses", "Add the classes you're taking this year"),
    ("Activities", "Sports, clubs, a job: anything that takes up your time"),
    ("Daily Routine", "When your day starts, ends, and when you do homework"),
    ("Study Preferences", "How you like to study, so your plan fits you"),
    ("Reminders", "A daily email with what to study, so nothing sneaks up on you")
]


# ============================================================
# SESSION STATE
# ============================================================

for field, empty in storage.SAVED_FIELDS.items():
    if field not in st.session_state:
        st.session_state[field] = empty()

if "reminders" not in st.session_state:
    st.session_state.reminders = {}

if "found_assignments" not in st.session_state:
    st.session_state.found_assignments = []

if "found_batch" not in st.session_state:
    st.session_state.found_batch = 0

if "flashcard_sets" not in st.session_state:
    st.session_state.flashcard_sets = []

if "assignment_form" not in st.session_state:
    st.session_state.assignment_form = 0


def prepare_saved_data():
    st.session_state.courses = setup.normalize_courses(st.session_state.courses)
    st.session_state.activities = setup.normalize_activities(st.session_state.activities)
    st.session_state.profile = setup.complete_profile(st.session_state.profile)
    st.session_state.study_style = setup.complete_study_style(st.session_state.study_style)
    st.session_state.flashcard_sets = fcard.normalize_sets(st.session_state.get("flashcard_sets"))


if "data_prepared" not in st.session_state:
    prepare_saved_data()
    st.session_state.data_prepared = True


# ============================================================
# ACCOUNT
# ============================================================

def google_login_available():
    try:
        return "auth" in st.secrets
    except Exception:
        return False


def signed_in_with_google():
    return google_login_available() and st.user.is_logged_in


def read_guest_cookie():
    with COOKIE_SLOT:
        controller = CookieController(key="studyflow_cookie_controller")

        if "cookie_controller_loaded" not in st.session_state:
            st.session_state.cookie_controller_loaded = True
            st.stop()

        return controller.get(GUEST_COOKIE)


def existing_guest_token():
    token = st.session_state.get("guest_token") or st.context.cookies.get(GUEST_COOKIE)
    if token or st.session_state.get("guest_cookie_checked"):
        return token

    token = read_guest_cookie()
    st.session_state.guest_cookie_checked = True
    if token:
        st.session_state.guest_token = token
    return token


def create_guest_token():
    with COOKIE_SLOT:
        controller = CookieController(key="studyflow_cookie_controller")

        if "cookie_controller_loaded" not in st.session_state:
            st.session_state.cookie_controller_loaded = True
            st.stop()

        token = controller.get(GUEST_COOKIE) or secrets.token_urlsafe(32)
        controller.set(
            GUEST_COOKIE,
            token,
            expires=datetime.now() + timedelta(days=400),
            secure=True,
            same_site="strict"
        )
    st.session_state.guest_token = token
    return token


def show_welcome():
    st.markdown(
        """
        <div class="studyflow-title">
            <span class="brand-name">StudyFlow</span>
            <span class="brand-ai"> AI</span>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="studyflow-subtitle">Your AI-powered academic planner</div>',
        unsafe_allow_html=True
    )
    st.write(
        "Welcome! StudyFlow saves your courses, assignments, and study plan "
        "so they're still here next time you visit."
    )

    google_column, guest_column = st.columns(2)

    if google_login_available():
        with google_column:
            with st.container(border=True):
                st.subheader("Sign in with Google")
                st.caption("Your plan is saved to your account and works on any device.")
                if st.button("Sign in with Google", type="primary", width="stretch"):
                    st.login()

    with guest_column:
        with st.container(border=True):
            st.subheader("Continue without signing in")
            st.caption("Your plan is saved on this browser only. You can sign in later.")
            if st.button("Continue as guest", width="stretch"):
                st.session_state.guest_chosen = True
                st.rerun()

    st.stop()


def current_identity():
    if signed_in_with_google():
        return {
            "google_sub": st.user.get("sub"),
            "guest_token": existing_guest_token()
        }

    token = existing_guest_token()

    if not token and st.session_state.get("guest_chosen"):
        token = create_guest_token()

    if not token:
        show_welcome()

    return {
        "google_sub": None,
        "guest_token": token
    }


def load_student():
    supabase = storage.get_supabase()
    if supabase is None:
        return None

    identity = current_identity()
    identity_key = identity["google_sub"] or identity["guest_token"]

    if st.session_state.get("loaded_identity") == identity_key:
        return supabase

    try:
        student = storage.find_or_create_student(supabase, **identity)
    except Exception as error:
        st.error(
            "StudyFlow couldn't reach its database, "
            "so your changes won't be saved right now."
        )
        with st.expander("Technical details"):
            st.code(str(error))
        return None

    for field, value in storage.saved_data(student).items():
        st.session_state[field] = value
    st.session_state.reminders = student.get("reminders") or {}
    st.session_state.flashcard_sets = student.get("flashcards") or []

    prepare_saved_data()
    setup.reset_form_state()
    st.session_state.wizard_step = 0
    st.session_state.found_assignments = []
    st.session_state.student_id = student["id"]
    st.session_state.loaded_identity = identity_key
    return supabase


def save():
    if SUPABASE is None or not st.session_state.get("student_id"):
        return

    data = {field: st.session_state[field] for field in storage.SAVED_FIELDS}

    try:
        storage.save_student(SUPABASE, st.session_state.student_id, data)
    except Exception as error:
        print("SAVE FAILED:", error)
        if "profile" in str(error) or "study_style" in str(error):
            st.error(
                "Your database is missing the new setup columns. "
                "Run supabase/add_setup.sql in the Supabase SQL Editor."
            )
        else:
            st.toast("Couldn't save your latest changes. Check your connection.", icon=":material/warning:")


def save_flashcards():
    if SUPABASE is None or not st.session_state.get("student_id"):
        return

    try:
        storage.save_flashcards(SUPABASE, st.session_state.student_id, st.session_state.flashcard_sets)
    except Exception as error:
        print("FLASHCARD SAVE FAILED:", error)
        if not st.session_state.get("flashcard_save_warned"):
            st.session_state.flashcard_save_warned = True
            st.toast(
                "Flashcards can't be saved to your account yet. "
                "Run supabase/add_flashcards.sql in the Supabase SQL Editor.",
                icon=":material/warning:"
            )


def delete_flashcard_set(set_id):
    st.session_state.flashcard_sets = [
        card_set for card_set in st.session_state.flashcard_sets
        if card_set["id"] != set_id
    ]
    save_flashcards()


def delete_my_data():
    storage.delete_student(SUPABASE, st.session_state.student_id)
    st.session_state.reminders = {}
    st.session_state.flashcard_sets = []

    for field, empty in storage.SAVED_FIELDS.items():
        st.session_state[field] = empty()

    prepare_saved_data()
    setup.reset_form_state()
    st.session_state.wizard_step = 0
    st.session_state.found_assignments = []
    st.session_state.student_id = None
    st.session_state.loaded_identity = None


COOKIE_SLOT = st.container()


def handle_unsubscribe():
    token = st.query_params.get("unsubscribe")
    if not token:
        return

    supabase = storage.get_supabase()
    try:
        done = supabase is not None and storage.unsubscribe(supabase, token)
    except Exception as error:
        print("UNSUBSCRIBE FAILED:", error)
        done = False

    st.markdown(
        """
        <div class="studyflow-title">
            <span class="brand-name">StudyFlow</span>
            <span class="brand-ai"> AI</span>
        </div>
        """,
        unsafe_allow_html=True
    )
    if done:
        st.success("You won't get any more reminder emails. You can turn them back on in Settings anytime.")
    else:
        st.warning("That link didn't work. You can turn reminders off in Settings, under Reminders.")
    if st.button("Open StudyFlow", type="primary"):
        st.query_params.clear()
        st.rerun()
    st.stop()


handle_unsubscribe()

SUPABASE = load_student()


# ============================================================
# DATE HELPER
# ============================================================

def student_now():
    zone = st.session_state.profile.get("timezone") or APP_TIMEZONE
    try:
        return datetime.now(ZoneInfo(zone))
    except Exception:
        try:
            return datetime.now(ZoneInfo(APP_TIMEZONE))
        except Exception:
            return datetime.now()


def uses_ab_calendar():
    return st.session_state.profile.get("ab_calendar", True)


def day_note(day):
    if not uses_ab_calendar() or day.weekday() >= 5:
        return ""
    return ab_calendar.describe_day(day)


def date_context(days=14):
    today = student_now().date()
    today_note = day_note(today)

    tomorrow = today + timedelta(days=1)
    lines = [
        f"Today is {today:%A}, {today:%Y-%m-%d}" + (f" ({today_note})." if today_note else "."),
        f"Tomorrow is {tomorrow:%A}, {tomorrow:%Y-%m-%d}."
    ]

    if uses_ab_calendar():
        lines.append(
            f"The student's school follows the FCPS {ab_calendar.SCHOOL_YEAR} A/B day calendar. "
            "Each course meets only on its A or B days, and weekdays marked "
            "\"no school\" are holidays."
        )

    lines.append(
        "Calendar for the coming days (use it to convert relative dates like "
        "\"next Friday\" or \"next class\"):"
    )
    for i in range(1, days + 1):
        day = today + timedelta(days=i)
        note = day_note(day)
        lines.append(f"- {day:%A} {day:%Y-%m-%d}" + (f" ({note})" if note else ""))

    return "\n".join(lines)


def plan_days():
    today = student_now().date()
    latest = today
    for assignment in st.session_state.assignments:
        try:
            due = datetime.strptime(str(assignment.get("due_date")), "%Y-%m-%d").date()
        except ValueError:
            continue
        latest = max(latest, due)
    return min(max((latest - today).days, 14), 60)


# ============================================================
# AI HELPER
# ============================================================

def build_messages(prompt, system_message, conversation=None, images=None):
    messages = [
        {
            "role": "system",
            "content": system_message
        }
    ]

    if conversation:
        messages[0]["content"] += "\n\n" + prompt
        for m in conversation:
            model_message = {
                "role": m["role"],
                "content": m["content"]
            }
            if m.get("images"):
                model_message["images"] = m["images"]
            messages.append(model_message)
    else:
        user_message = {
            "role": "user",
            "content": prompt
        }
        if images:
            user_message["images"] = images
        messages.append(user_message)

    return messages


def think_setting(model):
    return "low" if model.startswith("gpt-oss") else False


def is_timeout(error):
    return "timeout" in type(error).__name__.lower()


def call_model(model, messages, use_json, temperature):
    request = {
        "model": model,
        "messages": messages,
        "format": "json" if use_json else None,
        "options": {"temperature": temperature}
    }

    for attempt in range(AI_ATTEMPTS):
        started = time.monotonic()
        try:
            try:
                response = client.chat(think=think_setting(model), **request)
            except ResponseError as error:
                if "think" not in str(error).lower():
                    raise
                response = client.chat(**request)
            print(f"AI {model} answered in {time.monotonic() - started:.1f}s")
            return response
        except Exception as error:
            print(f"AI {model} failed after {time.monotonic() - started:.1f}s: {type(error).__name__}")
            if is_timeout(error) and attempt < AI_ATTEMPTS - 1:
                continue
            raise


def stream_model(model, messages, temperature):
    request = {
        "model": model,
        "messages": messages,
        "options": {"temperature": temperature},
        "stream": True
    }

    try:
        yield from client.chat(think=think_setting(model), **request)
    except ResponseError as error:
        if "think" not in str(error).lower():
            raise
        yield from client.chat(**request)


def parse_json_reply(text):
    # Some models wrap JSON in ```json fences even when asked for plain JSON.
    cleaned = str(text or "").strip()
    for fence in ("```json", "```"):
        cleaned = cleaned.removeprefix(fence)
    return json.loads(cleaned.removesuffix("```").strip())


def ask_ai(prompt, system_message, conversation=None, use_json=True, images=None, model=MODEL, temperature=0):
    try:
        messages = build_messages(prompt, system_message, conversation, images)
        response = call_model(model, messages, use_json, temperature)

        result = response.message.content

        print("RAW RESPONSE:")
        print(ascii(result))

        if not use_json:
            return result.strip()

        parsed = parse_json_reply(result)

        if not isinstance(parsed, dict):
            st.error("AI returned an unexpected format.")
            return None

        return parsed

    except json.JSONDecodeError:
        st.error("AI returned invalid JSON.")
        return None

    except Exception as e:
        print("AI REQUEST FAILED:", type(e).__name__, e)
        if is_timeout(e):
            st.error("The AI took too long to answer. Please try again in a minute.")
        else:
            st.error("Unable to connect to Ollama.")
            st.code(str(e))
        return None


# ============================================================
# FLASHCARD MAKER
# ============================================================

def generate_flashcards(prompt, images=None, spinner_text="Making flashcards..."):
    with st.spinner(spinner_text):
        result = ask_ai(
            prompt,
            fcard.SYSTEM_MESSAGE,
            images=images,
            model=VISION_MODEL if images else MODEL,
            temperature=0.3
        )

    if result is None:
        return None, ""

    cards = fcard.clean_cards(result)
    if len(cards) < fcard.MIN_CARDS:
        st.error(
            "The AI couldn't make good flashcards from that. Try again with a more specific topic, "
            "or add the vocab words or topics you want."
        )
        return None, ""

    return cards, result.get("title", "")


def make_flashcards(assignment):
    cards, _ = generate_flashcards(
        fcard.flashcard_prompt(assignment, st.session_state.profile),
        spinner_text=f"Making flashcards for {assignment.get('name') or 'this assignment'}..."
    )
    if not cards:
        return

    card_set = fcard.new_set(assignment.get("name"), assignment.get("course"), cards)
    existing = fcard.find_set(st.session_state.flashcard_sets, assignment)
    if existing is None:
        st.session_state.flashcard_sets.append(card_set)
    else:
        fcard.reset_state(st.session_state.flashcard_sets[existing])
        st.session_state.flashcard_sets[existing] = card_set
    save_flashcards()
    st.session_state.flash = (
        f"Made {len(cards)} flashcards for {card_set['assignment']}. Open the Flashcards tab to study them."
    )
    st.rerun()


def make_requested_flashcards(request, course="", count=fcard.TARGET_CARDS, notes="", images=None):
    cards, title = generate_flashcards(
        fcard.request_prompt(request, course, count, st.session_state.profile, notes, bool(images)),
        images=images
    )
    if not cards:
        return None

    card_set = fcard.new_set(
        fcard.set_title({"title": title}, request or "Flashcards from my notes"),
        course,
        cards,
        source="request"
    )
    st.session_state.flashcard_sets.insert(0, card_set)
    save_flashcards()
    return card_set


def show_flashcard_maker():
    form = st.session_state.get("flashcard_form", 0)

    with st.expander(
        ":material/auto_awesome: Make your own flashcards",
        expanded=not st.session_state.flashcard_sets
    ):
        request = st.text_area(
            "What should the flashcards cover?",
            placeholder="Example: Spanish 2 food vocab, the causes of World War I, or cell organelles and what they do",
            key=f"flashcard_request_{form}"
        )

        course_options = ["Not for a specific course"] + setup.course_names(st.session_state.courses)
        course_column, count_column = st.columns([2, 1])
        with course_column:
            course = st.selectbox("Course", course_options, key=f"flashcard_course_{form}")
        with count_column:
            count = st.number_input(
                "Cards",
                min_value=5,
                max_value=fcard.MAX_CARDS,
                value=fcard.TARGET_CARDS,
                step=1,
                key=f"flashcard_count_{form}"
            )

        notes_file = st.file_uploader(
            "Photo or PDF of your notes (optional)",
            type=uploads.IMAGE_TYPES + ["pdf"],
            key=f"flashcard_file_{form}"
        )

        if st.button(":material/style: Make flashcards", type="primary", width="stretch", key=f"flashcard_make_{form}"):
            if not request.strip() and notes_file is None:
                st.warning("Type a topic or upload your notes first.")
                return

            notes = ""
            images = None
            if notes_file is not None:
                try:
                    if uploads.is_pdf(notes_file):
                        notes = uploads.pdf_text(notes_file)
                    else:
                        images = [uploads.encode_image(notes_file)]
                except ValueError as error:
                    st.error(str(error))
                    return

            card_set = make_requested_flashcards(
                request.strip(),
                "" if course == course_options[0] else course,
                count,
                notes,
                images
            )
            if card_set:
                st.session_state.flashcard_form = form + 1
                st.session_state.flash = f"Made {len(card_set['cards'])} flashcards: {card_set['assignment']}."
                st.rerun()


# ============================================================
# ASSIGNMENT ANALYZER
# ============================================================

def _text(value, default):
    if value is None:
        return default
    if isinstance(value, float) and value != value:
        return default
    value = str(value).strip()
    return value or default


def _whole_number(value, default):
    try:
        return int(float(value))
    except (TypeError, ValueError, OverflowError):
        return default


ASSIGNMENT_TYPES = [
    "homework",
    "test",
    "quiz",
    "project",
    "essay",
    "presentation",
    "notes",
    "program",
    "script",
    "other"
]

COURSE_RULE = (
    "The course must be one of the student's courses, written exactly as it appears in their course list. "
    "Pick the closest one even when the student uses a nickname or abbreviation (for example \"precalc\" "
    "means their Precalculus course, \"bio\" their Biology course, and \"english essay\" their English course). "
    "Use \"General\" only when the item clearly doesn't belong to any of their courses."
)

NO_COURSES_RULE = (
    "The student hasn't listed their courses yet, so the course is the subject the item is for "
    "(for example \"Biology\" or \"English\"), or \"General\" if the subject isn't clear."
)


def course_rule():
    return COURSE_RULE if setup.course_names(st.session_state.courses) else NO_COURSES_RULE


def course_list_text():
    names = setup.course_names(st.session_state.courses)
    return json.dumps(names) if names else "None listed yet."


COURSE_FILLER_WORDS = {
    "ap", "ib", "honors", "hn", "h", "aa", "gt", "de", "dual", "enrollment", "advanced",
    "intro", "introduction", "to", "the", "and", "of", "in", "&", "class", "course"
}

COURSE_NICKNAMES = {
    "apush": "united states history",
    "ush": "united states history",
    "bio": "biology",
    "alg": "algebra",
    "eng": "english",
    "sci": "science",
    "euro": "european",
    "apes": "environmental science",
    "csa": "computer science",
    "csp": "computer science",
    "cs": "computer science",
    "compsci": "computer science",
    "lang": "language",
    "lit": "literature",
    "gov": "government",
    "stats": "statistics",
    "trig": "trigonometry",
    "pe": "physical education",
    "gym": "physical education",
    "ela": "english"
}


def _course_words(text):
    words = re.findall(r"[a-z]+|\d+", str(text or "").lower())
    expanded = []
    for word in words:
        expanded.extend(COURSE_NICKNAMES.get(word, word).split())
    return expanded


def match_course(text, names):
    """Return the student's course that `text` refers to, or None if it's unclear."""
    if not text:
        return None
    for name in names:
        if str(text).strip().casefold() == name.casefold():
            return name

    text_words = [word for word in _course_words(text) if word not in COURSE_FILLER_WORDS]
    scores = {}
    for name in names:
        course_words = [
            word for word in _course_words(name)
            if word not in COURSE_FILLER_WORDS and not word.isdigit()
        ]
        score = 0
        for course_word in course_words:
            # Whole words match at any length; prefixes ("precalc", "chem") need 4+ letters.
            if any(
                word == course_word
                or (min(len(word), len(course_word)) >= 4
                    and (course_word.startswith(word) or word.startswith(course_word)))
                for word in text_words
            ):
                score += 1
        if score:
            scores[name] = score

    if not scores:
        return None
    best = max(scores.values())
    winners = [name for name, score in scores.items() if score == best]
    return winners[0] if len(winners) == 1 else None


def guess_course(assignment):
    names = setup.course_names(st.session_state.courses)
    course = assignment.get("course") or ""
    if course in names:
        return course
    for text in (course, assignment.get("name"), assignment.get("description")):
        match = match_course(text, names)
        if match:
            return match
    return course or "General"


def fix_general_courses():
    # One-time repair for assignments saved before course matching existed.
    if st.session_state.profile.get("courses_matched"):
        return

    fixed = {}
    for assignment in st.session_state.assignments:
        if assignment.get("course") in ("", "General"):
            assignment["course"] = guess_course({**assignment, "course": ""})
            fixed[assignment.get("name")] = assignment["course"]

    for session in plan_sessions():
        if session.get("course") in ("", "General") and fixed.get(session.get("assignment"), "General") != "General":
            session["course"] = fixed[session["assignment"]]

    st.session_state.profile["courses_matched"] = True
    save()


ASSIGNMENT_NAME_RULE = (
    "The name is the full, specific name of the item: the course's exact name from the student's "
    "course list, then any unit, chapter, or topic the student or the file gave, then the type. "
    "Expand nicknames and abbreviations, so \"precalc quiz\" for a student taking AP Precalculus BC "
    "becomes \"AP Precalculus BC Unit 2 Quiz\" when it covers unit 2. Never invent unit or chapter numbers."
)


def title_case(text):
    # Words already in all caps are usually acronyms (AP, DNA), so keep them.
    return " ".join(
        word if word.isupper() else word[:1].upper() + word[1:].lower()
        for word in text.split()
    )


MAX_STUDY_MATERIAL = 2000


def normalize_assignment(assignment):
    priority = _text(assignment.get("priority"), "Medium").title()
    if priority not in ("Low", "Medium", "High"):
        priority = "Medium"

    assignment_type = _text(assignment.get("type"), "").lower()
    if assignment_type not in ASSIGNMENT_TYPES:
        assignment_type = ""

    name = _text(assignment.get("name"), "Untitled assignment")

    return {
        "name": title_case(name),
        "type": assignment_type,
        "course": _text(assignment.get("course"), "General"),
        "due_date": _text(assignment.get("due_date"), "Not set"),
        "difficulty": min(5, max(1, _whole_number(assignment.get("difficulty"), 3))),
        "estimated_minutes": max(5, _whole_number(assignment.get("estimated_minutes"), 60)),
        "priority": priority,
        "description": _text(assignment.get("description"), ""),
        "study_material": _text(assignment.get("study_material"), "")[:MAX_STUDY_MATERIAL]
    }


def due_date_value(value):
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def due_date_text(value):
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return _text(value, "Not set")


def pretty_due_date(value):
    day = due_date_value(value)
    if day is None:
        return _text(value, "Not set")
    return f"{day:%a, %b} {day.day}, {day.year}"


def remove_past_assignments():
    today = student_now().date()
    upcoming = [
        assignment for assignment in st.session_state.assignments
        if (due_date_value(assignment.get("due_date")) or today) >= today
    ]
    if len(upcoming) != len(st.session_state.assignments):
        st.session_state.assignments = upcoming
        save()


@st.dialog("Edit assignment")
def edit_assignment_dialog(index):
    assignment = st.session_state.assignments[index]
    key = f"edit_{index}"

    course_options = setup.course_names(st.session_state.courses) + ["General"]
    current_course = assignment.get("course") or "General"
    if current_course not in course_options:
        course_options.append(current_course)

    type_options = [""] + ASSIGNMENT_TYPES
    current_type = assignment.get("type") or ""
    if current_type not in type_options:
        current_type = ""

    name = st.text_input("Assignment", value=assignment.get("name", ""), key=f"{key}_name")

    type_column, course_column = st.columns(2)
    with type_column:
        assignment_type = st.selectbox(
            "Type",
            type_options,
            index=type_options.index(current_type),
            format_func=lambda option: option.title() if option else "Not sure",
            key=f"{key}_type"
        )
    with course_column:
        course = st.selectbox(
            "Course",
            course_options,
            index=course_options.index(current_course),
            key=f"{key}_course"
        )

    due_column, priority_column = st.columns(2)
    with due_column:
        due = st.date_input(
            "Due date",
            value=due_date_value(assignment.get("due_date")),
            format="MM/DD/YYYY",
            key=f"{key}_due"
        )
    with priority_column:
        priorities = ["Low", "Medium", "High"]
        priority = st.selectbox(
            "Priority",
            priorities,
            index=priorities.index(assignment.get("priority", "Medium")),
            key=f"{key}_priority"
        )

    difficulty_column, minutes_column = st.columns(2)
    with difficulty_column:
        difficulty = st.slider(
            "Difficulty",
            1,
            5,
            value=_whole_number(assignment.get("difficulty"), 3),
            key=f"{key}_difficulty"
        )
    with minutes_column:
        minutes = st.number_input(
            "Prep minutes" if assignment_type in scheduler.PREP_TYPES else "Work minutes",
            min_value=5,
            step=5,
            value=_whole_number(assignment.get("estimated_minutes"), 60),
            key=f"{key}_minutes"
        )

    description = st.text_area("Notes", value=assignment.get("description", ""), key=f"{key}_notes")
    study_material = st.text_area(
        "Study material",
        value=assignment.get("study_material", ""),
        placeholder="Vocab words, key terms, or topics. StudyFlow uses these to make your flashcards.",
        key=f"{key}_study_material"
    )

    save_column, cancel_column = st.columns(2)
    with save_column:
        if st.button("Save", type="primary", width="stretch", key=f"{key}_save"):
            if not name.strip():
                st.warning("Please give the assignment a name.")
            else:
                st.session_state.assignments[index] = normalize_assignment({
                    "name": name,
                    "type": assignment_type,
                    "course": course,
                    "due_date": due_date_text(due),
                    "difficulty": difficulty,
                    "estimated_minutes": minutes,
                    "priority": priority,
                    "description": description,
                    "study_material": study_material
                })
                save()
                st.session_state.flash = "Assignment updated. Press Update my plan on the Study Plan tab to include the changes."
                st.rerun()
    with cancel_column:
        if st.button("Cancel", width="stretch", key=f"{key}_cancel"):
            st.rerun()


def extract_assignments(text, uploaded_file=None):
    sources = []
    images = None
    model = MODEL

    if text:
        sources.append(f'The student described their work like this:\n"""\n{text}\n"""')

    if uploaded_file is not None:
        if uploads.is_pdf(uploaded_file):
            document_text = uploads.pdf_text(uploaded_file)
            sources.append(f'Here is the text of the uploaded document:\n"""\n{document_text}\n"""')
        else:
            images = [uploads.encode_image(uploaded_file)]
            sources.append(
                "The attached image is a photo of the student's assignment sheet, "
                "syllabus, or planner page."
            )
            model = VISION_MODEL

    source = "\n\n".join(sources)

    prompt = f"""
{date_context()}

The student's courses are:
{course_list_text()}

{source}

Find every assignment, test, quiz, project, or other item the student needs to do.
Return ONLY valid JSON.
Use exactly this format:
{{
    "assignments": [
        {{
            "name": "",
            "type": "",
            "course": "",
            "due_date": "YYYY-MM-DD",
            "difficulty": 3,
            "estimated_minutes": 60,
            "priority": "Medium",
            "description": "",
            "study_material": ""
        }}
    ]
}}

Rules:
- Only include items the student described or that actually appear in the file. Never invent items.
- If the student wrote a description and uploaded a file, use the description to fill in or
  correct details from the file (for example, which course it is for or when it is due).
- {course_rule()}
- {ASSIGNMENT_NAME_RULE}
- Use YYYY-MM-DD for the due date. Convert relative dates such as "next Tuesday" using the calendar above.
- If an item has no due date, use "Not set".
- If a date has no year, use the next upcoming date.
- Difficulty must be 1-5 (1 = extremely easy, 5 = extremely difficult).
- Priority must be Low, Medium, or High.
- Type must be one of: {", ".join(ASSIGNMENT_TYPES)}.
  Use the type the student gives, or infer it only if you are EXTREMELY SURE. If you are not sure, leave the type blank.
  Use the type to help decide the priority and difficulty.
- If the type is test, quiz, or presentation, the estimated minutes is the time to prepare for it ONLY.
  Otherwise, it is the time to complete it.
- Estimate realistic focused work time.
- The description lists every useful detail the student or the file gave: chapters, sections, page numbers,
  problem numbers, topics covered, and requirements. Never invent details.
- study_material copies the actual study content listed for this item: vocabulary words, key terms, concepts,
  formulas, people, dates, or review questions (up to about 150 words). Leave it blank if none are listed.
- If nothing is found, return {{"assignments": []}}.
"""
    result = ask_ai(
        prompt,
        "You are an AI academic planner that reads students' descriptions and assignment sheets. "
        "Return only valid JSON.",
        images=images,
        model=model
    )

    if result is None:
        return None

    found = result.get("assignments")
    if not isinstance(found, list):
        return []

    found = [normalize_assignment(item) for item in found if isinstance(item, dict)]
    for item in found:
        item["course"] = guess_course(item)
    return found

# ============================================================
# STUDY PLAN GENERATOR
# ============================================================

def plan_day_label(value):
    if not uses_ab_calendar():
        return ""
    try:
        day = datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return ""
    return ab_calendar.short_label(day)


def show_calendar_export(sessions, zone_name):
    with st.container(border=True):
        st.subheader(":material/ios_share: Export to your calendar")

        include_due = st.toggle(
            "Include assignment due dates",
            value=True,
            key="export_include_due"
        )

        session_count, due_count = calendar_export.count_events(
            sessions,
            st.session_state.assignments,
            include_due
        )

        if not session_count and not due_count:
            st.caption("There's nothing with a date to export yet.")
            return

        summary = f"{session_count} study session{'s' if session_count != 1 else ''}"
        if include_due:
            summary += f" and {due_count} due date{'s' if due_count != 1 else ''}"
        st.caption(f"{summary}, each study session with a 10-minute reminder.")

        st.download_button(
            ":material/download: Download calendar file (.ics)",
            data=calendar_export.build_ics(
                sessions,
                st.session_state.assignments,
                zone_name,
                include_due
            ),
            file_name="studyflow-study-plan.ics",
            mime="text/calendar",
            type="primary",
            width="stretch",
            key="export_download"
        )

        with st.expander("How to add it to Google Calendar"):
            st.markdown(
                "1. Open **calendar.google.com** on a computer.\n"
                "2. Click **:material/settings: Settings**, then **Import & export**.\n"
                "3. Choose the file you downloaded and click **Import**.\n\n"
                "Tip: make a new calendar called *StudyFlow* first and import into it, "
                "so you can hide or delete the whole plan in one click. "
                "If you make a new plan later, clear out the old one before importing again. "
                "The file also works with Apple Calendar and Outlook."
            )


def is_school_day_for_student(day):
    if not uses_ab_calendar():
        return day.weekday() < 5
    if ab_calendar.in_school_year(day):
        return ab_calendar.day_type(day) is not None
    return day.weekday() < 5


def write_tasks(sessions):
    if not sessions:
        return {}

    details = []
    for number, session in enumerate(sessions, start=1):
        details.append({
            "id": number,
            "course": session["course"],
            "assignment": session["assignment"],
            "type": session["type"],
            "notes": session["description"][:600],
            "part": f"{session['part']} of {session['parts']}",
            "minutes": session["minutes"],
            "due": session["due_date"]
        })

    prompt = f"""
Write one study task for each study session below.

Sessions:
{json.dumps(details, indent=1)}

Rules:
- Each task tells the student exactly what to do in that session, in 10 to 25 words.
- Name the specific chapters, sections, pages, problems, or topics from the notes, and divide them
  across the parts of the same assignment so each part covers a different piece
  (for example, part 1: sections 2.1-2.3, part 2: sections 2.4-2.6, part 3: mixed review).
- Parts of the same assignment build on each other, from getting started to finishing.
- For tests and quizzes, use active study: practice problems, self-quizzing, flashcards, reviewing mistakes.
- For presentations, prepare slides or notes and rehearse out loud.
- Fit the task to the session length.
- Use the notes when they help, but never invent page numbers or details.

Return ONLY valid JSON in exactly this format:
{{"tasks": [{{"id": 1, "task": ""}}]}}
"""
    messages = build_messages(prompt, "You are a study coach who writes short, specific study tasks. Return only valid JSON.")
    request = {
        "model": CHAT_MODEL,
        "messages": messages,
        "format": "json",
        "options": {"temperature": 0.3}
    }

    started = time.monotonic()
    try:
        try:
            response = task_client.chat(think=False, **request)
        except ResponseError as error:
            if "think" not in str(error).lower():
                raise
            response = task_client.chat(**request)
        data = parse_json_reply(response.message.content)
        print(f"AI tasks written in {time.monotonic() - started:.1f}s")
    except Exception as error:
        print(f"AI tasks skipped after {time.monotonic() - started:.1f}s: {type(error).__name__}")
        return {}

    tasks = {}
    for item in data.get("tasks", []) if isinstance(data, dict) else []:
        if isinstance(item, dict) and str(item.get("task") or "").strip():
            tasks[_whole_number(item.get("id"), 0)] = str(item["task"]).strip()
    return tasks


def plan_sessions():
    plan = st.session_state.study_plan or {}
    return [session for session in plan.get("study_sessions", []) if isinstance(session, dict)]


def set_session_done(index, key):
    session = st.session_state.study_plan["study_sessions"][index]
    session["done"] = st.session_state[key]
    session["done_on"] = student_now().date().isoformat() if session["done"] else None
    save()



PLAN_VIEWS = {
    "Calendar": ":material/calendar_month: Calendar",
    "List": ":material/view_agenda: List"
}


def is_phone():
    try:
        agent = st.context.headers.get("User-Agent", "")
    except Exception:
        agent = ""
    return any(word in agent for word in ("Mobi", "Android", "iPhone"))


def one_time_events():
    availability = st.session_state.availability if isinstance(st.session_state.availability, dict) else {}
    return calendar_events.normalize_events(availability.get("events"))


def save_one_time_events(event_list):
    availability = dict(st.session_state.availability) if isinstance(st.session_state.availability, dict) else {}
    availability["events"] = calendar_events.normalize_events(event_list)
    st.session_state.availability = availability
    save()


def event_time_label(event):
    day = due_date_value(event["date"])
    when = "All day" if event["all_day"] else f"{setup.pretty_time(event['start'])} - {setup.pretty_time(event['end'])}"
    return f"{day:%a, %b} {day.day} · {when}" if day else when


def overlap_note(event):
    sessions = (st.session_state.study_plan or {}).get("study_sessions", [])
    count = len(calendar_events.overlapping_sessions(event, sessions))
    if not count:
        return ""
    return (
        f"This overlaps {count} study session{'s' if count != 1 else ''}. "
        "Drag the session somewhere else, or press Update my plan to move it automatically."
    )


def event_form(key, defaults):
    name = st.text_input(
        "Event",
        value=defaults.get("name", ""),
        placeholder="Dentist appointment, away game, family dinner...",
        key=f"{key}_name"
    )
    all_day = st.toggle("All day", value=bool(defaults.get("all_day")), key=f"{key}_all_day")

    date_column, start_column, end_column = st.columns([2, 1, 1])
    with date_column:
        day = st.date_input(
            "Date",
            value=defaults.get("date") or student_now().date(),
            format="MM/DD/YYYY",
            key=f"{key}_date"
        )
    start = end = None
    if not all_day:
        with start_column:
            start = st.time_input(
                "Starts",
                value=setup.to_time(defaults.get("start") or "16:00"),
                step=300,
                format="12h",
                key=f"{key}_start"
            )
        with end_column:
            end = st.time_input(
                "Ends",
                value=setup.to_time(defaults.get("end") or "17:00"),
                step=300,
                format="12h",
                key=f"{key}_end"
            )
    return {"name": name.strip(), "date": day, "start": start, "end": end, "all_day": all_day}


def add_event_from_form(values):
    if not values["name"]:
        st.warning("Give the event a name.")
        return False
    if not values["all_day"] and values["end"] <= values["start"]:
        st.warning("The event has to end after it starts.")
        return False

    event = calendar_events.new_event(
        values["name"],
        f"{values['date']:%Y-%m-%d}",
        f"{values['start']:%H:%M}" if values["start"] else None,
        f"{values['end']:%H:%M}" if values["end"] else None,
        values["all_day"]
    )
    save_one_time_events(one_time_events() + [event])
    note = overlap_note(event)
    if note:
        st.session_state.flash = f"Added {event['name']}. {note}"
    elif st.session_state.study_plan:
        st.session_state.flash = f"Added {event['name']}. Press Update my plan to plan around it."
    else:
        st.session_state.flash = f"Added {event['name']}. Your study plan will work around it."
    return True


def delete_event(event_id):
    save_one_time_events([event for event in one_time_events() if event["id"] != event_id])
    if st.session_state.get("calendar_selected") == ("event", event_id):
        st.session_state.calendar_selected = None


def show_event_manager():
    upcoming = calendar_events.upcoming(one_time_events(), student_now().date())

    with st.expander(":material/event_busy: One-time events"):
        st.caption(
            "Appointments, games, trips: anything that only happens once. "
            "Your study plan works around them. You can also click or drag on the calendar to add one."
        )
        for event in upcoming:
            with st.container(key=f"event_row_{event['id']}"):
                text_column, delete_column = st.columns([6, 1])
                with text_column:
                    st.markdown(f"**{html.escape(event['name'])}** · {event_time_label(event)}")
                with delete_column:
                    st.button(
                        ":material/delete:",
                        key=f"event_delete_{event['id']}",
                        help="Delete this event",
                        type="tertiary",
                        on_click=delete_event,
                        args=(event["id"],)
                    )

        form = st.session_state.get("event_form", 0)
        values = event_form(f"event_form_{form}", {})
        if st.button(":material/add: Add event", key=f"event_add_{form}", type="primary"):
            if add_event_from_form(values):
                st.session_state.event_form = form + 1
                st.rerun()


def show_new_event_form():
    pending = st.session_state.get("pending_event")
    if not pending:
        return

    with st.container(border=True, key="calendar_new_event"):
        st.subheader(":material/event: New event")
        values = event_form(f"pending_event_{pending['key']}", pending)
        save_column, cancel_column = st.columns(2)
        with save_column:
            if st.button("Add event", type="primary", width="stretch", key=f"pending_save_{pending['key']}"):
                if add_event_from_form(values):
                    st.session_state.pending_event = None
                    st.rerun()
        with cancel_column:
            if st.button("Cancel", width="stretch", key=f"pending_cancel_{pending['key']}"):
                st.session_state.pending_event = None
                st.rerun()


def show_plan_calendar(zone_name):
    plan_sessions_list = st.session_state.study_plan.get("study_sessions", [])
    revision = st.session_state.get("calendar_revision", 0)

    st.caption(
        ":material/drag_pan: Drag a session to move it, or drag its bottom edge to change how long it is. "
        "Click a session to see what to do, or click an empty spot to add an event."
    )
    state = plan_calendar.show(
        plan_sessions_list,
        st.session_state.assignments,
        st.session_state.activities,
        setup.course_names(st.session_state.courses),
        st.session_state.study_style,
        student_now().replace(tzinfo=None),
        uses_ab_calendar(),
        is_phone(),
        revision,
        one_time_events()
    )

    action = plan_calendar.read_action(state)
    if action:
        index = action.get("index")
        valid = isinstance(index, int) and 0 <= index < len(plan_sessions_list)
        if action["type"] == "move" and valid:
            plan_calendar.move_session(plan_sessions_list[index], action["start"], action["end"])
            save()
            st.session_state.calendar_selected = ("session", index)
            moved_to = action["start"]
            st.toast(
                f"Moved to {moved_to:%a, %b} {moved_to.day} at {setup.pretty_time(moved_to.strftime('%H:%M'))}",
                icon=":material/event:"
            )
        elif action["type"] in ("move", "revert"):
            st.session_state.calendar_revision = revision + 1
            if action.get("reason") == "all_day":
                st.session_state.flash = "Study sessions need a time. Drag it onto a time slot instead."
            st.rerun()
        elif action["type"] == "select":
            st.session_state.calendar_selected = (action["kind"], index)
            st.session_state.pending_event = None
        elif action["type"] == "new_event":
            st.session_state.pending_event = {
                "key": st.session_state.get("pending_count", 0),
                "date": action["date"],
                "start": action["start"].strftime("%H:%M") if action["start"] else None,
                "end": action["end"].strftime("%H:%M") if action["end"] else None,
                "all_day": action["all_day"]
            }
            st.session_state.pending_count = st.session_state.pending_event["key"] + 1
            st.session_state.calendar_selected = None
        elif action["type"] == "move_event":
            moved = None
            event_list = one_time_events()
            for event in event_list:
                if event["id"] == action["id"]:
                    event["date"] = f"{action['date']:%Y-%m-%d}"
                    event["all_day"] = action["all_day"]
                    if not action["all_day"]:
                        event["start"] = action["start"].strftime("%H:%M")
                        event["end"] = action["end"].strftime("%H:%M")
                    moved = event
            if moved:
                save_one_time_events(event_list)
                st.session_state.calendar_selected = ("event", moved["id"])
                st.toast(f"Moved {moved['name']} to {event_time_label(moved)}", icon=":material/event:")

    show_new_event_form()
    show_calendar_details(zone_name)


def show_calendar_details(zone_name):
    selected = st.session_state.get("calendar_selected")
    if not selected:
        return
    kind, index = selected

    if kind == "session":
        all_sessions = st.session_state.study_plan.get("study_sessions", [])
        if not isinstance(index, int) or not 0 <= index < len(all_sessions):
            return
        session = all_sessions[index]
        day = due_date_value(session.get("date"))
        day_label = plan_day_label(session.get("date"))
        details = [
            session.get("course") or "",
            f"{day:%A, %b} {day.day}" if day else "",
            f"{setup.pretty_time(session.get('start_time'))} - {setup.pretty_time(session.get('end_time'))}",
            f"{session.get('minutes', '')} min",
            day_label
        ]

        with st.container(border=True, key="calendar_details"):
            st.subheader(f":material/menu_book: {session.get('assignment') or 'Study session'}")
            st.caption(" · ".join(part for part in details if part))
            st.write(f":material/checklist: **What to do:** {session.get('task') or 'Work on this assignment.'}")

            done_key = f"calendar_done_{st.session_state.study_plan.get('created', '')}_{index}"
            if st.session_state.get(done_key) != bool(session.get("done")):
                st.session_state[done_key] = bool(session.get("done"))
            st.toggle("Mark as done", key=done_key, on_change=set_session_done, args=(index, done_key))
            if not session.get("done") and st.button(
                ":material/event_repeat: Can't make it? Move it",
                key=f"calendar_skip_{index}",
                help="StudyFlow finds another free time before it's due."
            ):
                st.session_state.flash = skip_session(index)
                st.rerun()

            google_link = calendar_export.google_calendar_link(session, zone_name)
            if google_link:
                st.markdown(f":material/calendar_add_on: [Add to Google Calendar]({google_link})")

    elif kind == "event":
        event = next((item for item in one_time_events() if item["id"] == index), None)
        if not event:
            return
        with st.container(border=True, key="calendar_details"):
            st.subheader(f":material/event_busy: {event['name']}")
            st.caption(f"One-time event · {event_time_label(event)}")
            note = overlap_note(event)
            if note:
                st.warning(note, icon=":material/warning:")
            st.caption("Drag it on the calendar to change the time, or drag its bottom edge to change how long it is.")
            st.button(
                ":material/delete: Delete event",
                key=f"calendar_delete_event_{event['id']}",
                on_click=delete_event,
                args=(event["id"],)
            )

    elif kind == "due":
        assignments = st.session_state.assignments
        if not isinstance(index, int) or not 0 <= index < len(assignments):
            return
        assignment = assignments[index]
        with st.container(border=True, key="calendar_details"):
            st.subheader(f":material/assignment: {assignment.get('name') or 'Assignment'}")
            st.caption(
                f"{assignment.get('course') or 'General'} · "
                f"{(assignment.get('type') or 'due').title()} on {pretty_due_date(assignment.get('due_date'))}"
            )
            if assignment.get("description"):
                st.write(assignment["description"])


def show_session_list(sessions, zone_name, hide_done):
    plan_key = st.session_state.study_plan.get("created", "")

    for index, session in enumerate(sessions):
        if not isinstance(session, dict):
            continue
        is_done = bool(session.get("done"))
        if is_done and hide_done:
            continue
        with st.container(border=True, key=f"session_card_{index}"):
            check_column, col1, col2, col3 = st.columns(
                [0.5, 1.5, 2, 4]
            )
            with check_column:
                done_key = f"session_done_{plan_key}_{index}"
                st.checkbox(
                    "Done",
                    value=is_done,
                    key=done_key,
                    on_change=set_session_done,
                    args=(index, done_key),
                    label_visibility="collapsed",
                    help="Check this off when you finish the session"
                )
            with col1:
                st.write(
                    f":material/event: **{session.get('date', '')}**"
                )
                day_label = plan_day_label(session.get("date"))
                if day_label:
                    st.caption(day_label)
                st.write(
                    f":material/schedule: "
                    f"{setup.pretty_time(session.get('start_time'))} - "
                    f"{setup.pretty_time(session.get('end_time'))}"
                )
            with col2:
                st.write(
                    f":material/menu_book: **{session.get('course', '')}**"
                )
                st.write(
                    f":material/assignment: {session.get('assignment', '')}"
                )

            with col3:
                task = session.get("task", "")
                st.write(
                    f":material/check_circle: **Done:** ~~{task}~~" if is_done
                    else f":material/checklist: **What to do:** {task}"
                )
                st.caption(
                    f"{session.get('minutes', '')} minutes"
                )
                google_link = calendar_export.google_calendar_link(session, zone_name)
                if google_link:
                    st.markdown(f":material/calendar_add_on: [Add to Google Calendar]({google_link})")
                if not is_done and st.button(
                    ":material/event_repeat: Can't make it? Move it",
                    key=f"session_skip_{plan_key}_{index}",
                    type="tertiary",
                    help="StudyFlow finds another free time before it's due."
                ):
                    st.session_state.flash = skip_session(index)
                    st.rerun()


def _work_key(item, name_field="assignment"):
    return (item.get(name_field) or "", item.get("course") or "")


def session_end(session):
    day = due_date_value(session.get("date"))
    end = setup.to_time(session.get("end_time"))
    if not day or not end:
        return None
    return datetime.combine(day, end)


def busy_blocks():
    return setup.normalize_activities(st.session_state.activities) + calendar_events.as_busy_blocks(one_time_events())


def build_study_plan(keep_future=False, avoid=()):
    """Plan the work that's left. Checked-off sessions always stay. With keep_future, sessions still
    ahead stay where they are too, so only missed, moved, or newly added work gets new times."""
    if not st.session_state.assignments:
        return None, 0

    now = student_now().replace(tzinfo=None)
    busy = busy_blocks() + list(avoid)
    due_days = {
        _work_key(assignment, "name"): due_date_value(assignment.get("due_date"))
        for assignment in st.session_state.assignments
    }

    finished, kept = [], []
    for session in plan_sessions():
        if session.get("done"):
            finished.append(session)
            continue
        if not keep_future:
            continue
        key = _work_key(session)
        end = session_end(session)
        due = due_days.get(key)
        if key not in due_days or end is None or end <= now:
            continue  # its assignment is gone, or it was missed: plan that time again
        if due and end.date() >= due:
            continue  # the due date moved earlier
        if scheduler.clashes(session, busy):
            continue  # an event or activity now takes that time
        kept.append(session)

    planned_minutes = {}
    for session in finished + kept:
        key = _work_key(session)
        planned_minutes[key] = planned_minutes.get(key, 0) + _whole_number(session.get("minutes"), 0)

    remaining = []
    for assignment in st.session_state.assignments:
        left = _whole_number(assignment.get("estimated_minutes"), 60) - planned_minutes.get(_work_key(assignment, "name"), 0)
        if left > 0:
            remaining.append({**assignment, "estimated_minutes": left})

    sessions, unscheduled = scheduler.build_plan(
        remaining,
        setup.complete_study_style(st.session_state.study_style),
        busy,
        now,
        is_school_day_for_student,
        booked=kept
    )

    tasks = write_tasks(sessions)
    for number, session in enumerate(sessions, start=1):
        session["task"] = tasks.get(number) or scheduler.default_task(session)

    all_sessions = finished + kept + [scheduler.public_session(session) for session in sessions]
    all_sessions.sort(key=lambda session: (session.get("date", ""), session.get("start_time", "")))

    plan = {
        "study_sessions": all_sessions,
        "unscheduled": unscheduled,
        "created": student_now().isoformat()
    }
    return plan, len(sessions)


def generate_plan():
    return build_study_plan()[0]


def apply_plan(plan):
    st.session_state.study_plan = plan
    st.session_state.calendar_selected = None
    save()


def update_plan(avoid=(), spinner_text="Updating your study plan..."):
    """Fit missed or new work into the plan without moving anything else. Returns a message."""
    with st.spinner(spinner_text):
        plan, added = build_study_plan(keep_future=True, avoid=avoid)
    if plan is None:
        return "Add an assignment first, then StudyFlow can plan it."
    apply_plan(plan)
    message = (
        f"Updated your plan with {added} new session{'s' if added != 1 else ''}."
        if added else "Your plan is up to date."
    )
    if plan["unscheduled"]:
        message += " Some work didn't fit before its due date: see the Study Plan tab."
    return message


def missed_sessions():
    now = student_now().replace(tzinfo=None)
    return [
        index for index, session in enumerate(plan_sessions())
        if not session.get("done") and (session_end(session) or now) < now
    ]


def unplanned_assignments():
    today = student_now().date()
    planned = {_work_key(session) for session in plan_sessions()}
    return [
        assignment for assignment in st.session_state.assignments
        if _work_key(assignment, "name") not in planned
        and (due_date_value(assignment.get("due_date")) or today + timedelta(days=1)) > today
    ]


def mark_sessions_done(indexes):
    sessions = st.session_state.study_plan["study_sessions"]
    for index in indexes:
        sessions[index]["done"] = True
        sessions[index]["done_on"] = sessions[index].get("date") or student_now().date().isoformat()
    save()


def skip_session(index):
    """Take a session off the calendar and fit its work in at another time."""
    session = st.session_state.study_plan["study_sessions"].pop(index)
    avoid = [{"date": session.get("date"), "start": session.get("start_time"), "end": session.get("end_time")}]
    return update_plan(avoid, spinner_text="Finding a new time...")


def show_plan_attention():
    missed = missed_sessions()
    unplanned = unplanned_assignments()
    if not missed and not unplanned:
        return

    with st.container(border=True, key="plan_attention"):
        if missed:
            st.markdown(
                f":material/history: **{len(missed)} past session{'s' if len(missed) != 1 else ''} "
                f"{'weren' if len(missed) != 1 else 'wasn'}'t checked off.** "
                "If you missed them, StudyFlow can fit that work in before it's due."
            )
        if unplanned:
            names = ", ".join(f"**{assignment['name']}**" for assignment in unplanned[:3])
            more = f" and {len(unplanned) - 3} more" if len(unplanned) > 3 else ""
            st.markdown(f":material/playlist_add: Not in your plan yet: {names}{more}.")

        update_column, done_column = st.columns(2)
        with update_column:
            label = ":material/update: Reschedule missed work" if missed else ":material/update: Add them to my plan"
            if st.button(label, type="primary", width="stretch", key="attention_update"):
                st.session_state.flash = update_plan()
                st.rerun()
        with done_column:
            if missed and st.button(":material/done_all: I did them", width="stretch", key="attention_done"):
                mark_sessions_done(missed)
                st.session_state.flash = f"Marked {len(missed)} session{'s' if len(missed) != 1 else ''} as done."
                st.rerun()


# ============================================================
# ANALYTICS HELPERS
# ============================================================

CARD_HEIGHT = 340


def stat_tiles_html(tiles):
    cards = "".join(
        f'<div class="stat-tile"><div class="stat-icon" style="background-color:{color}">{icon}</div>'
        f'<div style="min-width:0"><div class="stat-label">{html.escape(label)}</div>'
        f'<div class="stat-value">{html.escape(value)}</div></div></div>'
        for icon, color, label, value in tiles
    )
    return f'<div class="stat-grid">{cards}</div>'


def card_title_html(icon, title):
    return f'<div class="card-title"><span class="card-icon">{icon}</span>{html.escape(title)}</div>'


def course_load_html(rows):
    if not rows:
        return '<p class="load-empty">Add courses in Settings to see your course load.</p>'

    parts = []
    for row in rows:
        share = row["done"] / row["total"] if row["total"] else 0
        parts.append(
            f'<div class="load-row"><div class="load-head"><span>{html.escape(row["course"])}</span>'
            f'<span class="load-count">{row["done"]}/{row["total"]}</span></div>'
            f'<div class="load-track"><div class="load-fill" style="width:{share * 100:.0f}%"></div></div></div>'
        )
    return "".join(parts)


def styled_chart(chart):
    return (
        chart.properties(height=230)
        .configure(background="transparent", font="Inter")
        .configure_axis(
            labelColor="#94A3B8",
            labelFontSize=12,
            gridColor="#334155",
            gridDash=[2, 4],
            domainColor="#475569",
            tickColor="#475569"
        )
        .configure_view(stroke=None)
    )


def horizontal_bars(values, label_field, value_field, color):
    most = max((value[value_field] for value in values), default=0)
    base = alt.Chart(alt.Data(values=values)).encode(
        y=alt.Y(f"{label_field}:N", sort=None, title=None, axis=alt.Axis(labelLimit=170, ticks=False)),
        x=alt.X(
            f"{value_field}:Q",
            title=None,
            scale=alt.Scale(domain=[0, max(1, most) * 1.15]),
            axis=alt.Axis(tickMinStep=1, format="d")
        ),
        tooltip=[alt.Tooltip(f"{label_field}:N"), alt.Tooltip(f"{value_field}:Q")]
    )
    bars = base.mark_bar(color=color, cornerRadiusTopRight=4, cornerRadiusBottomRight=4, height={"band": 0.6})
    labels = base.mark_text(align="left", dx=6, color="#CBD5E1", fontSize=12).encode(text=f"{value_field}:Q")
    return bars + labels


# ============================================================
# CHATBOT
# ============================================================

CHAT_SYSTEM_PROMPT = """You are StudyFlow AI: a capable, friendly, practical study assistant for high school students.
Help with understanding schoolwork, studying for tests, planning workload, writing, brainstorming, and explaining images of homework or notes.
Use the conversation history to maintain context. Be honest when you are uncertain, never claim to see an image that was not included, and give clear, useful answers. Format with Markdown only when it improves readability.
When the student is working on homework, guide them through the steps so they understand how to solve it, instead of only giving the final answer.
Always write times in 12-hour format with AM or PM (for example 4:30 PM), never in 24-hour format.
"""

ACTION_TAGS = (
    "add_assignment",
    "update_assignment",
    "remove_assignment",
    "add_event",
    "remove_event",
    "mark_done",
    "move_session",
    "update_plan",
    "update_settings",
    "make_flashcards"
)

ACTION_TAG = re.compile(r"<(" + "|".join(ACTION_TAGS) + r")>(.*?)</\1>", re.S)

# Models sometimes write an action as attributes instead: <make_flashcards request="..." count="5"/>
ATTRIBUTE_TAG = re.compile(
    r"<(" + "|".join(ACTION_TAGS) + r")((?:\s+[a-z_]+\s*=\s*(?:\"[^\"]*\"|'[^']*'))+)\s*/?>(?:\s*</\1>)?"
)

ATTRIBUTE = re.compile(r"([a-z_]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)')")

UNFINISHED_TAG = re.compile(r"<(" + "|".join(ACTION_TAGS) + r")(?:>.*|\s[^>]*)?$", re.S)

ASSIGNMENT_FIELDS = (
    "name", "type", "course", "due_date", "difficulty", "estimated_minutes", "priority", "description", "study_material"
)

STYLE_TIMES = ("wake", "bed", "dinner", "homework_start")

STYLE_NUMBERS = {"session_length": (10, 90), "max_per_day": (30, 600), "break_length": (0, 60)}

STYLE_SWITCHES = ("weekends", "lighter_fridays", "sunday_catchup")

STYLE_LABELS = {
    "wake": "wake-up time",
    "bed": "bedtime",
    "dinner": "dinner time",
    "homework_start": "homework start",
    "session_length": "session length",
    "max_per_day": "max study per day",
    "break_length": "break length",
    "weekends": "weekend studying",
    "lighter_fridays": "lighter Fridays",
    "sunday_catchup": "Sunday catch-up day",
    "peak": "peak productivity"
}


def schedule_context():
    now = student_now().replace(tzinfo=None)
    today = now.date()

    event_lines = [
        f"- {event['name']}: {event_time_label(event)}"
        for event in calendar_events.upcoming(one_time_events(), today, days_back=0)
    ]

    session_lines = []
    for session in plan_sessions():
        day = due_date_value(session.get("date"))
        if not day or not today - timedelta(days=7) <= day <= today + timedelta(days=14):
            continue
        end = session_end(session)
        status = " (done)" if session.get("done") else " (missed, not checked off)" if end and end < now else ""
        session_lines.append(
            f"- {day:%a %Y-%m-%d} {setup.pretty_time(session.get('start_time'))}-{setup.pretty_time(session.get('end_time'))}: "
            f"{session.get('assignment')} ({session.get('course') or 'General'}){status}"
        )

    plan_note = "" if st.session_state.study_plan else " The student has no study plan yet."
    events_text = "\n".join(event_lines[:30]) or "- none"
    sessions_text = "\n".join(session_lines[:60]) or "- none"
    return (
        f"It is now {setup.pretty_time(now.strftime('%H:%M'))} on {now:%A}.\n\n"
        f"The student's one-time events (appointments, games, trips):\n{events_text}\n\n"
        f"The student's study sessions from the past week through the next two weeks:{plan_note}\n{sessions_text}"
    )


def chat_context():
    student = setup.describe_for_ai(
        st.session_state.profile,
        st.session_state.courses,
        st.session_state.activities,
        st.session_state.study_style
    )
    ab_hint = (
        "\nWhen it helps, mention whether a day is an A day or a B day and which of their classes meet."
        if uses_ab_calendar() else ""
    )
    return f"""
{date_context()}

{schedule_context()}

About the student (use their first name naturally, and keep their schedule and preferences in mind):{ab_hint}
{student}

The student's current assignments are:
{json.dumps(st.session_state.assignments, indent=2)}

Changing the student's planner:
You can change the planner by putting action lines at the very end of your reply, one per line, each in
exactly the format shown below. Use them only when the student asks you to change something or clearly
tells you about a change (for example "I finished my bio session" or "I have a dentist appointment Tuesday
at 3"). First reply normally, in one or two sentences, saying what you're doing. StudyFlow carries out the
actions and adds a summary of what changed after your reply, so never write that summary yourself, and
never say you changed something without including its action line. Never mention the tags or show them
to the student.

<add_assignment>{{"name": "", "type": "", "course": "", "due_date": "YYYY-MM-DD", "difficulty": 3, "estimated_minutes": 60, "priority": "Medium", "description": ""}}</add_assignment>
Adds an assignment, test, quiz, or project.
- Difficulty must be 1-5. Priority must be Low, Medium, or High.
- Type must be one of: {", ".join(ASSIGNMENT_TYPES)}, or blank if you are not sure.
- {ASSIGNMENT_NAME_RULE}
- {course_rule()}

<update_assignment>{{"name": "exact current name", "changes": {{"due_date": "YYYY-MM-DD"}}}}</update_assignment>
Changes an existing assignment. "changes" holds only the fields that change, using the fields above.

<remove_assignment>{{"name": "exact current name"}}</remove_assignment>
Removes an assignment the student finished, dropped, or added by mistake.

<add_event>{{"name": "", "date": "YYYY-MM-DD", "start": "HH:MM", "end": "HH:MM", "all_day": false}}</add_event>
Adds a one-time event the student is busy for (an appointment, game, trip, or family plans).
Use 24-hour HH:MM inside the tag. If they give a start time but no end, make it one hour long.
For a whole day (a trip, being sick), set "all_day": true and leave start and end blank.

<remove_event>{{"name": "", "date": "YYYY-MM-DD"}}</remove_event>
Removes one of the one-time events listed above.

<mark_done>{{"assignment": "", "date": "YYYY-MM-DD"}}</mark_done>
Checks off the study sessions for that assignment on that date. Leave the date blank to check off every
session for it up to today.

<move_session>{{"assignment": "", "date": "YYYY-MM-DD"}}</move_session>
Moves the study session for that assignment on that date to another free time, when the student can't
make it. If they're busy for a stretch of time, use add_event and update_plan instead.

<update_plan>{{"start_over": false}}</update_plan>
Updates the study plan: reschedules missed sessions and fits in new or changed assignments and events
without moving anything else. It makes a plan if there isn't one. Set "start_over" to true only if the
student asks for a completely new plan. Add it after any other change that affects the schedule, and
when the student says they missed or forgot something.

<update_settings>{{"max_per_day": 180}}</update_settings>
Changes study settings. Allowed keys: wake, bed, dinner, homework_start (HH:MM); session_length (10-90),
max_per_day (30-600), and break_length (0-60) in minutes; weekends, lighter_fridays, and sunday_catchup
(true or false); peak ({", ".join(setup.PEAK_TIMES)}).

<make_flashcards>{{"request": "", "course": "", "count": 12}}</make_flashcards>
Makes flashcards. request describes exactly what the cards should cover, with every detail the student
gave (topic, unit, vocab words, or "the attached notes" if they sent a photo). course is one of the
student's courses, or blank. count is 5-20: the number they asked for, or 12. Never write the flashcards
yourself in the reply.

Rules for actions:
- Convert relative dates and times such as "next Friday" or "tonight" using the calendar and time above.
- Use names exactly as they appear above when changing or removing something.
- If you don't know which item, day, or time they mean, ask a short question instead of guessing.
- Email reminders, courses, and activities are changed in the Settings tab, so point the student there.
"""


def pull_actions(reply):
    actions = []
    for kind, raw in ACTION_TAG.findall(reply):
        try:
            data = parse_json_reply(raw)
        except json.JSONDecodeError:
            print("AI ACTION SKIPPED (bad JSON):", kind)
            continue
        if isinstance(data, dict):
            actions.append((kind, data))
    for kind, attributes in ATTRIBUTE_TAG.findall(reply):
        data = {}
        for key, double_quoted, single_quoted in ATTRIBUTE.findall(attributes):
            value = double_quoted or single_quoted
            data[key] = {"true": True, "false": False}.get(value.lower(), value)
        actions.append((kind, data))
    return visible_reply(reply), actions


def visible_reply(text):
    text = UNFINISHED_TAG.sub("", ATTRIBUTE_TAG.sub("", ACTION_TAG.sub("", text)))
    return re.sub(r"<[a-z_]*$", "", text).strip()


def find_assignment(text):
    """Index of the assignment `text` names, or None when it's missing or unclear."""
    wanted = " ".join(str(text or "").split()).casefold()
    if not wanted:
        return None
    names = [str(assignment.get("name") or "").casefold() for assignment in st.session_state.assignments]
    if wanted in names:
        return names.index(wanted)
    partial = [index for index, name in enumerate(names) if wanted in name or (name and name in wanted)]
    return partial[0] if len(partial) == 1 else None


def rename_sessions(old_key, assignment):
    for session in plan_sessions():
        if _work_key(session) == old_key:
            session["assignment"] = assignment["name"]
            session["course"] = assignment["course"]


def clean_time(value):
    return setup.from_time(setup.to_time(value)) if value else None


def act_add_assignment(data):
    assignment = normalize_assignment(data)
    assignment["course"] = guess_course(assignment)
    st.session_state.assignments.append(assignment)
    return f":material/assignment_add: Added **{assignment['name']}** (due {pretty_due_date(assignment['due_date'])})."


def act_update_assignment(data):
    index = find_assignment(data.get("name"))
    if index is None:
        return f":material/help: Couldn't find an assignment called **{data.get('name') or '?'}**."
    changes = data.get("changes") if isinstance(data.get("changes"), dict) else {
        key: value for key, value in data.items() if key != "name"
    }
    old = st.session_state.assignments[index]
    updated = normalize_assignment({
        **old,
        **{key: value for key, value in changes.items() if key in ASSIGNMENT_FIELDS and value not in (None, "")}
    })
    if "course" in changes:
        updated["course"] = guess_course(updated)
    st.session_state.assignments[index] = updated
    rename_sessions(_work_key(old, "name"), updated)
    changed = [key.replace("_", " ") for key in ASSIGNMENT_FIELDS if updated.get(key) != old.get(key)]
    return f":material/edit: Updated **{updated['name']}**" + (f" ({', '.join(changed)})." if changed else ".")


def act_remove_assignment(data):
    index = find_assignment(data.get("name"))
    if index is None:
        return f":material/help: Couldn't find an assignment called **{data.get('name') or '?'}**."
    removed = st.session_state.assignments.pop(index)
    key = _work_key(removed, "name")
    if st.session_state.study_plan:
        st.session_state.study_plan["study_sessions"] = [
            session for session in plan_sessions()
            if session.get("done") or _work_key(session) != key
        ]
    return f":material/delete: Removed **{removed['name']}** and its upcoming study sessions."


def act_add_event(data):
    day = due_date_value(data.get("date"))
    if day is None:
        return ":material/help: Couldn't add that event because the date wasn't clear."
    start = clean_time(data.get("start"))
    all_day = bool(data.get("all_day")) or not start
    start = start or calendar_events.DEFAULT_START
    end = clean_time(data.get("end"))
    if not end:
        end = (datetime.combine(day, setup.to_time(start)) + timedelta(hours=1)).strftime("%H:%M")
    event = calendar_events.new_event(data.get("name") or "Busy", day.isoformat(), start, end, all_day)
    save_one_time_events(one_time_events() + [event])
    clash = len(calendar_events.overlapping_sessions(event, plan_sessions()))
    note = f" It overlaps {clash} study session{'s' if clash != 1 else ''}." if clash else ""
    return f":material/event: Added **{event['name']}** on {event_time_label(event)}.{note}"


def act_remove_event(data):
    wanted = " ".join(str(data.get("name") or "").split()).casefold()
    day = due_date_value(data.get("date"))
    if not wanted and day is None:
        return ":material/help: Couldn't tell which event to remove."
    matches = [
        event for event in calendar_events.upcoming(one_time_events(), student_now().date())
        if (not wanted or wanted in event["name"].casefold() or event["name"].casefold() in wanted)
        and (day is None or event["date"] == day.isoformat())
    ]
    if not matches:
        return f":material/help: Couldn't find the event **{data.get('name') or '?'}**."
    removed = matches[0]
    delete_event(removed["id"])
    return f":material/event_busy: Removed **{removed['name']}** ({event_time_label(removed)})."


def sessions_for(assignment_text, day=None):
    """Indexes of unchecked sessions for the named assignment: on `day`, or up to today."""
    index = find_assignment(assignment_text)
    wanted = (
        str(st.session_state.assignments[index]["name"]).casefold() if index is not None
        else " ".join(str(assignment_text or "").split()).casefold()
    )
    if not wanted:
        return []
    today = student_now().date()
    found = []
    for position, session in enumerate(plan_sessions()):
        name = str(session.get("assignment") or "").casefold()
        session_day = due_date_value(session.get("date"))
        if session.get("done") or not session_day or not (wanted in name or name in wanted):
            continue
        if (session_day == day) if day else (session_day <= today):
            found.append(position)
    return found


def act_mark_done(data):
    found = sessions_for(data.get("assignment"), due_date_value(data.get("date")))
    if not found:
        return f":material/help: Couldn't find an unchecked session for **{data.get('assignment') or '?'}** to check off."
    sessions = st.session_state.study_plan["study_sessions"]
    for index in found:
        sessions[index]["done"] = True
        sessions[index]["done_on"] = student_now().date().isoformat()
    return (
        f":material/check_circle: Checked off {len(found)} session{'s' if len(found) != 1 else ''} "
        f"for **{sessions[found[0]]['assignment']}**."
    )


def act_move_session(data):
    day = due_date_value(data.get("date"))
    found = sessions_for(data.get("assignment"), day) if day else []
    if not found:
        return f":material/help: Couldn't find a session for **{data.get('assignment') or '?'}** on that day to move."
    return ":material/event_repeat: " + skip_session(found[0])


def act_update_settings(data):
    style = dict(st.session_state.study_style)
    changed = []
    for key, value in data.items():
        if key in STYLE_TIMES and clean_time(value):
            style[key] = clean_time(value)
        elif key in STYLE_NUMBERS and _whole_number(value, None) is not None:
            low, high = STYLE_NUMBERS[key]
            style[key] = max(low, min(high, _whole_number(value, None)))
        elif key in STYLE_SWITCHES and isinstance(value, bool):
            style[key] = value
        elif key == "peak" and str(value).title() in setup.PEAK_TIMES:
            style[key] = str(value).title()
        else:
            continue
        changed.append(STYLE_LABELS[key])
    if not changed:
        return ":material/help: Those settings can't be changed from chat. Open the Settings tab instead."
    st.session_state.study_style = style
    return f":material/tune: Updated your {', '.join(changed)}."


ACTIONS = {
    "add_assignment": act_add_assignment,
    "update_assignment": act_update_assignment,
    "remove_assignment": act_remove_assignment,
    "add_event": act_add_event,
    "remove_event": act_remove_event,
    "mark_done": act_mark_done,
    "move_session": act_move_session,
    "update_settings": act_update_settings
}


def carry_out(actions):
    """Run the AI's actions. Flashcards and the plan update go last so they see every other change."""
    notes = []
    flashcard_requests = []
    plan_request = None
    moved = False

    for kind, data in actions:
        moved = moved or kind == "move_session"
        if kind == "make_flashcards":
            flashcard_requests.append(data)
        elif kind == "update_plan":
            plan_request = {**(plan_request or {}), **data}
        else:
            try:
                notes.append(ACTIONS[kind](data))
            except Exception as error:
                print("AI ACTION FAILED:", kind, type(error).__name__, error)
                notes.append(":material/error: Something went wrong with one of those changes. Please make it in the app.")

    images = next(
        (message.get("images") for message in reversed(st.session_state.messages) if message["role"] == "user"),
        None
    ) or None
    for data in flashcard_requests[:2]:
        course = str(data.get("course") or "").strip()
        course = course if course in setup.course_names(st.session_state.courses) else ""
        card_set = make_requested_flashcards(
            str(data.get("request") or "").strip(), course, fcard.clamp_count(data.get("count")), images=images
        )
        notes.append(
            f":material/style: Made **{len(card_set['cards'])} flashcards**: *{card_set['assignment']}*. "
            "Open the **Flashcards** tab to study them."
            if card_set else
            ":material/help: I couldn't make those flashcards this time. Try asking again with a more specific topic."
        )

    if plan_request is not None:
        if plan_request.get("start_over") is True or not st.session_state.study_plan:
            with st.spinner("Building your study plan..."):
                plan = generate_plan()
            if plan:
                apply_plan(plan)
                notes.append(":material/calendar_month: Made your study plan. Open the **Study Plan** tab to see it.")
            else:
                notes.append(":material/help: Add an assignment first, then I can make your plan.")
        elif not moved:  # moving a session already updated the plan
            notes.append(":material/update: " + update_plan())

    return notes


def stream_reply(messages, placeholder):
    for attempt in range(AI_ATTEMPTS):
        text = ""
        started = time.monotonic()
        try:
            for chunk in stream_model(CHAT_MODEL, messages, CHAT_TEMPERATURE):
                piece = chunk.message.content or ""
                if piece:
                    text += piece
                    placeholder.markdown(visible_reply(text) + " ▌")
            print(f"AI {CHAT_MODEL} streamed in {time.monotonic() - started:.1f}s")
            return text
        except Exception as error:
            print(f"AI {CHAT_MODEL} stream failed after {time.monotonic() - started:.1f}s: {type(error).__name__}")
            if is_timeout(error) and not text and attempt < AI_ATTEMPTS - 1:
                continue
            raise


def model_history():
    """Recent messages for the AI, with what StudyFlow changed written as plain notes."""
    history = []
    for message in st.session_state.messages[-MAX_HISTORY_MESSAGES:]:
        notes = [re.sub(r":material/[a-z_]+:\s*", "", note).replace("**", "") for note in message.get("notes") or []]
        content = message.get("content", "")
        if notes:
            content += "\n\n(StudyFlow then did this: " + " ".join(notes) + ")"
        history.append({**message, "content": content})
    return history


def chatbot(message):
    """Answer the student's message. Returns True when the AI changed the planner."""
    messages = build_messages(chat_context(), CHAT_SYSTEM_PROMPT, conversation=model_history())

    placeholder = st.empty()
    placeholder.markdown('<span class="chat-thinking">Thinking…</span>', unsafe_allow_html=True)

    try:
        reply = stream_reply(messages, placeholder)
    except Exception as error:
        placeholder.empty()
        print("AI REQUEST FAILED:", type(error).__name__, error)
        if is_timeout(error):
            st.error("The AI took too long to answer. Please try again in a minute.")
        else:
            st.error("Unable to connect to Ollama.")
            st.code(str(error))
        return False

    reply, actions = pull_actions(reply or "")
    notes = []
    if actions:
        placeholder.markdown(reply or "On it.")
        notes = carry_out(actions)
        reply = reply or "Done."

    if not reply:
        placeholder.empty()
        st.error("The AI sent back an empty reply. Please try again.")
        return False

    placeholder.markdown("\n\n".join([reply] + notes))

    st.session_state.messages.append({
        "role": "assistant",
        "content": reply,
        "notes": notes
    })

    return bool(actions)


def render_chat_message(message):
    avatar = AVATAR_PATH if message["role"] == "assistant" else ":material/person:"

    with st.chat_message(message["role"], avatar=avatar):
        if message.get("content"):
            st.markdown(message["content"])

        for note in message.get("notes") or []:
            st.markdown(note)

        for image_data in message.get("images", []):
            try:
                st.image(uploads.decode_image(image_data), width=400)
            except Exception:
                st.caption(":material/image_not_supported: This image couldn't be displayed.")

        if message.get("had_image") and not message.get("images"):
            st.caption(":material/photo_camera: An image was attached here (images aren't saved).")


# ============================================================
# EMAIL REMINDERS
# ============================================================

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def email_settings():
    try:
        return (
            st.secrets["GMAIL_ADDRESS"],
            st.secrets["GMAIL_APP_PASSWORD"],
            st.secrets.get("APP_URL", "https://studyflowai26.streamlit.app")
        )
    except Exception:
        return None


def send_test_email(reminders):
    settings = email_settings()
    if not settings:
        st.warning("Email isn't set up on this copy of StudyFlow yet.")
        return

    sender, password, app_url = settings
    student = {
        "profile": st.session_state.profile,
        "assignments": st.session_state.assignments,
        "study_plan": st.session_state.study_plan
    }
    today = student_now().date()
    unsubscribe_url = reminder_email.unsubscribe_link(app_url, reminders["token"])
    email = reminder_email.build_email(student, today, app_url, unsubscribe_url)

    if not email:
        subject = "StudyFlow: reminders are on"
        text = (
            "Your StudyFlow reminders are set up. You don't have any study sessions today "
            "or anything due in the next few days, so there's nothing to remind you about yet.\n\n"
            f"Open StudyFlow: {app_url}\n\nTurn off reminders: {unsubscribe_url}"
        )
        body_html = "<p>" + html.escape(text).replace("\n", "<br>") + "</p>"
    else:
        subject, text, body_html = email

    try:
        reminder_email.send_email(sender, password, reminders["email"], subject, text, body_html, unsubscribe_url)
        st.success(f"Test email sent to {reminders['email']}. Check your spam folder if you don't see it.")
    except Exception as error:
        print("TEST EMAIL FAILED:", type(error).__name__, error)
        st.error("The test email couldn't be sent. Please try again later.")


def reminders_available():
    return SUPABASE is not None and bool(st.session_state.get("student_id"))


def reminder_form(prefix, reminders):
    suggested = (st.user.get("email") or "") if signed_in_with_google() else ""

    enabled = st.toggle(
        "Email me a daily study reminder",
        value=bool(reminders.get("enabled")),
        key=f"{prefix}_reminders_enabled"
    )
    email = st.text_input(
        "Email address",
        value=reminders.get("email") or suggested,
        placeholder="you@example.com",
        key=f"{prefix}_reminders_email"
    )
    send_time = st.time_input(
        "Send it at",
        value=setup.to_time(reminder_email.reminder_time(reminders)),
        step=900,
        format="12h",
        key=f"{prefix}_reminders_time"
    )
    age_ok = st.checkbox(
        "I'm 13 or older, or a parent or guardian said it's OK",
        value=bool(reminders.get("age_ok")),
        key=f"{prefix}_reminders_age"
    )
    return {
        "enabled": enabled,
        "email": email.strip(),
        "time": setup.from_time(send_time) or reminder_email.DEFAULT_TIME,
        "age_ok": age_ok
    }


def reminder_problem(values):
    if values["enabled"] and not EMAIL_PATTERN.match(values["email"]):
        return "Please enter a valid email address."
    if values["enabled"] and not values["age_ok"]:
        return "Please confirm you're 13 or older, or that a parent or guardian said it's OK."
    return None


def save_reminder_values(values):
    reminders = st.session_state.reminders or {}
    updated = {
        **values,
        "email": values["email"] if values["enabled"] else "",
        "token": reminders.get("token") or secrets.token_urlsafe(24)
    }
    try:
        st.session_state.reminders = storage.save_reminders(SUPABASE, st.session_state.student_id, updated)
    except Exception as error:
        print("REMINDER SAVE FAILED:", error)
        if "reminders" in str(error):
            st.error(
                "Couldn't save because the database is missing the reminders column. "
                "Run supabase/add_reminders.sql in the Supabase SQL Editor."
            )
        else:
            st.error("Couldn't save your reminder settings. Please try again.")
        with st.expander("Technical details"):
            st.code(str(error))
        return False
    return True


REMINDER_DESCRIPTION = (
    "Get one email a day with that day's study sessions and anything due in the next few days. "
    "Emails come from studyflowreminders@gmail.com, and every email has a link to turn them off."
)


def show_reminder_settings():
    reminders = st.session_state.reminders or {}

    st.subheader("Daily email reminders")
    st.caption(REMINDER_DESCRIPTION)

    if not reminders_available():
        st.info("Email reminders need saving to be turned on.")
        return

    values = reminder_form("settings", reminders)

    save_column, test_column = st.columns(2)

    with save_column:
        save_clicked = st.button("Save reminders", type="primary", width="stretch", key="save_reminders_button")

    with test_column:
        test_clicked = st.button(
            ":material/send: Send a test email",
            width="stretch",
            disabled=not (reminders.get("enabled") and reminders.get("email")),
            help="Save your reminder settings first, then send a test.",
            key="test_reminders_button"
        )

    if save_clicked:
        problem = reminder_problem(values)
        if problem:
            st.warning(problem)
        elif save_reminder_values(values):
            st.session_state.flash = "Reminders turned on" if values["enabled"] else "Reminders turned off"
            st.rerun()

    if test_clicked:
        send_test_email(reminders)

    if reminders.get("enabled") and reminders.get("email"):
        st.caption(
            f"Reminders go to **{reminders['email']}** every day around "
            f"{setup.pretty_time(reminder_email.reminder_time(reminders))}, on days with something to study or due soon."
        )


# ============================================================
# SETUP WIZARD
# ============================================================

REMINDER_STEP = len(SETUP_STEPS) - 1


def suggested_name():
    if signed_in_with_google():
        return st.user.get("name") or ""
    return ""


def render_setup_section(step, prefix):
    if step == 0:
        return setup.profile_form(prefix, st.session_state.profile, suggested_name())
    if step == 1:
        return setup.courses_editor(prefix, st.session_state.courses, st.session_state.profile.get("grade"))
    if step == 2:
        return setup.activities_editor(prefix, st.session_state.activities)
    if step == 3:
        return setup.routine_form(prefix, st.session_state.study_style)
    if step == 4:
        return setup.preferences_form(prefix, st.session_state.study_style, st.session_state.courses)

    st.caption(REMINDER_DESCRIPTION)
    if not reminders_available():
        st.info("Email reminders need saving, which isn't turned on here. You can skip this step.")
        return None
    draft = st.session_state.get(f"{prefix}_reminders_draft") or st.session_state.reminders or {}
    return reminder_form(prefix, draft)


def commit_setup_section(step, values, prefix):
    if step == 0:
        st.session_state.profile = {**st.session_state.profile, **values}
    elif step == 1:
        st.session_state.courses = [course for course in values if course["name"]]
        st.session_state[f"{prefix}_courses_draft"] = list(st.session_state.courses)
    elif step == 2:
        st.session_state.activities = [item for item in values if item["name"]]
        st.session_state[f"{prefix}_activities_draft"] = list(st.session_state.activities)
    elif step == REMINDER_STEP:
        if values is not None:
            st.session_state[f"{prefix}_reminders_draft"] = values
    else:
        st.session_state.study_style = {**st.session_state.study_style, **values}


def finish_setup():
    st.session_state.profile = {**st.session_state.profile, "onboarded": True}
    save()
    setup.reset_form_state()
    st.session_state.wizard_step = 0


def show_setup_wizard():
    step = min(st.session_state.get("wizard_step", 0), len(SETUP_STEPS) - 1)
    title, subtitle = SETUP_STEPS[step]
    last_step = step == len(SETUP_STEPS) - 1

    _, middle, _ = st.columns([1, 2.6, 1])

    with middle:
        st.markdown(
            """
            <div class="studyflow-title wizard-title">
                <span class="brand-name">StudyFlow</span>
                <span class="brand-ai"> AI</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.container(border=True):
            st.markdown(
                f'<div class="chat-kicker">Step {step + 1} of {len(SETUP_STEPS)}</div>',
                unsafe_allow_html=True
            )
            st.subheader(title)
            st.caption(subtitle)
            st.progress((step + 1) / len(SETUP_STEPS))

            values = render_setup_section(step, "setup")

            with st.container(key="wizard_nav"):
                back_column, _, next_column = st.columns([1, 1.5, 1])

                with back_column:
                    go_back = st.button(
                        ":material/arrow_back: Back",
                        disabled=step == 0,
                        width="stretch",
                        key="wizard_back"
                    )

                with next_column:
                    go_next = st.button(
                        ":material/check: Finish" if last_step else "Continue :material/arrow_forward:",
                        type="primary",
                        width="stretch",
                        key="wizard_next"
                    )

        skip = st.button(
            "Skip setup for now",
            type="tertiary",
            key="wizard_skip",
            help="You can fill this in later from the Settings tab."
        )

    if go_back:
        commit_setup_section(step, values, "setup")
        st.session_state.wizard_step = step - 1
        st.rerun()

    if go_next:
        if step == 0 and not values["name"]:
            with middle:
                st.warning("Please enter your name to continue.")
            st.stop()

        if step == REMINDER_STEP and values is not None:
            problem = reminder_problem(values)
            if problem:
                with middle:
                    st.warning(problem)
                st.stop()
            if values["enabled"] and not save_reminder_values(values):
                st.stop()

        commit_setup_section(step, values, "setup")

        if last_step:
            finish_setup()
            st.session_state.flash = "You're all set! Welcome to StudyFlow."
        else:
            save()
            st.session_state.wizard_step = step + 1

        st.rerun()

    if skip:
        commit_setup_section(step, values, "setup")
        finish_setup()
        st.rerun()

    st.stop()


if not st.session_state.profile.get("onboarded"):
    show_setup_wizard()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.sidebar.image(
    LOGO_PATH,
    width=140
    )

    if SUPABASE is None:
        st.caption("Saving is off because no database is connected.")
    elif signed_in_with_google():
        st.caption(f"Signed in as **{st.user.get('name') or st.user.get('email')}**")
        if st.button("Sign out"):
            st.logout()
    else:
        st.caption("Your plan is saved on this browser only.")
        if google_login_available() and st.button("Sign in with Google"):
            st.login()

    st.divider()
    st.subheader(":material/checklist: Your Setup")

    course_count = len(setup.course_names(st.session_state.courses))
    activity_count = len([a for a in st.session_state.activities if a.get("name")])
    routine = st.session_state.study_style

    st.caption(
        f"{course_count} course{'s' if course_count != 1 else ''} · "
        f"{activity_count} activit{'ies' if activity_count != 1 else 'y'}"
    )
    st.caption(
        f"Homework from {setup.pretty_time(routine.get('homework_start'))}, "
        f"bedtime {setup.pretty_time(routine.get('bed'))}"
    )
    st.caption("Change these anytime in the Settings tab.")

    if SUPABASE is not None and st.session_state.get("student_id"):
        st.divider()
        with st.expander(":material/lock_person: Your data"):
            st.caption(
                "StudyFlow saves your profile, courses, activities, routine, "
                "assignments, study plan, and chat messages so they're here "
                "next time. Images you attach are never saved. If you sign in "
                "with Google, StudyFlow keeps only an ID from Google, not your "
                "email address. If you turn on email reminders, StudyFlow saves "
                "the email you give it, only to send those reminders."
            )
            confirm_delete = st.checkbox("I want to delete all my StudyFlow data")
            if st.button("Delete my data", disabled=not confirm_delete):
                delete_my_data()
                st.rerun()


# ============================================================
# MAIN TITLE
# ============================================================

st.markdown(
    """
    <div class="studyflow-title">
        <span class="brand-name">StudyFlow</span>
        <span class="brand-ai"> AI</span>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    '<div class="studyflow-subtitle">Your AI-powered academic planner</div>',
    unsafe_allow_html=True
)

now = student_now()
part_of_day = "morning" if now.hour < 12 else "afternoon" if now.hour < 17 else "evening"
today_label = ""
if uses_ab_calendar() and ab_calendar.in_school_year(now.date()) and now.weekday() < 5:
    today_label = f" · {ab_calendar.short_label(now.date()) or 'No school'}"
first_name = html.escape((st.session_state.profile.get("name") or "").split(" ")[0])

st.markdown(
    f'<div class="greeting">Good {part_of_day}{", " + first_name if first_name else ""} <span class="greeting-icon">waving_hand</span></div>'
    f'<div class="greeting-date">{now:%A, %B} {now.day}{today_label}</div>',
    unsafe_allow_html=True
)

if "flash" in st.session_state:
    st.toast(st.session_state.pop("flash"), icon=":material/check_circle:")

st.divider()

# ============================================================
# TABS
# ============================================================

remove_past_assignments()
fix_general_courses()

tab1, tab2, tab3, analytics_tab, tab4, tab5 = st.tabs(
    [
        ":material/assignment_add: Assignments",
        ":material/calendar_clock: Study Plan",
        ":material/chat_bubble: AI Assistant",
        ":material/insights: Analytics",
        ":material/style: Flashcards",
        ":material/settings: Settings"
    ]
)

# ============================================================
# ASSIGNMENTS TAB
# ============================================================

with tab1:
    st.header(":material/edit_note: Add Assignments")
    st.caption(
        "Describe your work, upload a photo or PDF of an assignment sheet, "
        "syllabus, or planner page, or do both. StudyFlow will pull out the "
        "details so you can check and edit them before anything is added."
    )
    form_number = st.session_state.assignment_form

    assignment_input = st.text_area(
        "Describe your assignment",
        placeholder=
        "Example: I have an Algebra 2 final next Tuesday. "
        "It covers chapters 5-8 and I haven't studied yet.",
        key=f"assignment_text_{form_number}"
    )
    uploaded_file = st.file_uploader(
        "Photo or PDF (optional)",
        type=uploads.IMAGE_TYPES + ["pdf"],
        key=f"assignment_upload_{form_number}"
    )

    if st.button(
        "Analyze",
        width="stretch"
    ):
        if not assignment_input.strip() and uploaded_file is None:
            st.warning(
                "Describe an assignment or upload a file first."
            )
        else:
            found = None
            try:
                with st.spinner("Analyzing..."):
                    found = extract_assignments(
                        assignment_input.strip(),
                        uploaded_file
                    )
            except ValueError as error:
                st.error(str(error))

            if found == []:
                st.info("I couldn't find any assignments in that. Try adding more detail.")
            elif found:
                st.session_state.found_assignments = found
                st.session_state.found_batch += 1

    if st.session_state.found_assignments:
        st.write(
            "**Here's what I found.** Check every detail and fix anything "
            "that's wrong, uncheck anything you don't want, then add them."
        )
        course_options = setup.course_names(st.session_state.courses) + ["General"]
        for item in st.session_state.found_assignments:
            if item["course"] not in course_options:
                course_options.append(item["course"])

        edited = st.data_editor(
            [
                {"add": True, **item, "due_date": due_date_value(item["due_date"])}
                for item in st.session_state.found_assignments
            ],
            key=f"found_editor_{st.session_state.found_batch}",
            hide_index=True,
            width="stretch",
            column_order=[
                "add",
                "name",
                "type",
                "course",
                "due_date",
                "difficulty",
                "estimated_minutes",
                "priority",
                "description"
            ],
            column_config={
                "add": st.column_config.CheckboxColumn("Add?"),
                "name": st.column_config.TextColumn("Assignment", required=True),
                "type": st.column_config.SelectboxColumn("Type", options=ASSIGNMENT_TYPES),
                "course": st.column_config.SelectboxColumn("Course", options=course_options),
                "due_date": st.column_config.DateColumn("Due date", format="ddd, MMM D, YYYY"),
                "difficulty": st.column_config.NumberColumn("Difficulty (1-5)", min_value=1, max_value=5, step=1),
                "estimated_minutes": st.column_config.NumberColumn("Minutes", min_value=5, step=5),
                "priority": st.column_config.SelectboxColumn("Priority", options=["Low", "Medium", "High"]),
                "description": st.column_config.TextColumn("Notes")
            }
        )

        add_column, discard_column = st.columns(2)

        with add_column:
            if st.button(":material/check: Add Selected", type="primary", width="stretch"):
                chosen = [
                    normalize_assignment({**row, "due_date": due_date_text(row.get("due_date"))})
                    for row in edited
                    if row.get("add")
                ]
                if not chosen:
                    st.warning("Check at least one assignment to add, or discard them.")
                else:
                    st.session_state.assignments.extend(chosen)
                    st.session_state.found_assignments = []
                    st.session_state.assignment_form += 1
                    st.session_state.flash = (
                        f"Added {len(chosen)} assignment{'s' if len(chosen) != 1 else ''}!"
                    )
                    save()
                    st.rerun()

        with discard_column:
            if st.button("Discard", width="stretch"):
                st.session_state.found_assignments = []
                st.rerun()

    st.divider()
    st.header("Current Assignments")
    if not st.session_state.assignments:
        st.info(
            "No assignments yet. Add one above!"
        )

    else:
        for i, assignment in enumerate(
            st.session_state.assignments
        ):
            assignment_type = assignment.get("type") or ""
            is_prep = assignment_type in scheduler.PREP_TYPES

            with st.container(border=True, key=f"assignment_card_{i}"):
                col1, col2, col3 = st.columns(
                    [3, 2, 1]
                )
                with col1:
                    type_label = (
                        f'<div class="assignment-type">{html.escape(assignment_type.upper())}</div>'
                        if assignment_type else ""
                    )
                    st.markdown(
                        f'{type_label}<div class="assignment-name">'
                        f'{html.escape(assignment.get("name", ""))}</div>',
                        unsafe_allow_html=True
                    )
                    st.write(
                        assignment.get(
                            "description",
                            ""
                        )
                    )
                    
                    has_flashcards = fcard.find_set(st.session_state.flashcard_sets, assignment) is not None
                    if st.button(
                        ":material/style: Remake Flashcards" if has_flashcards else ":material/style: Create Flashcards",
                        key=f"flashcards_create_{i}",
                        help="Make a new set of flashcards for this assignment with AI"
                    ):
                        make_flashcards(assignment)
                    if has_flashcards:
                        st.caption(":material/check_circle: Flashcards are ready in the Flashcards tab.")

                with col2:
                    st.write(
                        f":material/assignment: **{assignment.get('course', 'General')}**"
                    )
                    due_label = (
                        f"{assignment_type.title()} on" if is_prep else "Due"
                    )
                    st.write(
                        f":material/event_note: {due_label}: "
                        f"{pretty_due_date(assignment.get('due_date'))}"
                    )
                    time_label = ":material/local_library: Prep time" if is_prep else ":material/timer: Work time"
                    st.write(
                        f"{time_label}: "
                        f"{assignment.get('estimated_minutes', 60)} min"
                    )

                with col3:
                    st.write(
                        f"Difficulty: "
                        f"{assignment.get('difficulty', 3)}/5"
                    )

                    st.write(
                        f"Priority: "
                        f"{assignment.get('priority', 'Medium')}"
                    )

                    edit_column, delete_column = st.columns(2)

                    with edit_column:
                        if st.button(
                            ":material/edit:",
                            key=f"edit_{i}",
                            help="Edit"
                        ):
                            edit_assignment_dialog(i)

                    with delete_column:
                        if st.button(
                            ":material/delete:",
                            key=f"delete_{i}",
                            help="Delete"
                        ):
                            st.session_state.assignments.pop(
                                i
                            )
                            save()
                            st.rerun()

# ============================================================
# STUDY PLAN TAB
# ============================================================

with tab2:
    st.header(":material/calendar_month: Your Study Plan")
    show_event_manager()
    if not st.session_state.study_plan:
        if st.button(
            ":material/auto_awesome: Generate Study Plan",
            width="stretch"
        ):
            if not st.session_state.assignments:
                st.warning(
                    "Add at least one assignment first."
                )
            else:
                with st.spinner(
                    "Building your personalized study plan..."
                ):
                    plan = generate_plan()
                if plan:
                    apply_plan(plan)
                    st.session_state.flash = "Study plan generated!"
                    st.rerun()
    else:
        update_column, rebuild_column = st.columns([2, 1])
        with update_column:
            if st.button(
                ":material/update: Update my plan",
                type="primary",
                width="stretch",
                key="plan_update",
                help="Keeps your plan and the sessions you moved. Reschedules missed sessions and "
                     "fits in new or changed assignments and events."
            ):
                st.session_state.flash = update_plan()
                st.rerun()
        with rebuild_column:
            if st.button(
                ":material/restart_alt: Start over",
                width="stretch",
                key="plan_rebuild",
                help="Makes a brand-new plan. Sessions you checked off stay."
            ):
                if not st.session_state.assignments:
                    st.warning("Add at least one assignment first.")
                else:
                    with st.spinner("Building your personalized study plan..."):
                        plan = generate_plan()
                    if plan:
                        apply_plan(plan)
                        st.session_state.flash = "Made you a new study plan."
                        st.rerun()
        show_plan_attention()

    if st.session_state.study_plan:
        sessions = st.session_state.study_plan.get(
            "study_sessions",
            []
        )
        zone_name = st.session_state.profile.get("timezone") or APP_TIMEZONE

        for item in st.session_state.study_plan.get("unscheduled", []):
            tip = (
                " Try raising your max study per day or turning on weekend studying in Settings."
                if "free time" in str(item.get("reason")) else ""
            )
            st.warning(
                f"Couldn't fit {item.get('minutes', '')} min of **{item.get('assignment', '')}**: "
                f"{item.get('reason', '')}.{tip}"
            )

        if not sessions:
            st.info("There was no free time to schedule before your due dates.")
        else:
            done_count = sum(1 for session in sessions if isinstance(session, dict) and session.get("done"))
            st.progress(
                done_count / len(sessions),
                text=f"{done_count} of {len(sessions)} study sessions done"
            )
            view = st.segmented_control(
                "View",
                ["Calendar", "List"],
                default="Calendar",
                format_func=lambda option: PLAN_VIEWS[option],
                key="plan_view",
                label_visibility="collapsed"
            )
            if view == "List":
                hide_done = st.toggle("Hide finished sessions", key="hide_done_sessions")
                show_session_list(sessions, zone_name, hide_done)
            else:
                show_plan_calendar(zone_name)

        show_calendar_export(sessions, zone_name)

        with st.expander(
            ":material/data_object: View Raw Study Plan"
        ):
            st.json(
                st.session_state.study_plan
            )

    else:
        st.info(
            "Your study plan will appear here "
            "after you generate it."
        )

# ============================================================
# AI ASSISTANT TAB
# ============================================================

with tab3:
    st.markdown('<div class="chat-kicker">Your study sidekick</div>', unsafe_allow_html=True)
    st.header(":material/forum: StudyFlow AI")
    st.markdown(
        '<p class="chat-subtitle">Ask about a tough topic, plan your week, '
        'or attach a photo of a problem for a step-by-step explanation.</p>',
        unsafe_allow_html=True
    )

    if st.session_state.messages and st.button(":material/delete: Clear chat"):
        st.session_state.messages = []
        save()
        st.rerun()

    conversation_area = st.container()

    with conversation_area:
        welcome_slot = st.empty()

        if not st.session_state.messages:
            welcome_slot.markdown(
                '<div class="welcome-card"><strong>Hi, I\'m StudyFlow AI </strong><br>'
                'Ask me to explain something, or tell me what\'s going on and I\'ll update your planner: '
                '"add my bio test on Friday", "I have a dentist appointment Tuesday at 3", '
                '"I missed yesterday\'s study session", "I finished my essay", or '
                '"make flashcards on the causes of World War I".</div>',
                unsafe_allow_html=True
            )

        for message in st.session_state.messages:
            render_chat_message(message)

    submission = st.chat_input(
        "Ask anything, or attach a photo...",
        accept_file=True,
        file_type=uploads.IMAGE_TYPES,
        key="chat_box"
    )

    if submission:
        message_text = (submission.text or "").strip()
        message_images = []

        if submission.files:
            try:
                message_images = [uploads.encode_image(submission.files[0])]
            except ValueError as error:
                st.error(str(error))

        if message_images and not message_text:
            message_text = "Can you explain this?"

        if message_text:
            user_message = {
                "role": "user",
                "content": message_text,
                "images": message_images
            }
            st.session_state.messages.append(user_message)
            welcome_slot.empty()

            with conversation_area:
                render_chat_message(user_message)

                with st.chat_message("assistant", avatar=AVATAR_PATH):
                    changed = chatbot(message_text)

                    save()

                    if changed:
                        st.rerun()

    st.html(
        """
        <span class="studyflow-script-marker"></span>
        <script>
        (() => {
            const doc = document;
            if (doc.__studyflowCopyHandler) {
                doc.removeEventListener('copy', doc.__studyflowCopyHandler);
            }
            doc.__studyflowCopyHandler = (event) => {
                const selection = doc.getSelection();
                if (!selection || selection.isCollapsed) return;
                const node = selection.anchorNode;
                const element = node && (node.nodeType === 1 ? node : node.parentElement);
                if (!element || !element.closest('[data-testid="stChatMessage"]')) return;

                const container = doc.createElement('div');
                for (let i = 0; i < selection.rangeCount; i++) {
                    container.appendChild(selection.getRangeAt(i).cloneContents());
                }
                container.querySelectorAll('*').forEach((el) => {
                    el.style.color = '#000';
                    el.style.backgroundColor = 'transparent';
                });
                // Build the wrapper with the DOM: st.html drops scripts that contain HTML tags in strings.
                container.style.color = '#000';
                container.style.background = 'transparent';

                event.clipboardData.setData('text/html', container.outerHTML);
                event.clipboardData.setData('text/plain', selection.toString());
                event.preventDefault();
            };
            doc.addEventListener('copy', doc.__studyflowCopyHandler);

            // Keep the chat scrolled to the newest message while the AI Assistant tab is open.
            const chatInput = () => doc.querySelector('[data-testid="stChatInput"]');
            let scrollQueued = false;
            const scrollChat = () => {
                scrollQueued = false;
                const input = chatInput();
                if (!input || !input.getClientRects().length) return;
                input.scrollIntoView({ block: 'end' });
            };
            const queueScroll = () => {
                if (scrollQueued) return;
                scrollQueued = true;
                requestAnimationFrame(scrollChat);
            };

            if (doc.__studyflowChatObserver) {
                doc.__studyflowChatObserver.disconnect();
            }
            doc.__studyflowChatObserver = new MutationObserver((mutations) => {
                const input = chatInput();
                const panel = input && input.closest('[role="tabpanel"]');
                if (panel && mutations.some((mutation) => panel.contains(mutation.target))) {
                    queueScroll();
                }
            });
            doc.__studyflowChatObserver.observe(doc.body, { childList: true, subtree: true, characterData: true });

            // Tab clicks don't bubble up to the document, so listen in the capture phase.
            if (doc.__studyflowTabClick) {
                doc.removeEventListener('click', doc.__studyflowTabClick, true);
            }
            doc.__studyflowTabClick = (event) => {
                if (event.target.closest('[role="tab"]')) setTimeout(queueScroll, 100);
            };
            doc.addEventListener('click', doc.__studyflowTabClick, true);
            queueScroll();
        })();
        </script>
        """,
        unsafe_allow_javascript=True
    )
    
# ============================================================
# ANALYTICS TAB
# ============================================================

with analytics_tab:
    st.header(":material/insights: Analytics")
    st.markdown(
        '<p class="chat-subtitle">Your study insights this week. '
        'Check off sessions in the Study Plan tab as you finish them.</p>',
        unsafe_allow_html=True
    )

    sessions = plan_sessions()
    assignments = st.session_state.assignments
    today = student_now().date()

    if not sessions and not assignments:
        st.info(
            "Add assignments and generate a study plan to see your analytics here."
        )
    else:
        stats = analytics.totals(sessions)
        week = analytics.minutes_by_day(sessions, today)
        streak = analytics.streak(sessions, today)

        st.markdown(
            stat_tiles_html([
                ("schedule", "#0F766E", "Study time (7d)",
                 analytics.pretty_minutes(sum(day["minutes"] for day in week))),
                ("check_circle", "#0F766E", "Completed",
                 f"{stats['done']} / {stats['total']}"),
                ("local_fire_department", "#0F766E", "Day streak",
                 f"{streak} day{'s' if streak != 1 else ''}"),
                ("adjust", "#0F766E", "Avg per task",
                 analytics.pretty_minutes(analytics.average_minutes(sessions)))
            ]),
            unsafe_allow_html=True
        )

        missed = analytics.missed(sessions, today)
        if missed:
            st.caption(
                f":material/warning: {len(missed)} past session{'s' if len(missed) != 1 else ''} "
                f"{'weren' if len(missed) != 1 else 'wasn'}'t checked off. "
                "Use Reschedule missed work on the Study Plan tab to fit that work back in."
            )

        hours_column, subject_column = st.columns(2)

        with hours_column:
            with st.container(border=True, height=CARD_HEIGHT):
                st.markdown(card_title_html("bar_chart", "Study Hours (Last 7 Days)"), unsafe_allow_html=True)
                values = [
                    {
                        "Day": f"{day['day']:%a}",
                        "Date": f"{day['day']:%a, %b} {day['day'].day}",
                        "Hours": round(day["minutes"] / 60, 2),
                        "Minutes": day["minutes"]
                    }
                    for day in week
                ]
                most = max(value["Hours"] for value in values)
                chart = (
                    alt.Chart(alt.Data(values=values))
                    .mark_bar(color="#14B8A6", cornerRadiusTopLeft=4, cornerRadiusTopRight=4, width={"band": 0.6})
                    .encode(
                        x=alt.X("Day:N", sort=None, title=None, axis=alt.Axis(labelAngle=0)),
                        y=alt.Y(
                            "Hours:Q",
                            title=None,
                            scale=alt.Scale(domain=[0, max(1, most)], nice=True),
                            axis=alt.Axis(tickMinStep=0.5)
                        ),
                        tooltip=[
                            alt.Tooltip("Date:N"),
                            alt.Tooltip("Minutes:Q", title="Minutes studied")
                        ]
                    )
                )
                st.altair_chart(styled_chart(chart), width="stretch", theme=None)
                if not stats["done"]:
                    st.caption("Check off study sessions to fill this in.")

        with subject_column:
            with st.container(border=True, height=CARD_HEIGHT):
                st.markdown(card_title_html("pie_chart", "Assignments by Subject"), unsafe_allow_html=True)
                subjects = analytics.assignments_by_subject(assignments)
                if subjects:
                    values = [{"Subject": row["course"], "Assignments": row["count"]} for row in subjects]
                    st.altair_chart(
                        styled_chart(horizontal_bars(values, "Subject", "Assignments", "#14B8A6")),
                        width="stretch",
                        theme=None
                    )
                else:
                    st.caption("No assignments yet.")

        difficulty_column, load_column = st.columns(2)

        with difficulty_column:
            with st.container(border=True, height=CARD_HEIGHT):
                st.markdown(card_title_html("signal_cellular_alt", "Difficulty Breakdown"), unsafe_allow_html=True)
                if assignments:
                    values = [
                        {"Difficulty": row["label"], "Assignments": row["count"]}
                        for row in analytics.difficulty_breakdown(assignments)
                    ]
                    st.altair_chart(
                        styled_chart(horizontal_bars(values, "Difficulty", "Assignments", "#14B8A6")),
                        width="stretch",
                        theme=None
                    )
                else:
                    st.caption("No assignments yet.")

        with load_column:
            with st.container(border=True, height=CARD_HEIGHT):
                st.markdown(card_title_html("menu_book", "Course Load"), unsafe_allow_html=True)
                load = analytics.course_load(sessions, setup.course_names(st.session_state.courses))
                st.markdown(course_load_html(load), unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown(card_title_html("event_upcoming", "Coming Up (Next 7 Days)"), unsafe_allow_html=True)
            upcoming = analytics.upcoming_deadlines(assignments, today)
            if not upcoming:
                st.caption("Nothing is due in the next 7 days.")
            for assignment in upcoming:
                days_left = assignment["days_left"]
                when = (
                    "today" if days_left == 0
                    else "tomorrow" if days_left == 1
                    else f"in {days_left} days"
                )
                st.write(
                    f":material/event_note: **{assignment.get('name', '')}** · "
                    f"{assignment.get('course', 'General')} · due {when} "
                    f"({pretty_due_date(assignment.get('due_date'))})"
                )

        with st.expander(":material/table: Show the numbers as tables"):
            st.dataframe(
                [{"Day": f"{day['day']:%A, %b} {day['day'].day}", "Minutes studied": day["minutes"]} for day in week],
                hide_index=True,
                width="stretch"
            )
            st.dataframe(
                [
                    {
                        "Course": row["course"],
                        "Sessions done": row["done"],
                        "Sessions planned": row["total"],
                        "Minutes done": row["done_minutes"],
                        "Minutes planned": row["total_minutes"]
                    }
                    for row in load
                ],
                hide_index=True,
                width="stretch"
            )


# ============================================================
# FLASHCARDS TAB
# ============================================================

with tab4:
    st.header(":material/style: Flashcards")
    show_flashcard_maker()
    flashcard_sets = st.session_state.flashcard_sets

    if not flashcard_sets:
        st.info(
            "No flashcards yet. Make your own above, press **Create Flashcards** on an assignment, "
            "or ask the AI Assistant to make some."
        )
    else:
        st.markdown(
            '<p class="chat-subtitle">Tap a card to flip it, then mark whether you knew it. '
            "Use Still learning to go back over the cards you missed.</p>",
            unsafe_allow_html=True
        )
        for card_set in flashcard_sets:
            label = card_set["assignment"]
            if card_set["course"]:
                label += f" · {card_set['course']}"
            with st.expander(
                f":material/style: {label} ({len(card_set['cards'])} cards)",
                expanded=len(flashcard_sets) == 1
            ):
                fcard.show_set(card_set, save_flashcards, delete_flashcard_set)


# ============================================================
# SETTINGS TAB
# ============================================================

with tab5:
    st.header(":material/settings: Settings")
    st.markdown(
        '<p class="chat-subtitle">Edit your profile, courses, and study preferences.</p>',
        unsafe_allow_html=True
    )

    profile_tab, courses_tab, activities_tab, style_tab, reminders_tab = st.tabs(
        [
            ":material/account_circle: Profile",
            ":material/book: Courses",
            ":material/directions_walk: Activities",
            ":material/wand_shine: Study Style",
            ":material/notifications: Reminders"
        ]
    )

    with profile_tab:
        profile_values = render_setup_section(0, "settings")
        if st.button("Save profile", type="primary", key="save_profile_button"):
            if not profile_values["name"]:
                st.warning("Please enter your name.")
            else:
                commit_setup_section(0, profile_values, "settings")
                save()
                st.session_state.flash = "Profile saved"
                st.rerun()

    with courses_tab:
        course_values = render_setup_section(1, "settings")
        if st.button("Save courses", type="primary", key="save_courses_button"):
            commit_setup_section(1, course_values, "settings")
            save()
            st.session_state.flash = "Courses saved"
            st.rerun()

    with activities_tab:
        activity_values = render_setup_section(2, "settings")
        if st.button("Save activities", type="primary", key="save_activities_button"):
            commit_setup_section(2, activity_values, "settings")
            save()
            st.session_state.flash = "Activities saved"
            st.rerun()

    with style_tab:
        st.subheader("Daily Routine")
        routine_values = render_setup_section(3, "settings")
        st.subheader("Study Preferences")
        preference_values = render_setup_section(4, "settings")
        if st.button("Save study style", type="primary", key="save_style_button"):
            commit_setup_section(3, {**routine_values, **preference_values}, "settings")
            save()
            st.session_state.flash = "Study style saved"
            st.rerun()

    with reminders_tab:
        show_reminder_settings()

# ============================================================
# FOOTER
# ============================================================

st.divider()
st.caption(
    "StudyFlow AI • Powered by Ollama"
)
