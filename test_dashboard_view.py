import os
import django
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS = ['*']


from django.test import RequestFactory
from django.contrib.auth.models import User
from apps.dashboard_core.views import AdminDashboardFinanceView


def run_diagnostics():
    print("[*] Initializing diagnostics for Dashboard Finance View...")
    rf = RequestFactory()
    req = rf.get('/finance-analytics-hub/')
    
    admin_user = User.objects.filter(is_staff=True).first()
    if not admin_user:
        print("[!] Warning: No staff user found in DB to simulate request context.")
        return
        
    req.user = admin_user
    view = AdminDashboardFinanceView.as_view()
    
    try:
        response = view(req)
        print(f"[+] View executed successfully! Status: {response.status_code}")
        # Force content rendering to trigger template processing
        response.render()
        print("[+] Template rendered successfully!")
    except Exception:
        print("[E] CRITICAL FAILURE DETECTED. TRACEBACK:")
        traceback.print_exc()

if __name__ == "__main__":
    run_diagnostics()
