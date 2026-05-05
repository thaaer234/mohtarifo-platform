from django.urls import path

from .views import MyAccessGrantsApiView, RedeemAccessCodeApiView

app_name = "billing"

urlpatterns = [
    path("access/redeem/", RedeemAccessCodeApiView.as_view(), name="access_redeem"),
    path("access/me/", MyAccessGrantsApiView.as_view(), name="my_access"),
]
