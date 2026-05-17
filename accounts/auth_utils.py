"""مساعدات تسجيل الدخول وإنشاء حسابات المدرسين."""
from __future__ import annotations

import re

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import ProgrammingError, OperationalError
from django.utils.text import slugify

from .models import InstructorProfile, StudentProfile

User = get_user_model()
PHONE_DIGITS_RE = re.compile(r"^09\d{8}$")


def get_instructor_profile(user):
    """يُرجع ملف المدرس أو None دون رفع استثناء."""
    if not user or not getattr(user, "pk", None):
        return None
    try:
        return user.instructor_profile
    except ObjectDoesNotExist:
        return None
    except InstructorProfile.DoesNotExist:
        return None


def normalize_phone(phone: str) -> str:
    """تنسيق موحّد لأرقام سورية: 09xxxxxxxx"""
    return re.sub(r"\D", "", (phone or "").strip())


def phone_lookup_variants(raw: str) -> set[str]:
    norm = normalize_phone(raw)
    variants = {v for v in {(raw or "").strip(), norm} if v}
    if norm.startswith("0") and len(norm) > 1:
        variants.add(norm.lstrip("0"))
    if norm and not norm.startswith("963"):
        variants.add(f"963{norm.lstrip('0')}")
    return variants


def build_instructor_username(*, first_name: str, last_name: str) -> str:
    """اسم مستخدم داخلي من الاسم الأول والكنية."""
    full = f"{first_name.strip()} {last_name.strip()}".strip()
    base = slugify(full, allow_unicode=True) or slugify(f"{first_name}-{last_name}", allow_unicode=False)
    if not base:
        raise ValueError("تعذر إنشاء اسم مستخدم من الاسم.")
    username = base
    counter = 2
    while User.objects.filter(username=username).exists():
        username = f"{base}-{counter}"
        counter += 1
    return username


def _find_instructor_by_phone(raw: str):
    variants = phone_lookup_variants(raw)
    if not variants:
        return None

    try:
        profile = (
            InstructorProfile.objects.filter(phone__in=variants)
            .select_related("user")
            .first()
        )
        if profile:
            return profile.user
    except (ProgrammingError, OperationalError):
        pass

    user = (
        User.objects.filter(instructor_profile__isnull=False, username__in=variants)
        .first()
    )
    if user:
        return user

    norm = normalize_phone(raw)
    if not norm:
        return None

    try:
        for profile in InstructorProfile.objects.select_related("user").exclude(phone=""):
            if normalize_phone(profile.phone) == norm:
                return profile.user
    except (ProgrammingError, OperationalError):
        pass

    for user in User.objects.filter(instructor_profile__isnull=False).only("id", "username"):
        if normalize_phone(user.username) == norm:
            return user

    return None


def _find_instructor_by_name(raw: str):
    compact = " ".join((raw or "").split())
    if not compact:
        return None

    parts = compact.split()
    if len(parts) >= 2:
        last = " ".join(parts[1:])
        user = User.objects.filter(
            instructor_profile__isnull=False,
            first_name__iexact=parts[0],
            last_name__iexact=last,
        ).first()
        if user:
            return user
        user = User.objects.filter(
            instructor_profile__isnull=False,
            first_name__icontains=parts[0],
            last_name__icontains=last,
        ).first()
        if user:
            return user

    slug = slugify(compact, allow_unicode=True)
    if slug:
        user = User.objects.filter(
            instructor_profile__isnull=False,
            username__iexact=slug,
        ).first()
        if user:
            return user

    users = User.objects.filter(instructor_profile__isnull=False).only(
        "id", "username", "first_name", "last_name"
    )
    lower = compact.casefold()
    for user in users:
        full = (user.get_full_name() or "").strip()
        if full and full.casefold() == lower:
            return user

    return None


def is_instructor_account(user) -> bool:
    if not user or not user.is_active:
        return False
    if get_instructor_profile(user):
        return True
    return bool(user.is_staff and PHONE_DIGITS_RE.fullmatch(normalize_phone(user.username)))


def resolve_user_for_login(raw_identifier: str):
    """
    يحوّل مدخل تسجيل الدخول إلى مستخدم.
    للمدرس: الاسم الكامل، اسم المستخدم، أو رقم الهاتف.
    """
    raw = (raw_identifier or "").strip()
    if not raw:
        return None

    norm = normalize_phone(raw)
    is_phone = bool(norm and PHONE_DIGITS_RE.fullmatch(norm))

    # أرقام الهاتف: المدرس أولاً (تجنب التباس مع حساب طالب بنفس الرقم)
    if is_phone:
        user = _find_instructor_by_phone(raw)
        if user:
            return user

    user = _find_instructor_by_name(raw)
    if user:
        return user

    user = User.objects.filter(username__iexact=raw).first()
    if user:
        return user

    if not is_phone:
        user = _find_instructor_by_phone(raw)
        if user:
            return user

    sp = StudentProfile.objects.filter(phone=raw).select_related("user").first()
    if not sp and norm:
        sp = StudentProfile.objects.filter(phone=norm).select_related("user").first()
    if sp:
        return sp.user

    if is_phone:
        return User.objects.filter(username__iexact=norm).first()

    return User.objects.filter(email__iexact=raw).first()


def instructor_password_candidates(user) -> list[str]:
    """قيم محتملة لكلمة مرور المدرس (هاتف الملف، اسم المستخدم إن كان رقماً...)."""
    candidates: list[str] = []
    profile = get_instructor_profile(user)
    if profile and profile.phone:
        candidates.append(normalize_phone(profile.phone))
    username_digits = normalize_phone(user.username)
    if PHONE_DIGITS_RE.fullmatch(username_digits):
        candidates.append(username_digits)
    return [c for c in candidates if c]


def _password_attempts(password: str, user) -> list[str]:
    raw = (password or "").strip()
    attempts: list[str] = []
    if raw:
        attempts.append(raw)
    digits = normalize_phone(raw)
    if digits and digits not in attempts:
        attempts.append(digits)
    for candidate in instructor_password_candidates(user):
        if candidate not in attempts:
            attempts.append(candidate)
    return attempts


def verify_instructor_password(user, password: str) -> bool:
    """يتحقق من كلمة مرور المدرس (الهاتف أو اسم المستخدم القديم كرقم)."""
    if not is_instructor_account(user):
        return False

    for attempt in _password_attempts(password, user):
        if user.check_password(attempt):
            return True
    return False


def normalize_login_password(user, password: str) -> str:
    """للمدرس: إذا أدخل رقماً ككلمة مرور نُوحّد التنسيق."""
    if get_instructor_profile(user):
        digits = normalize_phone(password)
        if digits and PHONE_DIGITS_RE.fullmatch(digits):
            return digits
    return password


def get_instructor_login_phone(user) -> str:
    """رقم الهاتف لإرسال OTP."""
    profile = get_instructor_profile(user)
    if profile and profile.phone:
        return profile.phone
    try:
        if user.student_profile.phone:
            return user.student_profile.phone
    except ObjectDoesNotExist:
        pass
    if PHONE_DIGITS_RE.fullmatch(normalize_phone(user.username)):
        return normalize_phone(user.username)
    return user.username
