import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

class ShamCashClient:
    """
    عميل موحد للتعامل مع Sham Cash API
    """
    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key or getattr(settings, "SHAMCASH_API_KEY", "")
        self.base_url = (base_url or getattr(settings, "SHAMCASH_BASE_URL", "https://api-shamcash.com/api")).rstrip("/")

    @property
    def headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request(self, method, endpoint, payload=None, params=None):
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=payload if payload else None,
                params=params if params else None,
                timeout=20,
            )
            data = response.json() if response.content else {}
            return {
                "success": response.ok,
                "status_code": response.status_code,
                "data": data,
            }
        except requests.RequestException as e:
            logger.error(f"Sham Cash API Error [{method} {url}]: {str(e)}")
            return {
                "success": False,
                "status_code": 500,
                "error": "CONNECTION_ERROR",
                "message": str(e),
            }

    # 1. استعلام المحافظ
    def get_wallets(self):
        return self._request("GET", "/v1/wallets")

    # 2. إنشاء فاتورة دفع
    def create_invoice(self, amount, currency="SYP", wallet_address=None, webhook_url=None, expires_in_minutes=60, metadata=None):
        wallet = wallet_address or getattr(settings, "SHAMCASH_DEFAULT_WALLET", "")
        if not wallet:
            # جلب أول محفظة نشطة تلقائياً إذا لم تكن محددة
            wallets_res = self.get_wallets()
            if wallets_res.get("success") and isinstance(wallets_res.get("data"), list) and len(wallets_res["data"]) > 0:
                wallet = wallets_res["data"][0].get("walletAddress")

        payload = {
            "amount": str(int(float(amount))),
            "currency": currency,
            "walletAddress": str(wallet),
            "expiresInMinutes": expires_in_minutes,
        }
        if webhook_url:
            payload["webhookUrl"] = webhook_url

        return self._request("POST", "/v1/invoices", payload=payload)

    # 3. جلب تفاصيل فاتورة
    def get_invoice(self, invoice_number):
        return self._request("GET", f"/v1/invoices/{invoice_number}")

    # 4. التحقق من دفع الفاتورة برقم عملية شام كاش
    def verify_invoice(self, invoice_number, tran_id):
        return self._request("POST", f"/v1/invoices/{invoice_number}/verify", payload={"tran_id": str(tran_id).strip()})

    # 5. تسجيل Webhook للمعاملات
    def register_wallet_webhook(self, wallet_address, webhook_url, direction="all"):
        return self._request("POST", f"/v1/wallets/shamcash/{wallet_address}/webhook", payload={
            "webhookUrl": webhook_url,
            "direction": direction,
        })
