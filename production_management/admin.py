from django.contrib import admin
from .models import (
    ProductionMember, ProductionRoom, TeacherProductionSession,
    ProductionTask, ProductionTimeline, ProductionCost, ProductionAlert,
    ProductionSchedule
)

@admin.register(ProductionMember)
class ProductionMemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active')

@admin.register(ProductionRoom)
class ProductionRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'capacity', 'is_active')

@admin.register(TeacherProductionSession)
class TeacherProductionSessionAdmin(admin.ModelAdmin):
    list_display = ('teacher_name', 'subject', 'branch', 'exam_date', 'shooting_date', 'status', 'priority')
    list_filter = ('status', 'branch', 'exam_date', 'shooting_date')
    search_fields = ('teacher_name', 'subject')

@admin.register(ProductionTask)
class ProductionTaskAdmin(admin.ModelAdmin):
    list_display = ('session', 'task_type', 'assigned_to', 'is_completed', 'start_time', 'end_time')
    list_filter = ('task_type', 'is_completed')

@admin.register(ProductionTimeline)
class ProductionTimelineAdmin(admin.ModelAdmin):
    list_display = ('session', 'status', 'created_at', 'changed_by')

@admin.register(ProductionCost)
class ProductionCostAdmin(admin.ModelAdmin):
    list_display = ('session', 'platform_price', 'teacher_cost', 'production_cost', 'platform_profit')

@admin.register(ProductionAlert)
class ProductionAlertAdmin(admin.ModelAdmin):
    list_display = ('session', 'level', 'message', 'is_resolved', 'created_at')
    list_filter = ('level', 'is_resolved')

@admin.register(ProductionSchedule)
class ProductionScheduleAdmin(admin.ModelAdmin):
    list_display = ('date', 'is_working_day', 'daily_capacity_hours')

