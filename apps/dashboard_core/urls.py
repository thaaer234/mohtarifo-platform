from django.urls import path
from .views import AdminDashboardFinanceView

app_name = 'dashboard_core'

urlpatterns = [
    path('', AdminDashboardFinanceView.as_view(), name='finance_overview'),
]
