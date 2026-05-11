from django.shortcuts import render, redirect
from django.views.generic import TemplateView, ListView, CreateView, DetailView, UpdateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from datetime import timedelta, date, time as dt_time
import json

from .models import (
    TeacherProductionSession, ProductionTask, ProductionMember,
    ProductionCost, ProductionStatus, ExamScheduleEntry
)
from .services import SmartSchedulingEngine
from .presentation_service import PresentationBuilder
from learning.models import Course

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['exam_entries'] = ExamScheduleEntry.objects.filter(is_active=True)
        context['branches'] = ExamScheduleEntry.BranchChoices.choices
        return context

    def post(self, request, *args, **kwargs):
        """Save exam schedule entries from scanner form."""
        action = request.POST.get('action')

        if action == 'save_entries':
            subjects = request.POST.getlist('subject_name')
            branches = request.POST.getlist('branch')
            dates = request.POST.getlist('exam_date')
            times = request.POST.getlist('exam_time')
            durations = request.POST.getlist('duration')

            saved = 0
            for i in range(len(subjects)):
                if not subjects[i] or not dates[i]:
                    continue
                exam_time = None
                if i < len(times) and times[i]:
                    try:
                        parts = times[i].split(':')
                        exam_time = dt_time(int(parts[0]), int(parts[1]))
                    except (ValueError, IndexError):
                        exam_time = dt_time(9, 0)

                ExamScheduleEntry.objects.update_or_create(
                    subject_name=subjects[i].strip(),
                    branch=branches[i] if i < len(branches) else 'ninth',
                    defaults={
                        'exam_date': dates[i],
                        'exam_time': exam_time,
                        'duration': durations[i] if i < len(durations) else '2',
                        'is_active': True,
                    }
                )
                saved += 1

            # Auto-generate production sessions from courses
            self._auto_generate_sessions()
            return redirect('production_management:scanner')

        elif action == 'delete_entry':
            entry_id = request.POST.get('entry_id')
            ExamScheduleEntry.objects.filter(id=entry_id).delete()
            return redirect('production_management:scanner')

        elif action == 'add_entry':
            ExamScheduleEntry.objects.update_or_create(
                subject_name=request.POST.get('subject_name', '').strip(),
                branch=request.POST.get('branch', 'ninth'),
                defaults={
                    'exam_date': request.POST.get('exam_date'),
                    'exam_time': dt_time(8, 30),
                    'duration': request.POST.get('duration', '2'),
                    'is_active': True,
                }
            )
            self._auto_generate_sessions(clear_existing=True)
            return redirect('production_management:scanner')

        elif action == 'regenerate_schedule':
            # The master button requested by the user
            self._auto_generate_sessions(clear_existing=True)
            return redirect('production_management:scanner')


        return redirect('production_management:scanner')

    def _auto_generate_sessions(self, clear_existing=True):
        """Auto-generate production sessions with strict collision solver."""
        exam_entries = ExamScheduleEntry.objects.filter(is_active=True)
        if not exam_entries.exists():
            return

        if clear_existing:
            TeacherProductionSession.objects.filter(status='scheduled').delete()

        TRACK_MAP = {'scientific': 'science', 'literary': 'literal', 'ninth': 'ninth', 'general': 'literal'}
        courses = Course.objects.filter(
            status__in=['published', 'review', 'draft']
        ).select_related('subject', 'instructor')

        schedule_date = PresentationBuilder.SCHEDULE_START_DATE
        
        from datetime import date as d_t
        EID_BLOCK = [d_t(2026, 5, 27), d_t(2026, 5, 28), d_t(2026, 5, 29)]
        HARD_END = d_t(2026, 6, 22)
        
        allocations = {} 
        # ── PRE-LOAD EXISTING RESERVATIONS TO PREVENT COLLISION ──
        existing_active = TeacherProductionSession.objects.exclude(status='scheduled').filter(shooting_date__isnull=False)
        for ex_sess in existing_active:
            w_d = ex_sess.shooting_date
            a_cnt = 0
            tries = 0
            while a_cnt < ex_sess.smart_duration and tries < 20:
                tries += 1
                if w_d not in EID_BLOCK and w_d.weekday() != 4:
                    allocations[w_d] = allocations.get(w_d, 0) + 1
                    a_cnt += 1
                w_d += timedelta(days=1)
        items = []
        for c in courses:
            br = TRACK_MAP.get(c.academic_track, 'ninth')
            match = self._find_exam(c.subject.name, br, exam_entries)
            items.append({'c': c, 'e': match, 'd': match.exam_date if match else None, 'b': br})
            
        items.sort(key=lambda x: (x['d'] is None, x['d']))

        for it in items:
            course = it['c']
            exam = it['e']
            ex_date = it['d']
            branch = it['b']
            if not course.subject or not course.instructor:
                 continue # Safeguard against corrupted or incomplete live records
            
            subject = course.subject.name
            
            if TeacherProductionSession.objects.filter(course=course, exam_date=ex_date).exists():
                continue

            # ── ULTIMATE FAIL-SAFE & BULLETPROOF WRAPPER ──
            try:
                num_days = 1
                norm_sub = subject.strip()
                if 'الرياضيات' in norm_sub:
                    num_days = 2 if branch == 'ninth' else 3
                elif any(kw in norm_sub for kw in ['الفيزياء', 'الكيمياء', 'العلوم', 'فيزياء']):
                    num_days = 2


                anchor = PresentationBuilder.SCHEDULE_START_DATE
                
                final_span = []
                s_date = None
                solved = False
                
                # ATOMIC BLOCK VALIDATOR
                for max_cap in [1, 2, 3]:
                    walk = anchor
                    steps = 0
                    while True:
                        if walk > HARD_END: break
                        
                        candidate_span = []
                        b_walk = walk
                        is_valid_start = True
                        
                        while len(candidate_span) < num_days:
                            if b_walk > HARD_END:
                                 is_valid_start = False
                                 break
                            
                            # 🛑 CRITICAL HARD BOUNDARY: Cannot shoot ON or AFTER exam date!
                            if ex_date and b_walk >= ex_date:
                                 is_valid_start = False
                                 break
                            
                            if b_walk.weekday() != 4 and b_walk not in EID_BLOCK:
                                 if allocations.get(b_walk, 0) < max_cap:
                                      candidate_span.append(b_walk)
                                 else:
                                      is_valid_start = False 
                                      break
                            b_walk += timedelta(days=1)
                        
                        if is_valid_start and len(candidate_span) == num_days:
                            s_date = walk 
                            final_span = candidate_span
                            solved = True
                            break
                        
                        walk += timedelta(days=1)
                        steps += 1
                        if steps > 90: break
                        
                    if solved: break

                if not s_date:
                    s_date = PresentationBuilder.SCHEDULE_START_DATE
                    final_span = [s_date]
                    
                for locked_day in final_span:
                     allocations[locked_day] = allocations.get(locked_day, 0) + 1

                price = course.price_cents / 100 if course.price_cents else PresentationBuilder.get_platform_price(subject, branch)
                
                session = TeacherProductionSession.objects.create(
                    course=course,
                    teacher_name=course.instructor.get_full_name() or course.instructor.username,
                    subject=subject,
                    branch=branch,
                    exam_date=ex_date,
                    exam_time=exam.exam_time if exam else None,
                    shooting_date=s_date,
                    shooting_time=dt_time(20, 0),
                    shooting_duration_days=num_days, 
                    status='scheduled',
                )
                ProductionCost.objects.create(session=session, platform_price=price)
            
            except Exception as e:
                # SILENT FAIL-SAFE: Prevents a single problematic course from crashing entire generation
                print(f"Warning: Skipped problem course generator pass: {e}")
                continue


    def _find_exam(self, subject_name, branch, entries):
        """Intelligent semantic resolver linking platform courses to official exam schedules."""
        
        def normalize(s):
            if not s: return ""
            s = s.strip().replace(' ', '')
            # Standardize Alefs
            s = s.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
            # Standardize Teh Marbuta
            s = s.replace('ة', 'ه')
            # Standardize Kaf/Jeem variances for English (الانكليزية / الانجليزية)
            s = s.replace('ج', 'ك') # Common mapping for English in some dialects
            return s

        norm_subject = normalize(subject_name)
        branch_entries = entries.filter(branch=branch)

        # 1. Direct Normalized Exact Match
        for entry in branch_entries:
            if normalize(entry.subject_name) == norm_subject:
                return entry

        # 2. Semantic Alias Expansion Map
        # Translates specific platform course names back to generalized exam categories.
        ALIAS_MAP = {
            'اللغة الفرنسية': ['الفرنسية', 'اللغة الأجنبية', 'اللغة الاجنبية', 'فرنسي'],
            'اللغة الإنكليزية': ['الإنكليزية', 'اللغة الأجنبية', 'اللغة الاجنبية', 'الانجليزية', 'إنكليزي'],
            'اللغة الانكليزية': ['الانكليزية', 'اللغة الأجنبية', 'اللغة الاجنبية', 'الانجليزية', 'انكليزي'],
            'الفيزياء': ['فيزياء', 'علوم عامة', 'العلوم العامة'],
            'الكيمياء': ['كيمياء', 'علوم عامة', 'العلوم العامة'],
            'العلوم': ['العلوم', 'علم الأحياء', 'احياء', 'علوم عامة', 'العلوم العامة'],
            'علم الأحياء': ['العلوم', 'الاحياء', 'احياء'],
            'الاجتماعيات': ['اجتماعيات', 'التاريخ', 'الجغرافية', 'التربية الوطنية'],
            'التربية الدينية': ['الديانة', 'الاسلامية', 'اسلامية', 'التربية الاسلامية', 'التربية الإسلامية', 'دين'],
            'التربية الإسلامية': ['التربية الدينية', 'الديانة', 'الاسلامية', 'اسلامية', 'التربية الاسلامية', 'دين'],
            'التربية الاسلامية': ['التربية الدينية', 'الديانة', 'الاسلامية', 'اسلامية', 'التربية الإسلامية', 'دين'],
            'الديانة': ['التربية الدينية', 'التربية الاسلامية', 'التربية الإسلامية', 'اسلامية']
        }

        # Check if current subject has established aliases
        candidate_aliases = []
        for key, list_val in ALIAS_MAP.items():
            if normalize(key) == norm_subject:
                candidate_aliases.extend([normalize(x) for x in list_val])
                break

        if candidate_aliases:
            for entry in branch_entries:
                ne = normalize(entry.subject_name)
                if ne in candidate_aliases:
                    return entry

        # 3. Fuzzy Substring Containment Fallback
        for entry in branch_entries:
            ne = normalize(entry.subject_name)
            if ne in norm_subject or norm_subject in ne:
                return entry
                
        # 4. Reverse Fuzzy Check: If exam entry matches one of our aliases via substring
        for entry in branch_entries:
            ne = normalize(entry.subject_name)
            for alias in candidate_aliases:
                if ne in alias or alias in ne:
                    return entry

        return None


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

        for card in presentation.get('teacher_cards', []):
            for session in card['sessions']:
                session['exam_date_str'] = session['exam_date'].strftime('%d-%m-%Y') if session['exam_date'] else ''
                session['shooting_date_str'] = session['shooting_date'].strftime('%d-%m-%Y') if session['shooting_date'] else ''

        context.update(presentation)
        return context


@require_POST
def quick_update_session(request):
    """API to handle rapid inline session edits from list views."""
    import json
    try:
        data = json.loads(request.body)
        session_id = data.get('id')
        if not session_id:
            return JsonResponse({'success': False, 'error': 'Missing ID'})

        session = TeacherProductionSession.objects.get(pk=session_id)
        
        if 'shooting_date' in data:
            session.shooting_date = data['shooting_date'] if data['shooting_date'] else None
        
        if 'shooting_time' in data:
            session.shooting_time = data['shooting_time'] if data['shooting_time'] else None
        
        # User requested: If edited, automatically flip from 'scheduled' to 'confirmed' 
        # unless they explicitly chose another specific status
        if 'status' in data:
            session.status = data['status']
        
        if session.status == 'scheduled':
            session.status = 'confirmed'
            
        session.save()

        # Handle related production cost
        cost_obj, created = ProductionCost.objects.get_or_create(session=session)
        
        if 'production_cost' in data:
            cost_obj.production_cost = data['production_cost'] or 0
            
        if 'platform_price' in data:
            cost_obj.platform_price = data['platform_price'] or 0
            
        cost_obj.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
