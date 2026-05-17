"""مساعدات تسجيل الدخول وإنشاء حسابات المدرسين."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.utils.text import slugify

from .models import InstructorProfile, StudentProfile

User = get_user_model()


def normalize_phone(phone: str) -> str:
    return "".join(ch for ch in (phone or "").strip() if ch.isdigit() or ch == "+")


def build_instructor_username(*, first_name: str, last_name: str, login_username_type: str, national_id: str = "") -> str:
    """يُنشئ اسم مستخدم فريد من الاسم أو رقم الهوية."""
    if login_username_type == "national_id":
        base = national_id.strip()
    else:
        full = f"{first_name.strip()} {last_name.strip()}".strip()
        base = slugify(full, allow_unicode=True) or slugify(f"{first_name}-{last_name}", allow_unicode=False)
    if not base:
        raise ValueError("تعذر إنشاء اسم مستخدم.")
    username = base
    counter = 2
    while User.objects.filter(username=username).exists():
        username = f"{base}-{counter}"
        counter += 1
    return username


def resolve_user_for_login(raw_identifier: str):
    """يحوّل المدخل (اسم مستخدم، هاتف، هوية، اسم كامل...) إلى مستخدم."""
    raw = (raw_identifier or "").strip()
    if not raw:
        return None

    user = User.objects.filter(username=raw).first()
    if user:
        return user

    instructor = (
        InstructorProfile.objects.filter(phone=raw)
        .select_related("user")
        .first()
    )
    if instructor:
        return instructor.user

    instructor = (
        InstructorProfile.objects.filter(national_id=raw)
        .select_related("user")
        .first()
    )
    if instructor:
        return instructor.user

    sp = StudentProfile.objects.filter(phone=raw).select_related("user").first()
    if sp:
        return sp.user

    user = User.objects.filter(email=raw).first()
    if user:
        return user

    parts = raw.split()
    if len(parts) >= 2:
        first_name = parts[0]
        last_name = " ".join(parts[1:])
        user = User.objects.filter(
            instructor_profile__isnull=False,
            first_name__iexact=first_name,
            last_name__iexact=last_name,
        ).first()
        if user:
            return user

    return None


def get_instructor_login_phone(user) -> str:
    """رقم الهاتف المستخدم لإرسال OTP للمدرس."""
    profile = getattr(user, "instructor_profile", None)
    if profile and profile.phone:
        return profile.phone
    if hasattr(user, "student_profile") and user.student_profile.phone:
        return user.student_profile.phone
    return user.username
