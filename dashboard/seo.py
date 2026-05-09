import json

from django.conf import settings
from django.templatetags.static import static
from django.utils.safestring import mark_safe


SITE_NAME = "محترفو التعليم"
CONTACT_WHATSAPP_LOCAL = "0984011372"
CONTACT_WHATSAPP_INTERNATIONAL = "963984011372"
CONTACT_INSTAGRAM = "education_pros1"
CONTACT_INSTAGRAM_URL = "https://www.instagram.com/education_pros1/"
CONTACT_FACEBOOK_URL = "https://www.facebook.com/bakaloria.syria/"
CONTACT_WHATSAPP_URL = f"https://wa.me/{CONTACT_WHATSAPP_INTERNATIONAL}"
DEFAULT_DESCRIPTION = (
    "منصة تعليمية سورية للمكثفات والدورات والامتحانات، تساعد طلاب الشهادة "
    "الثانوية والتاسع على الدراسة مع نخبة من الأساتذة."
)
DEFAULT_IMAGE_PATH = "dashboard/images/hero_student.png"

INDEXABLE_PATHS = {
    "/",
    "/landing/",
    "/shop/",
    "/about/",
    "/contact/",
    "/departments/",
    "/instructors/",
    "/faq/",
    "/privacy/",
    "/terms/",
    "/login/",
    "/register/",
}

NOINDEX_PREFIXES = (
    "/admin/",
    "/admin-dashboard/",
    "/api/",
    "/student/",
    "/instructor/",
    "/device-logged-out/",
    "/logout/",
)


def _site_url(request):
    if settings.SITE_URL:
        return settings.SITE_URL
    return request.build_absolute_uri("/").rstrip("/")


def _canonical_path(path):
    if path == "/":
        return "/landing/"
    return path if path.endswith("/") or "." in path.rsplit("/", 1)[-1] else f"{path}/"


def _is_indexable(path):
    if path in INDEXABLE_PATHS:
        return True
    if path.startswith("/course/"):
        return True
    if path.startswith("/instructor/") and path.endswith("/courses/"):
        return True
    if any(path.startswith(prefix) for prefix in NOINDEX_PREFIXES):
        return False
    return False


def _base_schema(site_url, image_url):
    return [
        {
            "@context": "https://schema.org",
            "@type": "EducationalOrganization",
            "name": SITE_NAME,
            "url": site_url,
            "logo": f"{site_url}{static('dashboard/icons/logo2.png')}",
            "image": image_url,
            "description": DEFAULT_DESCRIPTION,
            "sameAs": [CONTACT_INSTAGRAM_URL, CONTACT_FACEBOOK_URL],
        },
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": SITE_NAME,
            "url": site_url,
            "inLanguage": "ar-SY",
            "potentialAction": {
                "@type": "SearchAction",
                "target": f"{site_url}/search/?q={{search_term_string}}",
                "query-input": "required name=search_term_string",
            },
        },
        {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": "Site Navigation",
            "itemListElement": [
                {
                    "@type": "SiteNavigationElement",
                    "position": 1,
                    "name": "تسجيل الدخول",
                    "url": f"{site_url}/login/"
                },
                {
                    "@type": "SiteNavigationElement",
                    "position": 2,
                    "name": "إنشاء حساب جديد",
                    "url": f"{site_url}/register/"
                },
                {
                    "@type": "SiteNavigationElement",
                    "position": 3,
                    "name": "نخبة المدرسين",
                    "url": f"{site_url}/instructors/"
                }
            ]
        }
    ]


def seo_context(request):
    path = request.path or "/"
    site_url = _site_url(request)
    canonical_path = _canonical_path(path)
    image_url = f"{site_url}{static(DEFAULT_IMAGE_PATH)}"
    is_private_root = path == "/" and request.user.is_authenticated
    robots = "index,follow" if _is_indexable(path) and not is_private_root else "noindex,nofollow"
    return {
        "SEO_SITE_NAME": SITE_NAME,
        "SEO_DEFAULT_DESCRIPTION": DEFAULT_DESCRIPTION,
        "SEO_SITE_URL": site_url,
        "SEO_CANONICAL_URL": f"{site_url}{canonical_path}",
        "SEO_DEFAULT_IMAGE_URL": image_url,
        "SEO_ROBOTS": robots,
        "SEO_BASE_SCHEMA": mark_safe(json.dumps(_base_schema(site_url, image_url), ensure_ascii=False)),
        "CONTACT_WHATSAPP_LOCAL": CONTACT_WHATSAPP_LOCAL,
        "CONTACT_WHATSAPP_INTERNATIONAL": CONTACT_WHATSAPP_INTERNATIONAL,
        "CONTACT_WHATSAPP_URL": CONTACT_WHATSAPP_URL,
        "CONTACT_INSTAGRAM": CONTACT_INSTAGRAM,
        "CONTACT_INSTAGRAM_URL": CONTACT_INSTAGRAM_URL,
        "CONTACT_FACEBOOK_URL": CONTACT_FACEBOOK_URL,
    }
