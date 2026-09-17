from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import InstructorProfile
from billing.models import AccessGrant
from learning.models import Course, Lesson, LessonProgress, OnlineLessonSession, Subject, Unit
from dashboard.models import NotebookOrder, NotebookProduct


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


@override_settings(MIDDLEWARE=[middleware for middleware in settings.MIDDLEWARE if middleware != "billing.middleware.ActiveDeviceMiddleware"])
class NotebookStoreTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.instructor = user_model.objects.create_user(username="note-teacher", password="teacher12345")
        InstructorProfile.objects.create(user=self.instructor, specialty="Physics", status="active")
        self.student = user_model.objects.create_user(username="0991239876", first_name="Student", password="student12345")
        self.other_student = user_model.objects.create_user(username="0987654321", password="student12345")
        self.product = NotebookProduct.objects.create(
            instructor=self.instructor,
            title="Physics Notebook",
            price_syp=50000,
            pages_count=180,
            stock=3,
        )

    def order_data(self, **overrides):
        data = {
            "recipient_name": "Student Name",
            "phone": "0991239876",
            "governorate": "Damascus",
            "address": "Street 1, near the school",
            "location_latitude": "33.513800",
            "location_longitude": "36.276500",
            "quantity": "2",
            "payment_method": "cod",
            "payment_reference": "",
        }
        data.update(overrides)
        return data

    def test_order_requires_login(self):
        response = self.client.get(reverse("dashboard:notebook_order", args=[self.product.id]))
        self.assertRedirects(
            response,
            f"{reverse('dashboard:login')}?next={reverse('dashboard:notebook_order', args=[self.product.id])}",
        )

    def test_order_saves_exact_location_and_reduces_stock(self):
        self.client.force_login(self.student)
        response = self.client.post(reverse("dashboard:notebook_order", args=[self.product.id]), self.order_data())
        self.assertRedirects(response, reverse("dashboard:notebook_orders"))
        order = NotebookOrder.objects.get(student=self.student)
        self.assertEqual(str(order.location_latitude), "33.513800")
        self.assertEqual(order.unit_price_syp, 50000)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)

    def test_order_without_location_is_rejected(self):
        self.client.force_login(self.student)
        response = self.client.post(
            reverse("dashboard:notebook_order", args=[self.product.id]),
            self.order_data(location_latitude="", location_longitude=""),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(NotebookOrder.objects.exists())

    def test_student_only_sees_own_orders(self):
        NotebookOrder.objects.create(
            product=self.product,
            student=self.other_student,
            recipient_name="Other",
            phone="0988888888",
            governorate="Damascus",
            address="Other address",
            location_latitude="33.500000",
            location_longitude="36.200000",
            unit_price_syp=50000,
        )
        self.client.force_login(self.student)
        response = self.client.get(reverse("dashboard:notebook_orders"))
        self.assertNotContains(response, "Other address")

    def test_student_cannot_open_notebook_admin(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("dashboard:admin_notebooks"))
        self.assertEqual(response.status_code, 403)

# Create your tests here.
