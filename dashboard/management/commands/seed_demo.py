from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import InstructorProfile, StudentProfile
from analytics.models import StudyPlan, StudyPlanItem, TopicPerformance
from billing.models import AccessCode, AccessGrant, Plan, Subscription
from exams.models import Attempt, Exam, ExamQuestion, Question, QuestionOption
from learning.models import Course, CourseProgress, Lesson, LessonAttendance, LessonProgress, OnlineLessonSession, Subject, Topic, Unit
from dashboard.models import StudentNotification


class Command(BaseCommand):
    help = "Create demo data for Mohtarifo Education dashboards."

    def handle(self, *args, **options):
        User = get_user_model()
        demo_video_url = "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4"

        admin, _ = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@example.com",
                "is_staff": True,
                "is_superuser": True,
                "first_name": "مدير",
                "last_name": "المنصة",
            },
        )
        admin.set_password("admin12345")
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()

        instructor, _ = User.objects.get_or_create(
            username="teacher",
            defaults={"email": "teacher@example.com", "first_name": "مدرس", "last_name": "الرياضيات", "is_staff": True},
        )
        instructor.set_password("teacher12345")
        instructor.is_staff = True
        instructor.save()
        InstructorProfile.objects.get_or_create(user=instructor, defaults={"specialty": "رياضيات", "status": "active"})

        student, _ = User.objects.get_or_create(
            username="student",
            defaults={"email": "student@example.com", "first_name": "طالب", "last_name": "تجريبي"},
        )
        student.set_password("student12345")
        student.save()
        StudentProfile.objects.get_or_create(user=student, defaults={"grade": "الثالث الثانوي", "track": "علمي", "xp": 7420, "level": 7})

        subject, _ = Subject.objects.get_or_create(name="رياضيات", slug="math")
        physics, _ = Subject.objects.get_or_create(name="فيزياء", slug="physics")
        chemistry, _ = Subject.objects.get_or_create(name="كيمياء", slug="chemistry")

        course, _ = Course.objects.get_or_create(
            slug="math-intensive-limits",
            defaults={
                "subject": subject,
                "instructor": instructor,
                "title": "مكثف التفاضل والنهايات",
                "description": "مكثف امتحاني مركز لطلاب المرحلة الثانوية.",
                "status": "published",
                "published_at": timezone.now(),
            },
        )
        physics_course, _ = Course.objects.get_or_create(
            slug="physics-electricity-exams",
            defaults={
                "subject": physics,
                "instructor": instructor,
                "title": "امتحانيات الكهرباء والمغناطيس",
                "description": "نماذج وتدريبات مؤقتة على الكهرباء والمغناطيس.",
                "status": "published",
                "published_at": timezone.now(),
            },
        )
        chemistry_course, _ = Course.objects.get_or_create(
            slug="chemistry-organic-review",
            defaults={
                "subject": chemistry,
                "instructor": instructor,
                "title": "مراجعة الكيمياء العضوية",
                "description": "مراجعة مركزة مع ملفات PDF وأسئلة صح وخطأ.",
                "status": "published",
                "published_at": timezone.now(),
            },
        )
        unit, _ = Unit.objects.get_or_create(course=course, title="النهايات", defaults={"sort_order": 1})
        lesson, _ = Lesson.objects.get_or_create(
            unit=unit,
            title="قوانين النهايات الأساسية",
            defaults={"lesson_type": "video", "video_url": demo_video_url, "duration_seconds": 1800, "sort_order": 1},
        )
        if lesson.video_url in {"", "https://vimeo.com/demo"}:
            lesson.video_url = demo_video_url
            lesson.save(update_fields=["video_url", "updated_at"])
        topic, _ = Topic.objects.get_or_create(subject=subject, course=course, unit=unit, lesson=lesson, name="النهايات المركبة", slug="complex-limits")

        extra_lessons = [
            ("الاشتقاق الأساسي", "derivatives-basic", "الاشتقاق", 2),
            ("تطبيقات الاشتقاق الامتحانية", "derivatives-apps", "تطبيقات الاشتقاق", 3),
            ("نماذج شاملة في التحليل", "analysis-final-models", "نماذج شاملة", 4),
        ]
        for title, slug, topic_name, order in extra_lessons:
            extra_lesson, _ = Lesson.objects.get_or_create(
                unit=unit,
                title=title,
                defaults={"lesson_type": "video", "video_url": demo_video_url, "duration_seconds": 1500 + order * 120, "sort_order": order},
            )
            if extra_lesson.video_url in {"", "https://vimeo.com/demo"}:
                extra_lesson.video_url = demo_video_url
                extra_lesson.save(update_fields=["video_url", "updated_at"])
            Topic.objects.get_or_create(subject=subject, course=course, unit=unit, lesson=extra_lesson, name=topic_name, slug=slug)

        physics_unit, _ = Unit.objects.get_or_create(course=physics_course, title="الكهرباء", defaults={"sort_order": 1})
        physics_session_titles = [
            "الجلسة 01 - مدخل إلى الكهرباء",
            "الجلسة 02 - التيار والمقاومة",
            "الجلسة 03 - قانون أوم",
            "الجلسة 04 - ربط المقاومات",
            "الجلسة 05 - القدرة والطاقة الكهربائية",
            "الجلسة 06 - مسائل وزارية على الكهرباء",
            "الجلسة 07 - المجال المغناطيسي",
            "الجلسة 08 - القوة المغناطيسية",
            "الجلسة 09 - الحث الكهرومغناطيسي",
            "الجلسة 10 - قانون فاراداي",
            "الجلسة 11 - التيار المتناوب",
            "الجلسة 12 - المحولات",
            "الجلسة 13 - مراجعة شاملة",
            "الجلسة 14 - نموذج امتحاني نهائي",
        ]
        for order, title in enumerate(physics_session_titles, start=1):
            recorded_lesson, _ = Lesson.objects.get_or_create(
                unit=physics_unit,
                title=title,
                defaults={
                    "lesson_type": "video",
                    "video_url": demo_video_url,
                    "duration_seconds": 2400,
                    "sort_order": order,
                    "description": "جلسة مسجلة من مكثفة الفيزياء، تظهر للطالب بعد تفعيل كود المكثفة.",
                },
            )
            if recorded_lesson.video_url in {"", "https://vimeo.com/demo"}:
                recorded_lesson.video_url = demo_video_url
                recorded_lesson.save(update_fields=["video_url", "updated_at"])
        physics_lesson = Lesson.objects.get(unit=physics_unit, title="الجلسة 02 - التيار والمقاومة")
        physics_topic, _ = Topic.objects.get_or_create(subject=physics, course=physics_course, unit=physics_unit, lesson=physics_lesson, name="قانون أوم", slug="ohms-law")

        chemistry_unit, _ = Unit.objects.get_or_create(course=chemistry_course, title="المركبات العضوية", defaults={"sort_order": 1})
        chemistry_lesson, _ = Lesson.objects.get_or_create(
            unit=chemistry_unit,
            title="تصنيف المركبات العضوية",
            defaults={"lesson_type": "pdf", "duration_seconds": 1200, "sort_order": 1},
        )
        chemistry_topic, _ = Topic.objects.get_or_create(subject=chemistry, course=chemistry_course, unit=chemistry_unit, lesson=chemistry_lesson, name="التصنيف العضوي", slug="organic-classification")

        question, _ = Question.objects.get_or_create(
            topic=topic,
            author=instructor,
            body="إذا كانت lim f(x)=3 و lim g(x)=2، فما قيمة lim [f(x)+g(x)]؟",
            defaults={"course": course, "unit": unit, "lesson": lesson, "difficulty": "easy", "status": "published", "explanation": "نستخدم قانون جمع النهايات."},
        )
        if not question.options.exists():
            QuestionOption.objects.bulk_create(
                [
                    QuestionOption(question=question, body="1", is_correct=False, sort_order=1),
                    QuestionOption(question=question, body="5", is_correct=True, sort_order=2),
                    QuestionOption(question=question, body="6", is_correct=False, sort_order=3),
                ]
            )

        sample_questions = [
            (physics_course, physics_unit, physics_lesson, physics_topic, "إذا زادت المقاومة مع ثبات الجهد، ماذا يحدث للتيار؟", "ينقص"),
            (chemistry_course, chemistry_unit, chemistry_lesson, chemistry_topic, "المركبات العضوية تحتوي غالبًا على عنصر الكربون.", "صح"),
        ]
        for sample_course, sample_unit, sample_lesson, sample_topic, body, correct in sample_questions:
            sample_question, _ = Question.objects.get_or_create(
                topic=sample_topic,
                author=instructor,
                body=body,
                defaults={
                    "course": sample_course,
                    "unit": sample_unit,
                    "lesson": sample_lesson,
                    "difficulty": "medium",
                    "status": "published",
                    "explanation": "سؤال تدريبي تجريبي.",
                    "question_type": "mcq",
                },
            )
            if not sample_question.options.exists():
                QuestionOption.objects.bulk_create(
                    [
                        QuestionOption(question=sample_question, body=correct, is_correct=True, sort_order=1),
                        QuestionOption(question=sample_question, body="خيار غير صحيح", is_correct=False, sort_order=2),
                    ]
                )

        exam, _ = Exam.objects.get_or_create(
            course=course,
            title="اختبار النهايات 1",
            defaults={"unit": unit, "lesson": lesson, "duration_minutes": 20, "question_count": 10, "status": "published"},
        )
        ExamQuestion.objects.get_or_create(exam=exam, question=question, defaults={"points": 1, "sort_order": 1})

        for sample_course, sample_unit, sample_lesson, sample_topic, body, _correct in sample_questions:
            sample_exam, _ = Exam.objects.get_or_create(
                course=sample_course,
                title=f"اختبار {sample_topic.name}",
                defaults={"unit": sample_unit, "lesson": sample_lesson, "duration_minutes": 15, "question_count": 8, "status": "published"},
            )
            sample_question = Question.objects.get(topic=sample_topic, body=body)
            ExamQuestion.objects.get_or_create(exam=sample_exam, question=sample_question, defaults={"points": 1, "sort_order": 1})

        Attempt.objects.get_or_create(
            user=student,
            exam=exam,
            defaults={
                "status": "submitted",
                "submitted_at": timezone.now(),
                "expires_at": timezone.now() + timedelta(minutes=20),
                "score": 8,
                "max_score": 10,
                "accuracy": 80,
                "total_time_seconds": 1100,
            },
        )
        CourseProgress.objects.get_or_create(user=student, course=course, defaults={"completion_percent": 64, "completed_lessons": 18, "total_lessons": 30})
        CourseProgress.objects.get_or_create(user=student, course=physics_course, defaults={"completion_percent": 38, "completed_lessons": 8, "total_lessons": 22})
        CourseProgress.objects.get_or_create(user=student, course=chemistry_course, defaults={"completion_percent": 21, "completed_lessons": 4, "total_lessons": 18})
        LessonProgress.objects.get_or_create(user=student, lesson=lesson, defaults={"watched_seconds": 1200, "last_position_seconds": 1200})
        TopicPerformance.objects.get_or_create(
            user=student,
            topic=topic,
            defaults={"attempts_count": 4, "correct_count": 9, "wrong_count": 7, "accuracy": 56.25, "avg_time_seconds": 82, "mastery_score": 48},
        )
        TopicPerformance.objects.get_or_create(
            user=student,
            topic=physics_topic,
            defaults={"attempts_count": 3, "correct_count": 7, "wrong_count": 5, "accuracy": 58.33, "avg_time_seconds": 76, "mastery_score": 52},
        )
        TopicPerformance.objects.get_or_create(
            user=student,
            topic=chemistry_topic,
            defaults={"attempts_count": 2, "correct_count": 8, "wrong_count": 2, "accuracy": 80, "avg_time_seconds": 49, "mastery_score": 74},
        )

        plan, _ = Plan.objects.get_or_create(code="monthly", defaults={"name": "اشتراك شهري", "billing_period": "monthly", "price_cents": 1500})
        Subscription.objects.get_or_create(user=student, plan=plan, defaults={"provider": "stripe", "status": "active", "starts_at": timezone.now()})

        access_code, _ = AccessCode.objects.get_or_create(
            code="MATH-2026-DEMO",
            defaults={
                "access_type": "course",
                "course": course,
                "max_redemptions": 50,
                "valid_until": timezone.now() + timedelta(days=90),
                "notes": "Demo access code for the math intensive course.",
            },
        )
        AccessGrant.objects.get_or_create(
            user=student,
            course=course,
            access_code=access_code,
            defaults={"source": "code", "starts_at": timezone.now(), "expires_at": access_code.valid_until},
        )
        AccessCode.objects.get_or_create(
            code="PHYS-2026-DEMO",
            defaults={
                "access_type": "course",
                "course": physics_course,
                "max_redemptions": 50,
                "valid_until": timezone.now() + timedelta(days=90),
                "notes": "Demo access code for the physics exam course.",
            },
        )
        AccessCode.objects.get_or_create(
            code="CHEM-2026-DEMO",
            defaults={
                "access_type": "course",
                "course": chemistry_course,
                "max_redemptions": 50,
                "valid_until": timezone.now() + timedelta(days=90),
                "notes": "Demo access code for the chemistry review course.",
            },
        )

        session, _ = OnlineLessonSession.objects.get_or_create(
            lesson=lesson,
            title="جلسة مباشرة: مراجعة قوانين النهايات",
            defaults={
                "starts_at": timezone.now() + timedelta(days=1),
                "ends_at": timezone.now() + timedelta(days=1, hours=1),
                "meeting_url": "https://meet.example.com/math-limits",
                "status": "scheduled",
                "capacity": 100,
            },
        )
        LessonAttendance.objects.get_or_create(user=student, session=session, defaults={"status": "registered"})
        for live_lesson, live_title, offset in [
            (physics_lesson, "جلسة مباشرة: مسائل قانون أوم", 2),
            (chemistry_lesson, "جلسة مباشرة: مراجعة المركبات العضوية", 3),
        ]:
            live_session, _ = OnlineLessonSession.objects.get_or_create(
                lesson=live_lesson,
                title=live_title,
                defaults={
                    "starts_at": timezone.now() + timedelta(days=offset),
                    "ends_at": timezone.now() + timedelta(days=offset, hours=1),
                    "meeting_url": f"https://meet.example.com/session-{offset}",
                    "status": "scheduled",
                    "capacity": 100,
                },
            )
            LessonAttendance.objects.get_or_create(user=student, session=live_session, defaults={"status": "registered"})

        study_plan, _ = StudyPlan.objects.get_or_create(
            user=student,
            title="خطة النهايات المركبة",
            defaults={"starts_at": timezone.now().date(), "ends_at": (timezone.now() + timedelta(days=7)).date()},
        )
        StudyPlanItem.objects.get_or_create(
            study_plan=study_plan,
            title="راجع قوانين النهايات ثم حل 15 سؤالًا",
            defaults={"item_type": "lesson", "lesson": lesson, "topic": topic, "due_date": timezone.now().date(), "estimated_minutes": 35},
        )
        StudentNotification.objects.get_or_create(
            user=student,
            title="أهلًا بك في محترفو التعليم",
            defaults={
                "notification_type": "system",
                "body": "تم تجهيز حسابك التجريبي وموادك الأولى.",
                "url": "/student/",
            },
        )
        StudentNotification.objects.get_or_create(
            user=student,
            title="جلسة مباشرة قادمة",
            defaults={
                "notification_type": "attendance",
                "body": "لديك جلسة مباشرة في مادة الرياضيات.",
                "url": f"/student/lessons/{lesson.id}/",
            },
        )

        self.stdout.write(self.style.SUCCESS("Demo data created. Admin login: admin / admin12345. Demo code: MATH-2026-DEMO"))
