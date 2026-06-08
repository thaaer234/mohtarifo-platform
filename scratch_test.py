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
    loader.get_template("dashboard/admin_dashboard.html")
    print("TEMPLATE 'admin_dashboard.html' COMPILES OK!")
except Exception as e:
    print("TEMPLATE ERROR:", str(e))
    exit(1)

# Test 3: View execution
print("\n--- Testing View Execution ---")
try:
    from django.test import RequestFactory
    from django.contrib.auth.models import User
    from dashboard.views import admin_dashboard
    from django.contrib import messages
    from django.contrib.messages.storage.fallback import FallbackStorage
    from django.contrib.sessions.middleware import SessionMiddleware
    
    # Create request factory
    factory = RequestFactory()
    request = factory.get('/admin-dashboard/')
    
    # Process session middleware
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()
    
    # Add messages middleware storage
    setattr(request, '_messages', FallbackStorage(request))
    
    # Get or create an admin user
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.create_superuser('testadmin', 'admin@example.com', 'adminpassword')
        
    request.user = admin_user
    
    # Run view
    response = admin_dashboard(request)
    print("VIEW 'admin_dashboard' EXECUTED OK! Status code:", response.status_code)
    
except Exception as e:
    print("VIEW EXECUTION ERROR:", str(e))
    import traceback
    traceback.print_exc()
    exit(1)



