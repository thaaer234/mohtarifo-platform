import os
import sys
import django

# Setup django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from analytics.services import TrackingService
from django.test import RequestFactory
from analytics.models import LandingVisit

rf = RequestFactory()
request = rf.get('/')
# Mock session
from django.contrib.sessions.middleware import SessionMiddleware
middleware = SessionMiddleware(lambda r: None)
middleware.process_request(request)
request.session.save()

print("Initial count:", LandingVisit.objects.count())

try:
    TrackingService.log_landing_visit(request)
    print("Success! New count:", LandingVisit.objects.count())
except Exception as e:
    print("Failed with error:", str(e))
    import traceback
    traceback.print_exc()

# Check log file
if os.path.exists("landing_error_log.txt"):
    with open("landing_error_log.txt", "r") as f:
        print("\n--- CONTENT OF landing_error_log.txt ---")
        print(f.read())
else:
    print("\nlanding_error_log.txt does not exist.")
