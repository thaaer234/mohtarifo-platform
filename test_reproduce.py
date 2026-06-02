import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import transaction
from billing.models import SalesCenter, AccessCodeBatch, AccessCode, CoursePackage

print("--- REPRODUCTION TEST START ---")
try:
    with transaction.atomic():
        # Create a dummy center
        center, _ = SalesCenter.objects.get_or_create(name="Reproduction Center Test", defaults={"is_active": True})
        
        # Create a package with None price
        package, _ = CoursePackage.objects.get_or_create(
            code="test-reprod-pkg",
            defaults={"name": "Test Reprod Pkg", "price_cents": None, "is_active": True}
        )
        
        # Create a batch
        batch = AccessCodeBatch.objects.create(
            name="Reprod Batch",
            package=package,
            sales_center=center,
            allocated_count=1
        )
        
        # Create a sold code with sold_price_cents = None
        code1 = AccessCode.objects.create(
            code="TEST-REPROD-CODE-1",
            access_type="package",
            package=package,
            batch=batch,
            sales_center=center,
            sale_status="sold",
            sold_price_cents=None
        )
        
        # Create a sold code with sold_price_cents = 0
        code2 = AccessCode.objects.create(
            code="TEST-REPROD-CODE-2",
            access_type="package",
            package=package,
            batch=batch,
            sales_center=center,
            sale_status="sold",
            sold_price_cents=0
        )
        
        print("Created test records successfully!")
        
        # Now run centers_report simulation
        codes = AccessCode.objects.filter(sales_center=center).select_related("course", "package")
        sold_codes = codes.filter(sale_status="sold")
        sold_count = sold_codes.count()
        
        expected_balance_cents = 0
        for code in codes:
            if code.course and code.course.price_cents:
                expected_balance_cents += code.course.price_cents
            elif code.package and code.package.price_cents:
                expected_balance_cents += code.package.price_cents
                
        real_standard_cents = 0
        for code in sold_codes:
            if code.course and code.course.price_cents:
                real_standard_cents += code.course.price_cents
            elif code.package and code.package.price_cents:
                real_standard_cents += code.package.price_cents
                
        actual_earned_cents = 0
        for code in sold_codes:
            if code.sold_price_cents is not None:
                actual_earned_cents += code.sold_price_cents
            else:
                if code.course and code.course.price_cents:
                    actual_earned_cents += code.course.price_cents
                elif code.package and code.package.price_cents:
                    actual_earned_cents += code.package.price_cents
        
        actual_earned = actual_earned_cents / 100 if actual_earned_cents is not None else None
        print(f"Simulation: actual_earned_cents = {actual_earned_cents} | actual_earned = {actual_earned}")
        
        # Force rollback to keep database clean
        raise Exception("Force rollback to clean DB")
except Exception as e:
    if str(e) == "Force rollback to clean DB":
        print("Success: database rolled back cleanly.")
    else:
        import traceback
        traceback.print_exc()
