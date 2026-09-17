from django.contrib import admin

from .models import CatalogSection, NotebookOrder, NotebookProduct, StudentNotification, OTPVerificationLog, WhatsAppTemplate, WhatsAppMessageLog


@admin.register(CatalogSection)
class CatalogSectionAdmin(admin.ModelAdmin):
    list_display = ("label", "kind", "track", "sort_order", "is_visible")
    list_filter = ("is_visible", "kind", "track")
    search_fields = ("label",)


@admin.register(StudentNotification)
class StudentNotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "notification_type", "read_at", "created_at")
    list_filter = ("notification_type", "read_at")
    search_fields = ("user__username", "title", "body")


@admin.register(OTPVerificationLog)
class OTPVerificationLogAdmin(admin.ModelAdmin):
    list_display = ("phone", "user", "purpose", "is_verified", "created_at", "verified_at")
    list_filter = ("is_verified", "purpose", "created_at")
    search_fields = ("phone", "user__username", "code")
    readonly_fields = ("created_at",)


@admin.register(WhatsAppTemplate)
class WhatsAppTemplateAdmin(admin.ModelAdmin):
    list_display = ("title", "created_at")
    search_fields = ("title", "content")


@admin.register(WhatsAppMessageLog)
class WhatsAppMessageLogAdmin(admin.ModelAdmin):
    list_display = ("phone", "sent_at", "raw_text_hash")
    search_fields = ("phone", "sent_text")
    readonly_fields = ("sent_at",)


@admin.register(NotebookProduct)
class NotebookProductAdmin(admin.ModelAdmin):
    list_display = ("title", "instructor", "price_syp", "stock", "is_active", "created_at")
    list_filter = ("is_active", "instructor")
    search_fields = ("title", "instructor__first_name", "instructor__username")
    autocomplete_fields = ("instructor", "course")


@admin.register(NotebookOrder)
class NotebookOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "student", "driver", "phone", "payment_method", "status", "delivery_scheduled_at", "driver_updated_at", "created_at")
    list_filter = ("status", "driver", "payment_method", "governorate", "created_at")
    search_fields = ("recipient_name", "phone", "address", "product__title", "payment_reference")
    autocomplete_fields = ("product", "student", "driver")
    readonly_fields = ("unit_price_syp", "driver_updated_at", "created_at", "updated_at")

