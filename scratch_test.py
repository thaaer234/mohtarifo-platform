import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from billing.models import Subscription, Payment

print("--- Subscriptions Count by Status ---")
from django.db.models import Count
subs = Subscription.objects.values('status').annotate(count=Count('status'))
for s in subs:
    print(f"Status: {s['status']}, Count: {s['count']}")

print("\n--- Payments Count by Status ---")
pmts = Payment.objects.values('status').annotate(count=Count('status'))
for p in pmts:
    print(f"Status: {p['status']}, Count: {p['count']}")

print("\n--- Let's inspect some payments ---")
for p in Payment.objects.all()[:5]:
    print(f"User: {p.user}, Amount: {p.amount_cents}, Provider: {p.provider}, Status: {p.status}")
