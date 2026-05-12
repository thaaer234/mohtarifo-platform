import os
import django
import sys

sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from learning.models import Course
c = Course.objects.get(id=33)

print("BOOL(c.cover):", bool(c.cover))
print("c.cover NAME:", repr(c.cover.name))
try:
    url = c.cover.url
    print("URL:", url)
except Exception as e:
    print("EXC ON URL ACCESS:", str(e))

from django.template import Template, Context
tpl = Template("{% if course.cover %}{{ course.cover.url }}{% else %}NO COVER{% endif %}")
print("TEMPLATE RENDER TEST:", tpl.render(Context({'course': c})))
