import os
import sys
import django

sys.path.append(r"c:\Users\THAAER\Desktop\pro")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from production_management.views import ScannerView
from production_management.models import TeacherProductionSession

print("All imports working correctly after multi-day enhancements.")
