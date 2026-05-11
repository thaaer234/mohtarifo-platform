from django.urls import path
from . import views

app_name = 'production_management'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('sessions/', views.SessionListView.as_view(), name='session_list'),
    path('sessions/create/', views.SessionCreateView.as_view(), name='session_create'),
    path('sessions/<int:pk>/', views.SessionDetailView.as_view(), name='session_detail'),
    path('teachers/', views.TeacherCardsView.as_view(), name='teacher_cards'),
    path('kanban/', views.KanbanBoardView.as_view(), name='kanban_board'),
    path('calendar/', views.CalendarView.as_view(), name='calendar'),
    path('team/', views.TeamManagementView.as_view(), name='team_management'),
    path('financial/', views.FinancialStatsView.as_view(), name='financial_stats'),
    path('print/', views.PrintEngineView.as_view(), name='print_engine'),
    path('scanner/', views.ScannerView.as_view(), name='scanner'),
    path('presentation/', views.PresentationView.as_view(), name='presentation'),
    path('presentation/cards/', views.TeacherCardsPrintView.as_view(), name='teacher_cards_print'),
    path('api/presentation/', views.PresentationAPIView.as_view(), name='presentation_api'),
]
