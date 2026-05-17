from django.db.utils import OperationalError, ProgrammingError

from accounts.auth_utils import get_instructor_profile


def dashboard_user_role(request):
    """متغيرات آمنة للقوالب دون الوصول المباشر لـ user.instructor_profile."""
    if not request.user.is_authenticated:
        return {
            "user_has_instructor_profile": False,
            "user_is_platform_admin": False,
        }
    try:
        profile = get_instructor_profile(request.user)
        has_instructor = profile is not None
        return {
            "user_has_instructor_profile": has_instructor,
            "user_is_platform_admin": bool(request.user.is_staff and not has_instructor),
        }
    except (ProgrammingError, OperationalError, AttributeError):
        return {
            "user_has_instructor_profile": False,
            "user_is_platform_admin": bool(request.user.is_staff),
        }


def instructor_password_reminder(request):
    if not request.user.is_authenticated:
        return {}
    try:
        profile = get_instructor_profile(request.user)
        if not profile or profile.status != "active":
            return {}
        force_change = getattr(profile, "force_password_change", False)
        dismissed = request.session.get("instructor_password_modal_dismissed", False)
        return {
            "instructor_force_password_change": force_change,
            "show_instructor_password_modal": force_change and not dismissed,
            "show_instructor_password_banner": force_change,
        }
    except (ProgrammingError, OperationalError, AttributeError):
        return {}
