from functools import wraps
from collections import defaultdict
import secrets
import base64
import os
from io import BytesIO
import qrcode
from xml.sax.saxutils import escape

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core import management
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, transaction
from django.db.models import Avg, Count, Sum
from django.core import signing
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.core.paginator import Paginator
from openpyxl import Workbook

from accounts.models import InstructorProfile, StudentProfile
from analytics.models import TopicPerformance
from billing.devices import activate_user_device, device_fingerprint, device_seed, set_device_cookie
from billing.models import AccessCode, AccessCodeBatch, AccessCodePrintLog, AccessGrant, CoursePackage, Institute, Payment, SalesCenter, Subscription, UserDevice
from billing.services import create_codes_for_batch, create_codes_from_upload, unique_code
from exams.models import Attempt, Exam, Question
from learning.models import Course, CourseProgress, Lesson, LessonAttendance, LessonProgress, OnlineLessonSession

from .forms import (
    CatalogSectionForm,
    CourseCardMediaForm,
    CourseCodeBatchForm,
    CourseCodeSaleForm,
    CourseCreateForm,
    CourseEditForm,
    CourseLessonUploadForm,
    CourseUnitQuickForm,
    CoursePackageForm,
    CourseStudentImportForm,
    PackageCodeGenerateForm,
    PackageCodeBatchForm,
    PackageCodeSaleForm,
    InstructorAddForm,
    InstructorEditForm,
    InstituteForm,
    PartnerBatchForm,
    PartnerInstituteImportForm,
    RedeemCodeForm,
    SalesCenterForm,
    StudentRegistrationForm,
)
from .models import CatalogSection, StudentNotification
from .seo import _site_url
from .security import sanitize_plain_text, validate_syrian_mobile


def _is_admin_user(user):
    return user.is_authenticated and user.is_active and user.is_superuser


def _is_active_instructor(user):
    profile = getattr(user, "instructor_profile", None)
    return user.is_authenticated and user.is_active and profile is not None and profile.status == "active"


def _role_required(test_func, login_url="dashboard:login"):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"{reverse(login_url)}?next={request.get_full_path()}")
            if not test_func(request.user):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


admin_required = _role_required(_is_admin_user)
instructor_required = _role_required(_is_active_instructor)


def home(request):
    if not request.user.is_authenticated:
        return redirect("dashboard:landing")
    if _is_admin_user(request.user):
        return admin_dashboard(request)
    if _is_active_instructor(request.user):
        return instructor_dashboard(request)
    return student_dashboard(request)


def landing_page(request):
    instructor_id = request.GET.get("instructor")
    catalog_tabs = _catalog_tabs()
    requested_kind = request.GET.get("kind")
    requested_track = request.GET.get("track")
    selected_tab = None
    if requested_kind and requested_track:
        selected_tab = next(
            (tab for tab in catalog_tabs if tab["kind"] == requested_kind and tab["track"] == requested_track),
            None,
        )
    if not selected_tab and catalog_tabs:
        selected_tab = catalog_tabs[0]
    selected_kind = selected_tab["kind"] if selected_tab else ""
    selected_track = selected_tab["track"] if selected_tab else ""
    
    courses_query = Course.objects.filter(status="published")
    
    instructor_name = None
    if instructor_id:
        courses_query = courses_query.filter(instructor_id=instructor_id)
        instructor = User.objects.filter(id=instructor_id).first()
        if instructor:
            instructor_name = instructor.get_full_name() or instructor.username
    elif selected_tab:
        if selected_track in {"scientific", "literary"}:
            courses_query = courses_query.filter(kind=selected_kind).filter(
                models.Q(academic_track=selected_track) | models.Q(academic_track="general")
            )
        else:
            courses_query = courses_query.filter(kind=selected_kind, academic_track=selected_track)
    else:
        courses_query = courses_query.none()
        
    courses = (
        courses_query
        .select_related("subject", "instructor", "instructor__instructor_profile")
        .annotate(lessons_total=Count("units__lessons", distinct=True))
        .order_by("subject__name", "title")
    )
    
    return render(
        request,
        "dashboard/landing.html",
        {
            "courses": courses,
            "selected_kind": selected_kind,
            "selected_track": selected_track,
            "catalog_tabs": catalog_tabs,
            "filtered_instructor_name": instructor_name,
        },
    )


def shop_page(request):
    selected_kind = request.GET.get("kind", "")
    selected_track = request.GET.get("track", "")
    courses_query = Course.objects.filter(status="published").select_related("subject", "instructor", "instructor__instructor_profile")
    if selected_kind:
        courses_query = courses_query.filter(kind=selected_kind)
    if selected_track:
        if selected_track in {"scientific", "literary"}:
            courses_query = courses_query.filter(models.Q(academic_track=selected_track) | models.Q(academic_track="general"))
        else:
            courses_query = courses_query.filter(academic_track=selected_track)
    courses = (
        courses_query
        .annotate(
            lessons_total=Count("units__lessons", distinct=True),
            sales_centers_total=Count("access_codes__sales_center", distinct=True),
        )
        .order_by("academic_track", "kind", "subject__name", "title")
    )
    sales_centers = SalesCenter.objects.filter(is_active=True).select_related("institute").order_by("name")
    return render(
        request,
        "dashboard/shop.html",
        {
            "courses": courses,
            "sales_centers": sales_centers,
            "catalog_tabs": _catalog_tabs(),
            "selected_kind": selected_kind,
            "selected_track": selected_track,
        },
    )


def device_logged_out_page(request):
    return render(request, "dashboard/device_logged_out.html")


def public_course_detail(request, course_id):
    course = get_object_or_404(
        Course.objects.filter(status="published")
        .select_related("subject", "instructor", "instructor__instructor_profile")
        .prefetch_related("units__lessons"),
        id=course_id,
    )
    first_lesson = (
        Lesson.objects.filter(unit__course=course, is_free_preview=True, video_url__gt="")
        .select_related("unit", "unit__course")
        .order_by("unit__sort_order", "sort_order", "id")
        .first()
    )
    has_access = False
    if request.user.is_authenticated:
        has_access = _active_access_grants(request.user).filter(course=course).exists()
    sales_centers = (
        SalesCenter.objects.filter(access_codes__course=course, is_active=True)
        .select_related("institute")
        .distinct()
        .order_by("name")
    )
    return render(
        request,
        "dashboard/public_course_detail.html",
        {
            "course": course,
            "first_lesson": first_lesson,
            "has_access": has_access,
            "sales_centers": sales_centers,
            "video_embed_url": _video_embed_url(first_lesson.video_url) if first_lesson and (has_access or first_lesson.is_free_preview) else "",
        },
    )


def thaaer_review(request):
    courses = (
        Course.objects.filter(status="published")
        .select_related("subject", "instructor", "instructor__instructor_profile")
        .annotate(lessons_total=Count("units__lessons", distinct=True))
        .order_by("subject__name", "title")[:8]
    )
    sample_course = courses[0] if courses else None
    sample_lessons = []
    if sample_course:
        sample_lessons = Lesson.objects.filter(unit__course=sample_course).select_related("unit").order_by("unit__sort_order", "sort_order")[:12]
    context = {
        "courses": courses,
        "sample_course": sample_course,
        "sample_lessons": sample_lessons,
        "stats": {
            "courses": Course.objects.count(),
            "lessons": Lesson.objects.count(),
            "codes": AccessCode.objects.count(),
            "batches": AccessCodeBatch.objects.count(),
            "institutes": Institute.objects.count(),
            "sales_centers": SalesCenter.objects.count(),
            "students": User.objects.filter(is_staff=False).count(),
            "devices": UserDevice.objects.count(),
        },
        "screens": [
            ("الكتالوج العام", "/landing/", "كروت المكثفات قبل تسجيل الدخول."),
            ("صفحة المكثفة العامة", f"/course/{sample_course.id}/" if sample_course else "/course/<id>/", "معلومات المكثفة، الدروس المقفلة، ومعاينة الفيديو."),
            ("تسجيل الدخول", "/login/", "دخول الطالب برقم الهاتف وكلمة المرور."),
            ("إنشاء حساب", "/register/", "اسم الطالب، رقم الهاتف، الفرع، المحافظة."),
            ("لوحة الطالب", "/student/", "تفعيل كود، عرض المكثفات المفتوحة، الفيديوهات، الإشعارات."),
            ("صفحة مكثفة الطالب", f"/student/courses/{sample_course.id}/" if sample_course else "/student/courses/<id>/", "جلسات الفيديو المتاحة بعد التفعيل."),
            ("مشغل الجلسة", "/student/lessons/<id>/", "مشاهدة الفيديو وتسجيل حضور الجلسة."),
            ("لوحة الإدارة الداخلية", "/admin-dashboard/", "ملخص الطلاب والمكثفات والأكواد."),
            ("Django Admin", "/admin/", "إدارة المواد، الدروس، المعاهد، مراكز البيع، ودفعات الأكواد."),
        ],
    }
    return render(request, "dashboard/thaaer.html", context)


def pwa_manifest(_request):
    return JsonResponse(
        {
            "name": "محترفو التعليم",
            "short_name": "محترفون",
            "description": "منصة تعليمية عربية للمكثفات والدروس والامتحانات.",
            "start_url": "/landing/",
            "scope": "/",
            "display": "standalone",
            "orientation": "portrait-primary",
            "dir": "rtl",
            "lang": "ar",
            "background_color": "#f5f5f5",
            "theme_color": "#8f6f3e",
            "categories": ["education", "productivity"],
            "icons": [
                {
                    "src": "/static/dashboard/icons/icon.svg",
                    "sizes": "any",
                    "type": "image/svg+xml",
                    "purpose": "any maskable",
                },
                {
                    "src": "/static/dashboard/icons/icon-192.png",
                    "sizes": "192x192",
                    "type": "image/png",
                    "purpose": "any",
                },
                {
                    "src": "/static/dashboard/icons/icon-512.png",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "any maskable",
                },
            ],
        }
    )


def service_worker(_request):
    script = """
const CACHE_NAME = "mohtarifo-platform-v2";
const APP_SHELL = [
  "/landing/",
  "/login/",
  "/register/",
  "/static/dashboard/styles.css",
  "/static/dashboard/icons/icon.svg",
  "/static/dashboard/icons/icon-192.png",
  "/static/dashboard/icons/icon-512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") {
    return;
  }

  const url = new URL(event.request.url);
  const isSameOrigin = url.origin === self.location.origin;
  const isSensitiveRoute = isSameOrigin && (
    url.pathname.startsWith("/student/") ||
    url.pathname.startsWith("/api/") ||
    url.pathname === "/device-logged-out/" ||
    url.pathname === "/login/" ||
    url.pathname === "/logout/"
  );

  if (isSensitiveRoute || event.request.mode === "navigate") {
    event.respondWith(fetch(event.request));
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
        return response;
      })
      .catch(() => caches.match(event.request).then((cached) => cached || caches.match("/landing/")))
  );
});
"""
    response = HttpResponse(script, content_type="application/javascript")
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


def robots_txt(request):
    site_url = _site_url(request)
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        f"Disallow: /{settings.ADMIN_URL}",
        "Disallow: /admin-dashboard/",
        "Disallow: /api/",
        "Disallow: /student/",
        "Disallow: /login/",
        "Disallow: /register/",
        "Disallow: /device-logged-out/",
        f"Sitemap: {site_url}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")


def sitemap_xml(request):
    site_url = _site_url(request)
    urls = [
        (reverse("dashboard:landing"), "daily", "1.0"),
        (reverse("dashboard:departments_list"), "weekly", "0.8"),
        (reverse("dashboard:instructors_list"), "weekly", "0.8"),
        (reverse("dashboard:about"), "monthly", "0.6"),
        (reverse("dashboard:contact"), "monthly", "0.6"),
        (reverse("dashboard:faq"), "monthly", "0.6"),
        (reverse("dashboard:privacy"), "yearly", "0.3"),
        (reverse("dashboard:terms"), "yearly", "0.3"),
    ]

    courses = Course.objects.filter(status="published").only("id", "updated_at").order_by("-updated_at")
    for course in courses:
        urls.append((reverse("dashboard:public_course_detail", args=[course.id]), "weekly", "0.9", course.updated_at))

    instructors = (
        User.objects.filter(courses__status="published")
        .distinct()
        .only("id")
        .order_by("id")
    )
    for instructor in instructors:
        urls.append((reverse("dashboard:instructor_courses", args=[instructor.id]), "weekly", "0.7"))

    items = []
    for entry in urls:
        path, changefreq, priority, *lastmod = entry
        lastmod_tag = ""
        if lastmod and lastmod[0]:
            lastmod_tag = f"<lastmod>{lastmod[0].date().isoformat()}</lastmod>"
        items.append(
            "<url>"
            f"<loc>{escape(site_url + path)}</loc>"
            f"{lastmod_tag}"
            f"<changefreq>{changefreq}</changefreq>"
            f"<priority>{priority}</priority>"
            "</url>"
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(items)
        + "</urlset>"
    )
    return HttpResponse(xml, content_type="application/xml; charset=utf-8")


def _client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _login_attempt_key(request):
    username = (request.POST.get("username") or "").strip().lower()
    return f"login_attempts:{_client_ip(request)}:{username}"


def _login_is_rate_limited(request):
    return int(cache.get(_login_attempt_key(request), 0)) >= settings.LOGIN_RATE_LIMIT_ATTEMPTS


def _record_failed_login(request):
    key = _login_attempt_key(request)
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, settings.LOGIN_RATE_LIMIT_TIMEOUT_SECONDS)
    else:
        cache.touch(key, settings.LOGIN_RATE_LIMIT_TIMEOUT_SECONDS)


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and _login_is_rate_limited(request):
        messages.error(request, "Too many failed login attempts. Please try again later.")
        return render(request, "registration/login.html", {"form": form}, status=429)

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        cache.delete(_login_attempt_key(request))
        response = redirect("dashboard:home")
        if not user.is_staff:
            activate_user_device(request, user, response)
        return response
    if request.method == "POST":
        _record_failed_login(request)

    return render(request, "registration/login.html", {"form": form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")

    form = StudentRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        StudentProfile.objects.update_or_create(
            user=user,
            defaults={
                "grade": "الثالث الثانوي",
                "track": form.cleaned_data["track"],
                "governorate": form.cleaned_data["governorate"],
                "phone": form.cleaned_data["username"],
            },
        )
        login(request, user)
        messages.success(request, "تم إنشاء حسابك بنجاح. يمكنك الآن إضافة كود المادة.")
        response = redirect("dashboard:student_dashboard")
        activate_user_device(request, user, response)
        return response

    return render(request, "registration/register.html", {"form": form})


@admin_required
def admin_dashboard(request):
    courses = (
        Course.objects.select_related("subject", "instructor", "instructor__instructor_profile")
        .annotate(
            lessons_total=Count("units__lessons", distinct=True),
            codes_total=Count("access_codes", distinct=True),
            grants_total=Count("access_grants", distinct=True),
        )
        .order_by("-published_at", "title")[:12]
    )
    recent_batches = AccessCodeBatch.objects.select_related("course", "institute", "sales_center").order_by("-created_at")[:8]
    sales_centers = SalesCenter.objects.select_related("institute").filter(is_active=True).order_by("name")[:8]
    context = {
        "instructor_profile": getattr(request.user, 'instructor_profile', None),
        "students_count": User.objects.filter(is_staff=False).count(),
        "courses_count": Course.objects.count(),
        "lessons_count": Lesson.objects.count(),
        "questions_count": Question.objects.count(),
        "exams_count": Exam.objects.count(),
        "attempts_count": Attempt.objects.count(),
        "codes_count": AccessCode.objects.count(),
        "redeemed_codes_count": AccessCode.objects.filter(redeemed_count__gt=0).count(),
        "sold_codes_count": AccessCode.objects.filter(sale_status="sold").count(),
        "free_codes_count": AccessCode.objects.filter(is_free_code=True).count(),
        "institutes_count": Institute.objects.count(),
        "sales_centers_count": SalesCenter.objects.count(),
        "active_subscriptions": Subscription.objects.filter(status="active").count(),
        "paid_payments": Payment.objects.filter(status="paid").count(),
        "managed_courses": courses,
        "courses": courses,
        "recent_batches": recent_batches,
        "sales_centers": sales_centers,
    }
    return render(request, "dashboard/admin_dashboard.html", context)


@admin_required
def admin_course_create(request):
    initial = {}
    if request.method == "GET":
        initial["kind"] = request.GET.get("kind") or None
        initial["academic_track"] = request.GET.get("track") or None
        initial = {key: value for key, value in initial.items() if value}
    form = CourseCreateForm(request.POST or None, request.FILES or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        course = form.save()
        messages.success(request, "تم إنشاء المحتوى. الآن كمل الجلسات والأكواد والتفاصيل من لوحة الدورة.")
        return redirect("dashboard:admin_course_control", course_id=course.id)
    selected_tab = None
    for tab in _catalog_tabs():
        if tab["kind"] == initial.get("kind") and tab["track"] == initial.get("academic_track"):
            selected_tab = tab
            break
    return render(request, "dashboard/admin_course_create.html", {"form": form, "selected_tab": selected_tab})


@admin_required
def admin_catalog_manager(request):
    if request.method == "POST":
        action = request.POST.get("action")
        section_id = request.POST.get("section_id")
        section = CatalogSection.objects.filter(id=section_id).first() if section_id else None
        if action in {"create_section", "update_section"}:
            form = CatalogSectionForm(
                request.POST,
                instance=section,
                prefix="new" if action == "create_section" else "section",
            )
            if form.is_valid():
                saved = form.save()
                messages.success(request, f"تم حفظ فلتر {saved.label}.")
                return redirect(f"{reverse('dashboard:admin_catalog_manager')}?kind={saved.kind}&track={saved.track}")
        elif action == "delete_section" and section:
            courses_count = Course.objects.filter(kind=section.kind, academic_track=section.track).count()
            label = section.label
            if courses_count:
                section.is_visible = False
                section.save(update_fields=["is_visible", "updated_at"])
                messages.warning(request, f"تم إخفاء فلتر {label} من واجهة الطالب لأنه يحتوي على دورات.")
            else:
                section.delete()
                messages.success(request, f"تم حذف فلتر {label}.")
            return redirect("dashboard:admin_catalog_manager")

    base_tabs = _catalog_tabs(include_hidden=True)
    selected_kind = request.GET.get("kind") or (base_tabs[0]["kind"] if base_tabs else "")
    selected_track = request.GET.get("track") or (base_tabs[0]["track"] if base_tabs else "")
    tabs = []
    for tab in base_tabs:
        if tab["track"] in {"scientific", "literary"}:
            courses_qs = Course.objects.filter(kind=tab["kind"]).filter(
                models.Q(academic_track=tab["track"]) | models.Q(academic_track="general")
            )
        else:
            courses_qs = Course.objects.filter(kind=tab["kind"], academic_track=tab["track"])
            
        tab = {
            **tab,
            "courses_count": courses_qs.count(),
            "published_count": courses_qs.filter(status="published").count(),
            "draft_count": courses_qs.filter(status="draft").count(),
            "is_active": tab["kind"] == selected_kind and tab["track"] == selected_track,
        }
        tabs.append(tab)

    selected_tab = next((tab for tab in tabs if tab["is_active"]), tabs[0] if tabs else None)
    selected_section = CatalogSection.objects.filter(id=selected_tab.get("id")).first() if selected_tab else None
    section_form = CatalogSectionForm(instance=selected_section, prefix="section")
    new_section_form = CatalogSectionForm(prefix="new", initial={"sort_order": (CatalogSection.objects.count() + 1) * 10})
    courses = Course.objects.none()
    if selected_tab:
        if selected_tab["track"] in {"scientific", "literary"}:
            courses = (
                Course.objects.filter(kind=selected_tab["kind"]).filter(
                    models.Q(academic_track=selected_tab["track"]) | models.Q(academic_track="general")
                )
                .select_related("subject", "instructor", "instructor__instructor_profile")
                .annotate(
                    lessons_total=Count("units__lessons", distinct=True),
                    codes_total=Count("access_codes", distinct=True),
                    students_total=Count("access_grants", distinct=True),
                )
                .order_by("subject__name", "title")
            )
        else:
            courses = (
                Course.objects.filter(kind=selected_tab["kind"], academic_track=selected_tab["track"])
                .select_related("subject", "instructor", "instructor__instructor_profile")
                .annotate(
                    lessons_total=Count("units__lessons", distinct=True),
                    codes_total=Count("access_codes", distinct=True),
                    students_total=Count("access_grants", distinct=True),
                )
                .order_by("subject__name", "title")
            )
    return render(
        request,
        "dashboard/admin_catalog_manager.html",
        {
            "catalog_tabs": tabs,
            "selected_tab": selected_tab,
            "section_form": section_form,
            "new_section_form": new_section_form,
            "courses": courses,
        },
    )


@admin_required
def admin_partners(request):
    institute_form = InstituteForm(prefix="institute")
    center_form = SalesCenterForm(prefix="center")
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create_institute":
            institute_form = InstituteForm(request.POST, prefix="institute")
            if institute_form.is_valid():
                institute_form.save()
                messages.success(request, "تم إنشاء المعهد.")
                return redirect("dashboard:admin_partners")
        elif action == "create_center":
            center_form = SalesCenterForm(request.POST, prefix="center")
            if center_form.is_valid():
                center_form.save()
                messages.success(request, "تم إنشاء مركز البيع.")
                return redirect("dashboard:admin_partners")

    institutes = (
        Institute.objects.annotate(
            centers_total=Count("sales_centers", distinct=True),
            codes_total=Count("access_codes", distinct=True),
            activated_total=Count("access_codes__grants", distinct=True),
        )
        .order_by("name")
    )
    centers = (
        SalesCenter.objects.select_related("institute")
        .annotate(codes_total=Count("access_codes", distinct=True), activated_total=Count("access_codes__grants", distinct=True))
        .order_by("name")
    )
    return render(
        request,
        "dashboard/admin_partners.html",
        {
            "institute_form": institute_form,
            "center_form": center_form,
            "institutes": institutes,
            "centers": centers,
        },
    )


@admin_required
def admin_students(request):
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all')
    
    students_query = User.objects.filter(is_staff=False).select_related('student_profile')
    
    if query:
        students_query = students_query.filter(
            models.Q(username__icontains=query) |
            models.Q(first_name__icontains=query) |
            models.Q(last_name__icontains=query) |
            models.Q(student_profile__phone__icontains=query)
        )
        
    if status_filter == 'active':
        students_query = students_query.filter(is_active=True)
    elif status_filter == 'inactive':
        students_query = students_query.filter(is_active=False)
        
    students_query = students_query.annotate(
        courses_total=Count("access_grants", distinct=True), 
        devices_total=Count("devices", distinct=True)
    ).order_by("-date_joined")
    
    # Pagination
    paginator = Paginator(students_query, 50)
    page_number = request.GET.get('page')
    students = paginator.get_page(page_number)
    
    # Stats
    total_students = User.objects.filter(is_staff=False).count()
    active_students = User.objects.filter(is_staff=False, is_active=True).count()
    new_students_today = User.objects.filter(is_staff=False, date_joined__date=timezone.now().date()).count()
    total_devices = UserDevice.objects.count()

    grants = AccessGrant.objects.select_related("user", "course", "access_code").order_by("-created_at")[:20]
    devices = UserDevice.objects.select_related("user").order_by("-last_seen_at")[:20]

    # Governorate statistics
    gov_stats = []
    from accounts.models import StudentProfile
    profiles_grouped = StudentProfile.objects.values('governorate').annotate(count=Count('id')).order_by('-count')
    for p in profiles_grouped:
        gov_name = p['governorate'].strip() if p['governorate'] else ""
        if not gov_name:
            gov_name = "غير محدد"
        # Combine if "غير محدد" appears multiple times due to spaces
        existing = next((item for item in gov_stats if item['name'] == gov_name), None)
        if existing:
            existing['count'] += p['count']
        else:
            gov_stats.append({
                'name': gov_name,
                'count': p['count']
            })
    # Sort again by count descending
    gov_stats.sort(key=lambda x: x['count'], reverse=True)

    return render(
        request,
        "dashboard/admin_students.html",
        {
            "students": students,
            "grants": grants,
            "devices": devices,
            "query": query,
            "status_filter": status_filter,
            "stats": {
                "total": total_students,
                "active": active_students,
                "new_today": new_students_today,
                "devices": total_devices,
            }
        },
    )


@admin_required
def admin_institute_profile(request, institute_id):
    institute = get_object_or_404(Institute, id=institute_id)
    import_form = PartnerInstituteImportForm(prefix="import")
    edit_form = InstituteForm(instance=institute, prefix="edit")
    
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "import_institute_students":
            import_form = PartnerInstituteImportForm(request.POST, request.FILES, prefix="import")
            if import_form.is_valid():
                batch = AccessCodeBatch.objects.create(
                    name=import_form.cleaned_data["batch_name"],
                    course=import_form.cleaned_data["course"],
                    institute=institute,
                    code_prefix=import_form.cleaned_data["code_prefix"],
                    notes=f"طلاب مجانيون من {institute.name}",
                )
                created = create_codes_from_upload(batch, import_form.cleaned_data["file"], free_codes=True)
                messages.success(request, f"تم رفع {created} طالب وإنشاء أكواد مجانية مرتبطة بالمعهد.")
                return redirect("dashboard:admin_institute_profile", institute_id=institute.id)
        
        elif action == "edit_institute":
            edit_form = InstituteForm(request.POST, request.FILES, instance=institute, prefix="edit")
            if edit_form.is_valid():
                edit_form.save()
                messages.success(request, "تم تحديث بيانات المعهد والشعار بنجاح.")
                return redirect("dashboard:admin_institute_profile", institute_id=institute.id)

    batches = (
        AccessCodeBatch.objects.filter(institute=institute)
        .select_related("course")
        .annotate(codes_total=Count("codes", distinct=True), activated_total=Count("codes__grants", distinct=True))
        .order_by("-created_at")
    )
    return render(
        request,
        "dashboard/admin_institute_profile.html",
        {"institute": institute, "import_form": import_form, "edit_form": edit_form, "batches": batches},
    )


@admin_required
def admin_sales_center_profile(request, center_id):
    center = get_object_or_404(SalesCenter.objects.select_related("institute"), id=center_id)
    batch_form = PartnerBatchForm(prefix="batch")
    edit_form = SalesCenterForm(instance=center, prefix="edit")
    
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create_center_codes":
            batch_form = PartnerBatchForm(request.POST, prefix="batch")
            if batch_form.is_valid():
                batch = AccessCodeBatch.objects.create(
                    name=batch_form.cleaned_data["name"],
                    course=batch_form.cleaned_data["course"],
                    sales_center=center,
                    allocated_count=batch_form.cleaned_data["quantity"],
                    code_prefix=batch_form.cleaned_data["code_prefix"],
                    notes=batch_form.cleaned_data["notes"],
                )
                created = create_codes_for_batch(batch, batch_form.cleaned_data["quantity"], free_codes=False)
                messages.success(request, f"تم إنشاء {created} كود لمركز البيع.")
                return redirect("dashboard:admin_sales_center_profile", center_id=center.id)
        
        elif action == "edit_center":
            edit_form = SalesCenterForm(request.POST, instance=center, prefix="edit")
            if edit_form.is_valid():
                edit_form.save()
                messages.success(request, "تم تحديث بيانات مركز البيع بنجاح.")
                return redirect("dashboard:admin_sales_center_profile", center_id=center.id)

    batches = (
        AccessCodeBatch.objects.filter(sales_center=center)
        .select_related("course")
        .annotate(codes_total=Count("codes", distinct=True), sold_total=Count("codes", filter=models.Q(codes__sale_status="sold"), distinct=True), activated_total=Count("codes__grants", distinct=True))
        .order_by("-created_at")
    )
    return render(
        request,
        "dashboard/admin_sales_center_profile.html",
        {"center": center, "batch_form": batch_form, "edit_form": edit_form, "batches": batches},
    )


@admin_required
def admin_print_batch_cards(request, batch_id):
    """توليد صفحة قابلة للطباعة تحتوي على كروت الأكواد (وش وقفا)"""
    batch = get_object_or_404(
        AccessCodeBatch.objects.select_related("course", "package", "institute", "sales_center"), 
        id=batch_id
    )
    codes = batch.codes.all().order_by("created_at")
    target_title = batch.target_title
    card_course_title = (target_title or "").split(" - ", 1)[0].strip() or target_title
    
    # تحضير رابط المنصة لـ QR الخلفية
    platform_url = request.build_absolute_uri("/")
    platform_qr = _generate_qr_base64(platform_url)
    
    # تحضير الكروت مع الـ QR الخاص بكل كود
    cards = []
    for c in codes:
        cards.append({
            "obj": c,
            "qr": _generate_qr_base64(c.code)
        })
    AccessCodePrintLog.objects.create(
        batch=batch,
        printed_by=request.user if request.user.is_authenticated else None,
        cards_count=len(cards),
        notes="فتح صفحة طباعة الكروت",
    )
    
    # تقسيم الكروت لمجموعات (كل مجموعة 3 كروت لصفحة A4 واحدة)
    grouped_cards = [cards[i:i + 3] for i in range(0, len(cards), 3)]
        
    return render(request, "dashboard/admin_print_batch_cards.html", {
        "batch": batch,
        "card_course_title": card_course_title,
        "grouped_cards": grouped_cards,
        "platform_qr": platform_qr,
        "platform_name": "تركيز", # يمكن تغييرها حسب الرغبة
        "print_date": timezone.now(),
    })


def _generate_qr_base64(data):
    """دالة مساعدة لتوليد QR Code وتحويله لـ Base64 لدمجه في HTML"""
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()


@admin_required
def download_batch_codes(request, batch_id):
    batch = get_object_or_404(AccessCodeBatch.objects.select_related("course", "package", "institute", "sales_center"), id=batch_id)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "codes"
    sheet.append(["code", "target", "type", "partner", "status", "student_name", "student_phone", "activated"])
    partner = batch.institute.name if batch.institute else batch.sales_center.name if batch.sales_center else ""
    for code in batch.codes.order_by("created_at"):
        sheet.append([
            code.code,
            batch.target_title,
            code.get_access_type_display(),
            partner,
            code.sale_status,
            code.assigned_student_name,
            code.assigned_student_phone,
            "yes" if code.redeemed_count else "no",
        ])
    for column in ["A", "B", "C", "D", "E", "F", "G", "H"]:
        sheet.column_dimensions[column].width = 24
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="codes-batch-{batch.id}.xlsx"'
    return response


@admin_required
def download_student_import_template(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "students"
    headers = ["student_name", "student_phone", "notes"]
    sheet.append(headers)
    sheet.append(["مثال: أحمد محمد", "09xxxxxxxx", "طلاب معهد اليمان"])
    for cell in sheet[1]:
        cell.style = "Headline 3"
    sheet.column_dimensions["A"].width = 28
    sheet.column_dimensions["B"].width = 18
    sheet.column_dimensions["C"].width = 34
    info = workbook.create_sheet("instructions")
    info.append(["استخدم الأعمدة كما هي بدون تغيير أسماء العناوين."])
    info.append(["student_name", "اسم الطالب كما سيظهر في السجل"])
    info.append(["student_phone", "رقم الطالب ويستخدم لربط الكود بحسابه"])
    info.append(["notes", "ملاحظات اختيارية"])
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    filename = f"students-template-course-{course.id}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@admin_required
def admin_export_students(request):
    """تصدير كل بيانات الطلاب إلى ملف Excel للتواصل أو التسويق"""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Students"
    sheet.append(["الاسم الكامل", "اسم المستخدم/الهاتف", "الفرع", "المحافظة", "تاريخ الانضمام", "آخر نشاط", "XP", "المستوى"])
    
    students = User.objects.filter(is_staff=False).select_related("student_profile").order_by("-date_joined")
    
    for s in students:
        profile = getattr(s, 'student_profile', None)
        sheet.append([
            s.get_full_name(),
            s.username,
            profile.track if profile else "",
            profile.governorate if profile else "",
            s.date_joined.strftime("%Y-%m-%d"),
            profile.last_activity_date.strftime("%Y-%m-%d") if profile and profile.last_activity_date else "",
            profile.xp if profile else 0,
            profile.level if profile else 1,
        ])
    
    for column in ["A", "B", "C", "D", "E", "F", "G", "H"]:
        sheet.column_dimensions[column].width = 20
        
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="all-students-{timezone.now().strftime("%Y-%m-%d")}.xlsx"'
    return response

@admin_required
def admin_instructor_add(request):
    form = InstructorAddForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            messages.error(request, "اسم المستخدم / الهاتف موجود مسبقاً.")
        else:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    password=form.cleaned_data["password"],
                    first_name=form.cleaned_data["first_name"],
                    last_name=form.cleaned_data["last_name"],
                    is_staff=True,
                )
                InstructorProfile.objects.update_or_create(
                    user=user,
                    defaults={
                        "specialty": form.cleaned_data["specialty"],
                        "bio": form.cleaned_data["bio"],
                        "avatar": form.cleaned_data["photo"]
                    }
                )
                messages.success(request, f"تم إضافة المدرس {user.get_full_name()} بنجاح.")
                return redirect("dashboard:admin_instructors")
                
    return render(request, "dashboard/admin_instructor_add.html", {"form": form})


@admin_required
def admin_instructors(request):
    search = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    instructors = (
        User.objects.filter(instructor_profile__isnull=False)
        .select_related("instructor_profile")
        .annotate(courses_total=Count("courses", distinct=True), students_total=Count("courses__access_grants__user", distinct=True))
        .order_by("first_name", "last_name", "username")
    )
    if search:
        instructors = instructors.filter(
            models.Q(first_name__icontains=search)
            | models.Q(last_name__icontains=search)
            | models.Q(username__icontains=search)
            | models.Q(instructor_profile__specialty__icontains=search)
        )
    if status:
        instructors = instructors.filter(instructor_profile__status=status)
    stats = {
        "total": User.objects.filter(instructor_profile__isnull=False).count(),
        "active": User.objects.filter(instructor_profile__status="active").count(),
        "pending": User.objects.filter(instructor_profile__status="pending").count(),
        "suspended": User.objects.filter(instructor_profile__status="suspended").count(),
    }
    return render(
        request,
        "dashboard/admin_instructors.html",
        {
            "instructors": instructors,
            "stats": stats,
            "search": search,
            "status": status,
            "status_choices": InstructorProfile.STATUS_CHOICES,
        },
    )


@admin_required
def admin_instructor_edit(request, instructor_id):
    instructor = get_object_or_404(
        User.objects.select_related("instructor_profile").annotate(
            courses_total=Count("courses", distinct=True),
            students_total=Count("courses__access_grants__user", distinct=True),
        ),
        id=instructor_id,
        instructor_profile__isnull=False,
    )
    form = InstructorEditForm(request.POST or None, request.FILES or None, instructor=instructor)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم تحديث بيانات المدرس بنجاح.")
        return redirect("dashboard:admin_instructors")
    courses = Course.objects.filter(instructor=instructor).select_related("subject").order_by("-created_at")[:12]
    return render(
        request,
        "dashboard/admin_instructor_edit.html",
        {
            "form": form,
            "instructor": instructor,
            "courses": courses,
        },
    )


@admin_required
def admin_system_backup(request):
    if not settings.ENABLE_ADMIN_BACKUP_EXPORT:
        raise Http404("Backup export is disabled.")

    """تصدير قاعدة البيانات كاملة كملف JSON للنسخ الاحتياطي"""
    buffer = BytesIO()
    # Use management command to dump data to the buffer
    from django.core.management import call_command
    
    # Create a temporary file to hold the dump
    temp_file = "backup_temp.json"
    try:
        # Note: We use -o to ensure proper encoding on Windows
        call_command('dumpdata', exclude=['contenttypes', 'auth.Permission'], indent=2, output=temp_file)
        with open(temp_file, 'rb') as f:
            data = f.read()
        
        response = HttpResponse(data, content_type="application/json")
        response["Content-Disposition"] = f'attachment; filename="backup-{timezone.now().strftime("%Y-%m-%d-%H%M")}.json"'
        return response
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


@admin_required
def admin_course_control(request, course_id):
    course = get_object_or_404(Course.objects.select_related("subject", "instructor", "instructor__instructor_profile").prefetch_related("units__lessons"), id=course_id)
    batch_form = CourseCodeBatchForm(prefix="batch")
    import_form = CourseStudentImportForm(prefix="import", course=course)
    lesson_form = CourseLessonUploadForm(prefix="lesson", course=course)
    sale_form = CourseCodeSaleForm(prefix="sale", course=course)
    unit_form = CourseUnitQuickForm(prefix="unit")
    media_form = CourseCardMediaForm(prefix="media", instance=course)
    edit_form = CourseEditForm(prefix="edit", instance=course)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "edit_course_details":
            edit_form = CourseEditForm(request.POST, prefix="edit", instance=course)
            if edit_form.is_valid():
                edit_form.save()
                messages.success(request, "تم تحديث بيانات الدورة بنجاح.")
                return redirect("dashboard:admin_course_control", course_id=course.id)
            else:
                messages.error(request, "حدث خطأ أثناء حفظ بيانات الدورة، يرجى مراجعة الحقول.")
        elif action == "create_batch":
            batch_form = CourseCodeBatchForm(request.POST, prefix="batch")
            if batch_form.is_valid():
                batch = batch_form.save(commit=False)
                batch.course = course
                batch.save()
                messages.success(request, "تم إنشاء دفعة الأكواد. يمكنك الآن رفع ملف الطلاب عليها.")
                return redirect("dashboard:admin_course_control", course_id=course.id)
        elif action == "import_students":
            import_form = CourseStudentImportForm(request.POST, request.FILES, prefix="import", course=course)
            if import_form.is_valid():
                created = create_codes_from_upload(
                    import_form.cleaned_data["batch"],
                    import_form.cleaned_data["file"],
                    import_form.cleaned_data["free_codes"],
                )
                messages.success(request, f"تم توليد {created} كود من ملف الطلاب.")
                return redirect("dashboard:admin_course_control", course_id=course.id)
        elif action == "upload_lesson":
            lesson_form = CourseLessonUploadForm(request.POST, request.FILES, prefix="lesson", course=course)
            if lesson_form.is_valid():
                lesson = lesson_form.save(commit=False)
                lesson.lesson_type = "video"
                lesson.save()
                messages.success(request, "تم تسجيل الدرس بنجاح.")
                return redirect("dashboard:admin_course_control", course_id=course.id)
        elif action == "create_unit":
            unit_form = CourseUnitQuickForm(request.POST, prefix="unit")
            if unit_form.is_valid():
                unit = unit_form.save(commit=False)
                unit.course = course
                unit.save()
                messages.success(request, f"تم إنشاء الجلسة {unit.title}.")
                return redirect("dashboard:admin_course_control", course_id=course.id)
        elif action == "update_course_media":
            media_form = CourseCardMediaForm(request.POST, request.FILES, prefix="media", instance=course)
            if media_form.is_valid():
                media_form.save()
                messages.success(request, "تم تحديث غلاف كرت الدورة.")
                return redirect("dashboard:admin_course_control", course_id=course.id)
        elif action == "sell_code":
            sale_form = CourseCodeSaleForm(request.POST, prefix="sale", course=course)
            if sale_form.is_valid():
                with transaction.atomic():
                    access_code = AccessCode.objects.select_for_update().get(id=sale_form.cleaned_data["code"].id, course=course)
                    student_phone = sanitize_plain_text(sale_form.cleaned_data["student_phone"])
                    student_name = sanitize_plain_text(sale_form.cleaned_data["student_name"])
                    student, created = User.objects.get_or_create(
                        username=student_phone,
                        defaults={"first_name": student_name, "is_active": True},
                    )
                    if created:
                        student.set_unusable_password()
                        student.save(update_fields=["password"])
                    elif student_name and not student.get_full_name():
                        student.first_name = student_name
                        student.save(update_fields=["first_name"])
                    StudentProfile.objects.get_or_create(
                        user=student,
                        defaults={"phone": student_phone, "track": course.get_academic_track_display()},
                    )
                    access_code.assigned_student_name = student_name
                    access_code.assigned_student_phone = student_phone
                    access_code.sale_status = "sold"
                    access_code.sold_by = request.user
                    access_code.sold_at = timezone.now()
                    price_amount = sale_form.cleaned_data.get("price_amount")
                    if price_amount is not None:
                        access_code.sold_price_cents = int(price_amount * 100)
                        access_code.price_reason = "تحديد يدوي من الإدارة"
                    else:
                        base_price = course.price_cents or 0
                        from billing.models import DiscountRule
                        now = timezone.now()
                        active_discount = DiscountRule.objects.filter(
                            is_active=True,
                            starts_at__lte=now,
                            expires_at__gte=now
                        ).order_by("-discount_percent").first()
                        if active_discount and base_price > 0:
                            discount_amount = (base_price * active_discount.discount_percent) // 100
                            access_code.sold_price_cents = base_price - discount_amount
                            access_code.price_reason = f"حسم {active_discount.discount_percent}% بمناسبة {active_discount.name}"
                        else:
                            access_code.sold_price_cents = base_price
                            access_code.price_reason = "سعر كامل"
                    access_code.save(update_fields=[
                        "assigned_student_name",
                        "assigned_student_phone",
                        "sale_status",
                        "sold_by",
                        "sold_at",
                        "sold_price_cents",
                        "price_reason",
                        "updated_at",
                    ])
                    AccessGrant.objects.get_or_create(
                        user=student,
                        course=course,
                        lesson=None,
                        defaults={
                            "access_code": access_code,
                            "source": "admin",
                            "starts_at": timezone.now(),
                            "expires_at": access_code.valid_until,
                        },
                    )
                messages.success(request, f"تم بيع الكود {access_code.code} وإضافة الدورة لحساب الطالب.")
                return redirect("dashboard:admin_course_control", course_id=course.id)
        elif action == "clear_device":
            grant = get_object_or_404(AccessGrant, id=request.POST.get("grant_id"), course=course)
            grant.device_fingerprint = ""
            grant.save(update_fields=["device_fingerprint"])
            UserDevice.objects.filter(user=grant.user).update(is_active=False)
            messages.success(request, "تم نقل/فك جهاز الطالب. عند دخوله القادم سيتم ربط الجهاز الجديد.")
            return redirect("dashboard:admin_course_control", course_id=course.id)

    codes = AccessCode.objects.filter(course=course)
    batches = AccessCodeBatch.objects.filter(course=course).select_related("institute", "sales_center").order_by("-created_at")
    grants = AccessGrant.objects.filter(course=course).select_related("user", "access_code").order_by("-created_at")[:30]
    centers = (
        SalesCenter.objects.filter(access_codes__course=course)
        .select_related("institute")
        .annotate(total_codes=Count("access_codes", distinct=True), activated_codes=Count("access_codes__grants", distinct=True))
        .distinct()
        .order_by("name")
    )
    lessons = Lesson.objects.filter(unit__course=course).select_related("unit").order_by("unit__sort_order", "sort_order")
    units = course.units.prefetch_related("lessons").order_by("sort_order", "id")
    print_logs = AccessCodePrintLog.objects.filter(batch__course=course).select_related("batch", "printed_by").order_by("-created_at")[:12]
    stats = {
        "lessons": lessons.count(),
        "codes": codes.count(),
        "sold": codes.filter(sale_status="sold").count(),
        "available": codes.filter(sale_status__in=["available", "reserved"]).count(),
        "free": codes.filter(is_free_code=True).count(),
        "activated": codes.filter(redeemed_count__gt=0).count(),
        "inactive": codes.filter(redeemed_count=0).count(),
        "students": AccessGrant.objects.filter(course=course).values("user").distinct().count(),
        "gross_sales": codes.filter(sale_status="sold").aggregate(total=Sum("sold_price_cents"))["total"] or 0,
        "my_sales": codes.filter(sale_status="sold", sold_by=request.user).count(),
        "my_gross_sales": codes.filter(sale_status="sold", sold_by=request.user).aggregate(total=Sum("sold_price_cents"))["total"] or 0,
        "prints": AccessCodePrintLog.objects.filter(batch__course=course).count(),
        "printed_cards": AccessCodePrintLog.objects.filter(batch__course=course).aggregate(total=Sum("cards_count"))["total"] or 0,
    }
    stats["gross_sales_display"] = f"{stats['gross_sales'] // 100:,}"
    stats["my_gross_sales_display"] = f"{stats['my_gross_sales'] // 100:,}"
    return render(
        request,
        "dashboard/admin_course_control.html",
        {
            "course": course,
            "stats": stats,
            "batches": batches,
            "grants": grants,
            "centers": centers,
            "lessons": lessons[:20],
            "units": units,
            "print_logs": print_logs,
            "batch_form": batch_form,
            "import_form": import_form,
            "lesson_form": lesson_form,
            "sale_form": sale_form,
            "unit_form": unit_form,
            "media_form": media_form,
            "edit_form": edit_form,
        },
    )


@instructor_required
def instructor_dashboard(request):
    courses = (
        Course.objects.filter(instructor=request.user)
        .select_related("subject")
        .annotate(lessons_total=Count("units__lessons", distinct=True), grants_total=Count("access_grants", distinct=True))
    )
    sessions = (
        OnlineLessonSession.objects.filter(lesson__unit__course__in=courses)
        .select_related("lesson", "lesson__unit", "lesson__unit__course")
        .annotate(attendance_total=Count("attendances", distinct=True))
        .order_by("starts_at")
    )
    attendance_rows = LessonAttendance.objects.filter(session__lesson__unit__course__in=courses).select_related(
        "user", "session", "session__lesson", "session__lesson__unit", "session__lesson__unit__course"
    ).order_by("-created_at")
    context = {
        "courses": courses,
        "courses_count": courses.count(),
        "lessons_count": Lesson.objects.filter(unit__course__in=courses).count(),
        "sessions_count": sessions.count(),
        "attendance_count": attendance_rows.count(),
        "students_count": AccessGrant.objects.filter(course__in=courses).values("user").distinct().count(),
        "codes_count": AccessCode.objects.filter(course__in=courses).count(),
        "sessions": sessions[:8],
        "attendance_rows": attendance_rows[:10],
     }
    return render(request, "dashboard/instructor_dashboard.html", context)


def _package_subject_groups(access_code, user, current_device):
    courses = (
        access_code.package.eligible_courses_queryset()
        .select_related("subject", "instructor", "instructor__instructor_profile")
        .order_by("subject__name", "instructor__first_name", "title", "id")
    )
    groups_map = defaultdict(list)
    for course in courses:
        existing_grant = AccessGrant.objects.filter(user=user, course=course, lesson=None).first()
        if existing_grant and existing_grant.device_fingerprint and existing_grant.device_fingerprint != current_device:
            continue
        groups_map[course.subject_id].append(course)
    return [courses for _subject_id, courses in sorted(groups_map.items(), key=lambda item: item[1][0].subject.name)]


def _build_package_selection(access_code, user, current_device):
    groups = _package_subject_groups(access_code, user, current_device)
    steps = []
    auto_course_ids = []
    for courses in groups:
        if len(courses) == 1:
            auto_course_ids.append(courses[0].id)
        else:
            steps.append(
                {
                    "subject": courses[0].subject,
                    "courses": courses,
                    "index": len(steps) + 1,
                }
            )
    return {
        "code": access_code.code,
        "package": access_code.package,
        "steps": steps,
        "auto_course_ids": auto_course_ids,
        "requires_choice": bool(steps),
        "total_steps": len(steps),
    }


def _redeem_package_choices(request, access_code, current_device, auto_select=False):
    groups = _package_subject_groups(access_code, request.user, current_device)
    if not groups:
        return {"ok": False, "message": "لا توجد دورات منشورة داخل هذه الباقة حالياً.", "count": 0}

    selected_course_ids = []
    posted_values = list(request.POST.getlist("course_choices"))
    posted_values.extend(value for key, value in request.POST.items() if key.startswith("course_choice_"))
    posted_ids = {int(value) for value in posted_values if str(value).isdigit()}
    for courses in groups:
        valid_ids = {course.id for course in courses}
        if len(courses) == 1:
            selected_course_ids.append(courses[0].id)
            continue
        if auto_select:
            return {"ok": False, "message": "هذه الباقة تحتاج اختيار مدرس لكل مادة.", "count": 0}
        matching_ids = valid_ids & posted_ids
        if len(matching_ids) != 1:
            return {"ok": False, "message": f"اختر دورة واحدة لمادة {courses[0].subject.name}.", "count": 0}
        selected_course_ids.append(next(iter(matching_ids)))

    grants = []
    now = timezone.now()
    for course in Course.objects.filter(id__in=selected_course_ids).select_related("subject"):
        grant, _created = AccessGrant.objects.get_or_create(
            user=request.user,
            course=course,
            lesson=None,
            defaults={
                "access_code": access_code,
                "source": "code",
                "device_fingerprint": current_device,
                "starts_at": now,
                "expires_at": access_code.valid_until,
            },
        )
        if grant.device_fingerprint and grant.device_fingerprint != current_device:
            return {"ok": False, "message": "إحدى الدورات مرتبطة بجهاز آخر. تواصل مع الإدارة لنقل الجهاز.", "count": 0}
        if not grant.device_fingerprint:
            grant.device_fingerprint = current_device
            grant.save(update_fields=["device_fingerprint"])
        grants.append(grant)

    access_code.redeemed_count += 1
    if access_code.sale_status in {"available", "reserved"}:
        access_code.sale_status = "free" if access_code.is_free_code else "sold"
        if not access_code.is_free_code and access_code.package:
            base_price = access_code.package.price_cents or 0
            if base_price > 0:
                from billing.models import DiscountRule
                active_discount = DiscountRule.objects.filter(
                    is_active=True,
                    starts_at__lte=now,
                    expires_at__gte=now
                ).order_by("-discount_percent").first()
                if active_discount:
                    discount_amount = (base_price * active_discount.discount_percent) // 100
                    access_code.sold_price_cents = base_price - discount_amount
                    access_code.price_reason = f"حسم {active_discount.discount_percent}% بمناسبة {active_discount.name}"
                else:
                    access_code.sold_price_cents = base_price
                    access_code.price_reason = "سعر كامل"
    access_code.save(update_fields=["redeemed_count", "sale_status", "sold_price_cents", "price_reason", "updated_at"])
    StudentNotification.objects.create(
        user=request.user,
        notification_type="access",
        title="تم تفعيل باقة جديدة",
        body=f"تمت إضافة {len(grants)} دورة من باقة {access_code.package.name} إلى حسابك.",
        url="/student/my-courses/",
    )
    return {"ok": True, "message": "", "count": len(grants)}


@login_required
def student_dashboard(request):
    redeem_form = RedeemCodeForm(request.POST or None)
    current_device = _current_device_fingerprint(request)
    package_selection = None

    if request.method == "POST" and request.POST.get("action") == "complete_package_redeem":
        code_value = request.POST.get("package_code", "").strip().upper()
        with transaction.atomic():
            access_code = AccessCode.objects.select_for_update().filter(code__iexact=code_value).first()
            if access_code is None or access_code.access_type != "package" or not access_code.package:
                messages.error(request, "كود الباقة غير صحيح.")
            else:
                allowed, reason = access_code.is_redeemable(timezone.now())
                if not allowed:
                    messages.error(request, reason)
                elif not _access_code_matches_student(access_code, request.user):
                    messages.error(request, "هذا الكود مخصص لطالب آخر ولا يمكن تفعيله على هذا الحساب.")
                else:
                    result = _redeem_package_choices(request, access_code, current_device)
                    if result["ok"]:
                        messages.success(request, f"تم تفعيل الباقة وإضافة {result['count']} دورة إلى مكتبتك.")
                        return redirect("dashboard:student_dashboard")
                    messages.error(request, result["message"])
    elif request.method == "POST" and redeem_form.is_valid():
        code_value = redeem_form.cleaned_data["code"].strip().upper()
        with transaction.atomic():
            access_code = AccessCode.objects.select_for_update().filter(code__iexact=code_value).first()
            if access_code is None:
                messages.error(request, "الكود غير صحيح.")
            else:
                allowed, reason = access_code.is_redeemable(timezone.now())
                if not allowed:
                    messages.error(request, reason)
                elif not _access_code_matches_student(access_code, request.user):
                    messages.error(request, "هذا الكود مخصص لطالب آخر ولا يمكن تفعيله على هذا الحساب.")
                elif access_code.access_type == "package" and access_code.package:
                    package_selection = _build_package_selection(access_code, request.user, current_device)
                    if package_selection["requires_choice"]:
                        messages.info(request, "اختر مدرساً واحداً لكل مادة لإكمال تفعيل الباقة.")
                    else:
                        result = _redeem_package_choices(request, access_code, current_device, auto_select=True)
                        if result["ok"]:
                            messages.success(request, f"تم تفعيل الباقة وإضافة {result['count']} دورة إلى مكتبتك.")
                            return redirect("dashboard:student_dashboard")
                        messages.error(request, result["message"])
                else:
                    grant, created = AccessGrant.objects.get_or_create(
                        user=request.user,
                        course=access_code.course,
                        lesson=access_code.lesson,
                        defaults={
                            "access_code": access_code,
                            "source": "code",
                            "device_fingerprint": current_device,
                            "starts_at": timezone.now(),
                            "expires_at": access_code.valid_until,
                        },
                    )
                    if created:
                        access_code.redeemed_count += 1
                        if access_code.sale_status in {"available", "reserved"}:
                            access_code.sale_status = "free" if access_code.is_free_code else "sold"
                            if not access_code.is_free_code:
                                base_price = 0
                                if access_code.course:
                                    base_price = access_code.course.price_cents or 0
                                elif access_code.lesson:
                                    if not base_price and access_code.course:
                                        base_price = access_code.course.price_cents or 0
                                if base_price > 0:
                                    from billing.models import DiscountRule
                                    now = timezone.now()
                                    active_discount = DiscountRule.objects.filter(
                                        is_active=True,
                                        starts_at__lte=now,
                                        expires_at__gte=now
                                    ).order_by("-discount_percent").first()
                                    if active_discount:
                                        discount_amount = (base_price * active_discount.discount_percent) // 100
                                        access_code.sold_price_cents = base_price - discount_amount
                                        access_code.price_reason = f"حسم {active_discount.discount_percent}% بمناسبة {active_discount.name}"
                                    else:
                                        access_code.sold_price_cents = base_price
                                        access_code.price_reason = "سعر كامل"
                        access_code.save(update_fields=["redeemed_count", "sale_status", "sold_price_cents", "price_reason", "updated_at"])
                        StudentNotification.objects.create(
                            user=request.user,
                            notification_type="access",
                            title="تم تفعيل كود جديد",
                            body=f"تمت إضافة {access_code.course or access_code.lesson or access_code.plan} إلى حسابك.",
                            url="/student/",
                        )
                        messages.success(request, "تم تفعيل الكود وإضافة المادة إلى حسابك.")
                    else:
                        if grant.device_fingerprint and grant.device_fingerprint != current_device:
                            messages.error(request, "هذه المكثفة مرتبطة بجهاز آخر. تواصل مع الإدارة لنقل الجهاز.")
                        else:
                            if not grant.device_fingerprint:
                                grant.device_fingerprint = current_device
                                grant.save(update_fields=["device_fingerprint"])
                            messages.info(request, "هذه المادة أو الدرس مفعّل لديك مسبقًا.")
        if not package_selection:
            return redirect("dashboard:student_dashboard")

    grants = _device_grants(request.user, current_device).select_related("course", "lesson", "access_code").order_by("-created_at")
    sessions = _available_sessions_for_user(request.user, current_device)
    unlocked_lessons = (
        Lesson.objects.filter(id__in=_student_lesson_ids_for_device(request.user, current_device))
        .select_related("unit", "unit__course")
        .order_by("unit__course__title", "unit__sort_order", "sort_order")[:16]
    )

    # Gamification and Continue Learning
    student_profile = None
    if hasattr(request.user, 'student_profile'):
        student_profile = request.user.student_profile
        
    continue_learning = LessonProgress.objects.filter(user=request.user).select_related("lesson", "lesson__unit", "lesson__unit__course").order_by("-updated_at").first()

    context = {
        "redeem_form": redeem_form,
        "grants": grants,
        "unlocked_lessons": unlocked_lessons,
        "sessions": sessions[:12],
        "attendances": LessonAttendance.objects.filter(user=request.user).select_related("session").order_by("-created_at")[:12],
        "attempts": Attempt.objects.filter(user=request.user).select_related("exam").order_by("-created_at")[:8],
        "notifications": StudentNotification.objects.filter(user=request.user).order_by("-created_at")[:8],
        "student_profile": student_profile,
        "continue_learning": continue_learning,
        "package_selection": package_selection,
    }
    return render(request, "dashboard/student_dashboard.html", context)


@login_required
def student_device_ping(request):
    response = JsonResponse({"status": "active"})
    response["Cache-Control"] = "no-store"
    return response


@login_required
def my_courses_page(request):
    current_device = _current_device_fingerprint(request)
    grants = _device_grants(request.user, current_device).select_related(
        "course", "course__subject", "course__instructor", "course__instructor__instructor_profile", "lesson", "access_code"
    ).order_by("-created_at")
    progress_map = {}
    for cp in CourseProgress.objects.filter(user=request.user):
        progress_map[cp.course_id] = cp
    context = {
        "grants": grants,
        "progress_map": progress_map,
    }
    return render(request, "dashboard/my_courses.html", context)


@login_required
def favorites_page(request):
    context = {
        "favorites": [],
    }
    return render(request, "dashboard/favorites.html", context)


@login_required
def notifications_page(request):
    notifications = StudentNotification.objects.filter(user=request.user).order_by("-created_at")
    unread_count = notifications.filter(read_at__isnull=True).count()
    if request.method == "POST" and request.POST.get("action") == "mark_all_read":
        notifications.filter(read_at__isnull=True).update(read_at=timezone.now())
        messages.success(request, "تم تعليم جميع الإشعارات كمقروءة.")
        return redirect("dashboard:notifications")
    context = {
        "notifications": notifications,
        "unread_count": unread_count,
    }
    return render(request, "dashboard/notifications.html", context)


@login_required
def profile_page(request):
    student_profile = None
    if hasattr(request.user, "student_profile"):
        student_profile = request.user.student_profile
    current_device = _current_device_fingerprint(request)
    grants = _device_grants(request.user, current_device).select_related("course", "lesson").order_by("-created_at")
    total_xp = student_profile.xp if student_profile else 0
    level = student_profile.level if student_profile else 1
    streak = student_profile.streak_days if student_profile else 0
    completed_lessons = LessonProgress.objects.filter(user=request.user, completed_at__isnull=False).count()
    total_lessons = Lesson.objects.filter(
        unit__course__access_grants__user=request.user
    ).distinct().count()
    context = {
        "student_profile": student_profile,
        "grants": grants,
        "total_xp": total_xp,
        "level": level,
        "streak": streak,
        "completed_lessons": completed_lessons,
        "total_lessons": total_lessons,
    }
    return render(request, "dashboard/profile.html", context)
    
@login_required
def profile_edit(request):
    student_profile, _created = StudentProfile.objects.get_or_create(user=request.user)
        
    if request.method == "POST":
        try:
            first_name = sanitize_plain_text(request.POST.get("first_name"), max_length=120)
            last_name = sanitize_plain_text(request.POST.get("last_name"), max_length=120)
            phone = validate_syrian_mobile(request.POST.get("phone"), user=request.user)
            bio = sanitize_plain_text(request.POST.get("bio"), max_length=1000)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
            return redirect("dashboard:profile_edit")
        
        request.user.first_name = first_name
        request.user.last_name = last_name
        request.user.username = phone
        request.user.save()
        
        student_profile.phone = phone
        student_profile.bio = bio
        if request.FILES.get("avatar"):
            student_profile.avatar = request.FILES.get("avatar")
        student_profile.save()
            
        messages.success(request, "تم تحديث بياناتك الشخصية بنجاح.")
        return redirect("dashboard:profile")
        
    context = {
        "student_profile": student_profile,
    }
    return render(request, "dashboard/profile_edit.html", context)

@login_required
def view_certificate(request, course_id):
    from learning.models import Certificate
    course = get_object_or_404(Course, id=course_id)
    certificate = Certificate.objects.filter(user=request.user, course=course).first()
    
    if not certificate:
        # Check if student completed the course to issue a certificate
        progress = CourseProgress.objects.filter(user=request.user, course=course).first()
        if progress and progress.completion_percent >= 100:
            certificate = Certificate.objects.create(user=request.user, course=course)
        else:
            messages.error(request, "لم تقم بإكمال هذه الدورة بعد لتتمكن من الحصول على الشهادة.")
            return redirect("dashboard:student_course_detail", course_id=course.id)
            
    context = {
        "certificate": certificate,
        "course": course,
        "student": request.user,
    }
    return render(request, "dashboard/certificate.html", context)

def departments_list(request):
    from learning.models import Subject
    # Grouping logic or just listing subjects
    subjects = Subject.objects.all().prefetch_related('courses')
    context = {
        "subjects": subjects,
    }
    return render(request, "dashboard/departments.html", context)

def search_results(request):
    query = request.GET.get("q", "")
    courses = []
    if query:
        courses = Course.objects.filter(
            models.Q(title__icontains=query) | 
            models.Q(description__icontains=query) |
            models.Q(subject__name__icontains=query)
        ).filter(status="published").distinct()
    
    context = {
        "query": query,
        "courses": courses,
    }
    return render(request, "dashboard/search_results.html", context)

def about_page(request):
    return render(request, "dashboard/about.html")

def contact_page(request):
    if request.method == "POST":
        # Logic for contact form could go here
        messages.success(request, "تم استلام رسالتك بنجاح. سنقوم بالرد عليك في أقرب وقت.")
        return redirect("dashboard:contact")
    return render(request, "dashboard/contact.html")

def instructors_list(request):
    # Fetching users who are staff and have at least one published course
    from django.contrib.auth.models import User
    from learning.models import Course
    
    # Show all instructors who have a profile, regardless of published courses
    instructors = User.objects.filter(is_staff=True, instructor_profile__isnull=False).select_related('instructor_profile').distinct()
    
    context = {
        "instructors": instructors,
    }
    return render(request, "dashboard/instructors.html", context)

def faq_page(request):
    return render(request, "dashboard/faq.html")

def privacy_page(request):
    return render(request, "dashboard/privacy.html")

def terms_page(request):
    return render(request, "dashboard/terms.html")


def _student_course_ids(user):
    return list(_active_access_grants(user).filter(course__isnull=False).values_list("course_id", flat=True))


def _student_course_ids_for_device(user, device_fingerprint):
    return list(_device_grants(user, device_fingerprint).filter(course__isnull=False).values_list("course_id", flat=True))


def _student_lesson_ids(user):
    direct_lessons = list(_active_access_grants(user).filter(lesson__isnull=False).values_list("lesson_id", flat=True))
    course_lessons = list(Lesson.objects.filter(unit__course_id__in=_student_course_ids(user)).values_list("id", flat=True))
    return list(set(direct_lessons + course_lessons))


def _student_lesson_ids_for_device(user, device_fingerprint):
    direct_lessons = list(_device_grants(user, device_fingerprint).filter(lesson__isnull=False).values_list("lesson_id", flat=True))
    course_lessons = list(Lesson.objects.filter(unit__course_id__in=_student_course_ids_for_device(user, device_fingerprint)).values_list("id", flat=True))
    return list(set(direct_lessons + course_lessons))


def _available_sessions_for_user(user, device_fingerprint=None):
    lesson_ids = _student_lesson_ids_for_device(user, device_fingerprint) if device_fingerprint else _student_lesson_ids(user)
    return (
        OnlineLessonSession.objects.filter(lesson_id__in=lesson_ids)
        .select_related("lesson", "lesson__unit", "lesson__unit__course")
        .order_by("starts_at")
    )


@login_required
def student_course_detail(request, course_id):
    current_device = _current_device_fingerprint(request)
    course = get_object_or_404(Course.objects.select_related("subject", "instructor", "instructor__instructor_profile").prefetch_related("units__lessons"), id=course_id)
    if not _device_grants(request.user, current_device).filter(course=course).exists():
        raise Http404("Course not found")

    attempts = Attempt.objects.filter(user=request.user, exam__course=course).select_related("exam").order_by("-created_at")
    completed_lesson_ids = set(
        LessonProgress.objects.filter(
            user=request.user,
            lesson__unit__course=course,
            completed_at__isnull=False,
        ).values_list("lesson_id", flat=True)
    )
    return render(
        request,
        "dashboard/student_course_detail.html",
        {"course": course, "attempts": attempts, "completed_lesson_ids": completed_lesson_ids},
    )


@login_required
def student_lesson_detail(request, lesson_id):
    current_device = _current_device_fingerprint(request)
    lesson = get_object_or_404(Lesson.objects.select_related("unit", "unit__course"), id=lesson_id)
    if not request.user.is_staff and lesson.id not in _student_lesson_ids_for_device(request.user, current_device):
        raise Http404("Lesson not found")

    progress, _created = LessonProgress.objects.get_or_create(
        user=request.user,
        lesson=lesson,
    )
    _refresh_course_progress(request.user, lesson.unit.course)
    signed_video_url = ""
    if lesson.video_file:
        signed_video_url = _signed_lesson_video_url(request, lesson)
    return render(
        request,
        "dashboard/student_lesson_detail.html",
        {"lesson": lesson, "progress": progress, "video_embed_url": _video_embed_url(lesson.video_url), "signed_video_url": signed_video_url},
    )


@login_required
def signed_lesson_video(request, lesson_id, token):
    lesson = get_object_or_404(Lesson.objects.select_related("unit", "unit__course"), id=lesson_id)
    current_device = _current_device_fingerprint(request)
    if not request.user.is_staff and lesson.id not in _student_lesson_ids_for_device(request.user, current_device):
        raise Http404("Video not found")
    try:
        payload = signing.TimestampSigner(salt="lesson-video").unsign_object(token, max_age=60 * 10)
    except signing.BadSignature as exc:
        raise Http404("Video not found") from exc
    if payload.get("lesson_id") != lesson.id or payload.get("user_id") != request.user.id or payload.get("device") != current_device:
        raise Http404("Video not found")
    if not lesson.video_file:
        raise Http404("Video not found")
    response = FileResponse(lesson.video_file.open("rb"), content_type="video/mp4")
    response["Cache-Control"] = "no-store"
    response["Content-Disposition"] = 'inline; filename="lesson-video.mp4"'
    return response


def _video_embed_url(video_url):
    if not video_url:
        return ""
    if "youtube.com/watch?v=" in video_url:
        return video_url.replace("watch?v=", "embed/")
    if "youtu.be/" in video_url:
        return video_url.replace("youtu.be/", "www.youtube.com/embed/")
    if "vimeo.com/" in video_url and "player.vimeo.com" not in video_url:
        video_id = video_url.rstrip("/").split("/")[-1]
        return f"https://player.vimeo.com/video/{video_id}"
    
    # Bunny.net Support with Secure Token Authentication
    if "mediadelivery.net" in video_url:
        from urllib.parse import urlparse
        import hashlib
        import time
        import os
        parsed = urlparse(video_url)
        path_parts = [p for p in parsed.path.split("/") if p]
        library_id = ""
        video_id = ""
        if len(path_parts) >= 3:
            library_id = path_parts[1]
            video_id = path_parts[2]
        elif len(path_parts) == 2:
            library_id = path_parts[0]
            video_id = path_parts[1]
        if library_id and video_id:
            token_key = os.environ.get("BUNNY_STREAM_TOKEN_KEY", "").strip()
            if token_key:
                expires = int(time.time()) + 7200
                token_input = f"{token_key}{video_id}{expires}"
                token = hashlib.sha256(token_input.encode("utf-8")).hexdigest()
                return f"https://iframe.mediadelivery.net/embed/{library_id}/{video_id}?token={token}&expires={expires}"
            else:
                return f"https://iframe.mediadelivery.net/embed/{library_id}/{video_id}"
    # Legacy Fallback if parsing library_id and video_id failed
    if "mediadelivery.net" in video_url:
        if "/play/" in video_url:
            return video_url.replace("/play/", "/embed/")
        return video_url
        
    return video_url


def _signed_lesson_video_url(request, lesson):
    from django.urls import reverse

    payload = {
        "lesson_id": lesson.id,
        "user_id": request.user.id,
        "device": _current_device_fingerprint(request),
    }
    token = signing.TimestampSigner(salt="lesson-video").sign_object(payload)
    return reverse("dashboard:signed_lesson_video", args=[lesson.id, token])


@login_required
def complete_lesson(request, lesson_id):
    current_device = _current_device_fingerprint(request)
    lesson = get_object_or_404(Lesson.objects.select_related("unit", "unit__course"), id=lesson_id)
    if lesson.id not in _student_lesson_ids_for_device(request.user, current_device):
        messages.error(request, "هذا الدرس غير مفعّل على هذا الجهاز.")
        return redirect("dashboard:student_dashboard")

    from datetime import date
    from datetime import timedelta

    LessonProgress.objects.update_or_create(
        user=request.user,
        lesson=lesson,
        defaults={
            "watched_seconds": lesson.duration_seconds or 0,
            "last_position_seconds": lesson.duration_seconds or 0,
            "completed_at": timezone.now(),
        },
    )
    _refresh_course_progress(request.user, lesson.unit.course)
    
    # Gamification Engine
    if hasattr(request.user, 'student_profile'):
        profile = request.user.student_profile
        today = date.today()
        
        # Streak Logic
        if profile.last_activity_date != today:
            if profile.last_activity_date == today - timedelta(days=1):
                profile.streak_days += 1
            else:
                profile.streak_days = 1
            profile.last_activity_date = today
            
        # XP & Level Logic
        profile.xp += 50
        new_level = (profile.xp // 500) + 1
        level_up = False
        if new_level > profile.level:
            profile.level = new_level
            level_up = True
            
        profile.save()
        
        if level_up:
            messages.success(request, f"🎉 مبروك! وصلت للمستوى {profile.level}!")
        else:
            messages.success(request, f"تم تسجيل الدرس كمكتمل. +50 XP ⚡")
    else:
        messages.success(request, "تم تسجيل الدرس كمكتمل.")

    StudentNotification.objects.create(
        user=request.user,
        notification_type="lesson",
        title="تم إكمال درس",
        body=f"أكملت درس {lesson.title}.",
        url=f"/student/courses/{lesson.unit.course_id}/",
    )
    return redirect("dashboard:student_lesson_detail", lesson_id=lesson.id)

@login_required
def save_lesson_progress(request, lesson_id):
    current_device = _current_device_fingerprint(request)
    if lesson_id not in _student_lesson_ids_for_device(request.user, current_device):
        return JsonResponse({"status": "forbidden"}, status=403)

    if request.method == "POST":
        current_time = request.POST.get("current_time")
        if current_time:
            try:
                last_position = max(0, int(float(current_time)))
            except (TypeError, ValueError):
                return JsonResponse({"status": "error"}, status=400)
            LessonProgress.objects.update_or_create(
                user=request.user,
                lesson_id=lesson_id,
                defaults={"last_position_seconds": last_position},
            )
            return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)


@login_required
def join_session(request, session_id):
    current_device = _current_device_fingerprint(request)
    session = get_object_or_404(OnlineLessonSession.objects.select_related("lesson", "lesson__unit", "lesson__unit__course"), id=session_id)
    if session.lesson_id not in _student_lesson_ids_for_device(request.user, current_device):
        messages.error(request, "لا تملك صلاحية حضور هذه الجلسة.")
        return redirect("dashboard:student_dashboard")

    attendance, _created = LessonAttendance.objects.get_or_create(user=request.user, session=session)
    attendance.status = "attended"
    attendance.joined_at = attendance.joined_at or timezone.now()
    attendance.save(update_fields=["status", "joined_at", "updated_at"])
    StudentNotification.objects.create(
        user=request.user,
        notification_type="attendance",
        title="تم تسجيل حضورك",
        body=f"تم تسجيل حضورك في {session.title}.",
        url=f"/student/lessons/{session.lesson_id}/",
    )

    messages.success(request, "تم تسجيل حضورك في الجلسة.")
    if session.meeting_url:
        return redirect(session.meeting_url)
    return redirect("dashboard:student_lesson_detail", lesson_id=session.lesson_id)


def _refresh_course_progress(user, course):
    total_lessons = Lesson.objects.filter(unit__course=course).count()
    completed_lessons = LessonProgress.objects.filter(user=user, lesson__unit__course=course, completed_at__isnull=False).count()
    completion_percent = 0
    if total_lessons:
        completion_percent = round((completed_lessons / total_lessons) * 100, 2)
    CourseProgress.objects.update_or_create(
        user=user,
        course=course,
        defaults={
            "completion_percent": completion_percent,
            "completed_lessons": completed_lessons,
            "total_lessons": total_lessons,
            "last_activity_at": timezone.now(),
        },
    )


def _current_device_fingerprint(request):
    return device_fingerprint(request)


def _touch_user_device(request, user):
    return activate_user_device(request, user)


def _device_seed(request):
    return device_seed(request)


def _set_device_cookie(response, request):
    return set_device_cookie(response, request)


def _device_grants(user, device_fingerprint):
    return _active_access_grants(user).filter(
        models.Q(device_fingerprint="") | models.Q(device_fingerprint=device_fingerprint)
    )


def _active_access_grants(user):
    now = timezone.now()
    return AccessGrant.objects.filter(user=user).filter(
        models.Q(starts_at__isnull=True) | models.Q(starts_at__lte=now),
        models.Q(expires_at__isnull=True) | models.Q(expires_at__gte=now),
    )


def _access_code_matches_student(access_code, user):
    if not access_code.assigned_student_phone and not access_code.assigned_student_name:
        return True
    profile = getattr(user, "student_profile", None)
    user_phone = profile.phone if profile else user.username
    if access_code.assigned_student_phone:
        return access_code.assigned_student_phone.strip() == user_phone.strip()
    full_name = (user.get_full_name() or user.first_name or user.username).strip()
    return access_code.assigned_student_name.strip() == full_name


def _default_catalog_tabs():
    return [
        {"label": "مكثفات العلمي", "kind": "intensive", "track": "scientific"},
        {"label": "مكثفات الأدبي", "kind": "intensive", "track": "literary"},
        {"label": "منهاج العلمي", "kind": "curriculum", "track": "scientific"},
        {"label": "منهاج الأدبي", "kind": "curriculum", "track": "literary"},
        {"label": "التاسع", "kind": "material", "track": "ninth"},
    ]


def _ensure_default_catalog_sections():
    for index, tab in enumerate(_default_catalog_tabs(), start=1):
        CatalogSection.objects.get_or_create(
            kind=tab["kind"],
            track=tab["track"],
            defaults={"label": tab["label"], "sort_order": index * 10, "is_visible": True},
        )


def _catalog_tabs(include_hidden=False):
    try:
        all_sections = CatalogSection.objects.all()
        sections = all_sections
        if not include_hidden:
            sections = sections.filter(is_visible=True)
        sections = list(sections.order_by("sort_order", "label"))
        if not sections:
            return []
        return [
            {
                "id": section.id,
                "label": section.label,
                "kind": section.kind,
                "track": section.track,
                "sort_order": section.sort_order,
                "is_visible": section.is_visible,
            }
            for section in sections
        ]
    except Exception:
        return _default_catalog_tabs()


def instructor_courses(request, instructor_id):
    instructor = get_object_or_404(User, id=instructor_id)
    courses = (
        Course.objects.filter(instructor=instructor, status="published")
        .select_related("subject")
        .annotate(lessons_total=Count("units__lessons", distinct=True))
        .order_by("-published_at")
    )
    if not courses.exists():
        raise Http404("No published courses were found for this instructor.")
    instructor_profile = getattr(instructor, 'instructor_profile', None)
    
    return render(
        request,
        "dashboard/instructor_courses.html",
        {
            "instructor": instructor,
            "instructor_profile": instructor_profile,
            "courses": courses,
        },
    )


@admin_required
def admin_billing(request):
    from billing.models import Subscription, Payment, AccessCodeBatch, AccessCode, SalesCenter
    
    # Calculate counts on unsliced querysets
    active_subs_count = Subscription.objects.filter(status="active").count()
    
    # Get sliced data for display
    subscriptions = Subscription.objects.select_related("user", "plan").order_by("-created_at")[:50]
    payments = Payment.objects.select_related("user").order_by("-created_at")[:50]
    batches = AccessCodeBatch.objects.select_related("course", "institute", "sales_center").order_by("-created_at")[:50]
    
    # Prepare payments with dollar amounts
    for p in payments:
        p.amount_dollars = p.amount_cents / 100

    # General fund balance from sold codes
    general_fund_cents = AccessCode.objects.filter(sale_status="sold").aggregate(total=models.Sum("sold_price_cents"))["total"] or 0
    general_fund_syp = general_fund_cents / 100

    # Centers expected funds
    centers_report = []
    for center in SalesCenter.objects.filter(is_active=True).select_related("institute").order_by("name"):
        codes = AccessCode.objects.filter(sales_center=center).select_related("course", "package")
        sold_codes = codes.filter(sale_status="sold")
        sold_count = sold_codes.count()
        
        # 1. الصندوق المتوقع (Expected Fund): Sum of standard prices for ALL assigned codes (total potential)
        expected_balance_cents = 0
        for code in codes:
            if code.course and code.course.price_cents:
                expected_balance_cents += code.course.price_cents
            elif code.package and code.package.price_cents:
                expected_balance_cents += code.package.price_cents
                
        # 2. الصندوق الحقيقي الافتراضي (Standard Real Fund): Sum of standard prices for SOLD codes (gross standard value)
        real_standard_cents = 0
        for code in sold_codes:
            if code.course and code.course.price_cents:
                real_standard_cents += code.course.price_cents
            elif code.package and code.package.price_cents:
                real_standard_cents += code.package.price_cents
                
        # 3. الصندوق بعد الحسومات (Fund after discounts): Actual money earned (sold_price_cents)
        actual_earned_cents = sold_codes.aggregate(total=models.Sum("sold_price_cents"))["total"] or 0
        
        centers_report.append({
            "center": center,
            "total_codes": codes.count(),
            "sold_codes_count": sold_count,
            "expected_balance": expected_balance_cents / 100,
            "real_standard": real_standard_cents / 100,
            "actual_earned": actual_earned_cents / 100,
        })

    context = {
        "subscriptions": subscriptions,
        "payments": payments,
        "batches": batches,
        "total_revenue": sum(p.amount_cents for p in payments if p.status == "paid") / 100,
        "active_subs_count": active_subs_count,
        "filter_reports": _filter_financial_rows(),
        "course_reports": _course_financial_rows()[:30],
        "general_fund_syp": general_fund_syp,
        "centers_report": centers_report,
    }
    return render(request, "dashboard/admin_billing.html", context)


@admin_required
def admin_discounts(request):
    from billing.models import DiscountRule
    discounts = DiscountRule.objects.all().order_by("-created_at")
    return render(
        request,
        "dashboard/admin_discounts.html",
        {"discounts": discounts},
    )


@admin_required
def admin_discount_add(request):
    if request.method == "POST":
        from billing.models import DiscountRule
        from django.utils.dateparse import parse_datetime
        
        name = request.POST.get("name")
        percent = request.POST.get("discount_percent")
        starts_at = parse_datetime(request.POST.get("starts_at"))
        expires_at = parse_datetime(request.POST.get("expires_at"))
        is_active = request.POST.get("is_active") in ["on", "true", "1"]
        
        if name and percent:
            try:
                DiscountRule.objects.create(
                    name=name,
                    discount_percent=int(percent),
                    starts_at=starts_at,
                    expires_at=expires_at,
                    is_active=is_active,
                )
                messages.success(request, "تم إضافة حسم جديد بنجاح.")
            except Exception as e:
                messages.error(request, f"خطأ أثناء إضافة الحسم: {str(e)}")
        else:
            messages.error(request, "يرجى ملء جميع الحقول المطلوبة.")
    return redirect("dashboard:admin_discounts")


@admin_required
def admin_discount_toggle(request, discount_id):
    from billing.models import DiscountRule
    discount = get_object_or_404(DiscountRule, id=discount_id)
    discount.is_active = not discount.is_active
    discount.save()
    messages.success(request, f"تم تغيير حالة الحسم '{discount.name}' بنجاح.")
    return redirect("dashboard:admin_discounts")


@admin_required
def admin_discount_delete(request, discount_id):
    from billing.models import DiscountRule
    discount = get_object_or_404(DiscountRule, id=discount_id)
    name = discount.name
    discount.delete()
    messages.success(request, f"تم حذف الحسم '{name}' بنجاح.")
    return redirect("dashboard:admin_discounts")


def _filter_financial_rows():
    rows = []
    for tab in _catalog_tabs():
        codes = AccessCode.objects.filter(course__kind=tab["kind"], course__academic_track=tab["track"])
        prints = AccessCodePrintLog.objects.filter(batch__course__kind=tab["kind"], batch__course__academic_track=tab["track"])
        rows.append({
            "label": tab["label"],
            "kind": tab["kind"],
            "track": tab["track"],
            "courses": Course.objects.filter(kind=tab["kind"], academic_track=tab["track"]).count(),
            "codes": codes.count(),
            "sold": codes.filter(sale_status="sold").count(),
            "activated": codes.filter(redeemed_count__gt=0).count(),
            "inactive": codes.filter(redeemed_count=0).count(),
            "printed": prints.aggregate(total=Sum("cards_count"))["total"] or 0,
            "gross": (codes.filter(sale_status="sold").aggregate(total=Sum("sold_price_cents"))["total"] or 0) / 100,
        })
    return rows


def _course_financial_rows():
    rows = []
    courses = Course.objects.select_related("subject", "instructor", "instructor__instructor_profile").order_by("academic_track", "kind", "subject__name", "title")
    for course in courses:
        codes = AccessCode.objects.filter(course=course)
        prints = AccessCodePrintLog.objects.filter(batch__course=course)
        rows.append({
            "course": course,
            "codes": codes.count(),
            "sold": codes.filter(sale_status="sold").count(),
            "activated": codes.filter(redeemed_count__gt=0).count(),
            "inactive": codes.filter(redeemed_count=0).count(),
            "printed": prints.aggregate(total=Sum("cards_count"))["total"] or 0,
            "gross": (codes.filter(sale_status="sold").aggregate(total=Sum("sold_price_cents"))["total"] or 0) / 100,
        })
    return rows


def _package_financial_rows():
    rows = []
    packages = CoursePackage.objects.prefetch_related("courses").order_by("name")
    for package in packages:
        codes = AccessCode.objects.filter(access_type="package", package=package)
        eligible_courses = package.eligible_courses_queryset()
        rows.append({
            "package": package,
            "subjects": eligible_courses.values("subject").distinct().count(),
            "courses": eligible_courses.count(),
            "codes": codes.count(),
            "sold": codes.filter(sale_status="sold").count(),
            "activated": codes.filter(redeemed_count__gt=0).count(),
            "inactive": codes.filter(redeemed_count=0).count(),
            "gross": (codes.filter(sale_status="sold").aggregate(total=Sum("sold_price_cents"))["total"] or 0) / 100,
        })
    return rows


@admin_required
def admin_financial_report_export(request):
    workbook = Workbook()
    filters_sheet = workbook.active
    filters_sheet.title = "filters"
    filters_sheet.append(["filter", "courses", "codes", "sold", "activated", "inactive", "printed_cards", "gross_syp"])
    for row in _filter_financial_rows():
        filters_sheet.append([row["label"], row["courses"], row["codes"], row["sold"], row["activated"], row["inactive"], row["printed"], int(row["gross"])])

    courses_sheet = workbook.create_sheet("courses")
    courses_sheet.append(["course", "filter", "subject", "instructor", "codes", "sold", "activated", "inactive", "printed_cards", "gross_syp"])
    for row in _course_financial_rows():
        course = row["course"]
        courses_sheet.append([
            course.title,
            f"{course.get_kind_display()} {course.get_academic_track_display()}",
            course.subject.name,
            course.instructor.get_full_name() or course.instructor.username,
            row["codes"],
            row["sold"],
            row["activated"],
            row["inactive"],
            row["printed"],
            int(row["gross"]),
        ])
    packages_sheet = workbook.create_sheet("packages")
    packages_sheet.append(["package", "track", "subjects", "courses", "codes", "sold", "activated", "inactive", "gross_syp"])
    for row in _package_financial_rows():
        package = row["package"]
        packages_sheet.append([
            package.name,
            package.get_package_track_display(),
            row["subjects"],
            row["courses"],
            row["codes"],
            row["sold"],
            row["activated"],
            row["inactive"],
            int(row["gross"]),
        ])
    return _workbook_response(workbook, f"financial-report-{timezone.now().strftime('%Y%m%d-%H%M')}.xlsx")


@admin_required
def admin_packages_report_export(request):
    workbook = Workbook()
    summary = workbook.active
    summary.title = "packages"
    summary.append(["package", "track", "subjects", "courses", "codes", "sold", "activated", "inactive", "gross_syp"])
    for row in _package_financial_rows():
        package = row["package"]
        summary.append([
            package.name,
            package.get_package_track_display(),
            row["subjects"],
            row["courses"],
            row["codes"],
            row["sold"],
            row["activated"],
            row["inactive"],
            int(row["gross"]),
        ])

    codes_sheet = workbook.create_sheet("codes")
    codes_sheet.append(["code", "package", "sale_status", "student_name", "student_phone", "sold_by", "sold_at", "sold_price_syp", "activated", "batch", "sales_center"])
    codes = (
        AccessCode.objects.filter(access_type="package")
        .select_related("package", "sold_by", "batch", "sales_center")
        .order_by("package__name", "-created_at")
    )
    for code in codes:
        codes_sheet.append([
            code.code,
            code.package.name if code.package else "",
            code.sale_status,
            code.assigned_student_name,
            code.assigned_student_phone,
            code.sold_by.username if code.sold_by else "",
            code.sold_at.strftime("%Y-%m-%d %H:%M") if code.sold_at else "",
            (code.sold_price_cents or 0) // 100,
            "yes" if code.redeemed_count else "no",
            code.batch.name if code.batch else "",
            code.sales_center.name if code.sales_center else "",
        ])
    for sheet in workbook.worksheets:
        for column in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"]:
            sheet.column_dimensions[column].width = 22
    return _workbook_response(workbook, f"packages-report-{timezone.now().strftime('%Y%m%d-%H%M')}.xlsx")


@admin_required
def admin_course_report_export(request, course_id):
    course = get_object_or_404(Course.objects.select_related("subject", "instructor", "instructor__instructor_profile"), id=course_id)
    workbook = Workbook()
    summary = workbook.active
    summary.title = "summary"
    codes = AccessCode.objects.filter(course=course)
    prints = AccessCodePrintLog.objects.filter(batch__course=course)
    summary.append(["course", course.title])
    summary.append(["codes", codes.count()])
    summary.append(["sold", codes.filter(sale_status="sold").count()])
    summary.append(["activated", codes.filter(redeemed_count__gt=0).count()])
    summary.append(["inactive", codes.filter(redeemed_count=0).count()])
    summary.append(["printed_cards", prints.aggregate(total=Sum("cards_count"))["total"] or 0])
    summary.append(["gross_syp", (codes.filter(sale_status="sold").aggregate(total=Sum("sold_price_cents"))["total"] or 0) // 100])

    codes_sheet = workbook.create_sheet("codes")
    codes_sheet.append(["code", "sale_status", "student_name", "student_phone", "sold_by", "sold_at", "activated", "sales_center", "batch"])
    for code in codes.select_related("sold_by", "sales_center", "batch").order_by("-created_at"):
        codes_sheet.append([
            code.code,
            code.sale_status,
            code.assigned_student_name,
            code.assigned_student_phone,
            code.sold_by.username if code.sold_by else "",
            code.sold_at.strftime("%Y-%m-%d %H:%M") if code.sold_at else "",
            "yes" if code.redeemed_count else "no",
            code.sales_center.name if code.sales_center else "",
            code.batch.name if code.batch else "",
        ])

    activations = workbook.create_sheet("activations")
    activations.append(["student", "username", "code", "device", "created_at"])
    for grant in AccessGrant.objects.filter(course=course).select_related("user", "access_code").order_by("-created_at"):
        activations.append([
            grant.user.get_full_name() or grant.user.username,
            grant.user.username,
            grant.access_code.code if grant.access_code else "",
            grant.device_fingerprint,
            grant.created_at.strftime("%Y-%m-%d %H:%M"),
        ])
    return _workbook_response(workbook, f"course-report-{course.id}-{timezone.now().strftime('%Y%m%d-%H%M')}.xlsx")


@admin_required
def admin_instructor_report(request, instructor_id):
    from django.db.models import Sum, Count
    from billing.models import AccessCode
    instructor = get_object_or_404(User, id=instructor_id)
    courses = Course.objects.filter(instructor=instructor).select_related("subject")
    
    total_codes = 0
    total_sold = 0
    total_activated = 0
    total_gross = 0
    
    course_data = []
    for course in courses:
        codes = AccessCode.objects.filter(course=course)
        cnt_all = codes.count()
        cnt_sold = codes.filter(sale_status="sold").count()
        cnt_active = codes.filter(redeemed_count__gt=0).count()
        sum_gross = (codes.filter(sale_status="sold").aggregate(total=Sum("sold_price_cents"))["total"] or 0) // 100
        
        course_centers = (
            AccessCode.objects.filter(course=course, sale_status="sold")
            .select_related("sales_center")
            .values("sales_center__name")
            .annotate(sold_count=Count("id"), total_sales=Sum("sold_price_cents"))
            .order_by("-sold_count")
        )
        
        detailed_codes = codes.select_related("sold_by", "sales_center").order_by("-sold_at")
        
        course_data.append({
            "course": course,
            "cnt_all": cnt_all,
            "cnt_sold": cnt_sold,
            "cnt_active": cnt_active,
            "cnt_inactive": cnt_all - cnt_active,
            "sum_gross": sum_gross,
            "centers": course_centers,
            "codes": detailed_codes,
        })
        
        total_codes += cnt_all
        total_sold += cnt_sold
        total_activated += cnt_active
        total_gross += sum_gross

    centers_sales = (
        AccessCode.objects.filter(course__instructor=instructor, sale_status="sold")
        .select_related("sales_center", "sales_center__institute")
        .values("sales_center__name", "sales_center__institute__name")
        .annotate(sold_count=Count("id"), total_sales=Sum("sold_price_cents"))
        .order_by("-sold_count")
    )
    
    from billing.models import AccessGrant
    governorate_sales = (
        AccessGrant.objects.filter(course__instructor=instructor, source="code")
        .select_related("user__student_profile")
        .values("user__student_profile__governorate")
        .annotate(activated_count=Count("id"))
        .order_by("-activated_count")
    )

    discounts_sales = (
        AccessCode.objects.filter(course__instructor=instructor, sale_status="sold")
        .exclude(price_reason="")
        .exclude(price_reason="سعر كامل")
        .values("price_reason")
        .annotate(sold_count=Count("id"), total_sales=Sum("sold_price_cents"))
        .order_by("-sold_count")
    )

    return render(
        request,
        "dashboard/admin_instructor_report.html",
        {
            "instructor": instructor,
            "course_data": course_data,
            "total_codes": total_codes,
            "total_sold": total_sold,
            "total_activated": total_activated,
            "total_inactive": total_codes - total_activated,
            "total_gross": total_gross,
            "centers_sales": centers_sales,
            "governorate_sales": governorate_sales,
            "discounts_sales": discounts_sales,
        }
    )


@admin_required
def admin_instructor_report_export(request, instructor_id):
    from django.db.models import Sum, Count
    from billing.models import AccessCode
    instructor = get_object_or_404(User, id=instructor_id)
    courses = Course.objects.filter(instructor=instructor).select_related("subject")
    
    workbook = Workbook()
    
    # 1. Summary Sheet ("الملخص")
    summary_sheet = workbook.active
    summary_sheet.title = "الملخص الشامل"
    
    summary_sheet.append([f"التقرير المالي وتفصيل مبيعات المدرس: {instructor.get_full_name() or instructor.username}"])
    summary_sheet.append([]) # Empty row
    summary_sheet.append(["الدورة", "المادة", "المسار الأكاديمي", "إجمالي الأكواد", "المباعة", "المفعلة", "غير المفعلة", "إجمالي المبيعات (ل.س)"])
    
    total_all_codes = 0
    total_all_sold = 0
    total_all_activated = 0
    total_all_inactive = 0
    total_all_gross = 0
    
    for course in courses:
        codes = AccessCode.objects.filter(course=course)
        cnt_all = codes.count()
        cnt_sold = codes.filter(sale_status="sold").count()
        cnt_active = codes.filter(redeemed_count__gt=0).count()
        cnt_inactive = cnt_all - cnt_active
        sum_gross = (codes.filter(sale_status="sold").aggregate(total=Sum("sold_price_cents"))["total"] or 0) // 100
        
        summary_sheet.append([
            course.title,
            course.subject.name if course.subject else "",
            f"{course.get_kind_display()} - {course.get_academic_track_display()}",
            cnt_all,
            cnt_sold,
            cnt_active,
            cnt_inactive,
            sum_gross
        ])
        
        total_all_codes += cnt_all
        total_all_sold += cnt_sold
        total_all_activated += cnt_active
        total_all_inactive += cnt_inactive
        total_all_gross += sum_gross
        
    summary_sheet.append([
        "إجمالي المدرس",
        "",
        "",
        total_all_codes,
        total_all_sold,
        total_all_activated,
        total_all_inactive,
        total_all_gross
    ])
    
    # 2. Sales Centers Sheet ("مراكز البيع")
    centers_sheet = workbook.create_sheet("مراكز البيع")
    centers_sheet.append(["مركز البيع", "المعهد", "عدد الأكواد المباعة", "إجمالي المبيعات (ل.س)"])
    
    centers_sales = (
        AccessCode.objects.filter(course__instructor=instructor, sale_status="sold")
        .select_related("sales_center", "sales_center__institute")
        .values("sales_center__name", "sales_center__institute__name")
        .annotate(sold_count=Count("id"), total_sales=Sum("sold_price_cents"))
        .order_by("-sold_count")
    )
    
    total_centers_sold = 0
    total_centers_gross = 0
    
    for row in centers_sales:
        center_name = row["sales_center__name"] or "مبيعات المنصة / مباشرة"
        institute_name = row["sales_center__institute__name"] or "-"
        sold_count = row["sold_count"]
        sales_gross = (row["total_sales"] or 0) // 100
        
        centers_sheet.append([
            center_name,
            institute_name,
            sold_count,
            sales_gross
        ])
        total_centers_sold += sold_count
        total_centers_gross += sales_gross
        
    centers_sheet.append([
        "إجمالي مبيعات المراكز",
        "",
        total_centers_sold,
        total_centers_gross
    ])
    
    # 3. Course sheets ("تفصيل الدورات")
    for course in courses:
        sheet_title = course.title
        for char in "[]*?:/\\":
            sheet_title = sheet_title.replace(char, "")
        sheet_title = sheet_title[:30]
        
        cs = workbook.create_sheet(sheet_title)
        
        # Course Header
        cs.append([f"تفاصيل دورة: {course.title}"])
        cs.append([])
        
        codes = AccessCode.objects.filter(course=course).select_related("sold_by", "sales_center", "batch")
        cnt_all = codes.count()
        cnt_sold = codes.filter(sale_status="sold").count()
        cnt_active = codes.filter(redeemed_count__gt=0).count()
        cnt_inactive = cnt_all - cnt_active
        sum_gross = (codes.filter(sale_status="sold").aggregate(total=Sum("sold_price_cents"))["total"] or 0) // 100
        
        cs.append(["مؤشر الدورة", "القيمة"])
        cs.append(["المادة", course.subject.name if course.subject else ""])
        cs.append(["النوع / الفرع", f"{course.get_kind_display()} - {course.get_academic_track_display()}"])
        cs.append(["حالة الدورة", course.get_status_display()])
        cs.append(["إجمالي الأكواد", cnt_all])
        cs.append(["المباعة", cnt_sold])
        cs.append(["المفعلة", cnt_active])
        cs.append(["إجمالي المبيعات (ل.س)", sum_gross])
        
        cs.append([])
        cs.append([])
        
        cs.append(["مبيعات مراكز البيع لهذه الدورة"])
        cs.append(["مركز البيع", "عدد الأكواد المباعة", "إجمالي المبيعات (ل.س)"])
        
        course_centers = (
            AccessCode.objects.filter(course=course, sale_status="sold")
            .select_related("sales_center")
            .values("sales_center__name")
            .annotate(sold_count=Count("id"), total_sales=Sum("sold_price_cents"))
            .order_by("-sold_count")
        )
        
        for cc in course_centers:
            cs.append([
                cc["sales_center__name"] or "مبيعات المنصة / مباشرة",
                cc["sold_count"],
                (cc["total_sales"] or 0) // 100
            ])
            
        cs.append([])
        cs.append([])
        
        cs.append(["تفاصيل الأكواد والطلاب"])
        cs.append(["الكود", "حالة البيع", "اسم الطالب", "هاتف الطالب", "المباع بواسطة", "تاريخ البيع", "السعر (ل.س)", "مفعل", "مركز البيع"])
        
        for code in codes.order_by("-sold_at"):
            cs.append([
                code.code,
                code.get_sale_status_display(),
                code.assigned_student_name,
                code.assigned_student_phone,
                code.sold_by.username if code.sold_by else "",
                code.sold_at.strftime("%Y-%m-%d %H:%M") if code.sold_at else "",
                (code.sold_price_cents or 0) // 100,
                "نعم" if code.redeemed_count > 0 else "لا",
                code.sales_center.name if code.sales_center else ""
            ])
            
    return _workbook_response(workbook, f"instructor-report-{instructor.id}-{timezone.now().strftime('%Y%m%d-%H%M')}.xlsx")


from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

def _style_workbook(workbook):
    # Premium corporate colors matching the platform
    header_font = Font(name="Cairo", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F2937", end_color="1F2937", fill_type="solid") # Dark Slate Gray
    
    data_font = Font(name="Cairo", size=10)
    thin_border = Border(
        left=Side(style='thin', color='D1D5DB'),
        right=Side(style='thin', color='D1D5DB'),
        top=Side(style='thin', color='D1D5DB'),
        bottom=Side(style='thin', color='D1D5DB')
    )
    
    align_right = Alignment(horizontal='right', vertical='center')
    align_center = Alignment(horizontal='center', vertical='center')

    for sheet in workbook.worksheets:
        # Set RTL layout for Arabic
        sheet.sheet_view.rightToLeft = True
        
        # Ensure gridlines are visible when printing
        if sheet.views.sheetView:
            sheet.views.sheetView[0].showGridLines = True
            
        # Setup page layout optimized for A4 print
        sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
        sheet.page_setup.orientation = sheet.ORIENTATION_PORTRAIT
        sheet.page_setup.fitToWidth = 1
        sheet.page_setup.fitToHeight = 0
        
        # Format rows and cells
        for r_idx, row in enumerate(sheet.iter_rows(), start=1):
            is_header = r_idx == 1
            sheet.row_dimensions[r_idx].height = 28 if is_header else 22
            
            for cell in row:
                cell.border = thin_border
                if is_header:
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = align_center
                else:
                    cell.font = data_font
                    val = str(cell.value or '')
                    # Align numbers and short codes in the center, and text/names to the right
                    if val.isdigit() or len(val) <= 12 or cell.value is None:
                        cell.alignment = align_center
                    else:
                        cell.alignment = align_right
                        
        # Auto-adjust column widths to prevent truncation
        for col in sheet.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                val = str(cell.value or '')
                val_len = len(val.encode('utf-8')) // 2 if any(ord(c) > 127 for c in val) else len(val)
                if val_len > max_len:
                    max_len = val_len
            sheet.column_dimensions[col_letter].width = max(max_len + 4, 12)


def _workbook_response(workbook, filename):
    # Style workbook with Cairo, RTL and A4 printing support before saving
    try:
        _style_workbook(workbook)
    except Exception:
        pass
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@admin_required
def admin_packages(request):
    package_form = CoursePackageForm(prefix="package")
    code_form = PackageCodeGenerateForm(prefix="codes")
    batch_form = PackageCodeBatchForm(prefix="batch")
    sale_form = PackageCodeSaleForm(prefix="sale")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create_package":
            package_form = CoursePackageForm(request.POST, prefix="package")
            if package_form.is_valid():
                package = package_form.save()
                messages.success(request, f"تم إنشاء الباقة {package.name}.")
                return redirect("dashboard:admin_packages")
        elif action == "generate_package_codes":
            code_form = PackageCodeGenerateForm(request.POST, prefix="codes")
            if code_form.is_valid():
                package = code_form.cleaned_data["package"]
                quantity = code_form.cleaned_data["quantity"]
                prefix = code_form.cleaned_data["code_prefix"] or package.code or "PKG"
                created = 0
                for _index in range(quantity):
                    shim = type("CodePrefix", (), {"code_prefix": prefix})()
                    AccessCode.objects.create(
                        code=unique_code(shim),
                        access_type="package",
                        package=package,
                        sale_status="available",
                        max_redemptions=1,
                        valid_until=timezone.now() + timezone.timedelta(days=180),
                        notes=f"كود باقة: {package.name}",
                    )
                    created += 1
                messages.success(request, f"تم توليد {created} كود للباقة {package.name}.")
                return redirect("dashboard:admin_packages")
        elif action == "create_package_batch":
            batch_form = PackageCodeBatchForm(request.POST, prefix="batch")
            if batch_form.is_valid():
                package = request.POST.get("package_id")
                package_obj = get_object_or_404(CoursePackage, id=package)
                batch = batch_form.save(commit=False)
                batch.package = package_obj
                batch.allocated_count = batch_form.cleaned_data["quantity"]
                batch.free_count = batch_form.cleaned_data["quantity"] if batch_form.cleaned_data["free_codes"] else 0
                batch.save()
                created = create_codes_for_batch(
                    batch,
                    batch_form.cleaned_data["quantity"],
                    free_codes=batch_form.cleaned_data["free_codes"],
                )
                messages.success(request, f"تم إنشاء دفعة {batch.name} وتوليد {created} كود للباقة {package_obj.name}.")
                return redirect("dashboard:admin_packages")
        elif action == "sell_package_code":
            sale_form = PackageCodeSaleForm(request.POST, prefix="sale")
            if sale_form.is_valid():
                with transaction.atomic():
                    access_code = AccessCode.objects.select_for_update().get(
                        id=sale_form.cleaned_data["code"].id,
                        access_type="package",
                    )
                    student_phone = sanitize_plain_text(sale_form.cleaned_data["student_phone"])
                    student_name = sanitize_plain_text(sale_form.cleaned_data["student_name"])
                    student, created = User.objects.get_or_create(
                        username=student_phone,
                        defaults={"first_name": student_name, "is_active": True},
                    )
                    if created:
                        student.set_unusable_password()
                        student.save(update_fields=["password"])
                    elif student_name and not student.get_full_name():
                        student.first_name = student_name
                        student.save(update_fields=["first_name"])
                    StudentProfile.objects.get_or_create(
                        user=student,
                        defaults={"phone": student_phone, "track": access_code.package.get_package_track_display() if access_code.package else ""},
                    )
                    access_code.assigned_student_name = student_name
                    access_code.assigned_student_phone = student_phone
                    access_code.sale_status = "sold"
                    access_code.sold_by = request.user
                    access_code.sold_at = timezone.now()
                    price_amount = sale_form.cleaned_data.get("price_amount")
                    if price_amount is not None:
                        access_code.sold_price_cents = int(price_amount * 100)
                        access_code.price_reason = "تحديد يدوي من الإدارة"
                    else:
                        base_price = access_code.package.price_cents if access_code.package else 0
                        from billing.models import DiscountRule
                        now = timezone.now()
                        active_discount = DiscountRule.objects.filter(
                            is_active=True,
                            starts_at__lte=now,
                            expires_at__gte=now
                        ).order_by("-discount_percent").first()
                        if active_discount and base_price > 0:
                            discount_amount = (base_price * active_discount.discount_percent) // 100
                            access_code.sold_price_cents = base_price - discount_amount
                            access_code.price_reason = f"حسم {active_discount.discount_percent}% بمناسبة {active_discount.name}"
                        else:
                            access_code.sold_price_cents = base_price
                            access_code.price_reason = "سعر كامل"
                    access_code.save(update_fields=[
                        "assigned_student_name",
                        "assigned_student_phone",
                        "sale_status",
                        "sold_by",
                        "sold_at",
                        "sold_price_cents",
                        "price_reason",
                        "updated_at",
                    ])
                messages.success(request, f"تم بيع كود الباقة {access_code.code} للطالب {student_name}.")
                return redirect("dashboard:admin_packages")

    packages = (
        CoursePackage.objects.prefetch_related("courses")
        .annotate(
            courses_total=Count("courses", distinct=True),
            codes_total=Count("access_codes", distinct=True),
            sold_total=Count("access_codes", filter=models.Q(access_codes__sale_status="sold"), distinct=True),
            activated_total=Count("access_codes", filter=models.Q(access_codes__redeemed_count__gt=0), distinct=True),
            gross_sales=Sum("access_codes__sold_price_cents", filter=models.Q(access_codes__sale_status="sold")),
        )
        .order_by("name")
    )
    for package in packages:
        eligible_courses = package.eligible_courses_queryset()
        package.eligible_courses_count = eligible_courses.count()
        package.eligible_subjects_count = eligible_courses.values("subject").distinct().count()
    package_codes = AccessCode.objects.filter(access_type="package").select_related("package", "sold_by").order_by("-created_at")[:80]
    package_batches = AccessCodeBatch.objects.filter(package__isnull=False).select_related("package", "institute", "sales_center").order_by("-created_at")[:80]
    return render(
        request,
        "dashboard/admin_packages.html",
        {
            "package_form": package_form,
            "code_form": code_form,
            "batch_form": batch_form,
            "sale_form": sale_form,
            "packages": packages,
            "package_codes": package_codes,
            "package_batches": package_batches,
        },
    )


@admin_required
def admin_content_hub(request):
    from learning.models import Subject, Course
    from .forms import SubjectForm
    from django.utils.text import slugify

    subject_form = SubjectForm()
    
    if request.method == "POST" and request.POST.get("action") == "create_subject":
        subject_form = SubjectForm(request.POST)
        if subject_form.is_valid():
            subject = subject_form.save(commit=False)
            if not subject.slug:
                base_slug = slugify(subject.name, allow_unicode=True) or "subject"
                slug = base_slug
                counter = 2
                while Subject.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                subject.slug = slug
            subject.save()
            messages.success(request, f"تم إضافة المادة {subject.name} بنجاح.")
            return redirect("dashboard:admin_content_hub")

    subjects = Subject.objects.annotate(courses_count=Count("courses")).order_by("name")
    recent_courses = Course.objects.select_related("subject", "instructor", "instructor__instructor_profile").order_by("-created_at")
    
    return render(
        request,
        "dashboard/admin_content_hub.html",
        {
            "subjects": subjects,
            "recent_courses": recent_courses,
            "subject_form": subject_form,
        },
    )


@admin_required
def admin_exams_hub(request):
    from exams.models import Exam, Question, Attempt
    exams = Exam.objects.select_related("course").annotate(questions_count=Count("questions")).order_by("-created_at")
    recent_attempts = Attempt.objects.select_related("user", "exam").order_by("-created_at")[:50]
    
    return render(
        request,
        "dashboard/admin_exams_hub.html",
        {
            "exams": exams,
            "recent_attempts": recent_attempts,
            "total_questions": Question.objects.count(),
        },
    )


@admin_required
def admin_departments(request):
    from accounts.models import AcademicBranch
    from .forms import AcademicBranchForm
    
    if request.method == "POST":
        form = AcademicBranchForm(request.POST)
        if form.is_valid():
            branch = form.save()
            messages.success(request, f"تمت إضافة قسم {branch.name} بنجاح.")
            return redirect("dashboard:admin_departments")
            
    departments = AcademicBranch.objects.all().order_by("sort_order", "name")
    return render(request, "dashboard/admin_departments.html", {
        "departments": departments,
        "department_form": AcademicBranchForm()
    })


@admin_required
def admin_department_edit(request, department_id):
    from accounts.models import AcademicBranch
    from .forms import AcademicBranchForm
    branch = get_object_or_404(AcademicBranch, id=department_id)
    
    if request.method == "POST":
        form = AcademicBranchForm(request.POST, instance=branch)
        if form.is_valid():
            form.save()
            messages.success(request, f"تم تحديث قسم {branch.name} بنجاح.")
        else:
            messages.error(request, "حدث خطأ أثناء التحديث.")
            
    return redirect("dashboard:admin_departments")


@admin_required
def admin_subjects(request):
    from learning.models import Subject
    from .forms import SubjectForm
    from django.utils.text import slugify

    if request.method == "POST":
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save(commit=False)
            if not subject.slug:
                subject.slug = slugify(subject.name, allow_unicode=True) or f"sub-{Subject.objects.count() + 1}"
            subject.save()
            messages.success(request, f"تمت إضافة مادة {subject.name} بنجاح.")
            return redirect("dashboard:admin_subjects")

    subjects = Subject.objects.annotate(
        courses_count=Count("courses", distinct=True),
        units_count=Count("courses__units", distinct=True),
        lessons_count=Count("courses__units__lessons", distinct=True)
    ).order_by("name")
    
    return render(request, "dashboard/admin_subjects.html", {
        "subjects": subjects,
        "subject_form": SubjectForm()
    })


@admin_required
def admin_subject_edit(request, subject_id):
    from learning.models import Subject
    from .forms import SubjectForm
    subject = get_object_or_404(Subject, id=subject_id)
    
    if request.method == "POST":
        form = SubjectForm(request.POST, instance=subject)
        if form.is_valid():
            form.save()
            messages.success(request, f"تم تحديث مادة {subject.name} بنجاح.")
        else:
            messages.error(request, "حدث خطأ أثناء التحديث.")
            
    return redirect("dashboard:admin_subjects")


@admin_required
def admin_units(request):
    from learning.models import Unit, Course
    from .forms import UnitForm
    course_id = request.GET.get("course_id")
    
    if request.method == "POST":
        form = UnitForm(request.POST)
        if form.is_valid():
            unit = form.save()
            messages.success(request, f"تمت إضافة وحدة {unit.title} بنجاح.")
            next_url = request.POST.get("next")
            if next_url and next_url.startswith("/admin-dashboard/content/units/"):
                return redirect(next_url)
            return redirect("dashboard:admin_units")

    units = Unit.objects.select_related("course").annotate(
        lessons_count=Count("lessons")
    ).order_by("course__title", "sort_order")
    
    if course_id:
        units = units.filter(course_id=course_id)
        
    courses = Course.objects.only("id", "title").order_by("title")
    
    return render(request, "dashboard/admin_units.html", {
        "units": units,
        "courses": courses,
        "selected_course_id": course_id,
        "unit_form": UnitForm()
    })


@admin_required
def admin_unit_edit(request, unit_id):
    from learning.models import Unit
    from .forms import UnitForm
    unit = get_object_or_404(Unit, id=unit_id)
    
    if request.method == "POST":
        form = UnitForm(request.POST, instance=unit)
        if form.is_valid():
            form.save()
            messages.success(request, f"تم تحديث وحدة {unit.title} بنجاح.")
        else:
            messages.error(request, "حدث خطأ أثناء تحديث الوحدة.")
    next_url = request.POST.get("next")
    if next_url and next_url.startswith("/admin-dashboard/content/units/"):
        return redirect(next_url)
    return redirect("dashboard:admin_units")


@admin_required
def admin_lessons(request):
    from learning.models import Lesson, Course, Unit
    course_id = request.GET.get("course_id")
    unit_id = request.GET.get("unit_id")
    
    if request.method == "POST":
        unit = get_object_or_404(Unit.objects.select_related("course"), id=request.POST.get("unit"))
        lesson = Lesson.objects.create(
            unit=unit,
            title=request.POST.get("title", "").strip(),
            description=request.POST.get("description", "").strip(),
            lesson_type=request.POST.get("lesson_type", "video"),
            video_url=request.POST.get("video_url", ""),
            duration_seconds=request.POST.get("duration_seconds") or None,
            sort_order=request.POST.get("sort_order") or 0,
            is_free_preview=request.POST.get("is_free_preview") == "on",
        )
        if request.FILES.get("video_file"):
            lesson.video_file = request.FILES["video_file"]
        if request.FILES.get("pdf_file"):
            lesson.pdf_file = request.FILES["pdf_file"]
        if lesson.video_file or lesson.pdf_file:
            lesson.save(update_fields=["video_file", "pdf_file"])
        messages.success(request, f"تمت إضافة درس {lesson.title} بنجاح.")
        next_url = request.POST.get("next")
        if next_url and next_url.startswith("/admin-dashboard/content/lessons/"):
            return redirect(next_url)
        return redirect("dashboard:admin_lessons")

    lessons = Lesson.objects.select_related("unit", "unit__course").order_by("unit__course__title", "unit__sort_order", "sort_order")
    
    if unit_id:
        lessons = lessons.filter(unit_id=unit_id)
    elif course_id:
        lessons = lessons.filter(unit__course_id=course_id)
        
    courses = Course.objects.only("id", "title").order_by("title")
    units = Unit.objects.filter(course_id=course_id) if course_id else Unit.objects.none()
    
    return render(request, "dashboard/admin_lessons.html", {
        "lessons": lessons,
        "courses": courses,
        "units": units,
        "all_units": Unit.objects.select_related("course").all().order_by("course__title", "sort_order"),
        "selected_course_id": course_id,
        "selected_unit_id": unit_id
    })


@admin_required
def admin_lesson_edit(request, lesson_id):
    from learning.models import Lesson, Unit
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    if request.method == "POST":
        if request.POST.get("unit"):
            lesson.unit = get_object_or_404(Unit, id=request.POST.get("unit"))
        lesson.title = request.POST.get("title", "").strip()
        lesson.description = request.POST.get("description", "").strip()
        lesson.lesson_type = request.POST.get("lesson_type", lesson.lesson_type)
        lesson.video_url = request.POST.get("video_url", "")
        lesson.duration_seconds = request.POST.get("duration_seconds") or None
        lesson.sort_order = request.POST.get("sort_order") or 0
        lesson.is_free_preview = request.POST.get("is_free_preview") == "on"
        if request.FILES.get("video_file"):
            lesson.video_file = request.FILES["video_file"]
        if request.FILES.get("pdf_file"):
            lesson.pdf_file = request.FILES["pdf_file"]
        lesson.save()
        messages.success(request, f"تم تحديث درس {lesson.title} بنجاح.")
    next_url = request.POST.get("next")
    if next_url and next_url.startswith("/admin-dashboard/content/lessons/"):
        return redirect(next_url)
    return redirect("dashboard:admin_lessons")


@admin_required
def admin_student_detail(request, user_id):
    student = get_object_or_404(User.objects.select_related("student_profile"), id=user_id)
    
    if request.method == "POST":
        action = request.POST.get("action")
        
        if action == "toggle_status":
            student.is_active = not student.is_active
            student.save()
            status = "نشط" if student.is_active else "موقوف"
            messages.success(request, f"تم تغيير حالة الطالب إلى {status} بنجاح.")
            
        elif action == "reset_devices":
            student.devices.all().delete()
            messages.success(request, "تم تصفير جميع أجهزة الطالب بنجاح.")
            
        elif action == "grant_course":
            course_id = request.POST.get("course_id")
            course = get_object_or_404(Course, id=course_id)
            AccessGrant.objects.get_or_create(
                user=student,
                course=course,
                defaults={"source": "admin_manual"}
            )
            messages.success(request, f"تم تفعيل مادة {course.title} للطالب بنجاح.")
            
        elif action == "revoke_course":
            grant_id = request.POST.get("grant_id")
            AccessGrant.objects.filter(id=grant_id, user=student).delete()
            messages.success(request, "تم سحب صلاحية المادة من الطالب.")

        return redirect("dashboard:admin_student_detail", user_id=student.id)

    # Context data
    all_courses = Course.objects.filter(status="published").order_by("title")
    student_grants = AccessGrant.objects.filter(user=student).select_related("course", "access_code")
    enrolled_course_ids = student_grants.values_list("course_id", flat=True)
    available_courses = all_courses.exclude(id__in=enrolled_course_ids)
    
    attempts = Attempt.objects.filter(user=student).select_related("exam", "exam__course").order_by("-created_at")[:10]
    devices = UserDevice.objects.filter(user=student).order_by("-last_seen_at")

    context = {
        "student": student,
        "available_courses": available_courses,
        "student_grants": student_grants,
        "attempts": attempts,
        "devices": devices,
    }
    return render(request, "dashboard/admin_student_detail.html", context)
