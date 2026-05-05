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
