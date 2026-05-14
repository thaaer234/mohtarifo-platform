from django.urls import path
from . import views

app_name = 'accounting_erp'

urlpatterns = [
    path('', views.AccountingDashboardView.as_view(), name='dashboard_root'),
    path('chart/', views.ChartOfAccountsView.as_view(), name='chart_tree'),
    path('journals/', views.JournalListView.as_view(), name='journal_list'),
    path('trial-balance/', views.TrialBalanceView.as_view(), name='trial_balance'),
    path('income-statement/', views.IncomeStatementView.as_view(), name='income_statement'),
    path('balance-sheet/', views.BalanceSheetView.as_view(), name='balance_sheet'),
    path('voucher/<uuid:pk>/', views.VoucherDetailView.as_view(), name='voucher_detail'),
]
