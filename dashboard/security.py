import re

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.html import strip_tags


PHONE_RE = re.compile(r"^09\d{8}$")
SUSPICIOUS_INPUT_RE = re.compile(
    r"(<\s*/?\s*script\b|javascript\s*:|data\s*:\s*text/html|on\w+\s*=|"
    r"<\s*iframe\b|<\s*object\b|<\s*embed\b|<\s*svg\b|<\s*link\b|"
    r"<\s*meta\b|document\.cookie|localStorage|sessionStorage)",
    re.IGNORECASE,
)
SEQUENTIAL_PHONES = {"0912345678", "0987654321"}
REPEATED_FAKE_PHONES = {f"09{digit * 8}" for digit in "0123456789"}


def normalize_phone(value):
    return re.sub(r"\D", "", value or "")


def validate_syrian_mobile(value, *, user=None):
    phone = normalize_phone(value)
    if not PHONE_RE.fullmatch(phone):
        raise ValidationError("رقم الهاتف يجب أن يكون 10 خانات ويبدأ بـ 09.")
    if phone in REPEATED_FAKE_PHONES or phone in SEQUENTIAL_PHONES:
        raise ValidationError("رقم الهاتف غير مقبول. يرجى إدخال رقم حقيقي.")
    query = User.objects.filter(username=phone)
    if user is not None and user.pk:
        query = query.exclude(pk=user.pk)
    if query.exists():
        raise ValidationError("رقم الهاتف مستخدم مسبقاً.")
    return phone


def sanitize_plain_text(value, max_length=None):
    cleaned = strip_tags(value or "").strip()
    if has_suspicious_input(cleaned):
        raise ValidationError("المدخلات تحتوي على كود غير مسموح.")
    if max_length:
        cleaned = cleaned[:max_length]
    return cleaned


def has_suspicious_input(value):
    return bool(value and SUSPICIOUS_INPUT_RE.search(str(value)))
