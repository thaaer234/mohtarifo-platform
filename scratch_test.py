import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.template import loader
try:
    loader.get_template("dashboard/device_logged_out.html")
    print("TEMPLATE COMPILES OK!")
except Exception as e:
    print("TEMPLATE ERROR:", str(e))

