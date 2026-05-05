import os
import django
import secrets
from django.utils import timezone
from datetime import timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from learning.models import Subject, Course, Unit, Lesson
from accounts.models import StudentProfile, InstructorProfile
from billing.models import Institute, SalesCenter, AccessCodeBatch, AccessCode
from billing.services import create_codes_for_batch

def seed_data():
    print("🚀 البدء بتوليد بيانات تجريبية...")

    # 1. Create Admin
    if not User.objects.filter(username="admin").exists():
        admin = User.objects.create_superuser("admin", "admin@mohtarifo.net", "admin12345")
        print("✅ تم إنشاء حساب الأدمن: admin / admin12345")
    
    # 2. Create Instructor
    instructor_user, created = User.objects.get_or_create(
        username="teacher_ali",
        defaults={"first_name": "علي", "last_name": "منصور", "email": "ali@teacher.net"}
    )
    if created:
        instructor_user.set_password("teacher12345")
        instructor_user.save()
        InstructorProfile.objects.create(user=instructor_user, specialty="الفيزياء والرياضيات", status="active")
        print("✅ تم إنشاء حساب المدرس: teacher_ali / teacher12345")

    # 3. Create Subjects
    math, _ = Subject.objects.get_or_create(name="الرياضيات", defaults={"slug": "math"})
    phys, _ = Subject.objects.get_or_create(name="الفيزياء", defaults={"slug": "physics"})

    # 4. Create Courses
    course_math, _ = Course.objects.get_or_create(
        slug="math-intensive-2026",
        defaults={
            "title": "مكثفة الرياضيات - الأستاذ علي منصور",
            "subject": math,
            "instructor": instructor_user,
            "kind": "intensive",
            "academic_track": "scientific",
            "status": "published",
            "price_cents": 5000000, # 50,000 SYP
        }
    )
    
    course_phys, _ = Course.objects.get_or_create(
        slug="physics-intensive-2026",
        defaults={
            "title": "مكثفة الفيزياء - طريقك للـ 400",
            "subject": phys,
            "instructor": instructor_user,
            "kind": "intensive",
            "academic_track": "scientific",
            "status": "published",
            "price_cents": 4500000,
        }
    )
    print("✅ تم إنشاء الدورات.")

    # 5. Create Units & Lessons
    for course in [course_math, course_phys]:
        unit, _ = Unit.objects.get_or_create(course=course, title="الوحدة الأولى: المفاهيم الأساسية", sort_order=1)
        for i in range(1, 4):
            Lesson.objects.get_or_create(
                unit=unit,
                title=f"الدرس {i}: مقدمة وشرح عملي",
                defaults={
                    "lesson_type": "video",
                    "sort_order": i,
                    "video_url": "https://vimeo.com/76979871"
                }
            )
    print("✅ تم إنشاء الوحدات والدروس.")

    # 6. Create Institute & Sales Center
    inst, _ = Institute.objects.get_or_create(name="معهد اليمان التعليمي", defaults={"contact_name": "أ. محمد", "phone": "0912345678"})
    center, _ = SalesCenter.objects.get_or_create(name="مكتبة الأمل", defaults={"address": "وسط المدينة", "phone": "0987654321"})
    print("✅ تم إنشاء المعهد ومركز البيع.")

    # 7. Create Batches & Codes
    batch_inst, _ = AccessCodeBatch.objects.get_or_create(
        name="دفعة طلاب المعهد - رياضيات",
        course=course_math,
        institute=inst,
        defaults={"code_prefix": "YMN"}
    )
    create_codes_for_batch(batch_inst, 5, free_codes=True)

    batch_center, _ = AccessCodeBatch.objects.get_or_create(
        name="بطاقات مكتبة الأمل - فيزياء",
        course=course_phys,
        sales_center=center,
        defaults={"code_prefix": "AML"}
    )
    create_codes_for_batch(batch_center, 10, free_codes=False)
    print("✅ تم توليد دفعات الأكواد.")

    print("\n✨ انتهت العملية بنجاح! يمكنك الآن تسجيل الدخول وتجربة الطباعة والبيانات.")

if __name__ == "__main__":
    seed_data()
