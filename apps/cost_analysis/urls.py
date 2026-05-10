from django.urls import path
from .views import OperationalAnalyticsView

app_name = 'cost_analysis'

urlpatterns = [
    path('dashboard/', OperationalAnalyticsView.as_view(), name='ops_dashboard'),
]
