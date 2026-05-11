import os
import django
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS = ['*']

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

print("--- STARTING FULL STACK E2E WEB SIMULATION ---")

try:
    # Create or find superuser to bypass mixins
    user = User.objects.filter(is_superuser=True).first()
    if not user:
         # Fallback just in case there are no superusers locally
         user = User.objects.create_superuser('simadmin', 'sim@test.com', 'pass123')
         
    client = Client()
    client.force_login(user)
    
    # 1. Test GET loading of the scanner page initially
    print("1. Testing Scanner Page Initial Load...")
    r1 = client.get('/production/scanner/')
    print(f"   -> GET scanner Response Status: {r1.status_code}")
    if r1.status_code == 500:
         print("ERROR: GET scanner Crashed initially!")
         exit(1)
         
    # 2. Test TRIGGERING the POST regenerate schedule action
    print("2. Triggering Regenerate Schedule Action...")
    r2 = client.post('/production/scanner/', {'action': 'regenerate_schedule'})
    print(f"   -> POST regenerate Response Status: {r2.status_code}")
    
    if r2.status_code == 302:
         print("   -> Post redirected successfully. Following redirect...")
         r3 = client.get(r2.url)
         print(f"   -> Follow-up GET Status: {r3.status_code}")
         if r3.status_code == 500:
              print("FATAL: Redirection GET crashed after generation completed!")
              # Let's dump content to see what it crashed on? Wait, client error handler usually hides it.
              # We will need to trigger the view directly if this fails to see the trace!
              exit(1)
    elif r2.status_code == 500:
         print("FATAL: The generation process CRASHED directly during execution!")
         exit(1)
    
    print("--- ALL TESTS PASSED SUCCESSFULLY LOCALLY! ---")

except Exception as e:
    print("!!! TRAPPED CRITICAL FAULT !!!")
    traceback.print_exc()
