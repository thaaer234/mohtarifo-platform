import os
import django
import traceback
from django.apps import apps

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

NEW_APPS = [
    'financial_system', 'currency_engine', 'cost_analysis', 'infrastructure_finance', 
    'video_cost_engine', 'operational_expenses', 'financial_conversion', 'bunny_analytics',
    'analytics_engine', 'kpi_engine', 'dashboard_core', 'subscription_analytics'
]

def verify_db_access():
    print("[*] Scanning operational continuity for all financial models...")
    
    all_passed = True
    for app_label in NEW_APPS:
        try:
            app_config = apps.get_app_config(app_label)
            print(f"\n[*] Verifying App: {app_label}")
            for model in app_config.get_models():
                try:
                    # Attempt trivial operation to test table existence
                    cnt = model.objects.all().count()
                    print(f"  [+] Model '{model.__name__}': OK ({cnt} rows)")
                except Exception as ex:
                    print(f"  [X] Model '{model.__name__}': FAILED! -> {str(ex)}")
                    all_passed = False
        except LookupError:
            print(f"\n[!] Warning: App label '{app_label}' not registered.")
            all_passed = False
    
    if all_passed:
        print("\n[SUCCESS] All database tables validated successfully.")
    else:
        print("\n[ERROR] Critical database schema gaps detected.")

if __name__ == "__main__":
    verify_db_access()
