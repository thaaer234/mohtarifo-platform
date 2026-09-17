from django.urls import path
from .views import MyAccessGrantsApiView, RedeemAccessCodeApiView
from .views_shamcash import (
    CreateShamCashInvoiceApiView,
    VerifyShamCashInvoiceApiView,
    ShamCashWebhookApiView
)

app_name = "billing"

urlpatterns = [
    path("access/redeem/", RedeemAccessCodeApiView.as_view(), name="access_redeem"),
    path("access/me/", MyAccessGrantsApiView.as_view(), name="my_access"),
    
    # Sham Cash Endpoints
    path("shamcash/create-invoice/", CreateShamCashInvoiceApiView.as_view(), name="shamcash_create_invoice"),
    path("shamcash/verify-invoice/", VerifyShamCashInvoiceApiView.as_view(), name="shamcash_verify_invoice"),
    path("shamcash/webhook/", ShamCashWebhookApiView.as_view(), name="shamcash_webhook"),
]
