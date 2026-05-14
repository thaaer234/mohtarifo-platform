from decimal import Decimal
from django.db import transaction
from ..models import Account, JournalEntry, JournalLine, Wallet
from django.utils import timezone

class AccountingEventService:
    @staticmethod
    def process_payment(payment):
        """
        Dr Cash/Bank (1101)
        Cr Deferred Revenue (2101)
        """
        try:
            with transaction.atomic():
                # Check if already processed
                if JournalEntry.objects.filter(reference=f"PAY-{payment.id}").exists():
                    return

                cash_account = Account.objects.get(code='1101')
                deferred_revenue = Account.objects.get(code='2101')
                amount = Decimal(str(payment.amount_cents / 100))

                entry = JournalEntry.objects.create(
                    posting_date=payment.updated_at.date(),
                    memo=f"Payment received from {payment.user.username} via {payment.provider}",
                    reference=f"PAY-{payment.id}",
                    entry_type='RECEIPT',
                    is_posted=True
                )

                # Debit Cash
                JournalLine.objects.create(
                    journal=entry,
                    account=cash_account,
                    debit_amount=amount,
                    credit_amount=0
                )

                # Credit Deferred Revenue
                JournalLine.objects.create(
                    journal=entry,
                    account=deferred_revenue,
                    debit_amount=0,
                    credit_amount=amount
                )
        except Exception as e:
            print(f"Accounting Error [process_payment]: {e}")

    @staticmethod
    def process_purchase(purchase):
        """
        Dr Deferred Revenue (2101)
        Cr Revenue - Courses (4102)
        """
        try:
            with transaction.atomic():
                if JournalEntry.objects.filter(reference=f"PUR-{purchase.id}").exists():
                    return

                deferred_revenue = Account.objects.get(code='2101')
                revenue_account = Account.objects.get(code='4102') # Recorded Courses Revenue
                
                # Get amount from payment if available, or course price
                amount = Decimal('0.00')
                if purchase.payment:
                    amount = Decimal(str(purchase.payment.amount_cents / 100))
                else:
                    amount = Decimal(str(purchase.course.price or 0))

                entry = JournalEntry.objects.create(
                    posting_date=purchase.created_at.date(),
                    memo=f"Revenue Recognition: Course '{purchase.course.title}' purchased by {purchase.user.username}",
                    reference=f"PUR-{purchase.id}",
                    entry_type='JOURNAL',
                    is_posted=True
                )

                # Debit Deferred Revenue
                JournalLine.objects.create(
                    journal=entry,
                    account=deferred_revenue,
                    debit_amount=amount,
                    credit_amount=0
                )

                # Credit Revenue
                JournalLine.objects.create(
                    journal=entry,
                    account=revenue_account,
                    debit_amount=0,
                    credit_amount=amount
                )
        except Exception as e:
            print(f"Accounting Error [process_purchase]: {e}")

    @staticmethod
    def process_code_sale(access_code):
        """
        Handles access code sale via center.
        Dr Center Receivables (1104)
        Cr Deferred Revenue (2101)
        """
        try:
            with transaction.atomic():
                ref = f"CSALE-{access_code.id}"
                if JournalEntry.objects.filter(reference=ref).exists():
                    return

                receivable_account = Account.objects.get(code='1104') # Accounts Receivable
                deferred_revenue = Account.objects.get(code='2101')
                
                amount = Decimal(str((access_code.sold_price_cents or 0) / 100))

                entry = JournalEntry.objects.create(
                    posting_date=access_code.sold_at.date() if access_code.sold_at else timezone.now().date(),
                    memo=f"Access Code Sale: {access_code.code} via {access_code.sales_center.name if access_code.sales_center else 'Direct'}",
                    reference=ref,
                    entry_type='SALES',
                    is_posted=True
                )

                # Debit Receivable
                JournalLine.objects.create(
                    journal=entry,
                    account=receivable_account,
                    debit_amount=amount,
                    credit_amount=0
                )

                # Credit Deferred Revenue
                JournalLine.objects.create(
                    journal=entry,
                    account=deferred_revenue,
                    debit_amount=0,
                    credit_amount=amount
                )
        except Exception as e:
            print(f"Accounting Error [process_code_sale]: {e}")

    @staticmethod
    def process_session_completion(session):
        """
        Handles session completion logic:
        1. Revenue Recognition (Deferred -> Revenue)
        2. Teacher Payable (Expense -> Payable)
        3. Center Payable (Expense -> Payable)
        """
        from .commissions import CommissionEngine
        try:
            with transaction.atomic():
                ref = f"SES-{session.id}"
                if JournalEntry.objects.filter(reference=ref).exists():
                    return

                # Get session value (This should be calculated based on attendance or fixed session price)
                # For now, let's assume a fixed value or proportional to course price
                # (Actual business logic needed here)
                course = session.lesson.unit.course
                total_session_value = Decimal('5000.00') 

                splits = CommissionEngine.calculate_split(
                    amount=total_session_value,
                    instructor=course.instructor,
                    course=course
                )

                entry = JournalEntry.objects.create(
                    posting_date=session.ends_at.date(),
                    memo=f"Session Completion: {session.title} (Course: {course.title})",
                    reference=ref,
                    entry_type='JOURNAL',
                    is_posted=True
                )

                # 1. Revenue Recognition
                deferred_acc = Account.objects.get(code='2101')
                revenue_acc = Account.objects.get(code='4101') # Live Sessions Revenue
                
                # Dr Deferred
                JournalLine.objects.create(journal=entry, account=deferred_acc, debit_amount=total_session_value, credit_amount=0)
                # Cr Revenue
                JournalLine.objects.create(journal=entry, account=revenue_acc, debit_amount=0, credit_amount=total_session_value)

                # 2. Teacher Payable
                teacher_expense_acc = Account.objects.get(code='5101') # Teacher Costs
                teacher_payable_acc = Account.objects.get(code='2201') # Teacher Payables
                
                # Dr Expense
                JournalLine.objects.create(journal=entry, account=teacher_expense_acc, debit_amount=splits['instructor_amount'], credit_amount=0)
                # Cr Payable
                JournalLine.objects.create(journal=entry, account=teacher_payable_acc, debit_amount=0, credit_amount=splits['instructor_amount'])

                # --- NEW: Wallet Integration ---
                from .wallet_manager import WalletManager
                if hasattr(course.instructor, 'instructor_profile'):
                    instructor_wallet = WalletManager.get_or_create_wallet(course.instructor.instructor_profile, 'TEACHER')
                    WalletManager.credit(
                        wallet=instructor_wallet,
                        amount=splits['instructor_amount'],
                        source_event='session_completion',
                        reference_id=str(session.id),
                        description=f"Earnings from session: {session.title}"
                    )

                # --- NEW: Voucher (Settlement Statement) ---
                from ..models.vouchers import Voucher, VoucherType, VoucherItem
                import datetime
                
                voucher_num = f"SET-{datetime.date.today().year}-{session.id}"
                if not Voucher.objects.filter(number=voucher_num).exists():
                    v = Voucher.objects.create(
                        voucher_type=VoucherType.SETTLEMENT,
                        number=voucher_num,
                        date=datetime.date.today(),
                        instructor=course.instructor.instructor_profile,
                        total_amount=splits['instructor_amount'],
                        net_amount=splits['instructor_amount'],
                        journal_entry=entry,
                        status='posted'
                    )
                    VoucherItem.objects.create(
                        voucher=v,
                        description=f"Earnings split for session: {session.title}",
                        unit_price=splits['instructor_amount'],
                        total_price=splits['instructor_amount'],
                        session=session
                    )

        except Exception as e:
            print(f"Accounting Error [process_session_completion]: {e}")
