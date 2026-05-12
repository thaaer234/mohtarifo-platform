import os
import django
import sys

sys.stdout.reconfigure(encoding='utf-8')
os.environ['DJANGO_DEBUG'] = 'False'  # FORCE PROD MODE
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.template import Template, Context
from learning.models import Course

c = Course.objects.get(id=33)
path = c.instructor_cover_static_path
print(f"Testing Render in Fake-Prod Mode with Path: {repr(path)}")

tpl = Template("{% load static %}<img src='{% static path %}'>")
try:
    out = tpl.render(Context({'path': path}))
    print("RENDER SUCCESS IN PROD:", out)
except Exception as e:
    print("\n!!! CAUGHT EXCEPTION !!!")
    import traceback
    traceback.print_exc()
