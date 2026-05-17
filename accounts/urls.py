from django.urls import path

from .views import (
    AuthCsrfApiView,
    AuthLoginApiView,
    AuthLogoutApiView,
    AuthMeApiView,
    InstructorChangePasswordApiView,
    InstructorDismissPasswordReminderApiView,
)

app_name = "accounts"

urlpatterns = [
    path("auth/csrf/", AuthCsrfApiView.as_view(), name="auth_csrf"),
    path("auth/login/", AuthLoginApiView.as_view(), name="auth_login"),
    path("auth/logout/", AuthLogoutApiView.as_view(), name="auth_logout"),
    path("auth/me/", AuthMeApiView.as_view(), name="auth_me"),
    path("auth/instructor/change-password/", InstructorChangePasswordApiView.as_view(), name="instructor_change_password"),
    path(
        "auth/instructor/dismiss-password-reminder/",
        InstructorDismissPasswordReminderApiView.as_view(),
        name="instructor_dismiss_password_reminder",
    ),
]
