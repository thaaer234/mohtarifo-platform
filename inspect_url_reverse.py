import os
import django
import sys

sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.urls import reverse
from learning.models import Course

c = Course.objects.get(id=33)
print(f"Testing URL reversal for course ID {c.id}...")
try:
    url1 = reverse('dashboard:admin_course_control', args=[c.id])
    print("OK URL 1:", url1)
    
    url2 = reverse('dashboard:public_course_detail', args=[c.id])
    print("OK URL 2:", url2)
    
    # Test template explicit named params just in case
    from django.template import Template, Context
    tpl = Template("{% url 'dashboard:admin_course_control' course.id %}")
    out = tpl.render(Context({'course': c}))
    print("TPL RENDER OK:", out)
    
except Exception as e:
    print("!!! ERROR REVERSING URL !!!")
    import traceback
    traceback.print_exc()
