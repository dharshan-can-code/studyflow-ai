import streamlit as st
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from ollama import Client


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

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Sixtyfour&family=Sora:wght@400;500;600;700&display=swap');


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
    background-color: #1E293B !important;
    border: none !important;
    border-radius: 12px !important;
}

[data-testid="stChatInput"] textarea {
    background-color: #1E293B !important;
    color: #F8FAFC !important;

    border: none !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #64748B !important;
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

client = Client(
    host="https://ollama.com",
    headers={
        "Authorization": f"Bearer {ollama_api_key}"
    }

)

MODEL = "gpt-oss:20b-cloud"

APP_TIMEZONE = "America/New_York"

MAX_HISTORY_MESSAGES = 20


# ============================================================
# SESSION STATE
# ============================================================

if "assignments" not in st.session_state:
    st.session_state.assignments = []

if "study_plan" not in st.session_state:
    st.session_state.study_plan = None

if "courses" not in st.session_state:
    st.session_state.courses = []

if "activities" not in st.session_state:
    st.session_state.activities = []

if "messages" not in st.session_state:
    st.session_state.messages = []


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

def ask_ai(prompt, system_message, conversation=None, use_json=True):
    try:
        messages = [
            {
                "role": "system",
                "content": system_message
            }
        ]

        if conversation:
            messages[0]["content"] += "\n\n" + prompt
            messages.extend(
                {
                    "role": m["role"],
                    "content": m["content"]
                }
                for m in conversation
            )
        else:
            messages.append(
                {
                    "role": "user",
                    "content": prompt
                }
            )
        response = client.chat(
            model=MODEL,
            messages=messages,
            format="json" if use_json else None,
            options={
                "temperature": 0
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

def chatbot(message):
    prompt = f"""
{date_context()}

The student currently has these assignments:
{json.dumps(st.session_state.assignments, indent=4)}

You are the StudyFlow AI assistant.

The student is having a conversation with you. Answer their question naturally and helpfully.

IMPORTANT: You MUST return ONLY a valid JSON object using EXACTLY one of these formats.

For a normal conversation:
{{
    "action": "conversation",
    "assignment": null,
    "response": "Your complete answer to the student."
}}

For adding an assignment:
{{
    "action": "add_assignment",
    "assignment": {{
        "name": "Assignment name",
        "course": "Course name",
        "due_date": "YYYY-MM-DD",
        "difficulty": 1,
        "estimated_minutes": 60,
        "priority": "Medium"
    }},
    "response": "Confirmation message."
}}

RULES:
- Normal questions MUST use "action": "conversation".
- Put the answer to the student ONLY inside the "response" field.
- Do NOT use fields such as "explanation", "definition", "examples", or "visualization".
- If the student is asking to add an assignment, use "action": "add_assignment".
- Use the earlier messages in this conversation for context
  (for example, "explain that again" refers to your last answer).
- Difficulty must be 1-5.
- Priority must be Low, Medium, or High.
- Convert relative dates such as "next Friday" into YYYY-MM-DD.
- Return ONLY valid JSON.
"""
    history = st.session_state.messages[-MAX_HISTORY_MESSAGES:]

    result = ask_ai(
        prompt,
        "You are StudyFlow AI, a helpful student study assistant. "
        "Return only valid JSON.",
        conversation=history
    )

    if result is None:
        return None

    response_text = result.get("response")

    if result.get("action") == "add_assignment":
        assignment = result.get("assignment")

        if isinstance(assignment, dict):
            assignment = {
                "name": assignment.get("name") or "Untitled assignment",
                "course": assignment.get("course") or "General",
                "due_date": assignment.get("due_date") or "Not set",
                "difficulty": assignment.get("difficulty") or 3,
                "estimated_minutes": assignment.get("estimated_minutes") or 60,
                "priority": assignment.get("priority") or "Medium",
                "description": assignment.get("description", "")
            }

            st.session_state.assignments.append(assignment)

            if not response_text:
                response_text = (
                    f"Added **{assignment['name']}** "
                    "to your assignments."
                )

    if not response_text:
        st.error("AI response was missing the 'response' field.")
        st.json(result)
        return None

    st.session_state.messages.append({
        "role": "assistant",
        "content": response_text
    })

    return response_text


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.sidebar.image(
    "assets/studyflow_logo.png",
    width=50
    )

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

    st.divider()
    st.subheader("⏰ Study Availability")
    availability = {}

    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday"
    ]

    for day in days:
        availability[day] = st.text_input(
            day,
            placeholder="4:00 PM - 7:00 PM"
        )

    st.session_state.availability = availability


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
                    assignment
                )

                st.success(
                    "Assignment added!"
                )

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
    st.header("💬 StudyFlow AI")
    st.write(
        "Tell me about assignments, tests, or "
        "your study workload."
    )
    for message in st.session_state.messages:
        with st.chat_message(
            message["role"]
        ):
            st.markdown(
                message["content"]
            )

    user_message = st.chat_input(
        "Example: I have a biology test Friday..."
    )

    if user_message:
        st.session_state.messages.append(
            {
                "role": "user",
                "content": user_message
            }
        )
        with st.chat_message("user"):
            st.write(user_message)
        assignment_count = len(st.session_state.assignments)

        with st.chat_message("assistant"):
            with st.spinner(
                "🤖 Thinking..."
            ):
                reply = chatbot(user_message)

            if len(st.session_state.assignments) > assignment_count:
                st.rerun()

            if reply:
                st.markdown(reply)

# ============================================================
# FOOTER
# ============================================================

st.divider()
st.caption(
    "StudyFlow AI • Powered by Ollama"
)