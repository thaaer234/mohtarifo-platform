import logging
from django.utils import timezone
from django.db import transaction
from .models import ShamCashInvoice, AccessGrant
from .shamcash_client import ShamCashClient
from learning.models import Course

logger = logging.getLogger(__name__)

class ShamCashPaymentService:
    @staticmethod
    def create_payment_invoice(user, course_id=None, package_id=None, webhook_url=None, device_fingerprint=""):
        course = None
        amount = 0
        title = ""

        if course_id:
            course = Course.objects.get(id=course_id)
            amount = getattr(course, "price_cents", 0) or getattr(course, "price_syp", 0) or 2400
            title = course.title
        else:
            raise ValueError("يجب تحديد دورة لإنشاء الفاتورة.")

        client = ShamCashClient()
        metadata = {
            "user_id": user.id if user else None,
            "username": user.username if user else "guest",
            "course_id": course.id if course else None,
            "item_title": title,
            "device_fingerprint": device_fingerprint,
        }

        res = client.create_invoice(
            amount=amount,
            currency="SYP",
            webhook_url=webhook_url,
            metadata=metadata,
            expires_in_minutes=60,
        )

        if not res.get("success"):
            logger.error(f"Failed to create ShamCash invoice: {res}")
            return {"success": False, "error": res.get("data", {}).get("message", "فشل إنشاء الفاتورة في شام كاش")}

        data = res.get("data", {})
        invoice_number = data.get("invoiceNumber") or data.get("invoiceId") or data.get("id")

        invoice = ShamCashInvoice.objects.create(
            user=user,
            course=course,
            invoice_number=invoice_number,
            amount=amount,
            currency="SYP",
            wallet_address=data.get("walletAddress", ""),
            metadata=metadata,
        )

        return {
            "success": True,
            "invoice": invoice,
            "invoice_number": invoice_number,
            "amount": amount,
            "currency": "SYP",
            "wallet_address": invoice.wallet_address,
            "raw_data": data,
        }

    @classmethod
    def handle_successful_payment(cls, invoice_number, tran_id=None, paid_amount=None, counterparty=None, device_fingerprint=""):
        with transaction.atomic():
            try:
                invoice = ShamCashInvoice.objects.select_for_update().get(invoice_number=invoice_number)
            except ShamCashInvoice.DoesNotExist:
                logger.error(f"Invoice {invoice_number} not found for payment processing.")
                return False

            if invoice.status == ShamCashInvoice.Status.PAID:
                logger.info(f"Invoice {invoice_number} already paid.")
                return True

            invoice.status = ShamCashInvoice.Status.PAID
            if tran_id:
                invoice.transaction_ref = tran_id
            if paid_amount:
                invoice.paid_amount = paid_amount
            if counterparty:
                invoice.counterparty = counterparty
            invoice.paid_at = timezone.now()
            invoice.save()

            # منح صلاحية الوصول للطالب مع بصمة الجهاز وتاريخ البدء
            user = invoice.user
            fingerprint = device_fingerprint or invoice.metadata.get("device_fingerprint", "")
            
            if user and invoice.course:
                grant, created = AccessGrant.objects.get_or_create(
                    user=user,
                    course=invoice.course,
                    defaults={
                        "source": "purchase",
                        "device_fingerprint": fingerprint,
                        "starts_at": timezone.now(),
                    }
                )
                if not created:
                    # تحديث بصمة الجهاز إذا كانت فارغة
                    if not grant.device_fingerprint and fingerprint:
                        grant.device_fingerprint = fingerprint
                    if not grant.starts_at:
                        grant.starts_at = timezone.now()
                    grant.save()

            logger.info(f"Granted access to user {user.username if user else 'anonymous'} for invoice {invoice.invoice_number}")
            return True
