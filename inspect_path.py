import os
import django
import sys

sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from learning.models import Course
c = Course.objects.get(id=33)
print("STATIC PATH IS:", repr(c.instructor_cover_static_path))
