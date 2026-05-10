from django.urls import path, include

app_name = 'financial_system'

urlpatterns = [
    path('', include('apps.financial_system.api.urls')),
]
