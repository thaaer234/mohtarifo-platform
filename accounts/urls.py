from django.urls import path

from .views import AuthCsrfApiView, AuthLoginApiView, AuthLogoutApiView, AuthMeApiView

app_name = "accounts"

urlpatterns = [
    path("auth/csrf/", AuthCsrfApiView.as_view(), name="auth_csrf"),
    path("auth/login/", AuthLoginApiView.as_view(), name="auth_login"),
    path("auth/logout/", AuthLogoutApiView.as_view(), name="auth_logout"),
    path("auth/me/", AuthMeApiView.as_view(), name="auth_me"),
]
