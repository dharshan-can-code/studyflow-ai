import streamlit as st
from openai import OpenAI
import json
from datetime import datetime
from ollama import Client


# ============================================================
# PAGE SETTINGS
# ============================================================

st.set_page_config(
    page_title="StudyFlow AI",
    page_icon="📚",
    layout="wide"
)


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

MODEL = "llama3.2"


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
# AI HELPER
# ============================================================

def ask_ai(prompt, system_message):

    try:

        response = client.chat.completions.create(
            model=MODEL,

            messages=[
                {
                    "role": "system",
                    "content": system_message
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            response_format={"type": "json_object"},

            temperature=0
        )

        result = response.choices[0].message.content

        print("RAW RESPONSE:")
        print(repr(result))

        # Remove Markdown code blocks if the model adds them
        cleaned_result = result.strip()

        if cleaned_result.startswith("```json"):
            cleaned_result = cleaned_result[7:]

        elif cleaned_result.startswith("```"):
            cleaned_result = cleaned_result[3:]

        if cleaned_result.endswith("```"):
            cleaned_result = cleaned_result[:-3]

        cleaned_result = cleaned_result.strip()

        return json.loads(cleaned_result)

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

    today = datetime.now().strftime("%Y-%m-%d")

    prompt = f"""
Today's date is {today}.

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
Today's date is {datetime.now().strftime("%Y-%m-%d")}.

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
Today's date is {datetime.now().strftime("%Y-%m-%d")}.

The student currently has these assignments:

{json.dumps(st.session_state.assignments, indent=4)}

The student said:

"{message}"

Determine what the student wants.

If they are adding an assignment, return:

{{
    "action": "add_assignment",
    "assignment": {{
        "name": "",
        "course": "",
        "due_date": "YYYY-MM-DD",
        "difficulty": 1,
        "estimated_minutes": 60,
        "priority": "Medium"
    }},
    "response": ""
}}

If they are asking a normal question, return:

{{
    "action": "conversation",
    "assignment": null,
    "response": ""
}}

Rules:

- Difficulty must be 1-5.
- Priority must be Low, Medium, or High.
- Convert relative dates into YYYY-MM-DD.
- Return ONLY valid JSON.
"""

    result = ask_ai(
        prompt,
        "You are StudyFlow AI, a helpful student study assistant. "
        "Return only valid JSON."
    )

    if result is None:
        return

    if result.get("action") == "add_assignment":

        assignment = result.get("assignment")

        if assignment:

            st.session_state.assignments.append(
                assignment
            )

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content":
                    f"Added **{assignment['name']}** to your assignments."
                }
            )

    else:

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content":
                result.get(
                    "response",
                    "I'm not sure what you mean."
                )
            }
        )


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

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

st.title("📚 StudyFlow AI")

st.subheader(
    "Your AI-powered academic planner"
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

    # Display previous messages
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

        with st.chat_message("assistant"):

            with st.spinner(
                "🤖 Thinking..."
            ):

                chatbot(user_message)

            if st.session_state.messages:

                st.markdown(
                    st.session_state.messages[-1]["content"]
                )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "StudyFlow AI • Powered by Ollama"
)

