def instructor_password_reminder(request):
    if not request.user.is_authenticated:
        return {}
    profile = getattr(request.user, "instructor_profile", None)
    if not profile or profile.status != "active":
        return {}
    dismissed = request.session.get("instructor_password_modal_dismissed", False)
    return {
        "instructor_force_password_change": profile.force_password_change,
        "show_instructor_password_modal": profile.force_password_change and not dismissed,
        "show_instructor_password_banner": profile.force_password_change,
    }
