import os
import django
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from billing.models import UserDevice

try:
    import user_agents
except ImportError:
    user_agents = None

devices = UserDevice.objects.all()
updated_count = 0

for device in devices:
    # Clean if the label is empty, or if it is a raw User-Agent string (starts with Mozilla)
    if not device.label or device.label.startswith("Mozilla"):
        ua_string = device.user_agent
        if not ua_string:
            continue
            
        os_name = "Device"
        browser_name = ""
        inferred_model = ""

        if user_agents:
            try:
                parsed_ua = user_agents.parse(ua_string)
                os_name = str(parsed_ua.os.family)
                browser_name = str(parsed_ua.browser.family)
                if parsed_ua.device.family and parsed_ua.device.family not in ("Other", "Generic Smartphone", "Generic Feature Phone"):
                    inferred_model = str(parsed_ua.device.family)
            except Exception:
                pass

        # Fallbacks if user_agents failed or is missing
        if os_name == "Device":
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

        # Regex fallback for Android if model is still not found
        if not inferred_model and "android" in os_name.lower():
            match = re.search(r'android\s+[^;]+;\s*([^;)]+)', ua_string, re.IGNORECASE)
            if match:
                model_candidate = match.group(1).strip()
                if "Build" in model_candidate:
                    model_candidate = model_candidate.split("Build")[0].strip()
                if model_candidate and model_candidate not in ("Mobile", "wv", "Tablet"):
                    inferred_model = model_candidate

        label = os_name
        if inferred_model:
            label = f"{os_name} ({inferred_model})"
        if browser_name:
            label = f"{label} - {browser_name}"

        device.label = label[:115]
        device.save()
        updated_count += 1

print(f"Successfully cleaned and updated {updated_count} device labels in the database!")
