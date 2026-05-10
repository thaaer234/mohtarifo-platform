from django.urls import path
from . import views

app_name = 'accounting_erp'

urlpatterns = [
    path('chart/', views.ChartOfAccountsView.as_view(), name='chart_tree'),
    path('vouchers/', views.JournalVoucherListView.as_view(), name='journal_list'),
    path('vouchers/<uuid:pk>/', views.JournalVoucherDetailView.as_view(), name='voucher_detail'),
    path('trial-balance/', views.TrialBalanceReportView.as_view(), name='trial_balance'),

    path('income-statement/', views.IncomeStatementReportView.as_view(), name='income_statement'),
    path('export-excel/<str:report_type>/', views.UniversalErpExcelExportView.as_view(), name='export_excel'),


]
