from django.http import JsonResponse
from django.shortcuts import render


def _wants_json(request):
    accept = request.headers.get("accept", "")
    return request.path.startswith("/api/") or "application/json" in accept


def permission_denied(request, exception=None):
    if _wants_json(request):
        return JsonResponse({"detail": "Forbidden"}, status=403)
    return render(request, "403.html", status=403)


def page_not_found(request, exception=None):
    if _wants_json(request):
        return JsonResponse({"detail": "Not found"}, status=404)
    return render(request, "404.html", status=404)


def server_error(request):
    if _wants_json(request):
        return JsonResponse({"detail": "Server error"}, status=500)
    return render(request, "500.html", status=500)
