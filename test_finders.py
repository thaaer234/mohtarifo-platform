import os
import sys
import django
from django.conf import settings

# Add project to path
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.staticfiles import finders
path = 'dashboard/icons/logo2.png'
found = finders.find(path)
print(f"Found path for '{path}': {found}")

if found:
    import mimetypes
    import base64
    mime = mimetypes.guess_type(found)[0]
    print(f"Mime: {mime}")
    with open(found, 'rb') as f:
        encoded = base64.b64encode(f.read()[:10]).decode('ascii')
        print(f"Base64 (first 10 bytes): {encoded}")
else:
    print("Not found!")
    print(f"STATICFILES_DIRS: {settings.STATICFILES_DIRS}")
    # check filesystem
    for static_dir in settings.STATICFILES_DIRS:
        target = os.path.join(static_dir, path)
        print(f"Checking fs: {target} exists? {os.path.exists(target)}")
