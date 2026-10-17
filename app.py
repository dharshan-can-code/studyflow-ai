import streamlit as st
import json
import re
import secrets
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from ollama import Client
import streamlit.components.v1 as components
from streamlit_cookies_controller import CookieController

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

dark_css= """
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

.stButton > button {
    background-color: #6366F1 !important;
    color: #FFFFFF !important;

    border: none !important;
    border-radius: 10px !important;

    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;

    transition: background-color 0.2s ease;
}

.stButton > button:hover {
    background-color: #8B5CF6 !important;
    color: #FFFFFF !important;
}

.stButton > button:focus {
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
"""

#===================================================================================================================
# LIGHT MODE
#===================================================================================================================


light_css = """
<style>

/* ============================================================
   FONTS
   ============================================================ */

@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Inter:wght@400;500;600;700&family=Sixtyfour&family=Sora:wght@400;500;600;700&display=swap');


/* ============================================================
   MAIN APP
   ============================================================ */

.stApp {
    background-color: F8FAFC;
    color: #172033;
}


[data-testid="stHeader"] {
    background-color: #F8FAFC;
}

[data-testid="stHeader"] > div {
    background-color: #F8FAFC;
}


.main .block-container {
    color: #172033;
}


/* ============================================================
   TEXT
   ============================================================ */

p {
    color: #172033 !important;
    font-family: 'Inter', sans-serif !important;
}

label {
    color: #475569 !important;
    font-family: 'Inter', sans-serif !important;
}

small {
    color: #64748B !important;
}


/* ============================================================
   HEADINGS
   ============================================================ */

h1, h2, h3 {
    font-family: 'Sora', sans-serif !important;
    color: #172033 !important;
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
    color: #172033 !important;
    font-family: 'Sixtyfour', monospace !important;
}

.studyflow-title .brand-ai {
    color: #7C3AED !important;
    font-family: 'Sixtyfour', monospace !important;
}


/* ============================================================
   SUBTITLE
   ============================================================ */

.studyflow-subtitle {
    font-family: 'Inter', sans-serif !important;
    color: #64748B !important;
    font-size: 16px;
    margin-bottom: 20px;
}


/* ============================================================
   TEXT INPUTS
   ============================================================ */

.stTextInput input {
    background-color: #FFFFFF !important;
    color: #172033 !important;

    border: none !important;
    border-radius: 10px !important;

    font-family: 'Inter', sans-serif !important;
}

.stTextInput input::placeholder {
    color: #94A3B8 !important;
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
    background-color: #FFFFFF !important;
    color: #172033 !important;

    border: none !important;
    border-radius: 10px !important;

    font-family: 'Inter', sans-serif !important;
}

.stTextArea textarea::placeholder {
    color: #9413B8 !important;
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
    background-color: #FFFFFF !important;
    color: #172033 !important;

    border: none !important;
    border-radius: 10px !important;
}

.stSelectbox [data-baseweb="select"] span {
    color: #F8FAFC !important;
}


/* ============================================================
   BUTTONS
   ============================================================ */

.stButton > button {
    background-color: #7C3AED !important;
    color: #FFFFFF !important;

    border: none !important;
    border-radius: 10px !important;

    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;

    transition: background-color 0.2s ease;
}

.stButton > button:hover {
    background-color: #6D28D9 !important;
    color: #FFFFFF !important;
}

.stButton > button:focus {
    border: none !important;
    box-shadow: none !important;
}


/* ============================================================
   SIDEBAR
   ============================================================ */

[data-testid="stSidebar"] {
    background-color: #F1F5F9 !important;
}

[data-testid="stSidebar"] * {
    font-family: 'Inter', sans-serif;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #172033 !important;
}

[data-testid="stSidebar"] label {
    color: #475569 !important;
}


/* ============================================================
   TABS
   ============================================================ */

.stTabs [data-baseweb="tab-list"] {
    background-color: transparent !important;
    gap: 8px;
}

.stTabs [data-baseweb="tab"] {
    color: #64748B !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600;
}

.stTabs [aria-selected="true"] {
    color: #7C3AED !important;
}


/* ============================================================
   DIVIDERS
   ============================================================ */

hr {
    border: none !important;
    border-top: 1px solid #E2E8F0 !important;
}


/* ============================================================
   CONTAINERS / CARDS
   ============================================================ */

[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #FFFFFF !important;

    border: none !important;
    border-radius: 12px !important;
}


/* ============================================================
   CHAT
   ============================================================ */

[data-testid="stChatMessage"] {
    background: rgba(255, 255, 255, .92) !important;
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
    color: #172033 !important;
}

[data-testid="stChatMessage"] li::marker {
    color: #7C3AED;
}

[data-testid="stChatInput"] {
    background: #18233d !important;
    border: 1px solid rgba(124, 58, 237, .30) !important;
    border-radius: 15px !important;
}

[data-testid="stChatInput"] > div {
    background: transparent !important;
    border: none !important;
}

[data-testid="stChatInput"] textarea {
    color: #172033 !important;
    background: transparent !important;
    border: none !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #94A3B8 !important;
}

[data-testid="stChatInput"] button {
    color: #7C3AED !important;
}

.chat-kicker {
    color: #7C3AED;
    font-family: 'DM Mono', monospace;
    font-size: .72rem;
    letter-spacing: .13em;
    text-transform: uppercase;
    margin-bottom: .4rem;
}

.chat-subtitle {
    color: #64778B !important;
    font-size: 1rem;
    line-height: 1.65;
    max-width: 39rem;
    margin: .25rem 0 1.25rem;
}

.welcome-card {
    background: linear-gradient(115deg, rgba(237, 233, 23247, .90), rgba(248, 250, 252, .20));
    border: 1px solid rgba(124, 58, 252, .20);
    border-radius: 18px;
    padding: 1.15rem 1.25rem;
    margin: .5rem 0 1.5rem;
    color: #4C1D95;
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
    background-color: #FFFFFF !important;
    border: 1px dashed #CBD5E1 !important;
    border-radius: 10px !important;
}

[data-testid="stFileUploaderDropzone"] span,
[data-testid="stFileUploaderDropzone"] small,
[data-testid="stFileUploaderDropzone"] p {
    color: #475569 !important;
}

[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] {
    background-color: #E2E8F0 !important;
    color: #172033 !important;
    border: none !important;
}


/* ============================================================
   SCROLLBAR
   ============================================================ */

::-webkit-scrollbar {
    width: 8px;
}

::-webkit-scrollbar-track {
    background: #F1F5F9;
}

::-webkit-scrollbar-thumb {
    background: #CBD5E1;
    border-radius: 10px;
}

[data-testid="stSidebarCollapseButton"] button {
    color: #475569 !important;
}

[data-testid="stSidebarCollapseButton"] button span {
    font-family: 'Material Symbols Rounded' !important;
    font-size: 24px !important;
}

</style>
"""
# ============================================================
# THEME SELECTION
# ============================================================

if "theme" not in st.session_state:
    st.session_state.theme = "Dark"

if st.session_state.theme == "Dark":
    st.markdown(dark_css, unsafe_allow_html=True)
else:
    st.markdown(light_css, unsafe_allow_html=True)

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

client = Client(
    host="https://ollama.com",
    headers={
        "Authorization": f"Bearer {ollama_api_key}"
    }

)

MODEL = "gpt-oss:20b-cloud"

VISION_MODEL = "gemma4:31b-cloud"

CHAT_MODEL = "gemma4:31b-cloud"

CHAT_TEMPERATURE = 0.7

LOGO_PATH = "assets/studyflow_logo.png"

APP_TIMEZONE = "America/New_York"

MAX_HISTORY_MESSAGES = 50

GUEST_COOKIE = "studyflow_guest_token"

DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
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


def existing_guest_token():
    return st.session_state.get("guest_token") or st.context.cookies.get(GUEST_COOKIE)


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

    for day in DAYS:
        st.session_state[f"availability_{day}"] = st.session_state.availability.get(day, "")

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
        st.toast("Couldn't save your latest changes. Check your connection.", icon="⚠️")


def delete_my_data():
    storage.delete_student(SUPABASE, st.session_state.student_id)

    for field, empty in storage.SAVED_FIELDS.items():
        st.session_state[field] = empty()

    st.session_state.found_assignments = []
    st.session_state.student_id = None
    st.session_state.loaded_identity = None


COOKIE_SLOT = st.container()

SUPABASE = load_student()


# ============================================================
# DATE HELPER
# ============================================================

def date_context():
    try:
        today = datetime.now(ZoneInfo(APP_TIMEZONE)).date()
    except Exception:
        today = datetime.now().date()

    lines = [
        f"Today is {today:%A}, {today:%Y-%m-%d}.",
        "Calendar for the next two weeks (use it to convert "
        "relative dates like \"next Friday\"):"
    ]
    for i in range(1, 15):
        day = today + timedelta(days=i)
        lines.append(f"- {day:%A} {day:%Y-%m-%d}")

    return "\n".join(lines)


# ============================================================
# AI HELPER
# ============================================================

def ask_ai(prompt, system_message, conversation=None, use_json=True, images=None, model=MODEL, temperature=0):
    try:
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

        response = client.chat(
            model=model,
            messages=messages,
            format="json" if use_json else None,
            options={
                "temperature": temperature
            }
        )

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
{json.dumps(st.session_state.courses)}

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

def generate_plan():
    if not st.session_state.assignments:
        return None
    availability = st.session_state.availability
    prompt = f"""
{date_context()}
The student's courses are:
{json.dumps(st.session_state.courses, indent=4)}
The student's extracurricular activities are:
{json.dumps(st.session_state.activities, indent=4)}
The student's available study times are:
{json.dumps(availability, indent=4)}
The student's assignments are:
{json.dumps(st.session_state.assignments, indent=4)}
Create a realistic study schedule.

Rules:
1. Earlier deadlines have higher priority.
2. Difficult assignments should receive more preparation.
3. Large assignments should be split across multiple sessions.
4. Do not schedule more than 90 minutes of one assignment
   in a single session.
5. Do not schedule outside the student's availability.
6. Do not schedule after the assignment's due date.
7. Spread work across multiple days whenever possible.
8. Avoid overwhelming the student.
9. Include a specific task for every study session.
10. Do not schedule during extracurricular activities.
11. Leave reasonable breaks between sessions.

Return ONLY valid JSON.
Use exactly this format:

{{
    "study_sessions": [
        {{
            "date": "YYYY-MM-DD",
            "start_time": "16:00",
            "end_time": "17:00",
            "course": "",
            "assignment": "",
            "task": "",
            "minutes": 60
        }}
    ]
}}
"""
    return ask_ai(
        prompt,
        "You are an expert student study scheduler. "
        "Create realistic schedules and return only valid JSON."
    )

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
    return f"""
{date_context()}

The student's courses are:
{json.dumps(st.session_state.courses)}

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


def chatbot(message):
    history = st.session_state.messages[-MAX_HISTORY_MESSAGES:]

    reply = ask_ai(
        chat_context(),
        CHAT_SYSTEM_PROMPT,
        conversation=history,
        use_json=False,
        model=CHAT_MODEL,
        temperature=CHAT_TEMPERATURE
    )

    if not reply:
        return None

    reply, added = pull_assignment_tags(reply)

    if added:
        st.session_state.assignments.extend(added)

        if not reply:
            names = ", ".join(f"**{assignment['name']}**" for assignment in added)
            reply = f"Added {names} to your assignments."

    if not reply:
        st.error("The AI sent back an empty reply. Please try again.")
        return None

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
# SIDEBAR
# ============================================================

with st.sidebar:
    st.sidebar.image(
    "assets/studyflow_logo.png",
    width=50
    )

    st.divider()

    if st.button(
        "☀️ Switch to Light Mode"
        if st.session_state.theme == "Dark"
        else "🌙 Switch to Dark Mode",
        key="theme_toggle",
        use_container_width=True
    ):
        st.session_state.theme = (
            "Light"
            if st.session_state.theme == "Dark"
            else "Dark"
        )
        st.rerun()

    st.divider()

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

    st.title("⚙️ Setup")
    st.subheader("📚 Your Courses")
    course_input = st.text_input(
        "Add a course",
        placeholder="Algebra 2"
    )

    if st.button("Add Course"):
        if course_input.strip():
            st.session_state.courses.append(
                course_input.strip()
            )
            save()

    if st.session_state.courses:
        for course in st.session_state.courses:
            st.write("•", course)

    st.divider()
    st.subheader("🏃 Activities")

    activity_name = st.text_input(
        "Activity",
        placeholder="Soccer practice"
    )

    activity_day = st.selectbox(
        "Day",
        [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday"
        ]
    )

    activity_time = st.text_input(
        "Time",
        placeholder="4:00 PM - 6:00 PM"
    )

    if st.button("Add Activity"):
        if activity_name.strip():
            st.session_state.activities.append(
                {
                    "name": activity_name,
                    "day": activity_day,
                    "time": activity_time
                }
            )
            save()

    st.divider()
    st.subheader("⏰ Study Availability")
    availability = {}

    for day in DAYS:
        availability[day] = st.text_input(
            day,
            placeholder="4:00 PM - 7:00 PM",
            key=f"availability_{day}"
        )

    if availability != st.session_state.availability:
        st.session_state.availability = availability
        save()

    if SUPABASE is not None and st.session_state.get("student_id"):
        st.divider()
        with st.expander("🔒 Your data"):
            st.caption(
                "StudyFlow saves your courses, activities, availability, "
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

st.write(
    "Add your assignments, tests, and activities. "
    "StudyFlow will turn them into a realistic study schedule."
)

st.divider()

# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3 = st.tabs(
    [
        "📝 Assignments",
        "📅 Study Plan",
        "💬 AI Assistant"
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
        for session in sessions:
            with st.container(border=True):
                col1, col2, col3 = st.columns(
                    [1.5, 2, 4]
                )
                with col1:
                    st.write(
                        f"📅 **{session['date']}**"
                    )
                    st.write(
                        f"⏰ "
                        f"{session['start_time']} - "
                        f"{session['end_time']}"
                    )
                with col2:
                    st.write(
                        f"📚 **{session['course']}**"
                    )
                    st.write(
                        f"📝 {session['assignment']}"
                    )

                with col3:
                    st.write(
                        f"**Task:** "
                        f"{session['task']}"
                    )
                    st.caption(
                        f"{session['minutes']} minutes"
                    )

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
                '<div class="welcome-card"><strong>Hi, I\'m StudyFlow AI 👋</strong><br>'
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
                    with st.spinner("Thinking…"):
                        reply = chatbot(message_text)

                    save()

                    if len(st.session_state.assignments) > assignment_count:
                        st.rerun()

                    if reply:
                        st.markdown(reply)

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
# FOOTER
# ============================================================

st.divider()
st.caption(
    "StudyFlow AI • Powered by Ollama"
)
