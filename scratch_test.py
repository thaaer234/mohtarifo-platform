import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from dashboard.whatsapp_utils import is_2fa_disabled, set_2fa_disabled
from django.template import loader

# Test 1: Config toggle functionality
print("--- Testing 2FA Config Toggle ---")
original_state = is_2fa_disabled()
print(f"Original state: {original_state}")

print("Setting 2FA disabled to True...")
set_2fa_disabled(True)
assert is_2fa_disabled() == True, "Failed to disable 2FA"
print("2FA successfully disabled.")

print("Setting 2FA disabled to False...")
set_2fa_disabled(False)
assert is_2fa_disabled() == False, "Failed to enable 2FA"
print("2FA successfully enabled.")

# Restore original state
set_2fa_disabled(original_state)
print(f"Restored original state to: {original_state}")

# Test 2: Template compilation
print("\n--- Testing Template Compilation ---")
try:
    loader.get_template("dashboard/admin_whatsapp_control.html")
    print("TEMPLATE 'admin_whatsapp_control.html' COMPILES OK!")
except Exception as e:
    print("TEMPLATE ERROR:", str(e))
    exit(1)

