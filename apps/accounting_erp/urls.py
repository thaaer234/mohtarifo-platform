from django.urls import path
from . import views

app_name = 'accounting_erp'

urlpatterns = [
    path('', views.AccountingDashboardView.as_view(), name='dashboard_root'),
    path('chart/', views.ChartOfAccountsView.as_view(), name='chart_tree'),
    path('journals/', views.JournalListView.as_view(), name='journal_list'),
    path('trial-balance/', views.TrialBalanceView.as_view(), name='trial_balance'),
    path('trial-balance/export/', views.ExportTrialBalanceExcelView.as_view(), name='export_trial_balance'),
    path('voucher/<uuid:pk>/print/', views.VoucherPrintView.as_view(), name='voucher_print'),
]
