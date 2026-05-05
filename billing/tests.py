from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from learning.models import Course, Subject

from .models import AccessCode, AccessGrant


class AccessApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="student", password="student12345")
        self.instructor = get_user_model().objects.create_user(username="teacher", password="teacher12345")

    def test_my_access_endpoint_requires_authentication(self):
        response = self.client.get(reverse("billing:my_access"))
        self.assertEqual(response.status_code, 403)

    def test_my_access_endpoint_is_available_for_authenticated_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("billing:my_access"))
        self.assertEqual(response.status_code, 200)

    def test_redeem_requires_valid_code(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("billing:access_redeem"), {"code": "NOPE"})
        self.assertIn(response.status_code, [400, 404])

    def test_redeemed_access_is_bound_to_redeeming_device(self):
        client = APIClient()
        client.force_login(self.user)
        subject = Subject.objects.create(name="Math", slug="math")
        course = Course.objects.create(
            subject=subject,
            instructor=self.instructor,
            title="Course 1",
            slug="course-1",
            description="Test course",
            status="published",
        )
        AccessCode.objects.create(code="ABC123", course=course, max_redemptions=2)

        response = client.post(reverse("billing:access_redeem"), {"code": "ABC123"}, HTTP_USER_AGENT="Device One")
        self.assertEqual(response.status_code, 201)
        grant = AccessGrant.objects.get(user=self.user, course=course)
        self.assertTrue(grant.device_fingerprint)

        other_device = APIClient()
        other_device.force_login(self.user)
        other_response = other_device.post(reverse("billing:access_redeem"), {"code": "ABC123"}, HTTP_USER_AGENT="Device Two")
        self.assertEqual(other_response.status_code, 403)

# Create your tests here.
