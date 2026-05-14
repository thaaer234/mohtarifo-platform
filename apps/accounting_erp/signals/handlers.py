from django.db.models.signals import post_save
from django.dispatch import receiver
from billing.models import Payment, CoursePurchase, AccessCode
from learning.models import OnlineLessonSession
from .service import AccountingEventService

@receiver(post_save, sender=Payment)
def handle_payment_accounting(sender, instance, created, **kwargs):
    """
    Handles payment accounting: Cash In -> Deferred Revenue
    """
    if instance.status == 'paid':
        AccountingEventService.process_payment(instance)

@receiver(post_save, sender=CoursePurchase)
def handle_purchase_accounting(sender, instance, created, **kwargs):
    """
    Handles purchase accounting: Deferred Revenue -> Earned Revenue
    """
    if created:
        AccountingEventService.process_purchase(instance)

@receiver(post_save, sender=AccessCode)
def handle_access_code_sale(sender, instance, created, **kwargs):
    """
    Handles access code sales through centers
    """
    if instance.sale_status == 'sold':
        AccountingEventService.process_code_sale(instance)

@receiver(post_save, sender=OnlineLessonSession)
def handle_session_completion(sender, instance, created, **kwargs):
    """
    Handles session completion: Revenue Recognition + Teacher/Center Payables
    """
    if instance.status == 'completed':
        AccountingEventService.process_session_completion(instance)
