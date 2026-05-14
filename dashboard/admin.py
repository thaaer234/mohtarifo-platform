from django.contrib import admin

from .models import CatalogSection, StudentNotification, OTPVerificationLog


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
