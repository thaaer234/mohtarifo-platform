from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.utils import timezone

class ProductionMember(models.Model):
    class RoleChoices(models.TextChoices):
        MANAGER = 'manager', _('Production Manager')
        CAMERAMAN = 'cameraman', _('Cameraman')
        EDITOR = 'editor', _('Editor')
        DESIGNER = 'designer', _('Designer')
        REVIEWER = 'reviewer', _('Reviewer')
        UPLOADER = 'uploader', _('Uploader')

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='production_profile')
    role = models.CharField(max_length=20, choices=RoleChoices.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.get_role_display()}"

class ProductionRoom(models.Model):
    name = models.CharField(max_length=100)
    capacity = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    equipment_details = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class ProductionStatus(models.TextChoices):
    SCHEDULED = 'scheduled', _('مجدول')
    SHOOTING = 'shooting', _('تصوير')
    EDITING = 'editing', _('مونتاج')
    REVIEWING = 'reviewing', _('مراجعة')
    DESIGNING = 'designing', _('تصميم')
    READY = 'ready', _('جاهز للرفع')
    COMPLETED = 'completed', _('مكتمل')
    DELAYED = 'delayed', _('متأخر')
    CANCELED = 'canceled', _('ملغي')

class TeacherProductionSession(models.Model):
    class BranchChoices(models.TextChoices):
        SCIENCE = 'science', _('علمي')
        LITERAL = 'literal', _('أدبي')
        NINTH = 'ninth', _('تاسع')
        OTHER = 'other', _('أخرى')

    # Link to external Teacher model if exists, otherwise text
    teacher_name = models.CharField(max_length=255) 
    subject = models.CharField(max_length=255)
    branch = models.CharField(max_length=50, choices=BranchChoices.choices)
    
    exam_date = models.DateField()
    exam_time = models.TimeField(null=True, blank=True)
    
    shooting_date = models.DateField(null=True, blank=True)
    shooting_time = models.TimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=ProductionStatus.choices, default=ProductionStatus.SCHEDULED)
    priority = models.IntegerField(default=1) # Higher is higher priority
    
    room = models.ForeignKey(ProductionRoom, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.teacher_name} - {self.subject} ({self.get_branch_display()})"

class ProductionTask(models.Model):
    class TaskTypeChoices(models.TextChoices):
        SHOOTING = 'shooting', _('Shooting')
        EDITING = 'editing', _('Editing')
        DESIGNING = 'designing', _('Designing')
        REVIEWING = 'reviewing', _('Reviewing')
        UPLOADING = 'uploading', _('Uploading')

    session = models.ForeignKey(TeacherProductionSession, on_delete=models.CASCADE, related_name='tasks')
    task_type = models.CharField(max_length=20, choices=TaskTypeChoices.choices)
    assigned_to = models.ForeignKey(ProductionMember, on_delete=models.SET_NULL, null=True, blank=True)
    
    estimated_duration_hours = models.DecimalField(max_digits=5, decimal_places=2)
    actual_duration_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    
    is_completed = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.get_task_type_display()} for {self.session}"

class ProductionTimeline(models.Model):
    session = models.ForeignKey(TeacherProductionSession, on_delete=models.CASCADE, related_name='timeline')
    status = models.CharField(max_length=20, choices=ProductionStatus.choices)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

class ProductionCost(models.Model):
    session = models.OneToOneField(TeacherProductionSession, on_delete=models.CASCADE, related_name='cost')
    platform_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    teacher_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    production_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    
    @property
    def platform_profit(self):
        return self.platform_price - (self.teacher_cost + self.production_cost)

    def __str__(self):
        return f"Costs for {self.session}"

class ProductionAlert(models.Model):
    class AlertLevel(models.TextChoices):
        INFO = 'info', _('Info')
        WARNING = 'warning', _('Warning')
        CRITICAL = 'critical', _('Critical')

    session = models.ForeignKey(TeacherProductionSession, on_delete=models.CASCADE, related_name='alerts', null=True, blank=True)
    level = models.CharField(max_length=10, choices=AlertLevel.choices, default=AlertLevel.INFO)
    message = models.CharField(max_length=255)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_level_display()}: {self.message}"

class ProductionSchedule(models.Model):
    date = models.DateField(unique=True)
    is_working_day = models.BooleanField(default=True)
    daily_capacity_hours = models.DecimalField(max_digits=6, decimal_places=2, default=24.0)
    notes = models.TextField(blank=True, null=True)


class ExamScheduleEntry(models.Model):
    """Stores exam dates per subject/branch - fed from the scanner or manual entry."""
    class BranchChoices(models.TextChoices):
        SCIENCE = 'science', _('علمي')
        LITERAL = 'literal', _('أدبي')
        NINTH = 'ninth', _('تاسع')

    subject_name = models.CharField(max_length=255, verbose_name=_('اسم المادة'))
    branch = models.CharField(max_length=50, choices=BranchChoices.choices, verbose_name=_('الفرع'))
    exam_date = models.DateField(verbose_name=_('تاريخ الامتحان'))
    exam_time = models.TimeField(null=True, blank=True, verbose_name=_('وقت الامتحان'))
    duration = models.CharField(max_length=10, default='2', verbose_name=_('المدة (ساعات)'))
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('موعد امتحان')
        verbose_name_plural = _('جدول الامتحانات')
        unique_together = [('subject_name', 'branch')]
        ordering = ['exam_date']

    def __str__(self):
        return f"{self.subject_name} ({self.get_branch_display()}) - {self.exam_date}"
