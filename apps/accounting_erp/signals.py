import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models

logger = logging.getLogger('accounting_erp')

# ─────────────────────────────────────────────────────────────────────────────
# Access Code Sold -> Record Sale (Deferred Revenue)
# ─────────────────────────────────────────────────────────────────────────────
@receiver(post_save, sender='billing.AccessCode')
def on_access_code_saved(sender, instance, **kwargs):
    """
    When an access code is sold, record it in the accounting system.
    """
    if instance.sale_status == 'sold':
        try:
            from .services.accounting_engine import AccountingEngine
            # Check if already recorded to avoid duplicates (Idempotency)
            # We can use reference as 'AC-{instance.id}'
            ref = f"AC-{instance.id}"
            from .models import JournalEntry
            if not JournalEntry.objects.filter(source_id=ref).exists():
                amount = (instance.sold_price_cents or 0) / 100
                if amount > 0:
                    AccountingEngine.record_sale(
                        amount=amount,
                        student=instance.sold_by, # This might need to be student profile
                        course=instance.course,
                        sales_center=instance.sales_center,
                        reference=ref
                    )
        except Exception as e:
            logger.exception(f"[ERP Signal] access_code sold error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# Online Session Completed -> Recognize Revenue & Teacher Commission
# ─────────────────────────────────────────────────────────────────────────────
@receiver(post_save, sender='learning.OnlineLessonSession')
def on_session_saved(sender, instance, **kwargs):
    """
    When a session is completed, recognize revenue and calculate commissions.
    """
    if instance.status == 'completed':
        try:
            from .services.accounting_engine import AccountingEngine
            ref = f"SESS-{instance.id}"
            from .models import JournalEntry
            if not JournalEntry.objects.filter(source_id=ref).exists():
                # For a session, we need to determine the value to recognize.
                # If it's part of a course, we might recognize a portion of the course price.
                # For now, let's assume a fixed portion or look up total students.
                
                course = instance.lesson.unit.course
                instructor = course.instructor.instructor_profile
                
                # Logic to determine amount to recognize
                # This is a simplification: in a real ERP, we'd have a 'Revenue Recognition Schedule'
                # Let's assume we recognize a placeholder amount or calculate based on participants
                total_enrolled = course.purchases.count()
                price = (course.price_cents or 0) / 100
                
                # If course has 10 sessions, recognize 1/10 per session
                total_sessions = instance.lesson.unit.course.units.aggregate(
                    count=models.Count('lessons__online_sessions')
                )['count'] or 1
                
                amount_per_session = (price * total_enrolled) / total_sessions
                
                if amount_per_session > 0:
                    AccountingEngine.recognize_revenue(
                        amount=amount_per_session,
                        course=course,
                        instructor=instructor,
                        reference=ref
                    )
        except Exception as e:
            logger.exception(f"[ERP Signal] session completed error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# Payment Paid -> Record Cash Collection
# ─────────────────────────────────────────────────────────────────────────────
@receiver(post_save, sender='billing.Payment')
def on_payment_saved(sender, instance, **kwargs):
    if instance.status == 'paid':
        try:
            from .services.accounting_engine import AccountingEngine
            ref = f"PAY-{instance.id}"
            from .models import JournalEntry
            if not JournalEntry.objects.filter(source_id=ref).exists():
                amount = instance.amount_cents / 100
                # Record as sale/collection
                # This depends on if it's a direct purchase or top-up
                pass # Implementation depends on specific business flow
        except Exception as e:
            logger.exception(f"[ERP Signal] payment paid error: {e}")
