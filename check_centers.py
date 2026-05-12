import os
import django
import sys

sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from billing.models import SalesCenter
centers = list(SalesCenter.objects.all())
for c in centers:
    print(f"ID={c.id} NAME={c.name}")
    
# Check if special admin center is already there by name
exists = SalesCenter.objects.filter(name__icontains="شام").exists()
print("SHAM_EXISTS:", exists)
