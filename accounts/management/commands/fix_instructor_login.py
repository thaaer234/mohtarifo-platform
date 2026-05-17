"""مزامنة هاتف المدرس وكلمة المرور: python manage.py fix_instructor_login 0987654321 0984011372"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.auth_utils import PHONE_DIGITS_RE, normalize_phone
from accounts.models import InstructorProfile

User = get_user_model()


class Command(BaseCommand):
    help = "يحدّث هاتف المدرس ويجعل كلمة المرور = رقم الهاتف"

    def add_arguments(self, parser):
        parser.add_argument("username", help="اسم المستخدم الحالي للمدرس")
        parser.add_argument("phone", help="رقم الهاتف 09xxxxxxxx")

    def handle(self, *args, **options):
        username = options["username"].strip()
        phone = normalize_phone(options["phone"])
        if not PHONE_DIGITS_RE.fullmatch(phone):
            self.stderr.write(self.style.ERROR("رقم الهاتف غير صالح (09xxxxxxxx)."))
            return

        user = User.objects.filter(username=username).first()
        if not user:
            from accounts.auth_utils import resolve_user_for_login
            user = resolve_user_for_login(username)
            
        if not user:
            self.stderr.write(self.style.ERROR(f"لم يُعثر على مستخدم بـ: {username}"))
            return

        profile, _ = InstructorProfile.objects.get_or_create(
            user=user,
            defaults={"specialty": "مدرس", "status": "active"},
        )
        conflict = InstructorProfile.objects.filter(phone=phone).exclude(user_id=user.id).first()
        if conflict:
            self.stderr.write(
                self.style.ERROR(
                    f"الهاتف مستخدم من: {conflict.user.get_full_name() or conflict.user.username}"
                )
            )
            return

        profile.phone = phone
        profile.force_password_change = True
        profile.save()
        user.set_password(phone)
        user.is_staff = True
        user.save(update_fields=["password", "is_staff"])

        self.stdout.write(
            self.style.SUCCESS(
                f"تم التحديث: {user.get_full_name() or user.username} — الدخول بالاسم أو {phone} وكلمة المرور {phone}"
            )
        )
