import os
import sys
import django
from django.db import transaction

# Bootstrap Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from billing.models import SalesCenter, AccessCode, AccessCodeBatch

def migrate_center_data(source_pattern=u"\u062b\u0627\u0626\u0631", dry_run=True):
    print(f"--- Data Migration Diagnostic --- {'(DRY RUN)' if dry_run else '(LIVE UPDATE)'}")
    
    # 1. Locate Source Centers
    sources = list(SalesCenter.objects.filter(name__icontains=source_pattern))
    if not sources:
        print(f"[FAIL] No legacy centers found containing your requested pattern.")
        print("\nAvailable Centers currently in the database:")
        for c in SalesCenter.objects.all():
            # Use safe repr encoding to circumvent console font constraints
            safe_name = repr(c.name)
            print(f"  - ID: {c.id} | Name: {safe_name}")
        print("\nPlease re-run script and pass the desired pattern name from the list above.")
        return
    
    print(f"[OK] Found {len(sources)} matching center(s) as sources:")
    for s in sources:
        print(f"   - ID: {s.id} | Name: {s.name}")
        
    # 2. Locate Destination (Sham Cash Admin)
    from dashboard.views import _get_sham_cash_center
    try:
        target = _get_sham_cash_center()
        print(f"[TARGET] Resolved: ID: {target.id} | Name: {target.name}")
    except Exception as e:
        print(f"[FAIL] Failed to resolve destination center: {e}")
        return

    # 3. Perform Scans
    print("\n--- Scoping Record Impact ---")
    total_batches = 0
    total_codes = 0
    
    for src in sources:
        batches_count = AccessCodeBatch.objects.filter(sales_center=src).count()
        codes_count = AccessCode.objects.filter(sales_center=src).count()
        print(f"[INFO] Source '{src.name}': Contains {batches_count} Batches and {codes_count} AccessCodes")
        total_batches += batches_count
        total_codes += codes_count
        
    if total_batches == 0 and total_codes == 0:
        print("[WARNING] No data resides within legacy centers. Nothing to migrate.")
        return

    # 4. Transaction Execution
    print(f"\nAttempting migration of {total_batches} batches and {total_codes} individual codes to {target.name}...")
    
    try:
        with transaction.atomic():
            for src in sources:
                updated_batches = AccessCodeBatch.objects.filter(sales_center=src).update(sales_center=target)
                updated_codes = AccessCode.objects.filter(sales_center=src).update(sales_center=target)
                print(f"   Moved {updated_batches} batches and {updated_codes} codes from '{src.name}'")
            
            if dry_run:
                print("\n[DONE] SIMULATION COMPLETE. No changes were committed to the database.")
                print("Rerun with --commit flag to permanently apply.")
                raise Exception("DRY_RUN_ROLLBACK")
            else:
                print("\n[SUCCESS] All items have been permanently moved.")
                
    except Exception as e:
        if str(e) == "DRY_RUN_ROLLBACK":
            pass
        else:
            print(f"[ERROR] FATAL during migration: {e}")

if __name__ == "__main__":
    # Command line argument to trigger LIVE deployment
    commit = "--commit" in sys.argv
    migrate_center_data(source_pattern=u"\u062b\u0627\u0626\u0631", dry_run=not commit)
