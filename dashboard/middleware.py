from django.http import JsonResponse

from .security import has_suspicious_input


class SuspiciousInputMiddleware:
    SKIPPED_FIELD_PARTS = ("password", "csrfmiddlewaretoken", "token")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method in {"POST", "PUT", "PATCH"} and not getattr(request.user, "is_staff", False):
            for key, values in request.POST.lists():
                key_lower = key.lower()
                if any(part in key_lower for part in self.SKIPPED_FIELD_PARTS):
                    continue
                for value in values:
                    if has_suspicious_input(value):
                        if request.path.startswith("/api/"):
                            return JsonResponse({"detail": "Invalid input."}, status=400)
                        return JsonResponse({"detail": "Invalid input."}, status=400)
        return self.get_response(request)


class AntiFingerprintMiddleware:
    """
    Obfuscates backend framework signatures to blind scanners like Wappalyzer.
    Renames standard tokens like 'csrfmiddlewaretoken' dynamically.
    """
    FIELD_ALIAS = "auth_key_token" # Completely generic name

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. INTERCEPT INCOMING: Map the alias back to Django's standard name so internal logic continues working
        if request.method == "POST":
            if self.FIELD_ALIAS in request.POST:
                # Create mutable copy of POST QueryDict
                mutable_post = request.POST.copy()
                # Map the aliased token back to standard Django expected key
                mutable_post['csrfmiddlewaretoken'] = mutable_post.get(self.FIELD_ALIAS)
                # Assign back to request
                request.POST = mutable_post

        response = self.get_response(request)

        # 2. INTERCEPT OUTGOING: In the returned HTML, rewrite standard name to our stealth alias
        if response.status_code == 200 and "text/html" in response.get("Content-Type", ""):
            try:
                content = response.content.decode('utf-8')
                # Replace occurrences inside HTML form inputs: name="csrfmiddlewaretoken"
                if 'name="csrfmiddlewaretoken"' in content:
                    new_content = content.replace('name="csrfmiddlewaretoken"', f'name="{self.FIELD_ALIAS}"')
                    response.content = new_content.encode('utf-8')
                    # Update header if size changed
                    if response.has_header('Content-Length'):
                        response['Content-Length'] = str(len(response.content))
            except Exception:
                pass # Fail safe to original response if decoding errors occur

        return response
