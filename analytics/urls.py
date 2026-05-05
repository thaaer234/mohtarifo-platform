from django.urls import path

from .views import AnalyticsSummaryApiView, StudentDashboardApiView, StudyPlanApiView

app_name = "analytics"

urlpatterns = [
    path("student/dashboard/", StudentDashboardApiView.as_view(), name="student_dashboard"),
    path("analytics/me/", AnalyticsSummaryApiView.as_view(), name="analytics_summary"),
    path("study-plan/me/", StudyPlanApiView.as_view(), name="study_plan"),
]
