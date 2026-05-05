from django.contrib import admin

from .models import AcademicBranch, Governorate, InstructorProfile, StudentProfile


@admin.register(AcademicBranch)
class AcademicBranchAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    search_fields = ("name",)


@admin.register(Governorate)
class GovernorateAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    search_fields = ("name",)


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "grade", "track", "governorate", "current_level", "xp", "level")
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name", "phone")
    list_filter = ("grade", "track", "governorate", "level")


@admin.register(InstructorProfile)
class InstructorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "specialty", "status", "created_at")
    search_fields = ("user__username", "user__email", "specialty")
    list_filter = ("status", "specialty")

# Register your models here.
