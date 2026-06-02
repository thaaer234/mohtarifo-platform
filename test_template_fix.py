import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.template.loader import get_template
from django.template import TemplateSyntaxError

templates_to_test = [
    'dashboard/admin_dashboard.html',
    'dashboard/admin_billing.html',
    'dashboard/admin_sales_center_profile.html',
    'dashboard/admin_institute_profile.html',
]

print("--- TESTING MODIFIED TEMPLATES FOR SYNTAX ERRORS ---")
all_ok = True
for t in templates_to_test:
    try:
        get_template(t)
        print(f"ok - {t} loaded successfully")
    except TemplateSyntaxError as e:
        print(f"error - Template Syntax Error in {t}: {e}")
        all_ok = False
    except Exception as e:
        print(f"error - Error loading {t}: {e}")
        all_ok = False

if all_ok:
    print("All modified templates are syntactically correct!")
else:
    print("Some templates failed to load!")
    exit(1)
