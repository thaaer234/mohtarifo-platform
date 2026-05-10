from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.http import JsonResponse
from django.urls import include, path

admin.site.site_header = "محترفو التعليم"
admin.site.site_title = "إدارة محترفو التعليم"
admin.site.index_title = "لوحة إدارة المنصة"


def healthz(_request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path('', include('dashboard.urls')),
    path('exams/', include(('exams.urls', 'exams'), namespace='exams_templates')),
    path('logout/', LogoutView.as_view(next_page='dashboard:login'), name='logout'),
    path('healthz/', healthz, name='healthz'),
    path('api/v1/exams/', include(('exams.urls', 'exams'), namespace='exams_api')),
    path('api/v1/accounts/', include('accounts.urls')),
    path('api/v1/learning/', include('learning.urls')),
    path('api/v1/analytics/', include('analytics.urls')),
    path('api/v1/billing/', include('billing.urls')),
    
    # Enterprise Financial Analytics Engine API Extensions
    path('api/financial/', include('apps.financial_system.urls')),
    path('finance-analytics-hub/', include('apps.dashboard_core.urls')),
    path('finance-exports/', include('apps.export_center.urls')),
    path('ops-intelligence/', include('apps.cost_analysis.urls')),
    path('infra-bunny-analytics/', include('apps.bunny_analytics.urls')),
    
    path(settings.ADMIN_URL, admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = "dashboard.error_views.permission_denied"
handler404 = "dashboard.error_views.page_not_found"
handler500 = "dashboard.error_views.server_error"
