from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.auth_utils import normalize_phone, PHONE_DIGITS_RE
from accounts.models import InstructorProfile, StudentProfile

User = get_user_model()

# قائمة بيانات المدرسين الـ 22 المطلوب تحديثهم
INSTRUCTORS_DATA = [
    ("عمار", "مرزوق", "0968394081"),
    ("ضياء الدين", "عريبي", "0958625490"),
    ("سامر", "محاحي", "0932863150"),
    ("خالد", "منيّر", "0949369915"),
    ("ملهم", "علي", "0955997204"),
    ("علاء", "رحال", "0952480990"),
    ("هلا", "همج", "0951517727"),
    ("عبد الوهاب", "كلاوي", "0950500602"),
    ("طارق", "الصعيدي", "0956464898"),
    ("مهند", "خياط", "0967760099"),
    ("عامر", "حداد", "0947338040"),
    ("إسراء", "عودة", "0995930809"),
    ("محمد", "السعدي", "0955135828"),
    ("محمد خير", "السعدي", "33739458"),  # سيتم توحيد الرقم تلقائياً إلى 0933739458
    ("علي", "بدوي", "0935262898"),
    ("الاء", "الدمشقي", "0991245743"),
    ("رامه", "مطر", "0944664645"),
    ("عمار", "سليمان", "0932894296"),
    ("عهد", "عمر", "0966549164"),
    ("رياض", "دالاتي", "0992714851"),
    ("اسامة", "حيدر", "0999141974"),
    ("نبيل", "القسطي", "0957206131"),
    ("قصي", "الجابي", "0988450918"),
]


def clean_arabic(text):
    """تنظيف وتوحيد الحروف العربية لمطابقة مرنة تتخطى أخطاء الإملاء الشائعة"""
    if not text:
        return ""
    text = text.strip()
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ة", "ه").replace("ى", "ي")
    return " ".join(text.split())


def find_existing_user(first_name, last_name, phone):
    """البحث الذكي عن مستخدم موجود مسبقاً في النظام بعدة طرق لتفادي التكرار"""
    # 1. البحث برقم الهاتف في ملف المدرس
    profile = InstructorProfile.objects.filter(phone=phone).select_related('user').first()
    if profile:
        return profile.user

    # 2. البحث برقم الهاتف في ملف الطالب (في حال رغبة ترقيته لمدرس)
    sp = StudentProfile.objects.filter(phone=phone).select_related('user').first()
    if sp:
        return sp.user

    # 3. البحث باسم المستخدم المطابق للهاتف
    user = User.objects.filter(username=phone).first()
    if user:
        return user

    # 4. البحث بالاسم الثنائي الدقيق
    user = User.objects.filter(first_name__iexact=first_name, last_name__iexact=last_name).first()
    if user:
        return user

    # 5. البحث بالاسم الثنائي المرن (يحتوي على)
    user = User.objects.filter(first_name__icontains=first_name, last_name__icontains=last_name).first()
    if user:
        return user

    # 6. البحث المرن بتجاهل الفروقات الإملائية العربية (مثل همزة القطع والوصل والتاء المربوطة)
    target_clean = clean_arabic(f"{first_name} {last_name}")
    for u in User.objects.all():
        u_full = u.get_full_name() or u.username
        if clean_arabic(u_full) == target_clean:
            return u

    return None


class Command(BaseCommand):
    help = "تحديث حسابات المدرسين الموجودة مسبقاً فقط وتعيين الهاتف ككلمة مرور (دون إنشاء حسابات جديدة)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("بدء فحص وتحديث حسابات المدرسين المتواجدة على المنصة..."))
        self.stdout.write(self.style.WARNING("(ملاحظة: لن يتم إنشاء أي حسابات جديدة مطلقاً)\n"))

        updated_count = 0
        not_found_count = 0

        for first_name, last_name, raw_phone in INSTRUCTORS_DATA:
            # تنسيق رقم الهاتف
            phone = raw_phone.strip()
            if len(phone) == 8 and phone.isdigit():
                phone = "09" + phone
            phone = normalize_phone(phone)

            if not PHONE_DIGITS_RE.fullmatch(phone):
                self.stderr.write(self.style.ERROR(f"خطأ: رقم الهاتف {raw_phone} للمدرس {first_name} {last_name} غير صالح!"))
                continue

            # البحث عن المستخدم الحالي
            user = find_existing_user(first_name, last_name, phone)

            if not user:
                # لم يتم العثور على الحساب
                self.stderr.write(
                    self.style.WARNING(
                        f"تنبيه: لم يتم العثور على حساب لـ [{first_name} {last_name}] (الهاتف: {phone}) - يرجى مراجعة إملاء الاسم إدارياً."
                    )
                )
                not_found_count += 1
                continue

            # تحديث بيانات الحساب الموجود
            user.is_staff = True
            user.username = phone  # تحديث اسم المستخدم إلى رقم الهاتف
            # تحديث الاسم فقط إذا كان فارغاً أو للتأكيد
            if not user.first_name:
                user.first_name = first_name
            if not user.last_name:
                user.last_name = last_name
            user.set_password(phone)
            user.save()

            # إنشاء أو تحديث ملف المدرس
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

            updated_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"تم تحديث الحساب بنجاح لـ: {user.get_full_name() or user.username} | اسم المستخدم: {user.username} | هاتف/كلمة مرور: {phone}"
                )
            )

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS(f"اكتمل التحديث بنجاح!"))
        self.stdout.write(self.style.SUCCESS(f"تم تحديث وترقية: {updated_count} حساب مدرس موجود."))
        if not_found_count > 0:
            self.stdout.write(self.style.WARNING(f"لم يتم العثور على: {not_found_count} حساب مدرس (يرجى مراجعة تنبيهات الأسماء أعلاه)."))
