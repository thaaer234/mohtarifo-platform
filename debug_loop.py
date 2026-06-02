import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from billing.models import SalesCenter, AccessCode
from django.db.models import Sum

print("Starting debug of the centers loop...")
for center in SalesCenter.objects.filter(is_active=True).select_related("institute").order_by("name"):
    codes = AccessCode.objects.filter(sales_center=center).select_related("course", "package")
    sold_codes = codes.filter(sale_status="sold")
    sold_count = sold_codes.count()
    
    print(f"\nProcessing Center: {center.name} (ID: {center.id}) | Sold codes count: {sold_count}")
    
    actual_earned_cents = 0
    print(f"  Initial actual_earned_cents: {actual_earned_cents} ({type(actual_earned_cents)})")
    
    for idx, code in enumerate(sold_codes):
        print(f"  Code {idx+1}: {code.code} (ID: {code.id})")
        print(f"    code.sold_price_cents: {code.sold_price_cents} ({type(code.sold_price_cents)})")
        
        if code.sold_price_cents is not None:
            print(f"    Branch: code.sold_price_cents is not None")
            actual_earned_cents += code.sold_price_cents
        else:
            print(f"    Branch: else")
            if code.course and code.course.price_cents:
                print(f"      Adding course price: {code.course.price_cents}")
                actual_earned_cents += code.course.price_cents
            elif code.package and code.package.price_cents:
                print(f"      Adding package price: {code.package.price_cents}")
                actual_earned_cents += code.package.price_cents
                
        print(f"    actual_earned_cents after this code: {actual_earned_cents} ({type(actual_earned_cents)})")
        
    print(f"  Final actual_earned_cents for center: {actual_earned_cents} ({type(actual_earned_cents)})")
