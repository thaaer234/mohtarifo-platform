import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from billing.models import CoursePackage
print(f"Course Packages: {CoursePackage.objects.count()}")

from apps.accounting_erp.models import JournalEntry, JournalLine
print(f"Total Journal Entries: {JournalEntry.objects.count()}")
print(f"Total Journal Lines: {JournalLine.objects.count()}")

# Show net balance of key accounts
from django.db.models import Sum
from apps.accounting_erp.models import Account
for acc in Account.objects.filter(code__in=['1101', '1104', '2101', '4101', '4102']):
    bal = acc.ledger_lines.aggregate(
        debit=Sum('debit_amount'), 
        credit=Sum('credit_amount')
    )
    d = bal['debit'] or 0
    c = bal['credit'] or 0
    print(f"Account {acc.code} ({acc.name}): Dr {d} | Cr {c} | Bal {d-c}")
