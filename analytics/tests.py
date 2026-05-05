from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse


class AnalyticsApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="student", password="student12345")

    def test_student_dashboard_endpoint_requires_authentication(self):
        response = self.client.get(reverse("analytics:student_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_study_plan_endpoint_is_available_for_authenticated_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("analytics:study_plan"))
        self.assertEqual(response.status_code, 200)

# Create your tests here.
