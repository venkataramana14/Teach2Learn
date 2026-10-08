from functools import wraps
from django.shortcuts import redirect
from .models import Profile

def premium_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login_view")

        profile, _ = Profile.objects.get_or_create(
            user=request.user,
            defaults={
                "full_name": request.user.get_full_name() or request.user.username,
                "email": request.user.email,
            }
        )

        if not profile.is_premium:
            return redirect("premium_page")

        return view_func(request, *args, **kwargs)
    return wrapper