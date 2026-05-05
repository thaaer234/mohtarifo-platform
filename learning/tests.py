from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse


class CourseApiTests(TestCase):
    fixtures = []

    def test_course_list_endpoint_is_available(self):
        response = self.client.get(reverse("learning:course_list"))
        self.assertEqual(response.status_code, 200)

    def test_online_sessions_endpoint_is_available(self):
        user = get_user_model().objects.create_user(username="student", password="student12345")
        self.client.force_login(user)
        response = self.client.get(reverse("learning:online_sessions"))
        self.assertEqual(response.status_code, 200)

# Create your tests here.
