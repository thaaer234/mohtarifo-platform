import os
import django
import sys

sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from dashboard.views import admin_catalog_manager
from django.contrib.auth import get_user_model

User = get_user_model()
admin = User.objects.filter(is_staff=True).first()

factory = RequestFactory()
request = factory.get('/admin-dashboard/content/catalog/')
request.user = admin
# Mock messages middleware
from django.contrib.messages.storage.fallback import FallbackStorage
setattr(request, '_messages', FallbackStorage(request))

try:
    response = admin_catalog_manager(request)
    content = response.render().content.decode('utf-8')
    print("SUCCESSFULLY RENDERED")
except Exception as e:
    import traceback
    print("ERROR OCCURRED:")
    traceback.print_exc()
