from django.shortcuts import render, redirect
from django.views.generic import TemplateView, ListView, CreateView, DetailView, UpdateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta
import json

from .models import (
    TeacherProductionSession, ProductionTask, ProductionMember,
    ProductionCost, ProductionStatus
)
from .services import SmartSchedulingEngine
from .presentation_service import PresentationBuilder

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


class PresentationView(LoginRequiredMixin, IsProductionStaffMixin, TemplateView):
    """
    Interactive Presentation View for Exam Production Program.
    Generates a full slideshow with grid tables, teacher cards,
    smart scheduling, and pricing.
    """
    template_name = 'production_management/presentation.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        presentation = PresentationBuilder.build_presentation_data()
        context.update(presentation)

        # Serialize dates for JavaScript
        for slide in context.get('grid_slides', []):
            for row in slide:
                row['exam_date_str'] = row['exam_date'].strftime('%d-%m-%Y') if row['exam_date'] else ''
                row['shooting_date_str'] = row['shooting_date'].strftime('%d-%m-%Y') if row['shooting_date'] else ''

        for card in context.get('teacher_cards', []):
            for session in card['sessions']:
                session['exam_date_str'] = session['exam_date'].strftime('%d-%m-%Y') if session['exam_date'] else ''
                session['shooting_date_str'] = session['shooting_date'].strftime('%d-%m-%Y') if session['shooting_date'] else ''

        return context


class PresentationAPIView(LoginRequiredMixin, IsProductionStaffMixin, TemplateView):
    """JSON API for presentation data."""

    def get(self, request, *args, **kwargs):
        presentation = PresentationBuilder.build_presentation_data()

        # Convert dates to strings for JSON
        def serialize_row(row):
            return {
                'id': row['id'],
                'teacher_name': row['teacher_name'],
                'subject': row['subject'],
                'branch': row['branch'],
                'branch_code': row['branch_code'],
                'exam_date': row['exam_date'].strftime('%d-%m-%Y') if row['exam_date'] else '',
                'shooting_date': row['shooting_date'].strftime('%d-%m-%Y') if row['shooting_date'] else '',
                'status': row['status'],
                'status_display': row['status_display'],
                'platform_price': float(row['platform_price']),
                'price_display': row['price_display'],
                'shoot_hours': row['shoot_hours'],
                'edit_hours': row['edit_hours'],
            }

        data = {
            'rows': [serialize_row(r) for r in presentation['all_rows']],
            'stats': {
                'total_sessions': presentation['stats']['total_sessions'],
                'total_teachers': presentation['stats']['total_teachers'],
                'total_revenue': presentation['stats']['total_revenue'],
            },
        }
        return JsonResponse(data, json_dumps_params={'ensure_ascii': False})


class TeacherCardsPrintView(LoginRequiredMixin, IsProductionStaffMixin, TemplateView):
    """Separate print page for teacher cards with premium design."""
    template_name = 'production_management/teacher_cards_print.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        presentation = PresentationBuilder.build_presentation_data()

        # Add teacher photo paths from Course model if available
        from learning.models import Course
        for card in presentation.get('teacher_cards', []):
            # Try to find teacher photo from courses
            teacher_name = card['name']
            course = Course.objects.filter(
                instructor__first_name__icontains=teacher_name.split()[0] if teacher_name.split() else ''
            ).first()
            if course and course.teacher_photo:
                card['photo_url'] = course.teacher_photo.url
            else:
                card['photo_url'] = None

            for session in card['sessions']:
                session['exam_date_str'] = session['exam_date'].strftime('%d-%m-%Y') if session['exam_date'] else ''
                session['shooting_date_str'] = session['shooting_date'].strftime('%d-%m-%Y') if session['shooting_date'] else ''

        context.update(presentation)
        return context
