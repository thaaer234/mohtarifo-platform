import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from billing.models import SalesCenter, AccessCode
from dashboard.views import admin_billing

# Let's run the exact view code or a simulator of the view code
print("--- RUNNING SIMULATION OF admin_billing VIEW ---")
centers_report = []
for center in SalesCenter.objects.filter(is_active=True).select_related("institute").order_by("name"):
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
    print(f"Center {center.name}: initialized actual_earned_cents = {actual_earned_cents}")
    for idx, code in enumerate(sold_codes):
        print(f"  Code {idx}: sold_price_cents = {code.sold_price_cents}")
        if code.sold_price_cents is not None:
            actual_earned_cents += code.sold_price_cents
        else:
            if code.course and code.course.price_cents:
                actual_earned_cents += code.course.price_cents
            elif code.package and code.package.price_cents:
                actual_earned_cents += code.package.price_cents
        print(f"  actual_earned_cents now = {actual_earned_cents}")
        
    # Wait, check if actual_earned_cents is None
    actual_earned = actual_earned_cents / 100 if actual_earned_cents is not None else None
    print(f"  actual_earned = {actual_earned}")
    
    centers_report.append({
        "center": center,
        "total_codes": codes.count(),
        "sold_codes_count": sold_count,
        "expected_balance": expected_balance_cents / 100,
        "real_standard": real_standard_cents / 100,
        "actual_earned": actual_earned,
    })

print("Centers report:", centers_report)
try:
    total_centers_earned = sum(item["actual_earned"] for item in centers_report)
    print("Total centers earned:", total_centers_earned)
except Exception as e:
    print("Error in sum:", type(e), e)
