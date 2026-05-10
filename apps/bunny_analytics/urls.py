from django.urls import path
from .views import VideoCostDashboardView

app_name = 'bunny_analytics'

urlpatterns = [
    path('control-room/', VideoCostDashboardView.as_view(), name='dashboard'),
]
