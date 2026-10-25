import os
import sys

from supabase import create_client

import reminder_email


# ============================================================
# SETTINGS
# ============================================================

def setting(name):
    value = os.environ.get(name, "").strip()
    if not value:
        sys.exit(f"Missing the {name} secret.")
    return value


# ============================================================
# SEND TODAY'S REMINDERS
# ============================================================

def due_now(reminders, now):
    if not reminders.get("enabled") or not reminders.get("email") or not reminders.get("token"):
        return False
    chosen = reminder_email.minutes_of_day(reminder_email.reminder_time(reminders))
    current = now.hour * 60 + now.minute
    return current >= chosen and reminders.get("last_sent") != now.date().isoformat()


def main():
    supabase = create_client(setting("SUPABASE_URL"), setting("SUPABASE_SECRET_KEY"))
    sender = setting("GMAIL_ADDRESS")
    password = setting("GMAIL_APP_PASSWORD")
    app_url = setting("APP_URL")

    students = (
        supabase.table("students")
        .select("id, profile, assignments, study_plan, reminders")
        .eq("reminders->>enabled", "true")
        .execute()
        .data
    )

    sent = skipped = failed = 0

    for student in students:
        reminders = student.get("reminders") or {}
        now = reminder_email.student_today(student)
        if not due_now(reminders, now):
            continue

        unsubscribe_url = reminder_email.unsubscribe_link(app_url, reminders["token"])
        email = reminder_email.build_email(student, now.date(), app_url, unsubscribe_url)

        if email:
            subject, text, body_html = email
            try:
                reminder_email.send_email(sender, password, reminders["email"], subject, text, body_html, unsubscribe_url)
                sent += 1
            except Exception as error:
                print(f"Could not email student {student['id']}: {type(error).__name__}")
                failed += 1
                continue
        else:
            skipped += 1

        supabase.table("students").update(
            {"reminders": {**reminders, "last_sent": now.date().isoformat()}}
        ).eq("id", student["id"]).execute()

    print(f"Reminders sent: {sent}, nothing to send: {skipped}, failed: {failed}")


if __name__ == "__main__":
    main()
