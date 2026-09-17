import json
import logging
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .services_shamcash import ShamCashPaymentService
from .shamcash_client import ShamCashClient
from .models import ShamCashInvoice
from dashboard.views import _current_device_fingerprint

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class CreateShamCashInvoiceApiView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        if not user:
            from django.contrib.auth.models import User
            user = User.objects.filter(is_active=True).first()

        course_id = request.data.get("course_id")
        package_id = request.data.get("package_id")
        device_fingerprint = _current_device_fingerprint(request)
        
        if not course_id and not package_id:
            return Response({"error": "يجب تحديد معرف الدورة أو الباقة."}, status=status.HTTP_400_BAD_REQUEST)

        # تحديد مسار الـ Webhook العام
        webhook_url = request.build_absolute_uri("/api/v1/billing/shamcash/webhook/")
        if "localhost" in webhook_url or "127.0.0.1" in webhook_url:
            webhook_url = None  # API شام كاش يرفض localhost

        res = ShamCashPaymentService.create_payment_invoice(
            user=user,
            course_id=course_id,
            package_id=package_id,
            webhook_url=webhook_url,
            device_fingerprint=device_fingerprint
        )

        if not res.get("success"):
            return Response({"error": res.get("error")}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": "تم إنشاء الفاتورة بنجاح",
            "invoice_number": res["invoice_number"],
            "amount": res["amount"],
            "currency": res["currency"],
            "wallet_address": res["wallet_address"],
            "data": res["raw_data"],
        }, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name='dispatch')
class VerifyShamCashInvoiceApiView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        invoice_number = request.data.get("invoice_number")
        tran_id = request.data.get("tran_id")
        device_fingerprint = _current_device_fingerprint(request)

        if not invoice_number or not tran_id:
            return Response({"error": "رقم الفاتورة ورقم العملية مطلوبان."}, status=status.HTTP_400_BAD_REQUEST)

        client = ShamCashClient()
        verify_res = client.verify_invoice(invoice_number=invoice_number, tran_id=tran_id)

        if not verify_res.get("success"):
            error_data = verify_res.get("data", {})
            return Response({
                "error": error_data.get("message", "فشل التحقق من العملية"),
                "code": error_data.get("error")
            }, status=status.HTTP_400_BAD_REQUEST)

        # التحقق نجح وتم تأكيد الدفع في شام كاش
        ShamCashPaymentService.handle_successful_payment(
            invoice_number=invoice_number,
            tran_id=tran_id,
            device_fingerprint=device_fingerprint
        )

        return Response({
            "message": "تم تأكيد الدفع وتفعيل الاشتراك بنجاح!",
            "status": "paid"
        }, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class ShamCashWebhookApiView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        payload = request.data
        logger.info(f"Received ShamCash Webhook: {json.dumps(payload)}")

        event = payload.get("event")
        if event == "invoice.paid":
            invoice_number = payload.get("invoiceNumber")
            tran_ref = payload.get("transactionRef")
            paid_amount = payload.get("paidAmount")
            counterparty = payload.get("counterparty")

            if invoice_number:
                ShamCashPaymentService.handle_successful_payment(
                    invoice_number=invoice_number,
                    tran_id=tran_ref,
                    paid_amount=paid_amount,
                    counterparty=counterparty
                )
        elif event == "invoice.expired":
            invoice_number = payload.get("invoiceNumber")
            if invoice_number:
                ShamCashInvoice.objects.filter(invoice_number=invoice_number).update(
                    status=ShamCashInvoice.Status.EXPIRED
                )
        elif event == "transaction.new":
            transactions = payload.get("transactions", [])
            for txn in transactions:
                txn_id = txn.get("id")
                amount = txn.get("amount")
                txn_type = txn.get("type")
                counterparty = txn.get("counterparty")

                if txn_type == "credit" and txn_id:
                    pending_invoice = ShamCashInvoice.objects.filter(
                        status=ShamCashInvoice.Status.PENDING,
                        amount=amount
                    ).order_by("-created_at").first()

                    if pending_invoice:
                        ShamCashPaymentService.handle_successful_payment(
                            invoice_number=pending_invoice.invoice_number,
                            tran_id=txn_id,
                            paid_amount=amount,
                            counterparty=counterparty
                        )

        return Response({"status": "received"}, status=status.HTTP_200_OK)
