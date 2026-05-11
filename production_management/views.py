from django.shortcuts import render, redirect
from django.views.generic import TemplateView, ListView, CreateView, DetailView, UpdateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta

from .models import (
    TeacherProductionSession, ProductionTask, ProductionMember,
    ProductionCost, ProductionStatus
)
from .services import SmartSchedulingEngine

class IsProductionStaffMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser or hasattr(self.request.user, 'production_profile')

class DashboardView(LoginRequiredMixin, IsProductionStaffMixin, TemplateView):
    template_name = 'production_management/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sessions = TeacherProductionSession.objects.all()
        
        context['total_sessions'] = sessions.count()
        context['scheduled_sessions'] = sessions.filter(status=ProductionStatus.SCHEDULED).count()
        context['completed_sessions'] = sessions.filter(status=ProductionStatus.COMPLETED).count()
        context['delayed_sessions'] = sessions.filter(status=ProductionStatus.DELAYED).count()
        
        # Calculate Costs & Profits
        costs = ProductionCost.objects.aggregate(
            total_platform=Sum('platform_price'),
            total_teacher=Sum('teacher_cost'),
            total_production=Sum('production_cost')
        )
        total_platform = costs['total_platform'] or 0
        total_teacher = costs['total_teacher'] or 0
        total_production = costs['total_production'] or 0
        
        context['total_production_cost'] = total_teacher + total_production
        context['platform_profit'] = total_platform - context['total_production_cost']
        
        context['total_teachers'] = sessions.values('teacher_name').distinct().count()
        
        # Priorities / Alerts
        context['priority_alerts'] = sessions.filter(
            status__in=[ProductionStatus.SHOOTING, ProductionStatus.EDITING],
            exam_date__lte=timezone.now().date() + timedelta(days=5)
        )
        return context

class SessionListView(LoginRequiredMixin, IsProductionStaffMixin, ListView):
    template_name = 'production_management/session_list.html'
    model = TeacherProductionSession
    context_object_name = 'sessions'
    paginate_by = 50

    def get_queryset(self):
        qs = super().get_queryset().select_related('room', 'cost')
        search = self.request.GET.get('q')
        if search:
            qs = qs.filter(Q(teacher_name__icontains=search) | Q(subject__icontains=search))
        
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
            
        return qs.order_by('-priority', 'exam_date')

class SessionCreateView(LoginRequiredMixin, IsProductionStaffMixin, CreateView):
    template_name = 'production_management/session_form.html'
    model = TeacherProductionSession
    fields = ['teacher_name', 'subject', 'branch', 'exam_date', 'exam_time']
    success_url = reverse_lazy('production_management:session_list')

    def form_valid(self, form):
        # Auto Scheduling Logic
        response = super().form_valid(form)
        schedule = SmartSchedulingEngine.calculate_optimal_schedule(
            form.instance.exam_date,
            form.instance.branch
        )
        form.instance.shooting_date = schedule['recommended_shooting_date']
        form.instance.save()
        
        # Initialize Cost
        ProductionCost.objects.create(session=form.instance)
        
        return response

class SessionDetailView(LoginRequiredMixin, IsProductionStaffMixin, DetailView):
    template_name = 'production_management/session_detail.html'
    model = TeacherProductionSession
    context_object_name = 'session'

class TeacherCardsView(LoginRequiredMixin, IsProductionStaffMixin, ListView):
    template_name = 'production_management/teacher_cards.html'
    model = TeacherProductionSession
    context_object_name = 'sessions'

    def get_queryset(self):
        return super().get_queryset().select_related('cost')

class KanbanBoardView(LoginRequiredMixin, IsProductionStaffMixin, TemplateView):
    template_name = 'production_management/kanban_board.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sessions = TeacherProductionSession.objects.all()
        context['statuses'] = ProductionStatus.choices
        context['sessions_by_status'] = {
            status[0]: sessions.filter(status=status[0])
            for status in ProductionStatus.choices
        }
        return context

class CalendarView(LoginRequiredMixin, IsProductionStaffMixin, TemplateView):
    template_name = 'production_management/calendar.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sessions'] = TeacherProductionSession.objects.all()
        return context

class TeamManagementView(LoginRequiredMixin, IsProductionStaffMixin, ListView):
    template_name = 'production_management/team.html'
    model = ProductionMember
    context_object_name = 'members'

class FinancialStatsView(LoginRequiredMixin, IsProductionStaffMixin, TemplateView):
    template_name = 'production_management/financial.html'

class PrintEngineView(LoginRequiredMixin, IsProductionStaffMixin, TemplateView):
    template_name = 'production_management/print.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sessions'] = TeacherProductionSession.objects.all().order_by('exam_date')
        return context

class ScannerView(LoginRequiredMixin, IsProductionStaffMixin, TemplateView):
    template_name = 'production_management/scanner.html'
