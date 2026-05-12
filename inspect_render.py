import os
import django
import sys

sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.template import Template, Context
from learning.models import Course
c = Course.objects.get(id=33)

tpl = Template("{% load static %}<img src='{% static path %}'>")
try:
    out = tpl.render(Context({'path': c.instructor_cover_static_path}))
    print("RENDER SUCCESS:", out)
except Exception as e:
    print("ERROR RENDER STATIC:")
    import traceback
    traceback.print_exc()
