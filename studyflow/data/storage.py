import hashlib
from datetime import datetime, timezone

import streamlit as st
from supabase import create_client


SAVED_FIELDS = {
    "courses": list,
    "activities": list,
    "availability": dict,
    "assignments": list,
    "study_plan": lambda: None,
    "messages": list,
    "profile": dict,
    "study_style": dict,
}


# ============================================================
# CONNECTION
# ============================================================

def get_supabase_settings():
    try:
        return st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_SECRET_KEY"]
    except Exception:
        return None, None


@st.cache_resource
def _connect(url, secret_key):
    return create_client(url, secret_key)


def get_supabase():
    url, secret_key = get_supabase_settings()
    if not url or not secret_key:
        return None
    return _connect(url, secret_key)


# ============================================================
# STUDENTS
# ============================================================

def hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _find_one(supabase, column, value):
    response = (
        supabase.table("students")
        .select("*")
        .eq(column, value)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def _has_data(row):
    return any(row.get(field) for field in SAVED_FIELDS)


def find_or_create_student(supabase, google_sub=None, guest_token=None):
    guest_hash = hash_token(guest_token) if guest_token else None

    if google_sub:
        student = _find_one(supabase, "google_sub", google_sub)
        if student:
            return student

        guest = _find_one(supabase, "guest_token_hash", guest_hash) if guest_hash else None
        if guest and _has_data(guest):
            response = (
                supabase.table("students")
                .update({"google_sub": google_sub, "guest_token_hash": None})
                .eq("id", guest["id"])
                .execute()
            )
            return response.data[0]

        response = supabase.table("students").insert({"google_sub": google_sub}).execute()
        return response.data[0]

    student = _find_one(supabase, "guest_token_hash", guest_hash)
    if student:
        return student

    response = supabase.table("students").insert({"guest_token_hash": guest_hash}).execute()
    return response.data[0]


def saved_data(student):
    data = {}
    for field, empty in SAVED_FIELDS.items():
        value = student.get(field)
        data[field] = value if value is not None else empty()
    return data


def _messages_for_saving(messages):
    saved = []
    for message in messages:
        saved.append({
            "role": message["role"],
            "content": message.get("content", ""),
            "had_image": bool(message.get("images")) or message.get("had_image", False)
        })
    return saved


def save_student(supabase, student_id, data):
    row = {field: data.get(field) for field in SAVED_FIELDS}
    row["messages"] = _messages_for_saving(row.get("messages") or [])
    row["updated_at"] = datetime.now(timezone.utc).isoformat()
    supabase.table("students").update(row).eq("id", student_id).execute()


def delete_student(supabase, student_id):
    supabase.table("students").delete().eq("id", student_id).execute()


# ============================================================
# EMAIL REMINDERS
# ============================================================

def save_reminders(supabase, student_id, reminders):
    current = _find_one(supabase, "id", student_id) or {}
    stored = current.get("reminders") or {}
    merged = {**reminders, "last_sent": stored.get("last_sent")}
    supabase.table("students").update({"reminders": merged}).eq("id", student_id).execute()
    return merged


def unsubscribe(supabase, token):
    if not token or len(token) < 16:
        return False
    rows = (
        supabase.table("students")
        .select("id, reminders")
        .eq("reminders->>token", token)
        .execute()
        .data
    )
    for row in rows:
        reminders = {**(row.get("reminders") or {}), "enabled": False}
        supabase.table("students").update({"reminders": reminders}).eq("id", row["id"]).execute()
    return bool(rows)

