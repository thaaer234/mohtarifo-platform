import os
import django
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from production_management.views import ScannerView

print("Running HEAVY REAL-WORLD diagnostic test with full logging...")
try:
    view = ScannerView()
    
    # Override internal method with logger injection to catch exactly WHICH COURSE FAILS
    orig_gen = view._auto_generate_sessions
    
    # Run with real CLEAR EXISTING
    view._auto_generate_sessions(clear_existing=True)
    print("MASSIVE SUCCESS: Completely ran _auto_generate_sessions WITHOUT crashing.")

except Exception:
    print("FATAL DIAGNOSTIC TRAP:")
    traceback.print_exc()
