import re
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.auth_utils import build_instructor_username, normalize_phone, PHONE_DIGITS_RE
from accounts.models import InstructorProfile

User = get_user_model()

# قائمة بيانات المدرسين المطلوبة
INSTRUCTORS_DATA = [
    ("عمار", "مرزوق", "0968394081"),
    ("ضياء الدين", "عريبي", "0958625490"),
    ("سامر", "محاحي", "0932863150"),
    ("خالد", "منير", "0949369915"),
    ("ملهم", "علي", "0955997204"),
    ("علاء", "رحال", "0952480990"),
    ("هلا", "همج", "0951517727"),
    ("عبد الوهاب", "كلاوي", "0950500602"),
    ("طارق", "الصعيدي", "0956464898"),
    ("مهند", "خياط", "0967760099"),
    ("عامر", "حداد", "0947338040"),
    ("إسراء", "عودة", "0995930809"),
    ("محمد", "السعدي", "0955135828"),
    ("مححمد خير", "السعدي", "33739458"),  # سيتم توحيد الرقم تلقائياً إلى 0933739458
    ("علي", "بدوي", "0935262898"),
    ("الاء", "الدمشقي", "0991245743"),
    ("رامه", "مطر", "0944664645"),
    ("عمار", "سليمان", "0932894296"),
    ("عهد", "عمر", "0966549164"),
    ("رياض", "دالاتي", "0992714851"),
    ("اسامة", "حيدر", "0999141974"),
    ("نبيل", "القسطي", "0957206131"),
]


class Command(BaseCommand):
    help = "إنشاء وتحديث حسابات المدرسين دفعة واحدة وتعيين كلمة المرور ورقم الهاتف ومزامنتها"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("بدء معالجة وإنشاء حسابات المدرسين..."))
        success_count = 0

        for first_name, last_name, raw_phone in INSTRUCTORS_DATA:
            # توحيد وتنسيق رقم الهاتف السوري
            phone = raw_phone.strip()
            if len(phone) == 8 and phone.isdigit():
                phone = "09" + phone  # إصلاح الرقم الناقص البداية تلقائياً
            phone = normalize_phone(phone)

            if not PHONE_DIGITS_RE.fullmatch(phone):
                self.stderr.write(self.style.ERROR(f"خطأ: رقم الهاتف {raw_phone} للمدرس {first_name} {last_name} غير صالح!"))
                continue

            # 1. البحث عن الحساب لتفادي التكرار
            profile = InstructorProfile.objects.filter(phone=phone).select_related('user').first()
            if profile:
                user = profile.user
                self.stdout.write(f"تحديث مدرس موجود برقم الهاتف {phone}: {user.get_full_name()}")
            else:
                # البحث باسم مستخدم الهاتف
                user = User.objects.filter(username=phone).first()
                if not user:
                    # بناء اسم مستخدم فريد ومناسب باللغة الإنجليزية
                    username = build_instructor_username(first_name=first_name, last_name=last_name)
                    # فحص وجود اسم المستخدم مسبقاً
                    user = User.objects.filter(username=username).first()
                    if not user:
                        # إنشاء المستخدم الجديد
                        user = User.objects.create_user(
                            username=username,
                            password=phone,
                            is_staff=True,
                            first_name=first_name,
                            last_name=last_name
                        )
                        self.stdout.write(self.style.SUCCESS(f"تم إنشاء حساب جديد: {username} ({first_name} {last_name})"))
                    else:
                        self.stdout.write(f"تحديث حساب مدرس موجود باسم المستخدم: {username}")
                else:
                    self.stdout.write(f"تحديث حساب مدرس موجود برقم الهاتف كاسم مستخدم: {phone}")

            # 2. تحديث الحساب وضبط كلمة المرور والصلاحيات
            user.is_staff = True
            user.first_name = first_name
            user.last_name = last_name
            user.set_password(phone)
            user.save()

            # 3. إنشاء أو تحديث ملف المدرس Profile
            profile, created = InstructorProfile.objects.get_or_create(
                user=user,
                defaults={
                    "phone": phone,
                    "specialty": "مدرس",
                    "status": "active",
                    "force_password_change": True
                }
            )
            if not created:
                profile.phone = phone
                profile.force_password_change = True
                profile.status = "active"
                profile.save()

            success_count += 1
            self.stdout.write(self.style.SUCCESS(f"تم ضبط المدرس: {first_name} {last_name} | رقم الهاتف: {phone}"))

        self.stdout.write(self.style.SUCCESS(f"\nاكتملت العملية بنجاح! تم تجهيز {success_count} مدرسين."))
