import os
import django
import sys
from django.forms.models import model_to_dict

sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from learning.models import Course

c = Course.objects.get(id=33)
print("COURSE DATA:")
for key, val in model_to_dict(c).items():
    print(f"  {key}: {repr(val)}")
