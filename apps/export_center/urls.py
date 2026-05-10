from django.urls import path
from .api.views import TestDemoExportView

app_name = 'export_center'

urlpatterns = [
    path('test/<str:format_type>/', TestDemoExportView.as_view(), name='test_render'),
]
