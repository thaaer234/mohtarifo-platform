from django.conf import settings


SITE_NAME = "محترفو التعليم"
DEFAULT_DESCRIPTION = (
    "منصة تعليمية سورية للمكثفات والدورات والامتحانات، تساعد طلاب الشهادة "
    "الثانوية والتاسع على الدراسة مع نخبة من الأساتذة."
)

INDEXABLE_PATHS = {
    "/",
    "/landing/",
    "/about/",
    "/contact/",
    "/departments/",
    "/instructors/",
    "/faq/",
    "/privacy/",
    "/terms/",
}

NOINDEX_PREFIXES = (
    "/admin/",
    "/admin-dashboard/",
    "/api/",
    "/student/",
    "/instructor/",
    "/login/",
    "/register/",
    "/device-logged-out/",
    "/logout/",
)


def _site_url(request):
    if settings.SITE_URL:
        return settings.SITE_URL
    return request.build_absolute_uri("/").rstrip("/")


def _is_indexable(path):
    if path in INDEXABLE_PATHS:
        return True
    if path.startswith("/course/"):
        return True
    if path.startswith("/instructor/") and path.endswith("/courses/"):
        return True
    return False


def seo_context(request):
    path = request.path or "/"
    site_url = _site_url(request)
    canonical_path = path if path.endswith("/") or "." in path.rsplit("/", 1)[-1] else f"{path}/"
    return {
        "SEO_SITE_NAME": SITE_NAME,
        "SEO_DEFAULT_DESCRIPTION": DEFAULT_DESCRIPTION,
        "SEO_SITE_URL": site_url,
        "SEO_CANONICAL_URL": f"{site_url}{canonical_path}",
        "SEO_ROBOTS": "index,follow" if _is_indexable(path) else "noindex,nofollow",
    }
