import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from dashboard.views import admin_billing
import sys

rf = RequestFactory()
request = rf.get('/admin-dashboard/billing/')
# Override ALLOWED_HOSTS
from django.conf import settings
settings.ALLOWED_HOSTS = ['*']

admin = User.objects.filter(is_superuser=True).first() or User.objects.filter(is_staff=True).first()
request.user = admin

print("--- START TRACING admin_billing ---")

def trace_lines(frame, event, arg):
    if event == 'line':
        code = frame.f_code
        filename = code.co_filename
        if 'views.py' in filename and frame.f_lineno >= 3100 and frame.f_lineno <= 3160:
            locs = {}
            for k in ['actual_earned_cents', 'code', 'sold_codes', 'expected_balance_cents', 'real_standard_cents']:
                if k in frame.f_locals:
                    val = frame.f_locals[k]
                    if k == 'code' and val is not None:
                        locs[k] = f"Code(id={val.id}, code={val.code}, sold_price_cents={val.sold_price_cents})"
                    else:
                        locs[k] = val
            print(f"Line {frame.f_lineno}: {locs}")
    return trace_lines

sys.settrace(trace_lines)
try:
    admin_billing(request)
except Exception as e:
    print("Caught exception:", type(e), e)
finally:
    sys.settrace(None)
