from django.contrib import admin
from .models import Account, CostCenter, JournalEntry, JournalLine

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('code', 'display_name', 'account_type', 'is_group', 'is_active')
    list_filter = ('account_type', 'is_group', 'is_active')
    search_fields = ('code', 'name', 'name_ar')

@admin.register(CostCenter)
class CostCenterAdmin(admin.ModelAdmin):
    list_display = ('code', 'name_ar', 'cost_center_type', 'is_active')
    search_fields = ('code', 'name', 'name_ar')

class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 2

@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ('reference', 'posting_date', 'entry_type', 'is_posted', 'get_total_debit')
    list_filter = ('entry_type', 'is_posted', 'posting_date')
    search_fields = ('reference', 'memo')
    inlines = [JournalLineInline]
