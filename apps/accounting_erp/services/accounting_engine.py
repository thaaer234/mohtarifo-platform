from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from ..models import Account, JournalEntry, JournalEntryType, JournalLine, Wallet, WalletTransaction
from .commission_engine import CommissionEngine

class AccountingEngine:
    @staticmethod
    def record_sale(amount, student, course=None, sales_center=None, reference=""):
        """
        Record a sale:
        Dr Cash (if paid) or Student AR
        Cr Deferred Revenue (Liability - Accrual Principle)
        """
        with transaction.atomic():
            # Get necessary accounts (Assuming standard codes)
            # 1101: Cash / Bank
            # 1103: Student Receivables
            # 2101: Deferred Revenue
            
            cash_account = Account.objects.get(code='1101')
            deferred_rev_account = Account.objects.get(code='2101')
            
            student_name = student.get_full_name() if hasattr(student, 'get_full_name') else student.user.get_full_name()
            
            je = JournalEntry.objects.create(
                posting_date=timezone.now().date(),
                reference=f"SALE-{reference or uuid.uuid4().hex[:8]}",
                memo=f"Sale of {course.title if course else 'Course'} to {student_name}",
                entry_type=JournalEntryType.SALES,
                source_event='COURSE_PURCHASE',
                source_id=reference
            )
            
            # Dr Cash
            JournalLine.objects.create(
                journal=je,
                account=cash_account,
                debit_amount=Decimal(str(amount))
            )
            
            # Cr Deferred Revenue
            JournalLine.objects.create(
                journal=je,
                account=deferred_rev_account,
                credit_amount=Decimal(str(amount))
            )
            
            # Update Student Wallet (Optional, if we want to show it there)
            # In Accrual, the wallet might represent "Credits"
            
            return je

    @staticmethod
    def recognize_revenue(amount, course, instructor, sales_center=None, reference=""):
        """
        Recognize revenue (when session is completed):
        1. Dr Deferred Revenue
           Cr Earned Revenue (P&L)
        2. Dr Teacher Cost (Expense)
           Cr Teacher Payable (Liability)
        3. Dr Center Commission (Expense)
           Cr Center Payable (Liability)
        """
        with transaction.atomic():
            deferred_rev_account = Account.objects.get(code='2101')
            earned_rev_account = Account.objects.get(code='4101') # Course Revenue
            teacher_cost_account = Account.objects.get(code='5101')
            teacher_payable_account = Account.objects.get(code='2201')
            center_cost_account = Account.objects.get(code='5102')
            center_payable_account = Account.objects.get(code='2202')
            
            shares = CommissionEngine.calculate_shares(amount, instructor=instructor, course=course, sales_center=sales_center)
            
            je = JournalEntry.objects.create(
                posting_date=timezone.now().date(),
                reference=f"REV-{reference or uuid.uuid4().hex[:8]}",
                memo=f"Revenue Recognition for Session/Course: {course.title}",
                entry_type=JournalEntryType.ACCRUAL,
                source_event='SESSION_COMPLETED',
                source_id=reference
            )
            
            # 1. Dr Deferred Rev, Cr Earned Rev
            JournalLine.objects.create(journal=je, account=deferred_rev_account, debit_amount=Decimal(str(amount)))
            JournalLine.objects.create(journal=je, account=earned_rev_account, credit_amount=Decimal(str(amount)))
            
            # 2. Teacher Share
            if shares['instructor_amount'] > 0:
                JournalLine.objects.create(journal=je, account=teacher_cost_account, debit_amount=shares['instructor_amount'])
                JournalLine.objects.create(journal=je, account=teacher_payable_account, credit_amount=shares['instructor_amount'])
                
                # Update Teacher Wallet
                instructor_wallet, _ = Wallet.objects.get_or_create(instructor=instructor, defaults={'owner_type': 'TEACHER'})
                instructor_wallet.balance += shares['instructor_amount']
                instructor_wallet.save()
                
                WalletTransaction.objects.create(
                    wallet=instructor_wallet,
                    amount=shares['instructor_amount'],
                    transaction_type='credit',
                    source_event='REVENUE_RECOGNITION',
                    reference_id=reference,
                    description=f"Earned from session: {course.title}",
                    balance_before=instructor_wallet.balance - shares['instructor_amount'],
                    balance_after=instructor_wallet.balance
                )
            
            # 3. Center Share
            if shares['center_amount'] > 0 and sales_center:
                JournalLine.objects.create(journal=je, account=center_cost_account, debit_amount=shares['center_amount'])
                JournalLine.objects.create(journal=je, account=center_payable_account, credit_amount=shares['center_amount'])
                
                # Update Center Wallet
                center_wallet, _ = Wallet.objects.get_or_create(sales_center=sales_center, defaults={'owner_type': 'CENTER'})
                center_wallet.balance += shares['center_amount']
                center_wallet.save()
                
                WalletTransaction.objects.create(
                    wallet=center_wallet,
                    amount=shares['center_amount'],
                    transaction_type='credit',
                    source_event='REVENUE_RECOGNITION',
                    reference_id=reference,
                    description=f"Commission from course sale: {course.title}",
                    balance_before=center_wallet.balance - shares['center_amount'],
                    balance_after=center_wallet.balance
                )
                
            return je

import uuid
