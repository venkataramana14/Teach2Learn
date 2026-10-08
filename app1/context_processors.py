from .supabase_client import supabase
from django.db import connection
from django.utils import timezone
from datetime import datetime, time
from django.db import connection
from django.utils import timezone
   # Adjust import if needed
from datetime import datetime
from django.utils import timezone

def session_notifications(request):

    # User not logged in
    if not request.user.is_authenticated:
        return {
            "ongoing_sessions": [],
            "upcoming_sessions": [],
        }

    now = timezone.now()
    email = request.user.email

    response = (
        supabase.table("sessions")
        .select(
            "meeting_link, session_date, session_time, end_time, "
            "student_email, mentor_email, skill"
        )
        .or_(f"student_email.eq.{email},mentor_email.eq.{email}")
        .order("session_date")
        .order("session_time")
        .execute()
    )

    rows = response.data or []

    ongoing_sessions = []
    upcoming_sessions = []

    for row in rows:

        meeting_link = row.get("meeting_link")
        session_date = row.get("session_date")
        session_time = row.get("session_time")
        end_time = row.get("end_time")

        if not (meeting_link and session_date and session_time and end_time):
            continue

        # Convert session date
        if isinstance(session_date, str):
            session_date = datetime.strptime(
                session_date,
                "%Y-%m-%d"
            ).date()

        # Convert session start time
        if isinstance(session_time, str):
            try:
                session_time = datetime.strptime(
                    session_time,
                    "%H:%M:%S"
                ).time()
            except ValueError:
                session_time = datetime.strptime(
                    session_time,
                    "%H:%M"
                ).time()

        # Convert session end time
        if isinstance(end_time, str):
            try:
                end_time = datetime.strptime(
                    end_time,
                    "%H:%M:%S"
                ).time()
            except ValueError:
                end_time = datetime.strptime(
                    end_time,
                    "%H:%M"
                ).time()

        start_dt = datetime.combine(session_date, session_time)
        end_dt = datetime.combine(session_date, end_time)

        if timezone.is_naive(start_dt):
            start_dt = timezone.make_aware(
                start_dt,
                timezone.get_current_timezone()
            )

        if timezone.is_naive(end_dt):
            end_dt = timezone.make_aware(
                end_dt,
                timezone.get_current_timezone()
            )

        session = {
            "meeting_link": meeting_link,
            "skill": row.get("skill"),
            "start": start_dt,
            "end": end_dt,
        }

        # Ongoing
        if start_dt <= now < end_dt:
            session["status"] = "ongoing"
            ongoing_sessions.append(session)

        # Upcoming
        elif now < start_dt:
            session["status"] = "upcoming"
            upcoming_sessions.append(session)

        # Expired
        else:
            session["status"] = "expired"
            upcoming_sessions.append(session)

    return {
        "ongoing_sessions": ongoing_sessions,
        "upcoming_sessions": upcoming_sessions,
    }

def notification_count(request):
    if not request.user.is_authenticated:
        return {"notification_count": 0}

    unread_result = (
        supabase.table("notifications")
        .select("*", count="exact")
        .eq("user_email", request.user.email)
        .eq("status", "unread")
        .execute()
    )

    return {"notification_count": unread_result.count or 0}
    
def request_count(request):
    
    user_profile = request.session.get("user_profile")

    if not user_profile:
        return {"request_count": 0}

    result = (
        supabase
        .table("connections")
        .select("*")
        .eq("receiver_email", user_profile["email"])
        .eq("status", "pending")
        .execute()
    )

    return {
        "request_count": len(result.data)
    }
