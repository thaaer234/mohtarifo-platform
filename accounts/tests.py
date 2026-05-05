from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from billing.models import UserDevice


class AuthApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="student",
            password="student12345",
            email="student@example.com",
        )

    def test_login_then_me_then_logout(self):
        login_response = self.client.post(
            reverse("accounts:auth_login"),
            {"username": "student", "password": "student12345"},
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.data["username"], "student")

        me_response = self.client.get(reverse("accounts:auth_me"))
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.data["email"], "student@example.com")

        logout_response = self.client.post(reverse("accounts:auth_logout"), {}, format="json")
        self.assertEqual(logout_response.status_code, 200)

        me_after_logout = self.client.get(reverse("accounts:auth_me"))
        self.assertEqual(me_after_logout.status_code, 403)

    def test_login_requires_csrf_when_enforced(self):
        csrf_client = APIClient(enforce_csrf_checks=True)
        csrf_response = csrf_client.get(reverse("accounts:auth_csrf"))
        self.assertEqual(csrf_response.status_code, 200)
        csrf_token = csrf_response.cookies.get("csrftoken").value

        missing_csrf_login = csrf_client.post(
            reverse("accounts:auth_login"),
            {"username": "student", "password": "student12345"},
            format="json",
        )
        self.assertEqual(missing_csrf_login.status_code, 403)

        valid_login = csrf_client.post(
            reverse("accounts:auth_login"),
            {"username": "student", "password": "student12345"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(valid_login.status_code, 200)

    def test_new_login_logs_out_previous_device_immediately(self):
        first_device = APIClient()
        second_device = APIClient()

        first_login = first_device.post(
            reverse("accounts:auth_login"),
            {"username": "student", "password": "student12345"},
            format="json",
            HTTP_USER_AGENT="Device One",
        )
        self.assertEqual(first_login.status_code, 200)

        second_login = second_device.post(
            reverse("accounts:auth_login"),
            {"username": "student", "password": "student12345"},
            format="json",
            HTTP_USER_AGENT="Device Two",
        )
        self.assertEqual(second_login.status_code, 200)
        self.assertEqual(UserDevice.objects.filter(user=self.user, is_active=True).count(), 1)

        stale_response = first_device.get(reverse("accounts:auth_me"), HTTP_USER_AGENT="Device One")
        self.assertEqual(stale_response.status_code, 401)
        self.assertEqual(stale_response.json()["code"], "device_logged_out")
        self.assertEqual(stale_response.json()["redirect_url"], "/device-logged-out/")
