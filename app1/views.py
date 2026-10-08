from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import MultipleObjectsReturned
from google.oauth2 import id_token
from google.auth.transport import requests
from django.core.paginator import Paginator
from .models import UserProfile
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Profile
from .models import ContactMessage
import json
import csv
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import login
from google.oauth2 import id_token
from google.auth.transport import requests
from django.conf import settings as django_settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.hashers import make_password, check_password
from django.views.decorators.csrf import ensure_csrf_cookie
from django.middleware.csrf import get_token
from django.core.files.storage import FileSystemStorage
from reportlab.pdfgen import canvas
from django.http import HttpResponse
import os
from .supabase_client import supabase
from app1.supabase_client import supabase
from datetime import datetime
import google.generativeai as genai
from collections import Counter
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


genai.configure(
    api_key="YOUR_GEMINI_API_KEY"
)

model = genai.GenerativeModel(
    "gemini-1.5-flash"
)


def normalize_skills(skills):
    if not skills:
        return []
    if isinstance(skills, list):
        return [skill.strip() for skill in skills if skill and skill.strip()]
    return [
        skill.strip()
        for skill in skills.split(",")
        if skill.strip()
    ]


def get_learn_skills_from_session(request):
    learn_skills = request.session.get("learn_skills")
    if learn_skills:
        return normalize_skills(learn_skills)
    learn_skill = request.session.get("learn_skill")
    profile = request.session.get("profile") or {}
    if learn_skill:
        return normalize_skills(learn_skill)
    return normalize_skills(profile.get("learn_skills") or profile.get("learn"))


def format_supabase_error(error_message):
    if "row-level security policy" in error_message.lower():
        return (
            "Supabase blocked the save (Row Level Security). "
            "Run app1/supabase_migrations/002_profiles_rls_policies.sql "
            "in the Supabase SQL Editor, then try again."
        )

    if "teach_skills" in error_message or "learn_skills" in error_message:
        return (
            "Supabase table is missing skill columns. "
            "Run app1/supabase_migrations/001_profile_skills.sql "
            "in the Supabase SQL Editor, then try again."
        )

    if "could not find" in error_message.lower() and "column" in error_message.lower():
        return (
            "Supabase table is missing registration columns. "
            "Run app1/supabase_migrations/003_register_fields.sql "
            "in the Supabase SQL Editor, then try again."
        )

    return f"Could not save: {error_message}"



def home(request):
    print(request.user)
    print(request.user.is_authenticated)

    return render(request, 'public/home.html')

def about(request):
    return render(request,'public/about.html')

def howitworks(request):
    return render(request,'public/howitworks.html')

def pricing(request):
    return render(request,'public/pricing.html')

# def register_view(request):
#     if request.method == "POST":
#         username = request.POST.get("username")
#         email = request.POST.get("email")
#         password = request.POST.get("password")

#         user = User.objects.create_user(
#             username=username,
#             email=email,
#             password=password
#         )

#         Profile.objects.get_or_create(
#             user=user,
#             defaults={
#                 "full_name": username,
#                 "email": email,
#                 "is_premium": False,
#                 "premium_plan": "free"
#             }
#         )

#         login(request, user)
#         return redirect("login_view")

#     return render(request, "public/register.html")

from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login
from .models import Profile

def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            return render(request, "public/register.html", {"error": "Passwords do not match"})

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        Profile.objects.get_or_create(
            user=user,
            defaults={
                "full_name": username,
                "email": email,
                "is_premium": False,
                "premium_plan": "free"
            }
        )

        login(request, user)
        return redirect("login_view")

    return render(request, "public/register.html")

@csrf_exempt
def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        if email == "admin123@gmail.com" and password == "1234":
            return redirect("admindashboard")
        try:
            user_obj = User.objects.get(email=email)
            user = authenticate(
                request,
                username=user_obj.username,
                password=password
            )
            if user is not None:
                login(request, user)
                if user.is_superuser or user.is_staff:
                    return redirect("admindashboard")
                profile, created = Profile.objects.get_or_create(
                    user=user,
                    defaults={
                        "full_name": user.get_full_name() or user.username,
                        "email": user.email,
                        "is_premium": False,
                        "premium_plan": "free"
                    }
                )
                return redirect("home")
            messages.error(request, "Invalid email or password")
        except User.DoesNotExist:
            messages.error(request, "User not found")
        except MultipleObjectsReturned:
            messages.error(request, "Multiple accounts found with this email")
    return render(request, "public/login.html")

@login_required
def contact(request):

    if request.method == "POST":

        ContactMessage.objects.create(
            name=request.POST.get("name"),
            email=request.POST.get("email"),
            mobile=request.POST.get("mobile"),
            subject=request.POST.get("subject"),
            message=request.POST.get("message")
        )

    context = {
        "full_name": request.user.profile.full_name,
        "email": request.user.email,
    }

    return render(request, "public/contact.html", context)

@csrf_exempt
def google_login(request):

    if request.method != "POST":
        return JsonResponse(
            {"success": False},
            status=400
        )

    try:

        data = json.loads(request.body)

        credential = data.get("credential")

        CLIENT_ID = (
            "534088856082-fmbpmuvqchgqe6vp1be83v9uu87t8ft2.apps.googleusercontent.com"
        )

        user_info = id_token.verify_oauth2_token(
            credential,
            requests.Request(),
            CLIENT_ID
        )

        email = user_info["email"]

        full_name = user_info.get("name", "")

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": email
            }
        )

        login(request, user)

        return JsonResponse({
            "success": True
        })

    except Exception as e:

        return JsonResponse({
            "success": False,
            "error": str(e)
        })

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required(login_url="login_view")
def dashboard(request):

    email = request.user.email

    # Logged-in user's profile
    profile = (
        supabase.table("app1_profile")
        .select("*")
        .eq("email", email)
        .maybe_single()
        .execute()
    ).data

    if not profile:
        return redirect("editProfile")

    my_teach = set(profile.get("teach_skills") or [])
    my_learn = set(profile.get("learn_skills") or [])

    # ---------------- Match Suggestions ----------------
    profiles = (
        supabase.table("app1_profile")
        .select("*")
        .neq("email", email)
        .execute()
    ).data or []

    matched_users = []

    for p in profiles:

        other_teach = set(p.get("teach_skills") or [])
        other_learn = set(p.get("learn_skills") or [])

        learn_matches = my_learn & other_teach
        teach_matches = my_teach & other_learn

        matches = len(learn_matches) + len(teach_matches)
        total = len(my_teach) + len(my_learn)

        percent = int((matches / total) * 100) if total else 0

        if percent > 0:

            matched_users.append({
                "id": p.get("id"),
                "name": p.get("full_name"),
                "profile_image_url": p.get("profile_image"),
                "skills": list(learn_matches | teach_matches),
                "match": percent,
            })

    matched_users = sorted(
        matched_users,
        key=lambda x: x["match"],
        reverse=True
    )[:5]

    # ---------------- Previous Matches ----------------
    connections = (
        supabase.table("connections")
        .select("*")
        .eq("status", "accepted")
        .or_(f"sender_email.eq.{email},receiver_email.eq.{email}")
        .execute()
    ).data or []

    previous_matches = []

    for conn in connections:

        # Get the other user's email
        if conn["sender_email"] == email:
            other_email = conn["receiver_email"]
        else:
            other_email = conn["sender_email"]

        profile_result = (
            supabase.table("app1_profile")
            .select("full_name, profile_image, teach_skills")
            .eq("email", other_email)
            .maybe_single()
            .execute()
        )

        if profile_result.data:

            p = profile_result.data

            previous_matches.append({
                "name": p.get("full_name"),
                "email": other_email,
                "profile_image": p.get("profile_image"),
                "teach_skills": p.get("teach_skills") or [],
            })

    # ---------------- Statistics ----------------
    total_teach = len(my_teach)
    total_learn = len(my_learn)
    total_skills = total_teach + total_learn

    context = {
        "profile": profile,
        "matched_users": matched_users,
        "previous_matches": previous_matches,
        "teach_skills": list(my_teach),
        "learn_skills": list(my_learn),
        "total_skills": total_skills,
        "teach_count": total_teach,
        "learn_count": total_learn,
    }

    return render(request, "user/dashboard.html", context)

@login_required
def profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    return render(request, 'user/profile.html', {'profile': profile})

@login_required
def editProfile(request):
    profile, created = Profile.objects.get_or_create(
        user=request.user,
        defaults={
            "full_name": request.user.get_full_name() or request.user.username,
            "email": request.user.email,
        }
    )

    if request.method == "POST":
        profile.full_name = request.POST.get("full_name", "").strip()
        profile.professional_title = request.POST.get("professional_title", "").strip()
        profile.location = request.POST.get("location", "").strip()
        profile.email = request.POST.get("email", "").strip()
        profile.bio = request.POST.get("bio", "").strip()

        if request.FILES.get("profile_image"):
            profile.profile_image = request.FILES.get("profile_image")

        profile.linkedin = request.POST.get("linkedin", "").strip()
        profile.github = request.POST.get("github", "").strip()
        profile.twitter = request.POST.get("twitter", "").strip()
        profile.youtube = request.POST.get("youtube", "").strip()
        profile.education = request.POST.get("education", "").strip()
        profile.experience = request.POST.get("experience", "").strip()
        profile.achievements = request.POST.get("achievements", "").strip()

        teach_skills_raw = request.POST.get("teach_skills", "").strip()
        learn_skills_raw = request.POST.get("learn_skills", "").strip()

        profile.teach_skills = [
            skill.strip() for skill in teach_skills_raw.split(",") if skill.strip()
        ]

        profile.learn_skills = [
            skill.strip() for skill in learn_skills_raw.split(",") if skill.strip()
        ]
        profile.save()
        messages.success(request, "Profile updated successfully.")
        return redirect("editProfile")

    return render(request, "user/editProfile.html", {"profile": profile})

def certifications(request):
    return render(request,'user/certifications.html')


@login_required
def matches(request):
    email = request.user.email

    # -----------------------------
    # Current User Profile
    # -----------------------------
    profile_result = (
        supabase.table("app1_profile")
        .select("*")
        .eq("email", email)
        .maybe_single()
        .execute()
    )

    profile = profile_result.data if profile_result.data else {}

    # Convert comma-separated strings/lists into Python lists
    def normalize_list(value):
        if not value:
            return []

        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]

        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]

        return []

    profile["teach_skills"] = normalize_list(profile.get("teach_skills"))
    profile["learn_skills"] = normalize_list(profile.get("learn_skills"))

    image_name = profile.get("profile_image")
    if image_name:
        profile["profile_image_url"] = f"{settings.MEDIA_URL}{image_name}"
    else:
        profile["profile_image_url"] = None

    # -----------------------------
    # Search Skill
    # -----------------------------
    search_skill = request.GET.get("skill", "").strip().lower()

    if not search_skill:
        return render(
            request,
            "user/matches.html",
            {
                "members": [],
                "profile": profile,
                "notification_count": 0,
                "search_skill": "",
            }
        )

    # -----------------------------
    # Get all users
    # -----------------------------
    result = (
        supabase.table("app1_profile")
        .select("*")
        .execute()
    )

    members = result.data or []
    matched_members = []

    # Current user's learn skills
    learner_skills = [s.lower() for s in profile.get("learn_skills", [])]

    # -----------------------------
    # Match Users
    # -----------------------------
    for m in members:

        # Skip current user
        if m.get("email") == email:
            continue

        teach_skills = normalize_list(m.get("teach_skills"))
        learn_skills_member = normalize_list(m.get("learn_skills"))

        mentor_skills = [s.lower() for s in teach_skills]

        # Show only mentors who teach searched skill
        if search_skill not in mentor_skills:
            continue

        # -----------------------------
        # Skill Match
        # -----------------------------
        matched_skills = set(learner_skills).intersection(set(mentor_skills))
        matched_count = len(matched_skills)

        if learner_skills:
            skill_percentage = (matched_count / len(learner_skills)) * 100
        else:
            skill_percentage = 0

        # -----------------------------
        # Average Rating
        # -----------------------------
        rating_result = (
            supabase.table("connections")
            .select("rating")
            .eq("receiver_email", m["email"])
            .eq("completed", True)
            .execute()
        )

        ratings = [
            float(r["rating"])
            for r in (rating_result.data or [])
            if r.get("rating") is not None
        ]

        avg_rating = sum(ratings) / len(ratings) if ratings else 0

        rating_percentage = (avg_rating / 5) * 100

        # -----------------------------
        # Overall Match
        # -----------------------------
        final_score = (skill_percentage + rating_percentage) / 2

        # -----------------------------
        # Profile Image
        # -----------------------------
        image_name = m.get("profile_image")

        if image_name:
            m["profile_image_url"] = f"{settings.MEDIA_URL}{image_name}"
        else:
            m["profile_image_url"] = None

        m["teach_skills"] = teach_skills
        m["learn_skills"] = learn_skills_member
        m["average_rating"] = round(avg_rating, 2)
        m["rating_percentage"] = round(rating_percentage, 2)
        m["skill_percentage"] = round(skill_percentage, 2)
        m["match_score"] = round(final_score, 2)

        matched_members.append(m)

    # -----------------------------
    # Sort by Overall Match
    # -----------------------------
    matched_members.sort(
        key=lambda x: x["match_score"],
        reverse=True
    )

    if matched_members:
        matched_members[0]["is_top_match"] = True

    notification_count = 0

    return render(
        request,
        "user/matches.html",
        {
            "members": matched_members,
            "profile": profile,
            "notification_count": notification_count,
            "search_skill": search_skill,
        }
    )


from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.conf import settings

# @login_required
def member_profile(request, id):
    profile_result = supabase.table("app1_profile").select("*").eq("id", id).single().execute()
    profile_data = profile_result.data or {}

    user_id = profile_data.get("user_id")

    user_data = {}
    if user_id:
        user_result = (
            supabase.table("auth_user")
            .select("username, email, date_joined")
            .eq("id", user_id)
            .single()
            .execute()
        )
        user_data = user_result.data or {}

    email = profile_data.get("email") or user_data.get("email")

    latest_rating = {}
    if email:
        rating_result = (
            supabase.table("notifications")
            .select("rating, review, created_at")
            .eq("user_email", email)
            .not_.is_("rating", "null")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if rating_result.data:
            latest_rating = rating_result.data[0]

    def build_image_url(image_path):
        if not image_path:
            return None
        if image_path.startswith(("http://", "https://")):
            return image_path
        return settings.MEDIA_URL + image_path.lstrip("/")

    def get_profile_by_email(other_email):
        if not other_email:
            return None

        result = (
            supabase.table("app1_profile")
            .select("id, email, full_name, professional_title, location, bio, profile_image, learn_skills, teach_skills, education, experience, achievements")
            .eq("email", other_email)
            .maybe_single()
            .execute()
        )
        profile = result.data
        if profile:
            profile["profile_image_url"] = build_image_url(profile.get("profile_image"))
        return profile

    def attach_profile_ids(rows, email_field):
        updated = []
        for row in rows:
            other_email = row.get(email_field)
            other_profile = get_profile_by_email(other_email)
            row["other_profile"] = other_profile
            row["other_profile_id"] = other_profile.get("id") if other_profile else None
            updated.append(row)
        return updated

    teaching = (
        supabase.table("connections")
        .select("*")
        .eq("mentor_email", email)
        .eq("completed", False)
        .order("created_at", desc=True)
        .execute()
        .data or []
    )

    learning = (
        supabase.table("connections")
        .select("*")
        .eq("learner_email", email)
        .eq("completed", False)
        .order("created_at", desc=True)
        .execute()
        .data or []
    )

    completed = (
        supabase.table("connections")
        .select("*")
        .or_(f"mentor_email.eq.{email},learner_email.eq.{email}")
        .eq("completed", True)
        .order("completed_at", desc=True)
        .execute()
        .data or []
    )

    teaching = attach_profile_ids(teaching, "learner_email")
    learning = attach_profile_ids(learning, "mentor_email")
    completed = attach_profile_ids(completed, "mentor_email")

    profile_image = profile_data.get("profile_image")
    profile_image_url = build_image_url(profile_image)

    profile = {
        "full_name": profile_data.get("full_name") or user_data.get("username") or "Not Available",
        "professional_title": profile_data.get("professional_title") or "",
        "email": email or "Not Available",
        "location": profile_data.get("location") or "Not Available",
        "experience": profile_data.get("experience") or "Not Available",
        "bio": profile_data.get("bio") or "",
        "about": profile_data.get("bio") or "",
        "profile_image_url": profile_image_url,
        "teach_skills": profile_data.get("teach_skills") or [],
        "learn_skills": profile_data.get("learn_skills") or [],
        "is_premium": profile_data.get("is_premium", False),
        "date_joined": user_data.get("date_joined") or "",
        "avg_rating": latest_rating.get("rating", 0) or 0,
        "review": latest_rating.get("review", ""),
    }

    avg_rating = float(profile["avg_rating"]) if profile["avg_rating"] else 0
    stars = (
        "★★★★★" if avg_rating >= 4.5 else
        "★★★★☆" if avg_rating >= 3.5 else
        "★★★☆☆" if avg_rating >= 2.5 else
        "★★☆☆☆" if avg_rating >= 1.5 else
        "★☆☆☆☆" if avg_rating > 0 else
        "☆☆☆☆☆"
    )

    return render(request, "admin/member_profile.html", {
        "profile": profile,
        "stars": stars,
        "avg_rating": avg_rating,
        "teach_skills": profile["teach_skills"],
        "learn_skills": profile["learn_skills"],
        "teaching_connections": teaching,
        "learning_connections": learning,
        "completed_connections": completed,
    })


@login_required
def member_profile1(request, id):
    profile_result = supabase.table("app1_profile").select("*").eq("id", id).single().execute()
    profile_data = profile_result.data or {}

    user_id = profile_data.get("user_id")

    user_data = {}
    if user_id:
        user_result = (
            supabase.table("auth_user")
            .select("username, email, date_joined")
            .eq("id", user_id)
            .single()
            .execute()
        )
        user_data = user_result.data or {}

    email = profile_data.get("email") or user_data.get("email")

    latest_rating = {}
    if email:
        rating_result = (
            supabase.table("notifications")
            .select("rating, review, created_at")
            .eq("user_email", email)
            .not_.is_("rating", "null")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if rating_result.data:
            latest_rating = rating_result.data[0]

    def build_image_url(image_path):
        if not image_path:
            return None
        if image_path.startswith(("http://", "https://")):
            return image_path
        return settings.MEDIA_URL + image_path.lstrip("/")

    def get_profile_by_email(other_email):
        if not other_email:
            return None

        result = (
            supabase.table("app1_profile")
            .select("id, email, full_name, professional_title, location, bio, profile_image, learn_skills, teach_skills, education, experience, achievements")
            .eq("email", other_email)
            .maybe_single()
            .execute()
        )
        profile = result.data
        if profile:
            profile["profile_image_url"] = build_image_url(profile.get("profile_image"))
        return profile

    def attach_profile_ids(rows, email_field):
        updated = []
        for row in rows:
            other_email = row.get(email_field)
            other_profile = get_profile_by_email(other_email)
            row["other_profile"] = other_profile
            row["other_profile_id"] = other_profile.get("id") if other_profile else None
            updated.append(row)
        return updated

    teaching = (
        supabase.table("connections")
        .select("*")
        .eq("mentor_email", email)
        .eq("completed", False)
        .order("created_at", desc=True)
        .execute()
        .data or []
    )

    learning = (
        supabase.table("connections")
        .select("*")
        .eq("learner_email", email)
        .eq("completed", False)
        .order("created_at", desc=True)
        .execute()
        .data or []
    )

    completed = (
        supabase.table("connections")
        .select("*")
        .or_(f"mentor_email.eq.{email},learner_email.eq.{email}")
        .eq("completed", True)
        .order("completed_at", desc=True)
        .execute()
        .data or []
    )

    teaching = attach_profile_ids(teaching, "learner_email")
    learning = attach_profile_ids(learning, "mentor_email")
    completed = attach_profile_ids(completed, "mentor_email")

    profile_image = profile_data.get("profile_image")
    profile_image_url = build_image_url(profile_image)

    profile = {
        "full_name": profile_data.get("full_name") or user_data.get("username") or "Not Available",
        "professional_title": profile_data.get("professional_title") or "",
        "email": email or "Not Available",
        "location": profile_data.get("location") or "Not Available",
        "experience": profile_data.get("experience") or "Not Available",
        "bio": profile_data.get("bio") or "",
        "about": profile_data.get("bio") or "",
        "profile_image_url": profile_image_url,
        "teach_skills": profile_data.get("teach_skills") or [],
        "learn_skills": profile_data.get("learn_skills") or [],
        "is_premium": profile_data.get("is_premium", False),
        "date_joined": user_data.get("date_joined") or "",
        "avg_rating": latest_rating.get("rating", 0) or 0,
        "review": latest_rating.get("review", ""),
    }

    avg_rating = float(profile["avg_rating"]) if profile["avg_rating"] else 0
    stars = (
        "★★★★★" if avg_rating >= 4.5 else
        "★★★★☆" if avg_rating >= 3.5 else
        "★★★☆☆" if avg_rating >= 2.5 else
        "★★☆☆☆" if avg_rating >= 1.5 else
        "★☆☆☆☆" if avg_rating > 0 else
        "☆☆☆☆☆"
    )

    return render(request, "user/member_profile1.html", {
        "profile": profile,
        "stars": stars,
        "avg_rating": avg_rating,
        "teach_skills": profile["teach_skills"],
        "learn_skills": profile["learn_skills"],
        "teaching_connections": teaching,
        "learning_connections": learning,
        "completed_connections": completed,
    })

def assignments(request):
    return render(request,'user/assignments.html')

def chat(request):
    return render(request,'user/chat.html')

def interview(request):
    return render(request,'user/interview.html')

def progress(request):
    return render(request,'user/progress.html')

def sessions(request):
    return render(request,'user/sessions.html')

def usersubscriptions(request):
    return render(request,'user/usersubscriptions.html')

# ADMIN DASHBOARD SECTION

def admindashboard(request):
    return render(request,'admin/admin-dashboard.html')

def usermanagement(request):
    return render(request,'admin/user-management.html')

def skillmanagement(request):
    return render(request,'admin/skill-management.html')

def subscriptions(request):
    return render(request,'admin/subscriptions.html')

def analytics(request):
    return render(
        request,
        "admin/analytics.html",
    )
def support(request):
    return render(request,'admin/support-feedback.html')

def rating(request):
    return render(request,'user/rating.html')


from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages

@login_required
def send_request(request, member_id):
    sender_email = request.user.email
    skill = request.POST.get("skill")

    sender_result = (
        supabase.table("app1_profile")
        .select("is_premium,full_name,email")
        .eq("email", sender_email)
        .maybe_single()
        .execute()
    )

    sender = sender_result.data

    if not sender:
        messages.error(request, "Your profile was not found.")
        return redirect("matches")

    if not sender.get("is_premium"):
        messages.warning(
            request,
            "This is a Premium feature. Upgrade your plan to connect with other users."
        )
        return redirect("pricing")

    receiver_result = (
        supabase.table("app1_profile")
        .select("*")
        .eq("id", member_id)
        .maybe_single()
        .execute()
    )

    receiver = receiver_result.data

    if not receiver:
        messages.error(request, "User not found.")
        return redirect("matches")

    receiver_email = receiver.get("email")
    receiver_name = (
        receiver.get("full_name")
        or receiver.get("name")
        or receiver_email
    )

    if not receiver_email or sender_email == receiver_email:
        messages.error(request, "You cannot connect with yourself.")
        return redirect("matches")

    existing = (
        supabase.table("connections")
        .select("*")
        .or_(
            f"and(sender_email.eq.{sender_email},receiver_email.eq.{receiver_email}),"
            f"and(sender_email.eq.{receiver_email},receiver_email.eq.{sender_email})"
        )
        .execute()
    )

    if existing.data:
        messages.info(request, "Connection already exists.")
        return redirect("matches")

    connection_response = (
        supabase.table("connections")
        .insert({
            "sender_email": sender_email,
            "receiver_email": receiver_email,
            "mentor_email": receiver_email,
            "learner_email": sender_email,
            "skill": skill,
            "status": "pending",
            "completed": False,
            "connection_type": "teaching",
        })
        .execute()
    )

    connection_id = None
    if connection_response.data:
        connection_id = connection_response.data[0]["id"]

    supabase.table("notifications").insert({
        "user_email": receiver_email,
        "sender_email": sender_email,
        "title": "Learning Request",
        "message": f"{sender.get('full_name')} wants to learn {skill}",
        "type": "REQUEST",
        "connection_id": connection_id,
        "status": "unread"
    }).execute()

    messages.success(request, "Connection request sent successfully.")
    return redirect("matches")

@login_required
def connection_requests(request):
    email = request.user.email
    result = (
        supabase
        .table("connections")
        .select("*")
        .eq("receiver_email", email)
        .eq("status", "pending")
        .execute()
    )
    return render(request, "user/requests.html", {"requests": result.data})

@login_required
def notifications(request):

    email = request.user.email

    # Mark all notifications as read
    supabase.table("notifications").update({
        "status": "read"
    }).eq("user_email", email).execute()

    # Fetch all notifications
    result = (
        supabase.table("notifications")
        .select("*")
        .eq("user_email", email)
        .order("id", desc=True)
        .execute()
    )

    notifications = result.data or []

    # Process each notification
    for n in notifications:

        # Request notifications
        if n.get("type") == "REQUEST" and n.get("connection_id"):

            connection_result = (
                supabase.table("connections")
                .select("status, mentor_email, learner_email, completed")
                .eq("id", n["connection_id"])
                .maybe_single()
                .execute()
            )

            if connection_result.data:
                connection = connection_result.data
                n["request_status"] = connection.get("status", "").upper()
                n["is_mentor"] = connection.get("mentor_email") == email
                n["completed"] = connection.get("completed", False)
            else:
                n["request_status"] = ""
                n["is_mentor"] = False
                n["completed"] = False

        # Session notifications
        if n.get("type") == "SESSION" and n.get("connection_id"):

            session_result = (
                supabase.table("sessions")
                .select("skill, session_date, session_time, end_time, meeting_link")
                .eq("connection_id", n["connection_id"])
                .order("id", desc=True)
                .limit(1)
                .execute()
            )

            if session_result.data:
                session = session_result.data[0]
                n["skill"] = session.get("skill")
                n["session_date"] = session.get("session_date")
                n["session_time"] = session.get("session_time")
                n["end_time"] = session.get("end_time")
                n["meeting_link"] = session.get("meeting_link")

            connection_result = (
                supabase.table("connections")
                .select("mentor_email, learner_email, completed")
                .eq("id", n["connection_id"])
                .maybe_single()
                .execute()
            )

            if connection_result.data:
                connection = connection_result.data
                n["is_mentor"] = connection.get("mentor_email") == email
                n["completed"] = connection.get("completed", False)
            else:
                n["is_mentor"] = False
                n["completed"] = False

    # Count unread notifications
    notification_result = (
        supabase.table("notifications")
        .select("*")
        .eq("user_email", email)
        .eq("status", "unread")
        .execute()
    )

    notification_count = len(notification_result.data or [])

    return render(
        request,
        "user/notifications.html",
        {
            "notifications": notifications,
            "notification_count": notification_count,
            "connected_users": [],
        },
    )
@login_required
def accept_request(request, request_id):
    connection = (
        supabase.table("connections")
        .select("*")
        .eq("id", request_id)
        .maybe_single()
        .execute()
    )

    if not connection.data:
        return redirect("notifications")

    request_data = connection.data
    skill = request_data.get("skill")

    supabase.table("connections").update({
        "status": "accepted"
    }).eq("id", request_id).execute()

    supabase.table("notifications").insert({
        "user_email": request_data["sender_email"],
        "title": "Connection Accepted",
        "message": f"{request_data['receiver_email']} accepted your request to learn {skill}",
        "type": "ACCEPTED",
        "status": "unread",
        "connection_id": request_id
    }).execute()

    return redirect("notifications")

@login_required
def reject_request(request, request_id):
    connection = (
        supabase.table("connections")
        .select("*")
        .eq("id", request_id)
        .maybe_single()
        .execute()
    )

    if not connection.data:
        return redirect("notifications")

    request_data = connection.data

    supabase.table("connections").update({
        "status": "rejected"
    }).eq("id", request_id).execute()

    supabase.table("notifications").update({
        "status": "read"
    }).eq("connection_id", request_id).execute()

    create_notification(
        user_email=request_data["sender_email"],
        title="Connection Rejected",
        message="Your connection request was rejected.",
        notification_type="REJECTED",
        sender_email=request_data["receiver_email"],
        connection_id=request_id
    )

    return redirect("notifications")

def create_notification(
    user_email,
    title,
    message,
    notification_type,
    sender_email=None,
    connection_id=None,
    skill=None,
    file_url=None,
    deadline=None,
    session_date=None,
    session_time=None,
    end_time=None,
    meeting_link=None,
    rating=None,
    review=None,
):
    payload = {
        "user_email": user_email,
        "title": title,
        "message": message,
        "type": notification_type,
        "status": "unread",
    }

    if sender_email:
        payload["sender_email"] = sender_email
    if connection_id:
        payload["connection_id"] = connection_id
    if skill:
        payload["skill"] = skill
    if file_url:
        payload["file_url"] = file_url
    if deadline:
        payload["deadline"] = deadline
    if session_date:
        payload["session_date"] = session_date

    if session_time:
        payload["session_time"] = session_time

    if end_time:
        payload["end_time"] = end_time

    if meeting_link:
        payload["meeting_link"] = meeting_link

    if rating is not None:
        payload["rating"] = rating
    
    if review:
        payload["review"] = review

    return (
        supabase
        .table("notifications")
        .insert(payload)
        .execute()
    )

    
@login_required
def mark_notification_read(request):
    """Mark ALL notifications as read - returns JSON to update UI"""
    email = request.user.email
    
    supabase.table("notifications").update({
        "status": "read"
    }).eq("user_email", email).execute()
    
    return JsonResponse({"success": True, "count": 0})

def send_message(request):
    
    sender = request.session["profile"]["email"]
    receiver = request.POST["receiver"]
    message = request.POST["message"]

    supabase.table("messages").insert({
        "sender_email": sender,
        "receiver_email": receiver,
        "message": message
    }).execute()

    return redirect("chat_with_user", email=receiver)


from django.core.files.storage import FileSystemStorage

def chat(request, email=None):
    if not request.user.is_authenticated:
        return redirect("login_view")

    current_user = request.user.email
    selected_user = email

    if request.method == "POST" and email:
        assignment_file = request.FILES.get("assignment_file")
        deadline = request.POST.get("deadline") or None
        submission_file = request.FILES.get("submission_file")

        if assignment_file:
            upload_dir = "media/assignments"
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)

            fs = FileSystemStorage(location=upload_dir)
            filename = fs.save(assignment_file.name, assignment_file)
            file_url = f"/media/assignments/{filename}"

            supabase.table("messages").insert({
                "sender_email": current_user,
                "receiver_email": email,
                "message": f"Assignment: {filename}",
                "file_url": file_url,
                "deadline": deadline
            }).execute()

            supabase.table("notifications").insert({
                "user_email": email,
                "sender_email": current_user,
                "title": "New Assignment",
                "message": f"Assignment sent: {filename}",
                "file_url": file_url,
                "deadline": deadline,
                "type": "ASSIGNMENT",
                "status": "unread"
            }).execute()

            return redirect("chat_with_user", email=email)

        if submission_file:
            upload_dir = "media/assignments"
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)

            fs = FileSystemStorage(location=upload_dir)
            filename = fs.save(submission_file.name, submission_file)
            file_url = f"/media/assignments/{filename}"

            supabase.table("messages").insert({
                "sender_email": current_user,
                "receiver_email": email,
                "message": f"Assignment Submission: {filename}",
                "file_url": file_url
            }).execute()

            supabase.table("notifications").insert({
                "user_email": email,
                "sender_email": current_user,
                "title": "Assignment Submitted",
                "message": f"{current_user} submitted an assignment",
                "file_url": file_url,
                "deadline": deadline,
                "type": "SUBMISSION",
                "status": "unread"
            }).execute()

            return redirect("chat_with_user", email=email)

        message = request.POST.get("message", "").strip()

        if message:
            supabase.table("messages").insert({
                "sender_email": current_user,
                "receiver_email": email,
                "message": message
            }).execute()

            supabase.table("notifications").insert({
                "user_email": email,
                "sender_email": current_user,
                "title": "New Message",
                "message": message,
                "type": "MESSAGE",
                "status": "unread"
            }).execute()

            return redirect("chat_with_user", email=email)

    messages = []
    if email:
        result = (
            supabase.table("messages")
            .select("*")
            .or_(
                f"and(sender_email.eq.{current_user},receiver_email.eq.{email}),"
                f"and(sender_email.eq.{email},receiver_email.eq.{current_user})"
            )
            .order("created_at")
            .execute()
        )
        messages = result.data or []

    return render(
        request,
        "user/chat.html",
        {
            "messages": messages,
            "receiver": selected_user,
        }
    )


# razorpay

import razorpay
from django.conf import settings
from django.utils import timezone
from .decorators import premium_required
@login_required
def premium_page(request):
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={
            "full_name": request.user.get_full_name() or request.user.username,
            "email": request.user.email,
        }
    )

    if profile.is_premium:
        return redirect("premium_dashboard")

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    order_data = {
        "amount": settings.PREMIUM_PRICE_PAISE,
        "currency": "INR",
        "payment_capture": 1
    }

    order = client.order.create(data=order_data)

    profile.razorpay_order_id = order["id"]
    profile.premium_amount = settings.PREMIUM_PRICE_RUPEES
    profile.save()

    context = {
        "profile": profile,
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "order_id": order["id"],
        "amount": settings.PREMIUM_PRICE_PAISE,
        "display_amount": settings.PREMIUM_PRICE_RUPEES,
        "user_name": profile.full_name or request.user.username,
        "user_email": request.user.email,
    }
    return render(request, "user/premium_payment.html", context)

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


@login_required(login_url='login_view')
def premium_chat(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if not profile.is_premium:
        messages.error(request, "This feature is available only for premium users.")
        return redirect("premium_page")

    return render(request, "user/premium_chat.html")

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

@csrf_exempt
def verify_razorpay_payment(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request"}, status=405)

    data = json.loads(request.body)

    razorpay_order_id = data.get("razorpay_order_id")
    razorpay_payment_id = data.get("razorpay_payment_id")
    razorpay_signature = data.get("razorpay_signature")

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature
        })
        return JsonResponse({"success": True, "message": "Payment verified successfully"})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=400)

@login_required
def create_order(request):

    request.session["payment_user_email"] = request.user.email
    print("Saved Email:", request.session["payment_user_email"])

    amount = 299

    order = client.order.create({
        "amount": amount * 100,
        "currency": "INR",
        "receipt": f"receipt_{request.user.id}",
    })

    return JsonResponse({
        "success": True,
        "order_id": order["id"],
        "amount": amount * 100,
        "currency": "INR",
        "key": settings.RAZORPAY_KEY_ID,
    })

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def pricing(request):
    amount = 299
    razorpay_order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "receipt": "receipt_order_1",
    })
    return render(request, "public/pricing.html", {
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "amount": amount,
        "order_id": razorpay_order["id"],
        "currency": "INR",
    })



from django.contrib import messages
from django.utils import timezone
from razorpay.errors import SignatureVerificationError

    
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages


    
@login_required(login_url="login_view")
def payment_success(request):
    email = request.user.email

    try:
        response = (
            supabase.table("app1_profile")
            .update({
                "is_premium": True,
                "premium_amount": 299,
                "premium_plan": "premium"
            })
            .eq("email", email)
            .select("id, email, is_premium, premium_amount, premium_plan")
            .execute()
        )

        return redirect("dashboard")

    except Exception as e:
        print("Payment update failed:", str(e))
        return redirect("dashboard")


from datetime import datetime, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect


@login_required
def sessions(request, connection_id=None):

    connection = None

    if connection_id is not None:

        result = (
            supabase.table("connections")
            .select("*")
            .eq("id", connection_id)
            .maybe_single()
            .execute()
        )

        connection = result.data

        if not connection:
            messages.error(request, "Connection not found.")
            return redirect("notifications")

    if request.method == "POST":

        if connection_id is None or not connection:
            messages.error(request, "Invalid connection.")
            return redirect("notifications")

        session_date = request.POST.get("session_date")
        session_time = request.POST.get("session_time")
        meeting_link = request.POST.get("meeting_link")

        if not session_date or not session_time:
            messages.error(request, "Session date and time are required.")
            return render(
                request,
                "user/sessions.html",
                {
                    "connection": connection,
                    "connection_id": connection_id,
                },
            )

        # Calculate end time (1 hour duration)
        start_dt = datetime.strptime(
            f"{session_date} {session_time}",
            "%Y-%m-%d %H:%M"
        )

        end_dt = start_dt + timedelta(hours=1)
        end_time = end_dt.strftime("%H:%M")

        # Save session
        supabase.table("sessions").insert({
            "student_email": connection["sender_email"],
            "mentor_email": connection["receiver_email"],
            "skill": connection["skill"],
            "session_date": session_date,
            "session_time": session_time,
            "end_time": end_time,
            "meeting_link": meeting_link,
            "status": "Scheduled",
            "connection_id": connection_id,
        }).execute()

        # Notification for Student
        create_notification(
            user_email=connection["sender_email"],
            title="Session Scheduled",
            message=f"Session scheduled for {session_date} at {session_time}",
            notification_type="SESSION",
            sender_email=connection["receiver_email"],
            connection_id=connection_id,
            skill=connection["skill"],
            session_date=session_date,
            session_time=session_time,
            end_time=end_time,
            meeting_link=meeting_link,
        )

        # Notification for Mentor
        create_notification(
            user_email=connection["receiver_email"],
            title="Session Scheduled",
            message=f"Session scheduled for {session_date} at {session_time}",
            notification_type="SESSION",
            sender_email=connection["sender_email"],
            connection_id=connection_id,
            skill=connection["skill"],
            session_date=session_date,
            session_time=session_time,
            end_time=end_time,
            meeting_link=meeting_link,
        )

        messages.success(request, "Session scheduled successfully.")
        return redirect("notifications")

    return render(
        request,
        "user/sessions.html",
        {
            "connection": connection,
            "connection_id": connection_id,
        },
    )

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages
from datetime import datetime


from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages
from datetime import datetime

@login_required
def complete_course(request, connection_id):

    email = request.user.email

    result = (
        supabase
        .table("connections")
        .select("*")
        .eq("id", connection_id)
        .maybe_single()
        .execute()
    )

    if not result.data:
        messages.error(request, "Connection not found.")
        return redirect("notifications")

    connection = result.data

    # Only mentor can complete the course
    if connection["receiver_email"] != email:
        messages.error(request, "Only the mentor can complete the course.")
        return redirect("notifications")

    # Prevent duplicate completion
    if connection.get("completed"):
        messages.info(request, "Course is already completed.")
        return redirect("notifications")

    # Update connection
    (
        supabase
        .table("connections")
        .update({
            "completed": True
        })
        .eq("id", connection_id)
        .execute()
    )

    # Notify student
    create_notification(
        user_email=connection["sender_email"],
        title="Course Completed",
        message=f"{connection['receiver_email']} has completed your {connection['skill']} course. Please rate your mentor.",
        notification_type="COURSE_COMPLETED",
        sender_email=connection["receiver_email"],
        connection_id=connection_id,
        skill=connection["skill"]
    )

    messages.success(request, "Course marked as completed.")

    return redirect("notifications")

@csrf_exempt
def generate_question(request):
    data = json.loads(request.body)
    skill = data["skill"]
    return JsonResponse({
        "question": f"What is your experience with {skill}?"
    })

def test_ai(request):
    return JsonResponse({
        "message": "AI Route Working"
    })

@csrf_exempt
def evaluate_answer(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    data = json.loads(request.body)
    skill = data.get("skill", "").strip()
    answer = data.get("answer", "").strip()
    question_no = int(data.get("question_no", 1))
    questions = [
        f"What is {skill}?",
        f"What are the advantages of {skill}?",
        f"What are the disadvantages of {skill}?",
        f"Explain the architecture of {skill}.",
        f"What are the real-world applications of {skill}?",
        f"What challenges have you faced in {skill}?",
        f"Explain advanced concepts in {skill}.",
        f"How would you optimize a {skill} project?",
        f"What are best practices in {skill}?",
        f"Why should a company use {skill}?"
    ]

    if len(answer) < 20:
        feedback = "Your answer is too short. Add more detail."
    elif "don't know" in answer.lower() or "not sure" in answer.lower():
        feedback = "Try to explain the concept more confidently."
    elif len(answer) < 60:
        feedback = "Good start, but you can add more examples."
    else:
        feedback = "Good answer. Keep going!"

    next_index = question_no % len(questions)

    return JsonResponse({
        "feedback": feedback,
        "next_question": questions[next_index]
    })


from supabase import create_client
from datetime import datetime, timedelta, timezone
from django.conf import settings
from collections import Counter
from django.shortcuts import render
from collections import Counter
from django.conf import settings
import matplotlib.pyplot as plt
import os


def admindashboard(request):

    total_users = (
        supabase.table("app1_profile")
        .select("*", count="exact", head=True)
        .execute()
        .count or 0
    )

    profiles = (
        supabase.table("app1_profile")
        .select("full_name, is_premium, learn_skills, teach_skills")
        .execute()
        .data or []
    )

    # ---------- Skill Analytics ----------
    all_skills = []

    for profile in profiles:

        teach_skills = profile.get("teach_skills") or []
        learn_skills = profile.get("learn_skills") or []

        if isinstance(teach_skills, str):
            teach_skills = teach_skills.split(",")

        if isinstance(learn_skills, str):
            learn_skills = learn_skills.split(",")

        teach_skills = [
            skill.strip().lower()
            for skill in teach_skills
            if skill and skill.strip()
        ]

        learn_skills = [
            skill.strip().lower()
            for skill in learn_skills
            if skill and skill.strip()
        ]

        all_skills.extend(teach_skills)
    

    unique_skills = sorted(set(all_skills))

    skill_counts = Counter(all_skills)

    # Continue with the rest of your code...
    revenue_rows = (
        supabase.table("app1_profile")
        .select("premium_amount")
        .execute()
        .data or []
    )

    revenue = sum(
        row.get("premium_amount", 0)
        for row in revenue_rows
        if row.get("premium_amount")
    )

    recent_users = (
        supabase.table("auth_user")
        .select("email, date_joined")
        .order("date_joined", desc=True)
        .limit(3)
        .execute()
        .data or []
    )

    all_users = (
        supabase.table("auth_user")
        .select("date_joined")
        .order("date_joined")
        .execute()
        .data or []
    )

    join_dates = []

    for user in all_users:
        if user.get("date_joined"):
            join_dates.append(user["date_joined"][:10])

    join_counts = Counter(join_dates)

    recent_payments = (
        supabase.table("app1_profile")
        .select(
            "full_name, premium_amount, premium_plan, premium_started_at"
        )
        .order("premium_started_at", desc=True)
        .limit(3)
        .execute()
        .data or []
    )
    charts_dir = os.path.join(
        settings.BASE_DIR,
        "static",
        "charts"
    )

    os.makedirs(charts_dir, exist_ok=True)

    chart_path = os.path.join(
        charts_dir,
        "recent_users_chart.png"
    )

    dates = sorted(join_counts.keys())
    counts = [join_counts[d] for d in dates]

    plt.figure(figsize=(10, 5))

    plt.plot(
        dates,
        counts,
        marker="o",
        linewidth=2
    )

    plt.title("Daily User Registrations")
    plt.xlabel("Date")
    plt.ylabel("Users Joined")
    plt.xticks(rotation=45)
    plt.grid(True)

    plt.tight_layout()

    plt.savefig(
        chart_path,
        dpi=150,
        bbox_inches="tight"
    )

    plt.close()
    context = {
        "total_users": total_users,
        "premium_users": sum(
            1 for p in profiles if p.get("is_premium")
        ),
        "active_skills": len(unique_skills),
        "skills_data": [
            {
                "name": skill,
                "users": skill_counts[skill],
            }
            for skill in unique_skills
        ],
        "recent_users": recent_users,
        "recent_payments": recent_payments,
        "revenue": revenue,
        "recent_users_chart": "/static/charts/recent_users_chart.png",
    }

    return render(
        request,
        "admin/admin-dashboard.html",
        context,
    )

from django.core.paginator import Paginator

def usermanagement(request):

  
    total_users = (
        supabase.table("app1_profile")
        .select("*", count="exact", head=True)
        .execute()
        .count or 0
    )
    profiles = (
        supabase.table("app1_profile")
        .select("id,full_name,email,is_premium")
        .execute()
        .data or []
    )
    auth_users = (
        supabase.table("auth_user")
        .select("email,is_active,date_joined")
        .execute()
        .data or []
    )
    premium_users = sum(
        1 for p in profiles
        if p.get("is_premium")
    )

    free_users = total_users - premium_users
    active_users = sum(
        1 for user in auth_users
        if user.get("is_active")
    )

    # Merge Profile + Auth Data
    users = []

    for profile in profiles:

        email = profile.get("email")

        auth_user = next(
            (
                u
                for u in auth_users
                if u.get("email") == email
            ),
            {}
        )

        users.append({
            "id": profile.get("id"),
            "full_name": profile.get("full_name"),
            "email": email,
            "is_premium": profile.get("is_premium"),
            "is_active": auth_user.get("is_active", False),
            "date_joined": auth_user.get("date_joined"),
        })

    # Search
    search = request.GET.get("search", "").strip()

    if search:
        users = [
            user
            for user in users
            if (
                search.lower() in (user.get("full_name") or "").lower()
                or search.lower() in (user.get("email") or "").lower()
            )
        ]

    # Pagination
    paginator = Paginator(users, 5)  # 10 users per page

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "total_users": total_users,
        "free_users": free_users,
        "premium_users": premium_users,
        "active_users": active_users,
        "users": page_obj,
        "page_obj": page_obj,
        "search": search,
    }

    return render(
        request,
        "admin/user-management.html",
        context
    )


def export_users_csv(request): 
    print("CSV Export Started")


    profiles = (
        supabase.table("app1_profile")
        .select("full_name,email,is_premium")
        .execute()
        .data or []
    )

    auth_users = (
        supabase.table("auth_user")
        .select("email,is_active,date_joined")
        .execute()
        .data or []
    )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="users.csv"'

    writer = csv.writer(response)

    writer.writerow([
        "Full Name",
        "Email",
        "Plan",
        "Status",
        "Date Joined"
    ])

    for profile in profiles:

        email = profile.get("email")

        auth_user = next(
            (u for u in auth_users if u.get("email") == email),
            {}
        )

        plan = "Premium" if profile.get("is_premium") else "Free"

        status = (
            "Active"
            if auth_user.get("is_active")
            else "Inactive"
        )

        writer.writerow([
            profile.get("full_name"),
            email,
            plan,
            status,
            auth_user.get("date_joined")
        ])

    return response
from django.core.paginator import Paginator
from datetime import datetime

def subscriptions(request):

    profiles = (
        supabase.table("app1_profile")
        .select("id,full_name,email,is_premium")
        .execute()
        .data or []
    )

    auth_users = (
        supabase.table("auth_user")
        .select("email,is_active,date_joined")
        .execute()
        .data or []
    )

    total_users = len(profiles)

    premium_users = sum(
        1 for p in profiles
        if p.get("is_premium")
    )

    free_users = total_users - premium_users

    active_users = sum(
        1 for u in auth_users
        if u.get("is_active")
    )

    current_month = datetime.now().month
    current_year = datetime.now().year

    new_users_this_month = 0

    subscriptions_list = []

    for profile in profiles:

        auth_user = next(
            (
                u for u in auth_users
                if u.get("email") == profile.get("email")
            ),
            {}
        )

        joined = auth_user.get("date_joined")

        if joined:
            try:
                joined_date = datetime.fromisoformat(
                    joined.replace("Z", "+00:00")
                )

                if (
                    joined_date.month == current_month
                    and joined_date.year == current_year
                ):
                    new_users_this_month += 1

            except:
                pass

        subscriptions_list.append({
              "id": profile.get("id"),
              "full_name": profile.get("full_name"),
              "email": profile.get("email"),
              "is_premium": profile.get("is_premium"),  # MUST BE HERE
              "plan": "Premium" if profile.get("is_premium") else "Free",
              "amount": 299 if profile.get("is_premium") else 0,
              "is_active": auth_user.get("is_active", False),
              "date_joined": auth_user.get("date_joined"),

        })

    subscriptions_list.sort(
        key=lambda x: x.get("date_joined") or "",
        reverse=True
    )

    # Pagination
    paginator = Paginator(subscriptions_list, 5)

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "total_users": total_users,
        "premium_users": premium_users,
        "free_users": free_users,
        "active_users": active_users,
        "new_users_this_month": new_users_this_month,
        "subscriptions": page_obj,
        "page_obj": page_obj,
    }

    return render(
        request,
        "admin/subscriptions.html",
        context
    )

from django.http import HttpResponse
from reportlab.pdfgen import canvas
from datetime import datetime

def download_receipt(request, user_id):

    profile = (
        supabase.table("app1_profile")
        .select("*")
        .eq("id", user_id)
        .single()
        .execute()
        .data
    )

    if not profile:
        return HttpResponse("User not found")

    response = HttpResponse(
        content_type="application/pdf"
    )

    response[
        "Content-Disposition"
    ] = f'attachment; filename="receipt_{user_id}.pdf"'

    p = canvas.Canvas(response)

    p.setFont("Helvetica-Bold", 18)
    p.drawString(200, 800, "Teach2Learn")

    p.setFont("Helvetica", 12)
    p.drawString(50, 750, "Payment Receipt")

    p.line(50, 740, 550, 740)

    p.drawString(
        50,
        700,
        f"User: {profile.get('full_name')}"
    )

    p.drawString(
        50,
        670,
        f"Email: {profile.get('email')}"
    )

    p.drawString(
        50,
        640,
        "Plan: Premium"
        if profile.get("is_premium")
        else "Plan: Free"
    )

    p.drawString(
        50,
        610,
        f"Amount: ₹{'299' if profile.get('is_premium') else '0'}"
    )

    p.drawString(
        50,
        580,
        f"Date: {datetime.now().strftime('%d-%m-%Y')}"
    )

    p.drawString(
        50,
        550,
        "Payment Status: Success"
    )

    p.line(50, 520, 550, 520)

    p.drawString(
        50,
        490,
        "Thank you for using Teach2Learn."
    )

    p.save()

    return response



from collections import Counter,OrderedDict

from django.shortcuts import render

from django.conf import settings
import matplotlib.pyplot as plt
import os


def analytics(request):
    profiles = (
        supabase.table("app1_profile")
        .select(
            "email,is_premium, premium_amount, teach_skills, learn_skills"
        )
        .execute()
        .data or []
    )

    auth_users = (
        supabase.table("auth_user")
        .select("email, date_joined")
        .execute()
        .data or []
    )


    user_join_dates = {}

    for user in auth_users:
        if user.get("email") and user.get("date_joined"):
            user_join_dates[user["email"]] = user["date_joined"]

    total_users = len(auth_users)

    premium_users = sum(
        1 for p in profiles
        if p.get("is_premium")
    )

    free_users = total_users - premium_users

    revenue = sum(
    p.get("premium_amount", 0)
    for p in profiles
    if p.get("is_premium")
)

    all_skills = []

    for profile in profiles:

        teach_skills = profile.get("teach_skills") or []
        learn_skills = profile.get("learn_skills") or []

        if isinstance(teach_skills, str):
            teach_skills = teach_skills.split(",")

        if isinstance(learn_skills, str):
            learn_skills = learn_skills.split(",")

        teach_skills = [
            skill.strip().lower()
            for skill in teach_skills
            if skill and skill.strip()
        ]

        learn_skills = [
            skill.strip().lower()
            for skill in learn_skills
            if skill and skill.strip()
        ]

        all_skills.extend(teach_skills)
       

    unique_skills = sorted(set(all_skills))

    skill_counts = Counter(all_skills)

   
    monthly_revenue = OrderedDict({
    "Jan": 0,
    "Feb": 0,
    "Mar": 0,
    "Apr": 0,
    "May": 0,
    "Jun": 0,
    "Jul": 0,
    "Aug": 0,
    "Sep": 0,
    "Oct": 0,
    "Nov": 0,
    "Dec": 0,
})

    for profile in profiles:

       if profile.get("is_premium"):

        email = profile.get("email")

        if email in user_join_dates:

            date = datetime.fromisoformat(
                user_join_dates[email].replace("Z", "+00:00")
            )
            month = date.strftime("%b")
            monthly_revenue[month] += (
                profile.get("premium_amount") or 299
            )

    subscription_counter = OrderedDict({
    "Jan": 0,
    "Feb": 0,
    "Mar": 0,
    "Apr": 0,
    "May": 0,
    "Jun": 0,
    "Jul": 0,
    "Aug": 0,
    "Sep": 0,
    "Oct": 0,
    "Nov": 0,
    "Dec": 0,
})

    for profile in profiles:

      if profile.get("is_premium"):

        email = profile.get("email")

        if email in user_join_dates:

            month = date.strftime("%b")

            subscription_counter[month] += 1
    charts_dir = os.path.join(
        settings.BASE_DIR,
        "static",
        "charts"
    )

    os.makedirs(charts_dir, exist_ok=True)
    revenue_chart = os.path.join(
    charts_dir,
    "revenue_chart.png"
)
    months = list(monthly_revenue.keys())
    revenues = list(monthly_revenue.values())

    plt.figure(figsize=(9, 5))

    plt.bar(
    months,
    revenues,
    color="#0d6efd"
)

    plt.title("Monthly Revenue")
    plt.xlabel("Month")
    plt.ylabel("Revenue (₹)")
    plt.grid(axis="y")

    plt.tight_layout()

    plt.savefig(revenue_chart)

    plt.close()
    skills_chart = os.path.join(charts_dir,"skills_chart.png")
    top_skills = skill_counts.most_common(10)

    skills = [skill for skill, count in top_skills]
    counts = [count for skill, count in top_skills]

    plt.figure(figsize=(8,5))

    plt.bar(
    skills,
    counts,
    color="#0d6efd")

    plt.xticks(rotation=30, ha="right")

    plt.title("Top 10 Popular Skills")
    plt.xlabel("Skills")
    plt.ylabel("Users")

    plt.tight_layout()

    plt.savefig(skills_chart)

    plt.close()
    pie_chart = os.path.join(charts_dir,"pie_chart.png")
    
    plt.figure(figsize=(6, 6))

    plt.pie(
        [free_users, premium_users],
        labels=["Free", "Premium"],
        autopct="%1.1f%%",
        colors=["#6c757d","#0d6efd"],
        startangle=90,
       
    )

    plt.title("Free vs Premium Users")

    plt.savefig(pie_chart)

    plt.close()
    subscription_chart = os.path.join(
    charts_dir,
    "subscription_chart.png"
)
    months = list(subscription_counter.keys())
    subscriptions = list(subscription_counter.values())

    plt.figure(figsize=(9, 5))

    plt.plot(
    months,
    subscriptions,
    marker="o",
    linewidth=3,
    color="#198754"
)

    plt.fill_between(
    months,
    subscriptions,
    alpha=0.3,
    color="#198754"
)

    plt.title("Monthly Premium Subscriptions")
    plt.xlabel("Month")
    plt.ylabel("Premium Users")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(subscription_chart)
    plt.close()
    context = {

        "total_users": total_users,

        "premium_users": premium_users,

        "free_users": free_users,

        "revenue": revenue,

        "active_skills": len(unique_skills),

        "skills_data": [
            {
                "name": skill,
                "users": skill_counts[skill]
            }
            for skill in unique_skills
        ],

        "revenue_chart": "/static/charts/revenue_chart.png",

        "skills_chart": "/static/charts/skills_chart.png",

        "pie_chart": "/static/charts/pie_chart.png",

        "subscription_chart": "/static/charts/subscription_chart.png",

    }

    return render(
        request,
        "admin/analytics.html",
        context
    )

def support(request):

    requests = (
        supabase.table("app1_contactmessage")
        .select("*")
        .execute()
        .data or []
    )


    total_requests = len(requests)

    open_issues = len([
        r for r in requests
        if r.get("status") == "Open"
    ])

    resolved_issues = len([
        r for r in requests
        if r.get("status") == "Resolved"
    ])

    messages_count = total_requests

    paginator = Paginator(requests, 5)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    context = {
        "total_requests": total_requests,
        "open_issues": open_issues,
        "resolved_issues": resolved_issues,
        "messages_count": messages_count,
        "requests": requests,
        "page_obj": page_obj,
    }

    return render(
        request,
        "admin/support-feedback.html",
        context
    )

from django.shortcuts import get_object_or_404, redirect

def update_request_status(request, request_id, status):

    support_request = get_object_or_404(
        ContactMessage,
        id=request_id
    )

    if status in ["Open", "In Progress", "Resolved"]:
        support_request.status = status
        support_request.save()

    return redirect("support")

from django.contrib.auth.decorators import login_required

def rating(request):
    return render(request,'user/rating.html')


@login_required
def rate_mentor(request, connection_id):

    email = request.user.email

    result = (
        supabase
        .table("connections")
        .select("*")
        .eq("id", connection_id)
        .maybe_single()
        .execute()
    )

    if not result.data:
        messages.error(request, "Connection not found.")
        return redirect("notifications")

    connection = result.data

    # Only learner can rate
    if connection["sender_email"] != email:
        messages.error(request, "Only the learner can rate the mentor.")
        return redirect("notifications")

    # Course must be completed
    if not connection.get("completed"):
        messages.error(request, "Complete the course before rating.")
        return redirect("notifications")

    # Prevent duplicate ratings
    if connection.get("rated"):
        messages.info(request, "You have already rated this mentor.")
        return redirect("notifications")

    if request.method == "POST":

        rating = request.POST.get("rating")
        review = request.POST.get("review", "").strip()

        if not rating:
            messages.error(request, "Please select a rating.")
            return render(
                request,
                "user/rating.html",
                {
                    "connection": connection
                }
            )

        rating = float(rating)

        if rating < 1 or rating > 5:
            messages.error(request, "Invalid rating.")
            return redirect("notifications")

        # Update rating in connections table
        (
            supabase
            .table("connections")
            .update({
                "rating": rating,
                "review": review,
                "rated": True
            })
            .eq("id", connection_id)
            .execute()
        )

        # Send notification to mentor
        create_notification(
            user_email=connection["receiver_email"],
            sender_email=connection["sender_email"],
            title="New Rating",
            message=f"{connection['sender_email']} rated you {rating} ⭐",
            notification_type="RATING",
            connection_id=connection_id,
            rating=rating,
            review=review,
        )
        messages.success(
            request,
            "Thank you for rating your mentor!"
        )

        return redirect("notifications")

    return render(
        request,
        "user/rating.html",
        {
            "connection": connection
        }
    )


def my_connections(request):
    return render(request,'user/my_connections.html')



from django.conf import settings
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from supabase import create_client

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

@login_required
def my_connections(request):
    email = request.user.email

    teaching = (
        supabase.table("connections")
        .select("*")
        .eq("mentor_email", email)
        .eq("completed", False)
        .order("created_at", desc=True)
        .execute()
        .data or []
    )

    learning = (
        supabase.table("connections")
        .select("*")
        .eq("learner_email", email)
        .eq("completed", False)
        .order("created_at", desc=True)
        .execute()
        .data or []
    )

    completed = (
        supabase.table("connections")
        .select("*")
        .or_(f"mentor_email.eq.{email},learner_email.eq.{email}")
        .eq("completed", True)
        .order("completed_at", desc=True)
        .execute()
        .data or []
    )

    def get_profile_by_email(other_email):
        if not other_email:
            return None

        profile = (
            supabase.table("app1_profile")
            .select("id, email, full_name, professional_title, location, bio, profile_image, learn_skills, teach_skills, education, experience, achievements")
            .eq("email", other_email)
            .maybe_single()
            .execute()
            .data
        )


        return profile

    def build_image_url(image_path):
      if not image_path:
         return None

      if image_path.startswith(("http://", "https://")):
        return image_path

      url = settings.MEDIA_URL + image_path.lstrip("/")
      return url

    def attach_profile_ids(rows, other_email_field):
        for row in rows:
            profile = get_profile_by_email(row.get(other_email_field))

            if profile:
                profile["profile_image_url"] = build_image_url(profile.get("profile_image"))

            row["other_profile"] = profile
            row["other_profile_id"] = profile.get("id") if profile and profile.get("id") else None

        return rows

    teaching = attach_profile_ids(teaching, "learner_email")
    learning = attach_profile_ids(learning, "mentor_email")
    completed = attach_profile_ids(completed, "mentor_email")

    return render(request, "user/my_connections.html", {
        "teaching_connections": teaching,
        "learning_connections": learning,
        "completed_connections": completed,
    })


from django.utils import timezone

def my_page(request):
    return render(request, "user/sessions.html", {})