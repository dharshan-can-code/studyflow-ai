import streamlit as st
import html
import json
import re
import secrets
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from ollama import Client, ResponseError
import streamlit.components.v1 as components
from streamlit_cookies_controller import CookieController

import ab_calendar
import calendar_export
import scheduler
import setup_forms as setup
import storage
import uploads


# ============================================================
# PAGE SETTINGS
# ============================================================

st.set_page_config(
    page_title="StudyFlow AI",
    page_icon="assets/studyflow_logo.png",
    layout="wide"
)

st.markdown("""
<style>

/* ============================================================
   FONTS
   ============================================================ */

@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Inter:wght@400;500;600;700&family=Sixtyfour&family=Sora:wght@400;500;600;700&display=swap');


/* ============================================================
   MAIN APP
   ============================================================ */

.stApp {
    background-color: #0F172A;
    color: #F8FAFC;
}


[data-testid="stHeader"] {
    background-color: #0F172A;
}

[data-testid="stHeader"] > div {
    background-color: #0F172A;
}


.main .block-container {
    color: #F8FAFC;
}


/* ============================================================
   TEXT
   ============================================================ */

p {
    color: #F8FAFC !important;
    font-family: 'Inter', sans-serif !important;
}

label {
    color: #CBD5E1 !important;
    font-family: 'Inter', sans-serif !important;
}

small {
    color: #94A3B8 !important;
}


/* ============================================================
   HEADINGS
   ============================================================ */

h1, h2, h3 {
    font-family: 'Sora', sans-serif !important;
    color: #F8FAFC !important;
}


/* ============================================================
   STUDYFLOW AI TITLE
   ============================================================ */

.studyflow-title {
    font-family: 'Sixtyfour', monospace !important;
    font-size: 42px;
    font-weight: 400 !important;
    letter-spacing: -1px;
    line-height: 1.2;
    margin-bottom: 8px;
}

.studyflow-title .brand-name {
    color: #F8FAFC !important;
    font-family: 'Sixtyfour', monospace !important;
}

.studyflow-title .brand-ai {
    color: #8B5CF6 !important;
    font-family: 'Sixtyfour', monospace !important;
}


/* ============================================================
   SUBTITLE
   ============================================================ */

.studyflow-subtitle {
    font-family: 'Inter', sans-serif !important;
    color: #94A3B8 !important;
    font-size: 16px;
    margin-bottom: 20px;
}


/* ============================================================
   TEXT INPUTS
   ============================================================ */

.stTextInput input {
    background-color: #1E293B !important;
    color: #F8FAFC !important;

    border: none !important;
    border-radius: 10px !important;

    font-family: 'Inter', sans-serif !important;
}

.stTextInput input::placeholder {
    color: #64748B !important;
    opacity: 1 !important;
}

.stTextInput input:focus {
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
}


/* ============================================================
   TEXT AREAS
   ============================================================ */

.stTextArea textarea {
    background-color: #1E293B !important;
    color: #F8FAFC !important;

    border: none !important;
    border-radius: 10px !important;

    font-family: 'Inter', sans-serif !important;
}

.stTextArea textarea::placeholder {
    color: #64748B !important;
    opacity: 1 !important;
}

.stTextArea textarea:focus {
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
}


/* ============================================================
   SELECT BOX
   ============================================================ */

.stSelectbox [data-baseweb="select"] > div {
    background-color: #1E293B !important;
    color: #F8FAFC !important;

    border: none !important;
    border-radius: 10px !important;
}

.stSelectbox [data-baseweb="select"] span {
    color: #F8FAFC !important;
}


/* ============================================================
   BUTTONS
   ============================================================ */

.stButton button {
    background-color: #6366F1 !important;
    color: #FFFFFF !important;

    border: none !important;
    border-radius: 10px !important;

    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;

    transition: background-color 0.2s ease;
}

.stButton button:hover {
    background-color: #8B5CF6 !important;
    color: #FFFFFF !important;
}

.stButton button:focus {
    border: none !important;
    box-shadow: none !important;
}


/* ============================================================
   SIDEBAR
   ============================================================ */

[data-testid="stSidebar"] {
    background-color: #111C33 !important;
}

[data-testid="stSidebar"] * {
    font-family: 'Inter', sans-serif;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #F8FAFC !important;
}

[data-testid="stSidebar"] label {
    color: #CBD5E1 !important;
}


/* ============================================================
   TABS
   ============================================================ */

.stTabs [data-baseweb="tab-list"] {
    background-color: transparent !important;
    gap: 8px;
}

.stTabs [data-baseweb="tab"] {
    color: #94A3B8 !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600;
}

.stTabs [aria-selected="true"] {
    color: #8B5CF6 !important;
}


/* ============================================================
   DIVIDERS
   ============================================================ */

hr {
    border: none !important;
    border-top: 1px solid #1E293B !important;
}


/* ============================================================
   CONTAINERS / CARDS
   ============================================================ */

[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #1E293B !important;

    border: none !important;
    border-radius: 12px !important;
}


/* ============================================================
   CHAT
   ============================================================ */

[data-testid="stChatMessage"] {
    background: rgba(20, 29, 50, .84) !important;
    border: 1px solid rgba(148, 163, 184, .12) !important;
    border-radius: 16px !important;
    padding: 1rem 1.1rem !important;
    margin: .75rem 0 !important;
    box-shadow: 0 12px 32px rgba(0, 0, 0, .10);
}

[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li {
    line-height: 1.65;
}

[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] td,
[data-testid="stChatMessage"] th,
[data-testid="stChatMessage"] blockquote,
[data-testid="stChatMessage"] h4,
[data-testid="stChatMessage"] h5 {
    color: #F8FAFC !important;
}

[data-testid="stChatMessage"] li::marker {
    color: #a78bfa;
}

[data-testid="stChatInput"] {
    background: #18233d !important;
    border: 1px solid rgba(167, 139, 250, .35) !important;
    border-radius: 15px !important;
}

[data-testid="stChatInput"] > div {
    background: transparent !important;
    border: none !important;
}

[data-testid="stChatInput"] textarea {
    color: #F8FAFC !important;
    background: transparent !important;
    border: none !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #8491a8 !important;
}

[data-testid="stChatInput"] button {
    color: #a78bfa !important;
}

.chat-kicker {
    color: #a78bfa;
    font-family: 'DM Mono', monospace;
    font-size: .72rem;
    letter-spacing: .13em;
    text-transform: uppercase;
    margin-bottom: .4rem;
}

.chat-subtitle {
    color: #a9b5c9 !important;
    font-size: 1rem;
    line-height: 1.65;
    max-width: 39rem;
    margin: .25rem 0 1.25rem;
}

.welcome-card {
    background: linear-gradient(115deg, rgba(124, 58, 237, .22), rgba(30, 41, 72, .75));
    border: 1px solid rgba(196, 181, 253, .25);
    border-radius: 18px;
    padding: 1.15rem 1.25rem;
    margin: .5rem 0 1.5rem;
    color: #e9e5ff;
    font-family: 'Inter', sans-serif;
    line-height: 1.6;
}

.welcome-card strong {
    color: #fff;
}


/* ============================================================
   GENERAL STREAMLIT COMPONENT BORDERS
   ============================================================ */

div[data-baseweb="input"] {
    border: none !important;
}

div[data-baseweb="textarea"] {
    border: none !important;
}

div[data-baseweb="select"] {
    border: none !important;
}


/* ============================================================
   FILE UPLOADER
   ============================================================ */

[data-testid="stFileUploaderDropzone"] {
    background-color: #1E293B !important;
    border: 1px dashed #334155 !important;
    border-radius: 10px !important;
}

[data-testid="stFileUploaderDropzone"] span,
[data-testid="stFileUploaderDropzone"] small,
[data-testid="stFileUploaderDropzone"] p {
    color: #CBD5E1 !important;
}

[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] {
    background-color: #334155 !important;
    color: #F8FAFC !important;
    border: none !important;
}


/* ============================================================
   GREETING AND SETUP
   ============================================================ */

.greeting {
    font-family: 'Sora', sans-serif;
    font-size: 26px;
    font-weight: 600;
    color: #F8FAFC;
    margin-top: 4px;
}

.greeting-date {
    font-family: 'Inter', sans-serif;
    color: #94A3B8;
    font-size: 15px;
    margin-bottom: 6px;
}

.wizard-title {
    font-size: 30px;
    text-align: center;
    margin: 24px 0 16px;
}

[data-testid="stSidebar"] [data-testid="stIconMaterial"] {
    font-family: 'Material Symbols Rounded' !important;
}

[data-testid="stToast"] {
    background-color: #1E293B !important;
    border: 1px solid #334155 !important;
}

.stButton button[kind="tertiary"] {
    background: transparent !important;
    color: #94A3B8 !important;
    font-weight: 500 !important;
}

.stButton button[kind="tertiary"]:hover {
    background: transparent !important;
    color: #F8FAFC !important;
}

[data-testid="stProgressBarTrack"],
[data-testid="stProgress"] [role="progressbar"] > div {
    background-color: #1E293B !important;
}

[data-testid="stProgressBarTrack"] > div,
[data-testid="stProgress"] [role="progressbar"] > div > div {
    background-color: #8B5CF6 !important;
}

[data-testid="stSelectbox"] [role="group"],
[data-testid="stNumberInputContainer"],
[data-testid="stNumberInput"] input,
[data-testid="stTimeInputTimeDisplay"],
[data-testid="stTimeInput"] [data-baseweb="select"] > div,
[data-testid="stTimeInput"] [data-baseweb="input"] {
    background-color: #1E293B !important;
    color: #F8FAFC !important;
    border-radius: 10px !important;
}

[data-testid="stSelectbox"] [role="group"] *,
[data-testid="stNumberInputContainer"] input,
[data-testid="stTimeInput"] input,
[data-testid="stTimeInputTimeDisplay"] * {
    color: #F8FAFC !important;
    background-color: transparent !important;
}

.chat-thinking {
    color: #94A3B8;
    font-style: italic;
}

[data-testid="stMarkdownContainer"] a {
    color: #A78BFA !important;
}

[data-testid="stMarkdownContainer"] a:hover {
    color: #C4B5FD !important;
}

[data-testid="stSelectbox"] input::placeholder {
    color: #94A3B8 !important;
    opacity: 1 !important;
}

[data-testid="stNumberInputContainer"] button {
    background-color: #334155 !important;
    color: #F8FAFC !important;
}

[role="listbox"],
[data-baseweb="popover"] ul,
[data-baseweb="popover"] [role="dialog"] {
    background-color: #1E293B !important;
}

[role="option"],
[role="option"] * {
    color: #F8FAFC !important;
}

[role="option"]:hover,
[role="option"][data-focused="true"],
[role="option"][aria-selected="true"] {
    background-color: #334155 !important;
}

[data-testid="stButtonGroup"] button {
    background-color: #1E293B !important;
    border: 1px solid #334155 !important;
    color: #CBD5E1 !important;
}

[data-testid="stButtonGroup"] button p {
    color: #CBD5E1 !important;
}

[data-testid="stButtonGroup"] button:hover {
    border-color: #8B5CF6 !important;
}

[data-testid="stButtonGroup"] button[aria-pressed="true"],
[data-testid="stButtonGroup"] button[aria-checked="true"],
[data-testid="stButtonGroup"] button[data-selected="true"],
[data-testid="stButtonGroup"] button[kind$="Active"] {
    background-color: rgba(139, 92, 246, .25) !important;
    border-color: #8B5CF6 !important;
}

[data-testid="stButtonGroup"] button[aria-pressed="true"] p,
[data-testid="stButtonGroup"] button[aria-checked="true"] p,
[data-testid="stButtonGroup"] button[data-selected="true"] p,
[data-testid="stButtonGroup"] button[kind$="Active"] p {
    color: #F8FAFC !important;
}


/* ============================================================
   SCROLLBAR
   ============================================================ */

::-webkit-scrollbar {
    width: 8px;
}

::-webkit-scrollbar-track {
    background: #0F172A;
}

::-webkit-scrollbar-thumb {
    background: #334155;
    border-radius: 10px;
}

[data-testid="stSidebarCollapseButton"] button {
    color: #F8FAFC !important;
}

[data-testid="stSidebarCollapseButton"] button span {
    font-family: 'Material Symbols Rounded' !important;
    font-size: 24px !important;
}

</style>
""", unsafe_allow_html=True)

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

TASK_TIMEOUT_SECONDS = 12

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

LOGO_PATH = "assets/studyflow_logo.png"

APP_TIMEZONE = "America/New_York"

MAX_HISTORY_MESSAGES = 50

GUEST_COOKIE = "studyflow_guest_token"

SETUP_STEPS = [
    ("Basic Info", "Tell us about yourself"),
    ("Your Courses", "Add the classes you're taking this year"),
    ("Activities", "Sports, clubs, a job: anything that takes up your time"),
    ("Daily Routine", "When your day starts, ends, and when you do homework"),
    ("Study Preferences", "How you like to study, so your plan fits you")
]


# ============================================================
# SESSION STATE
# ============================================================

for field, empty in storage.SAVED_FIELDS.items():
    if field not in st.session_state:
        st.session_state[field] = empty()

if "found_assignments" not in st.session_state:
    st.session_state.found_assignments = []

if "found_batch" not in st.session_state:
    st.session_state.found_batch = 0


def prepare_saved_data():
    st.session_state.courses = setup.normalize_courses(st.session_state.courses)
    st.session_state.activities = setup.normalize_activities(st.session_state.activities)
    st.session_state.profile = setup.complete_profile(st.session_state.profile)
    st.session_state.study_style = setup.complete_study_style(st.session_state.study_style)


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
                if st.button("Sign in with Google", type="primary", use_container_width=True):
                    st.login()

    with guest_column:
        with st.container(border=True):
            st.subheader("Continue without signing in")
            st.caption("Your plan is saved on this browser only. You can sign in later.")
            if st.button("Continue as guest", use_container_width=True):
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
            st.toast("Couldn't save your latest changes. Check your connection.", icon="⚠️")


def delete_my_data():
    storage.delete_student(SUPABASE, st.session_state.student_id)

    for field, empty in storage.SAVED_FIELDS.items():
        st.session_state[field] = empty()

    prepare_saved_data()
    setup.reset_form_state()
    st.session_state.wizard_step = 0
    st.session_state.found_assignments = []
    st.session_state.student_id = None
    st.session_state.loaded_identity = None


COOKIE_SLOT = st.container()

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

    lines = [f"Today is {today:%A}, {today:%Y-%m-%d}" + (f" ({today_note})." if today_note else ".")]

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


def ask_ai(prompt, system_message, conversation=None, use_json=True, images=None, model=MODEL, temperature=0):
    try:
        messages = build_messages(prompt, system_message, conversation, images)
        response = call_model(model, messages, use_json, temperature)

        result = response.message.content

        print("RAW RESPONSE:")
        print(repr(result))

        if not use_json:
            return result.strip()

        cleaned_result = result.strip()

        if cleaned_result.startswith("```json"):
            cleaned_result = cleaned_result[7:]
        elif cleaned_result.startswith("```"):
            cleaned_result = cleaned_result[3:]

        if cleaned_result.endswith("```"):
            cleaned_result = cleaned_result[:-3]

        cleaned_result = cleaned_result.strip()

        parsed = json.loads(cleaned_result)

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


def normalize_assignment(assignment):
    priority = _text(assignment.get("priority"), "Medium").title()
    if priority not in ("Low", "Medium", "High"):
        priority = "Medium"

    return {
        "name": _text(assignment.get("name"), "Untitled assignment"),
        "course": _text(assignment.get("course"), "General"),
        "due_date": _text(assignment.get("due_date"), "Not set"),
        "difficulty": min(5, max(1, _whole_number(assignment.get("difficulty"), 3))),
        "estimated_minutes": max(5, _whole_number(assignment.get("estimated_minutes"), 60)),
        "priority": priority,
        "description": _text(assignment.get("description"), "")
    }


def find_assignments_in_upload(uploaded_file):
    if uploads.is_pdf(uploaded_file):
        document_text = uploads.pdf_text(uploaded_file)
        source = f'Here is the text of the uploaded document:\n"""\n{document_text}\n"""'
        images = None
        model = MODEL
    else:
        images = [uploads.encode_image(uploaded_file)]
        source = (
            "The attached image is a photo of the student's assignment sheet, "
            "syllabus, or planner page."
        )
        model = VISION_MODEL

    prompt = f"""
{date_context()}

The student's courses are:
{json.dumps(setup.course_names(st.session_state.courses))}

{source}

Find every assignment, test, quiz, project, or other item with a due date.
Return ONLY valid JSON.
Use exactly this format:
{{
    "assignments": [
        {{
            "name": "",
            "course": "",
            "due_date": "YYYY-MM-DD",
            "difficulty": 3,
            "estimated_minutes": 60,
            "priority": "Medium",
            "description": ""
        }}
    ]
}}

Rules:
- Only include items that actually appear in the document. Never invent items.
- Match the course to one of the student's courses when it clearly fits.
- If an item has no due date, use "Not set".
- If a date has no year, use the next upcoming date.
- Difficulty must be 1-5.
- Priority must be Low, Medium, or High.
- Estimate realistic focused work time.
- If nothing is found, return {{"assignments": []}}.
"""
    result = ask_ai(
        prompt,
        "You are an AI academic planner that reads assignment sheets. "
        "Return only valid JSON.",
        images=images,
        model=model
    )

    if result is None:
        return None

    found = result.get("assignments")
    if not isinstance(found, list):
        return []

    return [normalize_assignment(item) for item in found if isinstance(item, dict)]


def analyze_assignment(text):

    prompt = f"""
{date_context()}

The student's courses are:
{json.dumps(setup.course_names(st.session_state.courses))}

Analyze this student's academic task:
"{text}"
Return ONLY valid JSON.
Use exactly this format:
{{
    "name": "",
    "course": "",
    "due_date": "YYYY-MM-DD",
    "difficulty": 1,
    "estimated_minutes": 60,
    "priority": "Medium",
    "description": ""
}}

Rules:
- Difficulty must be 1-5.
- 1 = extremely easy.
- 5 = extremely difficult.
- Priority must be Low, Medium, or High.
- Estimate realistic focused work time.
- Use YYYY-MM-DD for the due date.
- Do not invent unnecessary information.
- Match the course to one of the student's courses when it clearly fits,
  using that course's exact name.
- If the student gives a relative date such as
  "next Tuesday", convert it into the correct date.
"""
    return ask_ai(
        prompt,
        "You are an intelligent AI academic planner. "
        "Return only valid JSON."
    )

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
        st.subheader("📤 Export to your calendar")

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
            "📅 Download calendar file (.ics)",
            data=calendar_export.build_ics(
                sessions,
                st.session_state.assignments,
                zone_name,
                include_due
            ),
            file_name="studyflow-study-plan.ics",
            mime="text/calendar",
            type="primary",
            use_container_width=True,
            key="export_download"
        )

        with st.expander("How to add it to Google Calendar"):
            st.markdown(
                "1. Open **calendar.google.com** on a computer.\n"
                "2. Click **⚙️ Settings**, then **Import & export**.\n"
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
            "notes": session["description"][:300],
            "part": f"{session['part']} of {session['parts']}",
            "minutes": session["minutes"],
            "due": session["due_date"]
        })

    prompt = f"""
Write one study task for each study session below.

Sessions:
{json.dumps(details, indent=1)}

Rules:
- Each task says exactly what to do in that session, in 6 to 15 words.
- Parts of the same assignment build on each other, from getting started to finishing.
- For tests and quizzes, use active study: practice problems, self-quizzing, flashcards, reviewing mistakes.
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
        data = json.loads(response.message.content)
        print(f"AI tasks written in {time.monotonic() - started:.1f}s")
    except Exception as error:
        print(f"AI tasks skipped after {time.monotonic() - started:.1f}s: {type(error).__name__}")
        return {}

    tasks = {}
    for item in data.get("tasks", []) if isinstance(data, dict) else []:
        if isinstance(item, dict) and str(item.get("task") or "").strip():
            tasks[_whole_number(item.get("id"), 0)] = str(item["task"]).strip()
    return tasks


def generate_plan():
    if not st.session_state.assignments:
        return None

    sessions, unscheduled = scheduler.build_plan(
        st.session_state.assignments,
        setup.complete_study_style(st.session_state.study_style),
        setup.normalize_activities(st.session_state.activities),
        student_now().replace(tzinfo=None),
        is_school_day_for_student
    )

    tasks = write_tasks(sessions)
    for number, session in enumerate(sessions, start=1):
        session["task"] = tasks.get(number) or scheduler.default_task(session)

    return {
        "study_sessions": [scheduler.public_session(session) for session in sessions],
        "unscheduled": unscheduled
    }


# ============================================================
# CHATBOT
# ============================================================

CHAT_SYSTEM_PROMPT = """You are StudyFlow AI: a capable, friendly, practical study assistant for high school students.
Help with understanding schoolwork, studying for tests, planning workload, writing, brainstorming, and explaining images of homework or notes.
Use the conversation history to maintain context. Be honest when you are uncertain, never claim to see an image that was not included, and give clear, useful answers. Format with Markdown only when it improves readability.
When the student is working on homework, guide them through the steps so they understand how to solve it, instead of only giving the final answer.
"""

ASSIGNMENT_TAG = re.compile(r"<add_assignment>(.*?)</add_assignment>", re.S)

UNFINISHED_TAG = re.compile(r"<add_assignment>.*$", re.S)


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

About the student (use their first name naturally, and keep their schedule and preferences in mind):{ab_hint}
{student}

The student's current assignments are:
{json.dumps(st.session_state.assignments, indent=2)}

Adding assignments:
If, and only if, the student asks you to add an assignment, test, quiz, or project to their planner,
reply normally, mention that you added it, and then put one line at the very end of your reply for each item,
in exactly this format:
<add_assignment>{{"name": "", "course": "", "due_date": "YYYY-MM-DD", "difficulty": 3, "estimated_minutes": 60, "priority": "Medium", "description": ""}}</add_assignment>
- Difficulty must be 1-5. Priority must be Low, Medium, or High.
- Convert relative dates such as "next Friday" into YYYY-MM-DD using the calendar above.
- Never use these tags for anything else, and never mention them to the student.
"""


def pull_assignment_tags(reply):
    added = []

    for raw in ASSIGNMENT_TAG.findall(reply):
        raw = raw.strip()
        for fence in ("```json", "```"):
            raw = raw.removeprefix(fence)
        raw = raw.removesuffix("```").strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        if isinstance(data, dict):
            added.append(normalize_assignment(data))

    clean_reply = UNFINISHED_TAG.sub("", ASSIGNMENT_TAG.sub("", reply)).strip()
    return clean_reply, added


def visible_reply(text):
    text = UNFINISHED_TAG.sub("", ASSIGNMENT_TAG.sub("", text))
    return re.sub(r"<[a-z_]*$", "", text).strip()


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


def chatbot(message):
    history = st.session_state.messages[-MAX_HISTORY_MESSAGES:]
    messages = build_messages(chat_context(), CHAT_SYSTEM_PROMPT, conversation=history)

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
        return None

    if not reply:
        placeholder.empty()
        st.error("The AI sent back an empty reply. Please try again.")
        return None

    reply, added = pull_assignment_tags(reply)

    if added:
        st.session_state.assignments.extend(added)

        if not reply:
            names = ", ".join(f"**{assignment['name']}**" for assignment in added)
            reply = f"Added {names} to your assignments."

    if not reply:
        placeholder.empty()
        st.error("The AI sent back an empty reply. Please try again.")
        return None

    placeholder.markdown(reply)

    st.session_state.messages.append({
        "role": "assistant",
        "content": reply
    })

    return reply


def render_chat_message(message):
    avatar = LOGO_PATH if message["role"] == "assistant" else "🙂"

    with st.chat_message(message["role"], avatar=avatar):
        if message.get("content"):
            st.markdown(message["content"])

        for image_data in message.get("images", []):
            try:
                st.image(uploads.decode_image(image_data), width=400)
            except Exception:
                st.caption("📷 This image couldn't be displayed.")

        if message.get("had_image") and not message.get("images"):
            st.caption("📷 An image was attached here (images aren't saved).")


# ============================================================
# SETUP WIZARD
# ============================================================

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
    return setup.preferences_form(prefix, st.session_state.study_style, st.session_state.courses)


def commit_setup_section(step, values, prefix):
    if step == 0:
        st.session_state.profile = {**st.session_state.profile, **values}
    elif step == 1:
        st.session_state.courses = [course for course in values if course["name"]]
        st.session_state[f"{prefix}_courses_draft"] = list(st.session_state.courses)
    elif step == 2:
        st.session_state.activities = [item for item in values if item["name"]]
        st.session_state[f"{prefix}_activities_draft"] = list(st.session_state.activities)
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

            back_column, _, next_column = st.columns([1, 1.5, 1])

            with back_column:
                go_back = st.button(
                    "‹ Back",
                    disabled=step == 0,
                    use_container_width=True,
                    key="wizard_back"
                )

            with next_column:
                go_next = st.button(
                    "Finish ✓" if last_step else "Continue ›",
                    type="primary",
                    use_container_width=True,
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
    "assets/studyflow_logo.png",
    width=50
    )

    if SUPABASE is None:
        st.caption("💾 Saving is off because no database is connected.")
    elif signed_in_with_google():
        st.caption(f"Signed in as **{st.user.get('name') or st.user.get('email')}**")
        if st.button("Sign out"):
            st.logout()
    else:
        st.caption("💾 Your plan is saved on this browser only.")
        if google_login_available() and st.button("Sign in with Google"):
            st.login()

    st.divider()
    st.subheader("📋 Your Setup")

    course_count = len(setup.course_names(st.session_state.courses))
    activity_count = len([a for a in st.session_state.activities if a.get("name")])
    routine = st.session_state.study_style

    st.caption(
        f"📚 {course_count} course{'s' if course_count != 1 else ''} · "
        f"🏃 {activity_count} activit{'ies' if activity_count != 1 else 'y'}"
    )
    st.caption(
        f"⏰ Homework from {setup.pretty_time(routine.get('homework_start'))}, "
        f"bedtime {setup.pretty_time(routine.get('bed'))}"
    )
    st.caption("Change these anytime in the ⚙️ Settings tab.")

    if SUPABASE is not None and st.session_state.get("student_id"):
        st.divider()
        with st.expander("🔒 Your data"):
            st.caption(
                "StudyFlow saves your profile, courses, activities, routine, "
                "assignments, study plan, and chat messages so they're here "
                "next time. Images you attach are never saved. If you sign in "
                "with Google, StudyFlow keeps only an ID from Google, not your "
                "email address."
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
    f'<div class="greeting">Good {part_of_day}{", " + first_name if first_name else ""} 👋</div>'
    f'<div class="greeting-date">{now:%A, %B} {now.day}{today_label}</div>',
    unsafe_allow_html=True
)

if "flash" in st.session_state:
    st.toast(st.session_state.pop("flash"), icon="✅")

st.divider()

# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "📝 Assignments",
        "📅 Study Plan",
        "💬 AI Assistant",
        "⚙️ Settings"
    ]
)

# ============================================================
# ASSIGNMENTS TAB
# ============================================================

with tab1:
    st.header("📝 Add an Assignment")
    assignment_input = st.text_area(
        "Describe your assignment",
        placeholder=
        "Example: I have an Algebra 2 final next Tuesday. "
        "It covers chapters 5-8 and I haven't studied yet."
    )
    if st.button(
        "🤖 Analyze Assignment",
        use_container_width=True
    ):
        if not assignment_input.strip():
            st.warning(
                "Please enter an assignment first."
            )
        else:
            with st.spinner(
                "🤖 Analyzing assignment..."
            ):
                assignment = analyze_assignment(
                    assignment_input
                )

            if assignment:
                st.session_state.assignments.append(
                    normalize_assignment(assignment)
                )
                save()

                st.success(
                    "Assignment added!"
                )

                st.rerun()

    st.subheader("📷 Or upload an assignment sheet")
    st.caption(
        "Upload a photo of an assignment sheet, syllabus, or planner page, "
        "or a PDF. StudyFlow will find the assignments so you can check them "
        "before adding."
    )
    uploaded_file = st.file_uploader(
        "Photo or PDF",
        type=uploads.IMAGE_TYPES + ["pdf"],
        key="assignment_upload"
    )

    if st.button(
        "🔍 Find Assignments",
        use_container_width=True,
        disabled=uploaded_file is None
    ):
        found = None
        try:
            with st.spinner("🤖 Reading your file..."):
                found = find_assignments_in_upload(uploaded_file)
        except ValueError as error:
            st.error(str(error))

        if found == []:
            st.info("I couldn't find any assignments in that file.")
        elif found:
            st.session_state.found_assignments = found
            st.session_state.found_batch += 1

    if st.session_state.found_assignments:
        st.write(
            "**Here's what I found.** Uncheck anything you don't want "
            "and fix any mistakes, then add them."
        )
        edited = st.data_editor(
            [{"add": True, **item} for item in st.session_state.found_assignments],
            key=f"found_editor_{st.session_state.found_batch}",
            hide_index=True,
            use_container_width=True,
            column_order=[
                "add",
                "name",
                "course",
                "due_date",
                "difficulty",
                "estimated_minutes",
                "priority",
                "description"
            ],
            column_config={
                "add": st.column_config.CheckboxColumn("Add?"),
                "name": st.column_config.TextColumn("Assignment"),
                "course": st.column_config.TextColumn("Course"),
                "due_date": st.column_config.TextColumn("Due (YYYY-MM-DD)"),
                "difficulty": st.column_config.NumberColumn("Difficulty", min_value=1, max_value=5, step=1),
                "estimated_minutes": st.column_config.NumberColumn("Minutes", min_value=5, step=5),
                "priority": st.column_config.SelectboxColumn("Priority", options=["Low", "Medium", "High"]),
                "description": st.column_config.TextColumn("Notes")
            }
        )

        add_column, discard_column = st.columns(2)

        with add_column:
            if st.button("✅ Add Selected", type="primary", use_container_width=True):
                chosen = [
                    normalize_assignment(row)
                    for row in edited
                    if row.get("add")
                ]
                st.session_state.assignments.extend(chosen)
                st.session_state.found_assignments = []
                save()
                st.rerun()

        with discard_column:
            if st.button("Discard", use_container_width=True):
                st.session_state.found_assignments = []
                st.rerun()

    st.divider()
    st.header("📚 Current Assignments")
    if not st.session_state.assignments:
        st.info(
            "No assignments yet. Add one above!"
        )

    else:
        for i, assignment in enumerate(
            st.session_state.assignments
        ):
            with st.container(border=True):
                col1, col2, col3 = st.columns(
                    [3, 2, 1]
                )
                with col1:
                    st.subheader(
                        assignment["name"]
                    )
                    st.write(
                        assignment.get(
                            "description",
                            ""
                        )
                    )

                with col2:
                    st.write(
                        f"📚 **{assignment['course']}**"
                    )
                    st.write(
                        f"📅 Due: "
                        f"{assignment['due_date']}"
                    )
                    st.write(
                        f"⏱️ "
                        f"{assignment['estimated_minutes']} min"
                    )

                with col3:
                    st.write(
                        f"Difficulty: "
                        f"{assignment['difficulty']}/5"
                    )

                    st.write(
                        f"Priority: "
                        f"{assignment['priority']}"
                    )

                    if st.button(
                        "🗑️",
                        key=f"delete_{i}"
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
    st.header("📅 Your Study Plan")
    if st.button(
        "✨ Generate Study Plan",
        use_container_width=True
    ):
        if not st.session_state.assignments:
            st.warning(
                "Add at least one assignment first."
            )
        else:
            with st.spinner(
                "🤖 Building your personalized study plan..."
            ):
                plan = generate_plan()
            if plan:
                st.session_state.study_plan = plan
                save()
                st.success(
                    "Study plan generated!"
                )

    if st.session_state.study_plan:
        sessions = st.session_state.study_plan.get(
            "study_sessions",
            []
        )
        zone_name = st.session_state.profile.get("timezone") or APP_TIMEZONE

        for item in st.session_state.study_plan.get("unscheduled", []):
            st.warning(
                f"Couldn't fit {item.get('minutes', '')} min of **{item.get('assignment', '')}**: "
                f"{item.get('reason', '')}. Try raising your max study per day "
                "or turning on weekend studying in ⚙️ Settings."
            )

        if not sessions:
            st.info("There was no free time to schedule before your due dates.")

        for session in sessions:
            if not isinstance(session, dict):
                continue
            with st.container(border=True):
                col1, col2, col3 = st.columns(
                    [1.5, 2, 4]
                )
                with col1:
                    st.write(
                        f"📅 **{session.get('date', '')}**"
                    )
                    day_label = plan_day_label(session.get("date"))
                    if day_label:
                        st.caption(day_label)
                    st.write(
                        f"⏰ "
                        f"{session.get('start_time', '')} - "
                        f"{session.get('end_time', '')}"
                    )
                with col2:
                    st.write(
                        f"📚 **{session.get('course', '')}**"
                    )
                    st.write(
                        f"📝 {session.get('assignment', '')}"
                    )

                with col3:
                    st.write(
                        f"**Task:** "
                        f"{session.get('task', '')}"
                    )
                    st.caption(
                        f"{session.get('minutes', '')} minutes"
                    )
                    google_link = calendar_export.google_calendar_link(session, zone_name)
                    if google_link:
                        st.markdown(f"[➕ Add to Google Calendar]({google_link})")

        show_calendar_export(sessions, zone_name)

        with st.expander(
            "📄 View Raw Study Plan"
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
    st.header("💬 StudyFlow AI")
    st.markdown(
        '<p class="chat-subtitle">Ask about a tough topic, plan your week, '
        'or attach a photo of a problem for a step-by-step explanation.</p>',
        unsafe_allow_html=True
    )

    if st.session_state.messages and st.button("🗑️ Clear chat"):
        st.session_state.messages = []
        save()
        st.rerun()

    conversation_area = st.container()

    with conversation_area:
        welcome_slot = st.empty()

        if not st.session_state.messages:
            welcome_slot.markdown(
                '<div class="welcome-card"><strong>Hi, I\'m StudyFlow AI </strong><br>'
                'Tell me about a test, ask me to explain something, or say '
                '"add my bio test on Friday" and I\'ll put it in your planner.</div>',
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

                assignment_count = len(st.session_state.assignments)

                with st.chat_message("assistant", avatar=LOGO_PATH):
                    chatbot(message_text)

                    save()

                    if len(st.session_state.assignments) > assignment_count:
                        st.rerun()

    components.html(
        """
        <script>
            const doc = window.parent.document;
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

                event.clipboardData.setData(
                    'text/html',
                    `<div style="color:#000;background:transparent">${container.innerHTML}</div>`
                );
                event.clipboardData.setData('text/plain', selection.toString());
                event.preventDefault();
            };
            doc.addEventListener('copy', doc.__studyflowCopyHandler);
        </script>
        """,
        height=0
    )

# ============================================================
# SETTINGS TAB
# ============================================================

with tab4:
    st.header("⚙️ Settings")
    st.markdown(
        '<p class="chat-subtitle">Edit your profile, courses, and study preferences.</p>',
        unsafe_allow_html=True
    )

    profile_tab, courses_tab, activities_tab, style_tab = st.tabs(
        [
            "👤 Profile",
            "📚 Courses",
            "🏃 Activities",
            "✨ Study Style"
        ]
    )

    with profile_tab:
        profile_values = render_setup_section(0, "settings")
        if st.button("💾 Save profile", type="primary", key="save_profile_button"):
            if not profile_values["name"]:
                st.warning("Please enter your name.")
            else:
                commit_setup_section(0, profile_values, "settings")
                save()
                st.session_state.flash = "Profile saved"
                st.rerun()

    with courses_tab:
        course_values = render_setup_section(1, "settings")
        if st.button("💾 Save courses", type="primary", key="save_courses_button"):
            commit_setup_section(1, course_values, "settings")
            save()
            st.session_state.flash = "Courses saved"
            st.rerun()

    with activities_tab:
        activity_values = render_setup_section(2, "settings")
        if st.button("💾 Save activities", type="primary", key="save_activities_button"):
            commit_setup_section(2, activity_values, "settings")
            save()
            st.session_state.flash = "Activities saved"
            st.rerun()

    with style_tab:
        st.subheader("Daily Routine")
        routine_values = render_setup_section(3, "settings")
        st.subheader("Study Preferences")
        preference_values = render_setup_section(4, "settings")
        if st.button("💾 Save study style", type="primary", key="save_style_button"):
            commit_setup_section(3, {**routine_values, **preference_values}, "settings")
            save()
            st.session_state.flash = "Study style saved"
            st.rerun()

# ============================================================
# FOOTER
# ============================================================

st.divider()
st.caption(
    "StudyFlow AI • Powered by Ollama"
)
