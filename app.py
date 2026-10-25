import streamlit as st
import altair as alt
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
import flashcard_display as fcard

import ab_calendar
import analytics
import calendar_export
import glass_background
import reminder_email
import scheduler
import setup_forms as setup
import storage
import uploads

import importlib
import os
import sys


# ============================================================
# KEEP HELPER FILES UP TO DATE
# ============================================================

HELPER_MODULES = [
    "fcps_courses",
    "ab_calendar",
    "uploads",
    "storage",
    "scheduler",
    "calendar_export",
    "reminder_email",
    "setup_forms",
    "analytics",
    "flashcard_display",
    "glass_background"
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
    color: #2DD4BF !important;
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
    background-color: #0F766E !important;
    color: #FFFFFF !important;

    border: none !important;
    border-radius: 10px !important;

    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;

    transition: background-color 0.2s ease;
}

.stButton button:hover {
    background-color: #0D9488 !important;
    color: #FFFFFF !important;
}

.stButton button:focus {
    border: none !important;
    box-shadow: none !important;
}

[data-testid="stCheckbox"] label:has(input[role="switch"]:not(:checked)) > span + div {
    background-color: #334155 !important;
}

.stButton button:disabled,
.stButton button:disabled:hover {
    background-color: #1E293B !important;
    color: #64748B !important;
    cursor: not-allowed;
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
    color: #2DD4BF !important;
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
   EXTENDERS
   ============================================================ */

details:open summary {
    background-color: #0f172a !important;
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
    color: #5EEAD4;
}

[data-testid="stChatInput"] {
    background: #18233d !important;
    border: 1px solid rgba(94, 234, 212, .3) !important;
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
    color: #5EEAD4 !important;
}

.chat-kicker {
    color: #5EEAD4;
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
    background: linear-gradient(115deg, rgba(20, 184, 166, .16), rgba(10, 20, 30, .85));
    border: 1px solid rgba(153, 246, 228, .22);
    border-radius: 18px;
    padding: 1.15rem 1.25rem;
    margin: .5rem 0 1.5rem;
    color: #E6FFFA;
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

.greeting-icon {
    font-family: 'Material Symbols Rounded';
    font-weight: normal;
    font-size: 26px;
    line-height: 1;
    vertical-align: -4px;
    color: #5EEAD4;
    font-feature-settings: 'liga';
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


/* ============================================================
   ASSIGNMENT CARDS
   ============================================================ */

.assignment-type {
    font-family: 'Inter', sans-serif;
    font-size: 0.85rem;
    font-weight: 700;
    letter-spacing: .08em;
    color: #94A3B8;
}

.assignment-name {
    font-family: 'Sora', sans-serif;
    font-size: 1.5rem;
    font-weight: 600;
    color: #F8FAFC;
    margin-bottom: 0.5rem;
}


/* ============================================================
   ANALYTICS
   ============================================================ */

.stat-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 16px;
    margin: 4px 0 20px;
}

@media (max-width: 1100px) {
    .stat-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}

.stat-tile {
    display: flex;
    align-items: center;
    gap: 14px;
    min-width: 0;
    padding: 18px;
    background-color: #1E293B;
    border-radius: 12px;
}

.stat-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    width: 44px;
    height: 44px;
    border-radius: 10px;
    color: #FFFFFF;
    font-family: 'Material Symbols Rounded';
    font-size: 24px;
}

.stat-label {
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    color: #94A3B8;
}

.stat-value {
    font-family: 'Sora', sans-serif;
    font-size: 22px;
    font-weight: 600;
    color: #F8FAFC;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.card-title {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
    font-family: 'Sora', sans-serif;
    font-size: 17px;
    font-weight: 600;
    color: #F8FAFC;
}

.card-icon {
    font-family: 'Material Symbols Rounded';
    font-size: 20px;
    color: #5EEAD4;
}

.load-row {
    margin-bottom: 14px;
}

.load-head {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 6px;
    font-family: 'Inter', sans-serif;
    font-size: 14px;
    color: #CBD5E1;
}

.load-count {
    color: #94A3B8;
    font-variant-numeric: tabular-nums;
}

.load-track {
    height: 6px;
    overflow: hidden;
    background-color: #334155;
    border-radius: 999px;
}

.load-fill {
    height: 100%;
    background-color: #14B8A6;
    border-radius: 999px;
}

.load-empty {
    color: #94A3B8 !important;
}

[data-testid="stSidebar"] [data-testid="stIconMaterial"] {
    font-family: 'Material Symbols Rounded' !important;
}

[data-testid="stToast"] {
    background-color: #1E293B !important;
    border: 1px solid #334155 !important;
}

[data-testid="stToast"] [data-testid="stIconMaterial"] {
    color: #5EEAD4 !important;
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
    background-color: #14B8A6 !important;
}

[data-testid="stSelectbox"] [role="group"],
[data-testid="stNumberInputContainer"],
[data-testid="stNumberInput"] input,
[data-testid="stTimeInputTimeDisplay"],
[data-testid="stTimeInput"] [data-baseweb="select"] > div,
[data-testid="stTimeInput"] [data-baseweb="input"],
[data-testid="stDateInput"] [data-baseweb="input"] {
    background-color: #1E293B !important;
    color: #F8FAFC !important;
    border-radius: 10px !important;
}

[data-testid="stSelectbox"] [role="group"] *,
[data-testid="stNumberInputContainer"] input,
[data-testid="stTimeInput"] input,
[data-testid="stTimeInputTimeDisplay"] *,
[data-testid="stDateInput"] input {
    color: #F8FAFC !important;
    background-color: transparent !important;
}

[data-testid="stDialog"] > div {
    background-color: #111C33 !important;
    border: 1px solid #334155 !important;
}

[data-testid="stDialog"] button[aria-label="Close"] {
    color: #F8FAFC !important;
}

.chat-thinking {
    color: #94A3B8;
    font-style: italic;
}

[data-testid="stCaptionContainer"] a,
[data-testid="stMarkdownContainer"] a {
    color: #5EEAD4 !important;
}

[data-testid="stCaptionContainer"] a:hover,
[data-testid="stMarkdownContainer"] a:hover {
    color: #99F6E4 !important;
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
    border-color: #14B8A6 !important;
}

[data-testid="stButtonGroup"] button[aria-pressed="true"],
[data-testid="stButtonGroup"] button[aria-checked="true"],
[data-testid="stButtonGroup"] button[data-selected="true"],
[data-testid="stButtonGroup"] button[kind$="Active"] {
    background-color: rgba(20, 184, 166, .22) !important;
    border-color: #14B8A6 !important;
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

LOGO_PATH = "assets/studyflow_logo.png"

APP_TIMEZONE = "America/New_York"

REGION = 'Virginia'

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

if "reminders" not in st.session_state:
    st.session_state.reminders = {}

if "found_assignments" not in st.session_state:
    st.session_state.found_assignments = []

if "found_batch" not in st.session_state:
    st.session_state.found_batch = 0

if 'card_idxs' not in st.session_state:
    st.session_state.card_idxs = []

#st.session_state.flashcard_sets = []
if "assignment_form" not in st.session_state:
    st.session_state.assignment_form = 0


def prepare_saved_data():
    st.session_state.courses = setup.normalize_courses(st.session_state.courses)
    st.session_state.activities = setup.normalize_activities(st.session_state.activities)
    st.session_state.profile = setup.complete_profile(st.session_state.profile)
    st.session_state.study_style = setup.complete_study_style(st.session_state.study_style)
    st.session_state.flashcard_sets = []


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
    st.session_state.reminders = student.get("reminders") or {}

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


def delete_my_data():
    storage.delete_student(SUPABASE, st.session_state.student_id)
    st.session_state.reminders = {}

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
        "description": _text(assignment.get("description"), "")
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

    save_column, cancel_column = st.columns(2)
    with save_column:
        if st.button(":material/check: Save", type="primary", use_container_width=True, key=f"{key}_save"):
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
                    "description": description
                })
                save()
                st.session_state.flash = "Assignment updated. Regenerate your study plan to include the changes."
                st.rerun()
    with cancel_column:
        if st.button("Cancel", use_container_width=True, key=f"{key}_cancel"):
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
{json.dumps(setup.course_names(st.session_state.courses))}

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
            "description": ""
        }}
    ]
}}

Rules:
- Only include items the student described or that actually appear in the file. Never invent items.
- If the student wrote a description and uploaded a file, use the description to fill in or
  correct details from the file (for example, which course it is for or when it is due).
- {COURSE_RULE}
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
            use_container_width=True,
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


def plan_sessions():
    plan = st.session_state.study_plan or {}
    return [session for session in plan.get("study_sessions", []) if isinstance(session, dict)]


def set_session_done(index, key):
    session = st.session_state.study_plan["study_sessions"][index]
    session["done"] = st.session_state[key]
    session["done_on"] = student_now().date().isoformat() if session["done"] else None
    save()



def generate_plan():
    if not st.session_state.assignments:
        return None

    # Keep checked-off sessions and only schedule the work that's left.
    finished = [session for session in plan_sessions() if session.get("done")]
    finished_minutes = {}
    for session in finished:
        match = (session.get("assignment"), session.get("course"))
        finished_minutes[match] = finished_minutes.get(match, 0) + _whole_number(session.get("minutes"), 0)

    remaining = []
    for assignment in st.session_state.assignments:
        match = (assignment.get("name"), assignment.get("course") or "")
        left = _whole_number(assignment.get("estimated_minutes"), 60) - finished_minutes.get(match, 0)
        if left > 0:
            remaining.append({**assignment, "estimated_minutes": left})

    sessions, unscheduled = scheduler.build_plan(
        remaining,
        setup.complete_study_style(st.session_state.study_style),
        setup.normalize_activities(st.session_state.activities),
        student_now().replace(tzinfo=None),
        is_school_day_for_student
    )

    tasks = write_tasks(sessions)
    for number, session in enumerate(sessions, start=1):
        session["task"] = tasks.get(number) or scheduler.default_task(session)

    all_sessions = finished + [scheduler.public_session(session) for session in sessions]
    all_sessions.sort(key=lambda session: (session.get("date", ""), session.get("start_time", "")))

    return {
        "study_sessions": all_sessions,
        "unscheduled": unscheduled,
        "created": student_now().isoformat()
    }

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
    <add_assignment>{{"name": "", "type": "", "course": "", "due_date": "YYYY-MM-DD", "difficulty": 3, "estimated_minutes": 60, "priority": "Medium", "description": ""}}</add_assignment>
    - Difficulty must be 1-5. Priority must be Low, Medium, or High.
    - Type must be one of: {", ".join(ASSIGNMENT_TYPES)}, or blank if you are not sure.
    - {ASSIGNMENT_NAME_RULE}
    - {COURSE_RULE}
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
            assignment = normalize_assignment(data)
            assignment["course"] = guess_course(assignment)
            added.append(assignment)

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
    avatar = LOGO_PATH if message["role"] == "assistant" else ":material/person:"

    with st.chat_message(message["role"], avatar=avatar):
        if message.get("content"):
            st.markdown(message["content"])

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


def show_reminder_settings():
    reminders = st.session_state.reminders or {}

    st.subheader("Daily email reminders")
    st.caption(
        "Get one email a day with that day's study sessions and anything due in the next few days. "
        "Emails come from studyflowreminders@gmail.com, and every email has a link to turn them off."
    )

    if SUPABASE is None or not st.session_state.get("student_id"):
        st.info("Email reminders need saving to be turned on.")
        return

    suggested = ""
    if signed_in_with_google():
        suggested = st.user.get("email") or ""

    enabled = st.toggle(
        "Email me a daily study reminder",
        value=bool(reminders.get("enabled")),
        key="settings_reminders_enabled"
    )
    email = st.text_input(
        "Email address",
        value=reminders.get("email") or suggested,
        placeholder="you@example.com",
        key="settings_reminders_email"
    )
    send_time = st.time_input(
        "Send it at",
        value=setup.to_time(reminder_email.reminder_time(reminders)),
        step=900,
        format="12h",
        key="settings_reminders_time"
    )
    age_ok = st.checkbox(
        "I'm 13 or older, or a parent or guardian said it's OK",
        value=bool(reminders.get("age_ok")),
        key="settings_reminders_age"
    )

    save_column, test_column = st.columns(2)

    with save_column:
        save_clicked = st.button("Save reminders", type="primary", use_container_width=True, key="save_reminders_button")

    with test_column:
        test_clicked = st.button(
            ":material/send: Send a test email",
            use_container_width=True,
            disabled=not (reminders.get("enabled") and reminders.get("email")),
            help="Save your reminder settings first, then send a test.",
            key="test_reminders_button"
        )

    if save_clicked:
        email = email.strip()
        if enabled and not EMAIL_PATTERN.match(email):
            st.warning("Please enter a valid email address.")
        elif enabled and not age_ok:
            st.warning("Please confirm you're 13 or older, or that a parent or guardian said it's OK.")
        else:
            updated = {
                "enabled": enabled,
                "email": email if enabled else "",
                "time": setup.from_time(send_time) or reminder_email.DEFAULT_TIME,
                "age_ok": age_ok,
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
            else:
                st.session_state.flash = "Reminders turned on" if enabled else "Reminders turned off"
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
                    ":material/arrow_back: Back",
                    disabled=step == 0,
                    use_container_width=True,
                    key="wizard_back"
                )

            with next_column:
                go_next = st.button(
                    ":material/check: Finish" if last_step else "Continue :material/arrow_forward:",
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
        f":material/book: {course_count} course{'s' if course_count != 1 else ''} · "
        f":material/directions_walk: {activity_count} activit{'ies' if activity_count != 1 else 'y'}"
    )
    st.caption(
        f":material/schedule: Homework from {setup.pretty_time(routine.get('homework_start'))}, "
        f"bedtime {setup.pretty_time(routine.get('bed'))}"
    )
    st.caption("Change these anytime in the :material/settings: Settings tab.")

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
        use_container_width=True
    ):
        if not assignment_input.strip() and uploaded_file is None:
            st.warning(
                "Describe an assignment or upload a file first."
            )
        else:
            found = None
            try:
                with st.spinner(":material/smart_toy: Analyzing..."):
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
            use_container_width=True,
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
            if st.button(":material/check: Add Selected", type="primary", use_container_width=True):
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
            if st.button("Discard", use_container_width=True):
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

            with st.container(border=True):
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
                    
                    if st.button(
                        ":material/style: Create Flashcards",
                        key=f"flashcards_create_{i}"
                    ):
                        set_is_unique = True
                        state = st.session_state.profile.get('region') or 'Virginia'
                        st.session_state.flashcard_sets.append(
                            ask_ai(
                                f"""
                                You are a professional flashcard maker and I am a student in need of flashcards.
                                You need to create a set of vocabulary flashcards for {assignment.get('name')} using the {state} curriculum.
                                Make sure the cards are only for the unit specified (if present) in {state} standard curriculum.
                                Return only in valid JSON using this format:
                                {{
                                    'assignment': 'name'
                                    'card 1 word': 'definition',
                                    'card 2 word': 'definition',
                                    ... and so on
                                }}
                                """,
                                "You are a professional flashcard maker"
                            ) 
                        )
                        for set in st.session_state.flashcard_sets[0:-1]:
                            if set.get('assignment') == assignment.get('name'):
                                st.session_state.flashcard_sets[-1].pop()
                                set_is_unique = False
                        if set_is_unique:
                            st.success(
                                f"Flashcards for {assignment.get('name')} created!"
                            )
                            set = list(st.session_state.flashcard_sets[-1].items())
                            set.insert(1, ('priority', assignment.get('priority')))
                            set.insert(-1,('known', {}))
                            st.session_state.flashcard_sets[-1] = dict(set)
                        else:
                            st.warning(
                                f"Flashcards for {assignment.get('name')} already exist!"
                            )
                            
                                

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
    if st.button(
        ":material/auto_awesome: Generate Study Plan",
        use_container_width=True
    ):
        if not st.session_state.assignments:
            st.warning(
                "Add at least one assignment first."
            )
        else:
            with st.spinner(
                ":material/smart_toy: Building your personalized study plan..."
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
                "or turning on weekend studying in :material/settings: Settings."
            )

        hide_done = False
        if not sessions:
            st.info("There was no free time to schedule before your due dates.")
        else:
            done_count = sum(1 for session in sessions if isinstance(session, dict) and session.get("done"))
            st.progress(
                done_count / len(sessions),
                text=f"{done_count} of {len(sessions)} study sessions done"
            )
            hide_done = st.toggle("Hide finished sessions", key="hide_done_sessions")

        plan_key = st.session_state.study_plan.get("created", "")

        for index, session in enumerate(sessions):
            if not isinstance(session, dict):
                continue
            is_done = bool(session.get("done"))
            if is_done and hide_done:
                continue
            with st.container(border=True):
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

            // Keep the chat scrolled to the newest message while the AI Assistant tab is open.
            const chatInput = () => doc.querySelector('[data-testid="stChatInput"]');
            let scrollQueued = false;
            const scrollChat = () => {
                scrollQueued = false;
                const input = chatInput();
                if (!input || !input.getClientRects().length) return;
                input.scrollIntoView({ block: 'end' });
            };
            // Use the page's animation frame: this hidden iframe's own frames are throttled.
            const queueScroll = () => {
                if (scrollQueued) return;
                scrollQueued = true;
                window.parent.requestAnimationFrame(scrollChat);
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
        </script>
        """,
        height=0
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
                "Regenerate your study plan to fit that work back in."
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
                st.altair_chart(styled_chart(chart), use_container_width=True, theme=None)
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
                        use_container_width=True,
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
                        use_container_width=True,
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
                use_container_width=True
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
                use_container_width=True
            )


# ============================================================
# FLASHCARDS TAB
# ============================================================

st.html(f'''<style>

{', '.join('.st-key-flashcard_' + str(set) for set in range(len(st.session_state.flashcard_sets)))} {{
    align-items: center !important;
    justify-content: center !important;
}}

{', '.join('.st-key-flashcard_' + str(set) + ' div button' for set in range(len(st.session_state.flashcard_sets)))} {{
    border: 0.5px solid #161C2F !important;
    border-radius: 8px !important;
    height: 500px !important;
    display: flex !important;
}}

{', '.join('.st-key-ik_' + str(set) for set in range(len(st.session_state.flashcard_sets)))}, {', '.join('.st-key-idk_' + str(set) for set in range(len(st.session_state.flashcard_sets)))} {{
    border: 0.5px solid #161C2F !important;
    border-radius: 8px !important;
}}

{', '.join('.st-key-ik_' + str(set) + ' div button div span' for set in range(len(st.session_state.flashcard_sets)))} {{
    color: lime;
    font-size: 25pt !important;
}}

{', '.join('.st-key-idk_' + str(set) + ' div button div span' for set in range(len(st.session_state.flashcard_sets)))} {{
    color: red;
    font-size: 25pt !important;
}}

{', '.join('.st-key-flashcard_' + str(set) + ' div button div span span div' for set in range(len(st.session_state.flashcard_sets)))} {{
    font-size: 25pt !important;
    padding: 50px !important;
}}

</style>''')

def finished_set(set):
    st.success("You've finished this set of flashcards! You can add more in the Assignments tab.", icon=":material/task_alt:")
    if st.button(':material/replay: Practice again'):
        st.session_state.flashcard_sets[0].update(st.session_state.flashcard_sets[set]['known'].pop())


with tab4:
    st.header(":material/style: Flashcards")
    if not st.session_state.flashcard_sets:
        st.info(
            "No flashcards yet. Add some in the Assignments tab."
        )
    else:
        for set in range(0, len(st.session_state.flashcard_sets)):
            with st.expander(
                st.session_state.flashcard_sets[set].get('assignment')
                ):
                try:
                    side = st.session_state.card_idxs[set][2] + 0
                except:
                    side = 0
                try:
                    card_idx = st.session_state.card_idxs[set][1] + 0
                except:
                    card_idx = 0
                
                if type(list(st.session_state.flashcard_sets[set].keys())[card_idx + 2]) is not dict:
                    side = fcard.draw(
                    side, 
                    list(st.session_state.flashcard_sets[set])[card_idx + 2], 
                    list(st.session_state.flashcard_sets[set].values())[card_idx + 2],
                    set
                    )
                    idk, ik = st.columns(2)
                    if idk.button(icon=":material/close:", label='', width='stretch', type='tertiary', key=f'idk_{set}'):
                        card_idx += 1
                        side = 0
                    if ik.button(icon=":material/check:", label='', width='stretch', type='tertiary', key=f'ik_{set}'):    
                        card = list(st.session_state.flashcard_sets[set].values())[card_idx + 2]
                        card_key = list(st.session_state.flashcard_sets[set].keys())[card_idx + 2]
                        st.session_state.flashcard_sets[set].pop(list(st.session_state.flashcard_sets[set])[card_idx + 2])
                        st.session_state.flashcard_sets[set]['known'].update({
                            card_key: card
                        })
                        side = 0
                    if len(st.session_state.card_idxs) == set:
                        prev_side = 0
                        st.session_state.card_idxs.insert(set, [set, card_idx, side])
                    elif len(st.session_state.card_idxs) > set:
                        prev_side = st.session_state.card_idxs[set][2]
                        st.session_state.card_idxs[set] = [set, card_idx, side]
                    else:
                        for i in range(set - len(st.session_state.card_idxs)):
                            st.session_state.card_idxs.insert(i, [None, None, None])
                        prev_side = st.session_state.card_idxs[set][2]
                        st.session_state.card_idxs[set] = [set, card_idx, side]
                    if side != prev_side:
                        st.rerun()
                else:
                    finished_set(set)
                
                with st.expander(":material/data_object: View raw JSON data"):    
                    st.json(st.session_state.flashcard_sets[set])
                if st.button(":material/delete: Delete this set", type="secondary", key=f'delete_set_{set}'):
                    del st.session_state.flashcard_sets[set]
                    st.session_state.card_idxs[set] = [None, None, None]
                    st.rerun()



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