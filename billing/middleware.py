from django.contrib.auth import logout
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect

from .devices import device_cache_key, DEVICE_CACHE_TTL
from .models import UserDevice


class ActiveDeviceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_staff:
            # Bypass active device check if an admin is impersonating the student
            if not request.session.get("impersonator_admin_id"):
                fingerprint = self._fingerprint(request)
                if fingerprint:
                    cache_key = device_cache_key(request.user.id, fingerprint)
                    is_active = cache.get(cache_key)
                    
                    if is_active is None:
                        # Cache miss, check DB
                        is_active = UserDevice.objects.filter(
                            user=request.user,
                            fingerprint=fingerprint,
                            is_active=True,
                        ).exists()
                        # Cache the result for 5 minutes (300 seconds)
                        cache.set(cache_key, is_active, DEVICE_CACHE_TTL)
                        
                    if not is_active:
                        logout(request)
                        message = (
                            "تم تسجيل خروجك لأن هذا الحساب تم فتحه من جهاز آخر. "
                            "إذا لم تكن أنت من قام بذلك، يرجى التواصل مع الدعم فوراً."
                        )
                        if request.path.startswith("/api/"):
                            return JsonResponse(
                                {
                                    "detail": message,
                                    "code": "device_logged_out",
                                    "redirect_url": "/device-logged-out/",
                                },
                                status=401,
                            )
                        return redirect("dashboard:device_logged_out")
        response = self.get_response(request)
        if request.user.is_authenticated and not request.user.is_staff and request.path.startswith("/student/"):
            response["Cache-Control"] = "no-store"
        return response

    def _fingerprint(self, request):
        from .devices import device_fingerprint
        return device_fingerprint(request)

