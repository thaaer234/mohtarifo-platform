from django.contrib import admin
from .models import Account, CostCenter, JournalEntry, JournalLine
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

class JournalLineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
            
        total_debit = 0
        total_credit = 0
        line_count = 0
        
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
            if form.cleaned_data:
                total_debit += form.cleaned_data.get('debit_amount') or 0
                total_credit += form.cleaned_data.get('credit_amount') or 0
                line_count += 1
                
        if line_count < 2:
            raise ValidationError("القيد المحاسبي يجب أن يحتوي على سطرين على الأقل (مدين ودائن).")
            
        if total_debit != total_credit:
            raise ValidationError(f"القيد غير متوازن حسابياً! مجموع المدين ({total_debit}) لا يساوي مجموع الدائن ({total_credit}).")

class JournalLineInline(admin.TabularInline):
    model = JournalLine
    formset = JournalLineFormSet
    extra = 2
    autocomplete_fields = ['account', 'cost_center']

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'is_group', 'parent')
    list_filter = ('category', 'is_group')
    search_fields = ('code', 'name')
    ordering = ('code',)

@admin.register(CostCenter)
class CostCenterAdmin(admin.ModelAdmin):
    list_display = ('name', 'center_type', 'created_at')
    list_filter = ('center_type',)
    search_fields = ('name',)

@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ('reference', 'posting_date', 'memo', 'created_at')
    list_filter = ('posting_date',)
    search_fields = ('reference', 'memo')
    inlines = [JournalLineInline]
    date_hierarchy = 'posting_date'
