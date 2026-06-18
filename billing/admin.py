from django import forms
from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path

from .models import (
    AccessCode,
    AccessCodeBatch,
    AccessCodePrintLog,
    AccessGrant,
    Coupon,
    CoursePackage,
    CoursePurchase,
    DiscountRule,
    Institute,
    Payment,
    Plan,
    SalesCenter,
    Subscription,
    UserDevice,
    BillingSetting,
    PlatformExpense,
)
from import_export.admin import ImportExportModelAdmin
from .services import create_codes_from_upload


@admin.register(Institute)
class InstituteAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_name", "phone", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "contact_name", "phone")


@admin.register(SalesCenter)
class SalesCenterAdmin(admin.ModelAdmin):
    list_display = ("name", "institute", "phone", "is_active", "created_at")
    list_filter = ("is_active", "institute")
    search_fields = ("name", "phone", "address", "institute__name")


@admin.register(AccessCodeBatch)
class AccessCodeBatchAdmin(admin.ModelAdmin):
    list_display = ("name", "course", "package", "institute", "sales_center", "allocated_count", "free_count", "sold_count", "redeemed_count", "created_at")
    list_filter = ("course", "package", "institute", "sales_center")
    search_fields = ("name", "course__title", "package__name", "institute__name", "sales_center__name")
    autocomplete_fields = ("course", "package", "institute", "sales_center")
    change_form_template = "admin/billing/accesscodebatch/change_form.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:batch_id>/import-students/",
                self.admin_site.admin_view(self.import_students_view),
                name="billing_accesscodebatch_import_students",
            )
        ]
        return custom_urls + urls

    def import_students_view(self, request, batch_id):
        batch = self.get_object(request, batch_id)
        if batch is None:
            self.message_user(request, "دفعة الأكواد غير موجودة.", messages.ERROR)
            return redirect("admin:billing_accesscodebatch_changelist")

        if request.method == "POST":
            form = StudentCodeImportForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    created = create_codes_from_upload(batch, form.cleaned_data["file"], form.cleaned_data["free_codes"])
                except forms.ValidationError as exc:
                    form.add_error("file", exc)
                else:
                    self.message_user(request, f"تم إنشاء {created} كود وربطها بالطلاب.", messages.SUCCESS)
                    return redirect("admin:billing_accesscodebatch_change", batch.id)
        else:
            form = StudentCodeImportForm(initial={"free_codes": True})

        return render(
            request,
            "admin/billing/accesscodebatch/import_students.html",
            {
                **self.admin_site.each_context(request),
                "opts": self.model._meta,
                "batch": batch,
                "form": form,
                "title": f"استيراد طلاب: {batch.name}",
            },
        )


@admin.register(AccessCodePrintLog)
class AccessCodePrintLogAdmin(admin.ModelAdmin):
    list_display = ("batch", "printed_by", "cards_count", "created_at")
    list_filter = ("batch__course", "batch__sales_center", "printed_by")
    search_fields = ("batch__name", "batch__course__title", "printed_by__username", "notes")
    autocomplete_fields = ("batch", "printed_by")


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "billing_period", "price_cents", "currency", "is_active")
    list_filter = ("billing_period", "is_active")
    search_fields = ("name", "code")
    prepopulated_fields = {"code": ("name",)}


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "provider", "status", "starts_at", "renews_at", "ends_at")
    list_filter = ("status", "plan", "provider")
    search_fields = ("user__username", "provider_subscription_id")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "amount_cents", "currency", "status", "created_at")
    list_filter = ("status", "provider", "currency")
    search_fields = ("user__username", "provider_payment_id")


@admin.register(CoursePurchase)
class CoursePurchaseAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "payment", "created_at")
    search_fields = ("user__username", "course__title")


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_percent", "discount_cents", "redeemed_count", "is_active", "expires_at")
    list_filter = ("is_active",)
    search_fields = ("code",)


@admin.register(CoursePackage)
class CoursePackageAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "package_track", "auto_include_shared", "price_cents", "is_active", "created_at")
    list_filter = ("package_track", "auto_include_shared", "is_active")
    search_fields = ("name", "code", "notes", "courses__title")
    prepopulated_fields = {"code": ("name",)}
    filter_horizontal = ("courses",)


@admin.register(AccessCode)
class AccessCodeAdmin(ImportExportModelAdmin):
    list_display = (
        "code",
        "access_type",
        "course",
        "package",
        "batch",
        "institute",
        "sales_center",
        "assigned_student_name",
        "assigned_student_phone",
        "sale_status",
        "sold_by",
        "sold_at",
        "sold_price_cents",
        "price_reason",
        "is_free_code",
        "status",
        "redeemed_count",
        "max_redemptions",
    )
    list_filter = ("access_type", "status", "sale_status", "is_free_code", "course", "package", "batch", "institute", "sales_center", "plan", "sold_by")
    search_fields = ("code", "course__title", "package__name", "lesson__title", "assigned_student_name", "assigned_student_phone", "sold_by__username", "notes")
    autocomplete_fields = ("course", "lesson", "plan", "package", "batch", "institute", "sales_center", "sold_by")


@admin.register(AccessGrant)
class AccessGrantAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "lesson", "source", "access_code", "print_password", "print_quota", "main_pdf_printed", "file1_printed", "file2_printed", "device_fingerprint", "starts_at", "expires_at", "created_at")
    list_filter = ("source", "course", "access_code__institute", "access_code__sales_center")
    search_fields = ("user__username", "user__email", "course__title", "lesson__title", "access_code__code", "device_fingerprint")
    autocomplete_fields = ("user", "course", "lesson", "access_code")
    actions = ("clear_device_lock",)

    @admin.action(description="فك قفل الجهاز للصلاحيات المحددة")
    def clear_device_lock(self, request, queryset):
        updated = queryset.update(device_fingerprint="")
        self.message_user(request, f"تم فك قفل الجهاز عن {updated} صلاحية. سيتربط الوصول بالجهاز التالي عند استخدام الطالب.", messages.SUCCESS)


@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ("user", "fingerprint", "label", "is_active", "first_seen_at", "last_seen_at")
    list_filter = ("is_active",)
    search_fields = ("user__username", "user__email", "fingerprint", "label", "user_agent")
    actions = ("deactivate_devices", "activate_devices")

    @admin.action(description="تعطيل الأجهزة المحددة")
    def deactivate_devices(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"تم تعطيل {updated} جهاز.", messages.SUCCESS)

    @admin.action(description="تفعيل الأجهزة المحددة")
    def activate_devices(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"تم تفعيل {updated} جهاز.", messages.SUCCESS)


class StudentCodeImportForm(forms.Form):
    file = forms.FileField(
        label="ملف الطلاب",
        help_text="CSV أو XLSX. الأعمدة المطلوبة: name و phone. يمكن استخدام الاسماء العربية: الاسم، الهاتف.",
    )
    free_codes = forms.BooleanField(label="أكواد مجانية", required=False, initial=True)


@admin.register(DiscountRule)
class DiscountRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "starts_at", "expires_at", "discount_percent", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(BillingSetting)
class BillingSettingAdmin(admin.ModelAdmin):
    list_display = ("label", "key", "value_numeric")
    search_fields = ("label", "key")


@admin.register(PlatformExpense)
class PlatformExpenseAdmin(admin.ModelAdmin):
    list_display = ("title", "amount_syp", "amount_usd", "course", "expense_type", "status", "created_at")
    list_filter = ("course", "expense_type", "status", "created_at")
    search_fields = ("title", "course__title")
    autocomplete_fields = ("course",)
    fields = ("title", "amount_syp", "amount_usd", "course", "expense_type", "status", "created_at")

