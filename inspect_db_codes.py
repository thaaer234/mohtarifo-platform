import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from billing.models import SalesCenter, AccessCode

for center in SalesCenter.objects.filter(is_active=True):
    print(f"Center: {center.name} (ID: {center.id})")
    codes = AccessCode.objects.filter(sales_center=center)
    sold_codes = codes.filter(sale_status="sold")
    print(f"  Total codes: {codes.count()} | Sold codes: {sold_codes.count()}")
    for code in sold_codes:
        print(f"    Code: {code.code} (ID: {code.id})")
        print(f"      sold_price_cents: {code.sold_price_cents} ({type(code.sold_price_cents)})")
        print(f"      course: {code.course} | price_cents: {code.course.price_cents if code.course else 'N/A'}")
        print(f"      package: {code.package} | price_cents: {code.package.price_cents if code.package else 'N/A'}")
