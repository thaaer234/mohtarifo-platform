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

    # Parse device model and name from User-Agent and client hints cookie
    ua_string = request.META.get("HTTP_USER_AGENT", "")
    device_model = request.COOKIES.get("device_model_hint")
    if device_model:
        import urllib.parse
        try:
            device_model = urllib.parse.unquote(device_model).strip()
        except Exception:
            pass

    os_name = "Device"
    browser_name = ""
    inferred_model = ""

    # 1. Parse using python user_agents library
    try:
        import user_agents
        parsed_ua = user_agents.parse(ua_string)
        os_name = str(parsed_ua.os.family)
        browser_name = str(parsed_ua.browser.family)
        if parsed_ua.device.family and parsed_ua.device.family not in ("Other", "Generic Smartphone", "Generic Feature Phone"):
            inferred_model = str(parsed_ua.device.family)
    except Exception:
        # Fallback if user_agents package fails
        ua_lower = ua_string.lower()
        if "windows" in ua_lower:
            os_name = "Windows"
        elif "android" in ua_lower:
            os_name = "Android"
        elif "iphone" in ua_lower:
            os_name = "iPhone"
        elif "ipad" in ua_lower:
            os_name = "iPad"
        elif "macintosh" in ua_lower or "mac os" in ua_lower:
            os_name = "macOS"
        elif "linux" in ua_lower:
            os_name = "Linux"

        if "chrome" in ua_lower and "edg" not in ua_lower:
            browser_name = "Chrome"
        elif "edg" in ua_lower:
            browser_name = "Edge"
        elif "safari" in ua_lower and "chrome" not in ua_lower:
            browser_name = "Safari"
        elif "firefox" in ua_lower:
            browser_name = "Firefox"

    # 2. Regex fallback for Android if model is still not found
    if not inferred_model and "android" in os_name.lower():
        import re
        match = re.search(r'android\s+[^;]+;\s*([^;)]+)', ua_string, re.IGNORECASE)
        if match:
            model_candidate = match.group(1).strip()
            if "Build" in model_candidate:
                model_candidate = model_candidate.split("Build")[0].strip()
            if model_candidate and model_candidate not in ("Mobile", "wv", "Tablet"):
                inferred_model = model_candidate

    # 3. Build the final label
    model_name = device_model or inferred_model
    if model_name:
        label = f"{os_name} ({model_name})"
    else:
        label = os_name

    if browser_name:
        label = f"{label} - {browser_name}"

    UserDevice.objects.update_or_create(
        user=user,
        fingerprint=fingerprint,
        defaults={
            "label": label[:115],
            "user_agent": ua_string,
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
