from django.urls import path

from .views import CourseDetailApiView, CourseListApiView, MyAttendanceApiView, OnlineSessionListApiView

app_name = "learning"

urlpatterns = [
    path("courses/", CourseListApiView.as_view(), name="course_list"),
    path("courses/<slug:slug>/", CourseDetailApiView.as_view(), name="course_detail"),
    path("online-sessions/", OnlineSessionListApiView.as_view(), name="online_sessions"),
    path("attendance/me/", MyAttendanceApiView.as_view(), name="my_attendance"),
]
