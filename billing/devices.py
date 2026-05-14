import hashlib
import uuid

from django.core.cache import cache

from .models import UserDevice


DEVICE_COOKIE_NAME = "mohtarifo_device_id"
DEVICE_CACHE_TTL = 300


def device_seed(request):
    # Safely try to get seed from cookies first
    seed = request.COOKIES.get(DEVICE_COOKIE_NAME)
    if seed:
        return seed

    # If not in cookies, try session with safety check
    session = getattr(request, "session", None)
    if session:
        seed = session.get("device_seed")
        if not seed:
            seed = uuid.uuid4().hex
            try:
                session["device_seed"] = seed
            except Exception:
                pass
        return seed
    
    # Fallback if both are missing
    return "anonymous_seed"



def device_fingerprint(request):
    seed = device_seed(request)
    raw = "|".join(
        [
            seed,
            request.META.get("HTTP_USER_AGENT", ""),
            request.META.get("HTTP_ACCEPT_LANGUAGE", ""),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def set_device_cookie(response, request):
    response.set_cookie(
        DEVICE_COOKIE_NAME,
        device_seed(request),
        max_age=60 * 60 * 24 * 365,
        httponly=True,
        samesite="Lax",
    )
    return response


def activate_user_device(request, user, response=None):
    fingerprint = device_fingerprint(request)
    previous_fingerprints = list(
        UserDevice.objects.filter(user=user, is_active=True)
        .exclude(fingerprint=fingerprint)
        .values_list("fingerprint", flat=True)
    )
    UserDevice.objects.filter(user=user).exclude(fingerprint=fingerprint).update(is_active=False)
    UserDevice.objects.update_or_create(
        user=user,
        fingerprint=fingerprint,
        defaults={
            "label": request.META.get("HTTP_USER_AGENT", "")[:110],
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
            "is_active": True,
        },
    )

    old_cache_keys = [device_cache_key(user.id, old_fingerprint) for old_fingerprint in previous_fingerprints]
    if old_cache_keys:
        cache.delete_many(old_cache_keys)
    cache.set(device_cache_key(user.id, fingerprint), True, DEVICE_CACHE_TTL)

    if response is not None:
        set_device_cookie(response, request)
    return fingerprint


def device_cache_key(user_id, fingerprint):
    return f"device_active_{user_id}_{fingerprint}"
