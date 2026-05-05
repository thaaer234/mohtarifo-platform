from django.urls import path
from . import views, views_templates

app_name = 'exams'

urlpatterns = [
    # API Views
    path('api/list/', views.ExamListApiView.as_view(), name='exam_list'),
    path('api/list/', views.ExamListApiView.as_view(), name='api_list'),
    path('api/<int:exam_id>/start/', views.ExamStartApiView.as_view(), name='exam_start'),
    path('api/<int:exam_id>/start/', views.ExamStartApiView.as_view(), name='api_start'),
    path('api/submit/<int:attempt_id>/', views.AttemptSubmitApiView.as_view(), name='attempt_submit'),
    path('api/submit/<int:attempt_id>/', views.AttemptSubmitApiView.as_view(), name='api_submit'),
    
    # Template Views
    path('<int:exam_id>/', views_templates.exam_detail, name='exam_detail'),
    path('<int:exam_id>/start/', views_templates.start_exam, name='start_exam'),
    path('attempt/<int:attempt_id>/solve/', views_templates.solve_exam, name='solve_exam'),
    path('attempt/<int:attempt_id>/result/', views_templates.exam_result, name='exam_result'),
]
