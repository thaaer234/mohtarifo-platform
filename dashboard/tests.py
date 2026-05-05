from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import InstructorProfile
from billing.models import AccessGrant
from learning.models import Course, Lesson, LessonProgress, OnlineLessonSession, Subject, Unit


class StudentAccessSecurityTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.instructor = user_model.objects.create_user(username="teacher", password="teacher12345")
        self.student = user_model.objects.create_user(username="student", password="student12345")
        subject = Subject.objects.create(name="Math", slug="math")
        self.course = Course.objects.create(
            subject=subject,
            instructor=self.instructor,
            title="Limits",
            slug="limits",
            description="Course",
            status="published",
        )
        unit = Unit.objects.create(course=self.course, title="Unit 1", sort_order=1)
        self.lesson = Lesson.objects.create(unit=unit, title="Lesson 1", sort_order=1)

    def test_save_lesson_progress_requires_active_access(self):
        self.client.force_login(self.student)
        response = self.client.post(
            reverse("dashboard:save_lesson_progress", args=[self.lesson.id]),
            {"current_time": "12"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(LessonProgress.objects.filter(user=self.student, lesson=self.lesson).exists())

    def test_save_lesson_progress_accepts_active_grant(self):
        AccessGrant.objects.create(user=self.student, course=self.course, source="admin")
        self.client.force_login(self.student)
        response = self.client.post(
            reverse("dashboard:save_lesson_progress", args=[self.lesson.id]),
            {"current_time": "12"},
        )
        self.assertEqual(response.status_code, 200)
        progress = LessonProgress.objects.get(user=self.student, lesson=self.lesson)
        self.assertEqual(progress.last_position_seconds, 12)

    def test_expired_grant_does_not_allow_lesson_access(self):
        AccessGrant.objects.create(
            user=self.student,
            course=self.course,
            source="admin",
            expires_at=timezone.now() - timedelta(days=1),
        )
        self.client.force_login(self.student)
        response = self.client.get(reverse("dashboard:student_lesson_detail", args=[self.lesson.id]))
        self.assertEqual(response.status_code, 404)

    def test_join_session_requires_device_scoped_access(self):
        session = OnlineLessonSession.objects.create(
            lesson=self.lesson,
            title="Live lesson",
            starts_at=timezone.now(),
            ends_at=timezone.now() + timedelta(hours=1),
        )
        AccessGrant.objects.create(user=self.student, course=self.course, source="admin", device_fingerprint="other-device")
        self.client.force_login(self.student)
        response = self.client.get(reverse("dashboard:join_session", args=[session.id]))
        self.assertEqual(response.status_code, 302)

    def test_device_logged_out_page_is_public(self):
        response = self.client.get(reverse("dashboard:device_logged_out"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "تم تسجيل خروجك")


class DashboardRoleSecurityTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_superuser(username="admin", password="admin12345")
        self.instructor = user_model.objects.create_user(username="teacher", password="teacher12345", is_staff=True)
        InstructorProfile.objects.create(user=self.instructor, specialty="Math", status="active")
        self.student = user_model.objects.create_user(username="student", password="student12345")

    def test_instructor_cannot_open_admin_dashboard(self):
        self.client.force_login(self.instructor)
        response = self.client.get(reverse("dashboard:admin_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_active_instructor_can_open_instructor_dashboard(self):
        self.client.force_login(self.instructor)
        response = self.client.get(reverse("dashboard:instructor_dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_student_cannot_open_instructor_dashboard(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("dashboard:instructor_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_admin_backup_export_disabled_by_default(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard:admin_system_backup"))
        self.assertEqual(response.status_code, 404)


class LoginRateLimitTests(TestCase):
    @override_settings(LOGIN_RATE_LIMIT_ATTEMPTS=1)
    def test_template_login_rate_limits_repeated_failures(self):
        url = reverse("dashboard:login")
        response = self.client.post(url, {"username": "student", "password": "wrong"})
        self.assertEqual(response.status_code, 200)

        response = self.client.post(url, {"username": "student", "password": "wrong"})
        self.assertEqual(response.status_code, 429)

# Create your tests here.
