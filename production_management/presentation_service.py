"""
Production Schedule Builder Service
Builds the full auto-generated production schedule from TeacherProductionSession data.
Calculates shooting dates, production times, costs, priorities.
"""
from datetime import date, timedelta
from collections import OrderedDict
from .models import TeacherProductionSession, ProductionCost, ProductionStatus


ARABIC_DAYS = {
    0: 'الاثنين',
    1: 'الثلاثاء',
    2: 'الأربعاء',
    3: 'الخميس',
    4: 'الجمعة',
    5: 'السبت',
    6: 'الأحد',
}


class PresentationBuilder:
    """Builds production schedule data from TeacherProductionSession records."""

    # ── Pricing Rules ──
    PRICING_RULES = {
        'ninth': {'default': 75000},
        'literal': {'default': 100000, 'الفلسفة': 150000},
        'science': {'default': 100000, 'الرياضيات': 200000, 'الفيزياء': 150000},
    }

    # ── Production Duration (hours) ──
    PRODUCTION_HOURS = {
        'science':  {'shoot_min': 4, 'shoot_max': 6, 'edit_min': 5, 'edit_max': 8, 'design': 1,   'review': 1,    'upload': 1},
        'literal':  {'shoot_min': 2, 'shoot_max': 4, 'edit_min': 3, 'edit_max': 5, 'design': 0.5, 'review': 0.5,  'upload': 0.5},
        'ninth':    {'shoot_min': 3, 'shoot_max': 5, 'edit_min': 4, 'edit_max': 6, 'design': 0.75,'review': 0.5,  'upload': 0.5},
        'other':    {'shoot_min': 3, 'shoot_max': 5, 'edit_min': 4, 'edit_max': 6, 'design': 0.5, 'review': 0.5,  'upload': 0.5},
    }

    # ── Subject Categories ──
    SCIENTIFIC_SUBJECTS = ['الرياضيات', 'الفيزياء', 'الكيمياء', 'العلوم', 'فيزياء وكيمياء', 'علم الأحياء']
    LANGUAGE_SUBJECTS = ['الإنكليزية', 'الفرنسية', 'العربية', 'اللغة الأجنبية']
    THEORY_SUBJECTS = ['الاجتماعيات', 'الجغرافيا', 'التاريخ', 'الفلسفة', 'الديانة', 'التربية الدينية']

    SCHEDULE_START_DATE = date(2026, 5, 17)

    # ── Exam durations (hours) based on subject type ──
    EXAM_DURATIONS = {
        'الرياضيات': {'science': '3:30', 'ninth': '2', 'literal': '2'},
        'الفيزياء': {'science': '3', 'ninth': '2', 'literal': '2'},
        'فيزياء وكيمياء': {'ninth': '2'},
        'الكيمياء': {'science': '2'},
        'العلوم': {'science': '2', 'ninth': '2'},
        'علم الأحياء': {'science': '2:30'},
        'الإنكليزية': {'science': '2', 'ninth': '1:30', 'literal': '2:30'},
        'الفرنسية': {'science': '2', 'ninth': '1:30', 'literal': '2:30'},
        'العربية': {'science': '2:30', 'ninth': '2:30', 'literal': '2:30'},
        'الفلسفة': {'literal': '3'},
        'الجغرافيا': {'literal': '2:30'},
        'التاريخ': {'literal': '2'},
        'الاجتماعيات': {'ninth': '2'},
        'الديانة': {'science': '1:30', 'ninth': '1:30', 'literal': '1:30'},
        'التربية الدينية': {'science': '1:30', 'ninth': '1:30', 'literal': '1:30'},
    }

    @classmethod
    def get_platform_price(cls, subject, branch):
        branch_rules = cls.PRICING_RULES.get(branch, {'default': 100000})
        return branch_rules.get(subject, branch_rules.get('default', 100000))

    @classmethod
    def get_production_hours(cls, subject, branch):
        if subject in cls.SCIENTIFIC_SUBJECTS:
            return cls.PRODUCTION_HOURS.get('science', cls.PRODUCTION_HOURS['other'])
        elif subject in cls.LANGUAGE_SUBJECTS:
            return cls.PRODUCTION_HOURS.get('ninth', cls.PRODUCTION_HOURS['other'])
        else:
            return cls.PRODUCTION_HOURS.get('literal', cls.PRODUCTION_HOURS['other'])

    @classmethod
    def get_exam_duration(cls, subject, branch):
        durations = cls.EXAM_DURATIONS.get(subject, {})
        return durations.get(branch, '2')

    @classmethod
    def format_duration(cls, hours):
        """Format hours to display like '5h', '30m', '1h 30m'."""
        if isinstance(hours, str):
            return hours
        if hours >= 1:
            h = int(hours)
            m = int((hours - h) * 60)
            if m > 0:
                return f"{h}h {m}m"
            return f"{h}h"
        else:
            return f"{int(hours * 60)}m"

    @classmethod
    def calculate_shooting_date(cls, exam_date, subject, branch, current_date=None):
        if current_date is None:
            current_date = cls.SCHEDULE_START_DATE
        hours = cls.get_production_hours(subject, branch)
        total_days = max(3, (hours['edit_max'] + hours['shoot_max']) // 8 + 2)
        latest = exam_date - timedelta(days=total_days)
        shoot = max(current_date, cls.SCHEDULE_START_DATE)
        if shoot > latest:
            shoot = latest
        # Skip Fridays
        if shoot.weekday() == 4:
            shoot -= timedelta(days=1)
        return shoot

    @classmethod
    def get_production_cost(cls, subject, branch):
        """Estimate production cost based on subject complexity."""
        hours = cls.get_production_hours(subject, branch)
        total_hours = hours['shoot_max'] + hours['edit_max'] + hours['design'] + hours['review'] + hours['upload']
        # Cost per hour estimate (in thousands)
        cost_per_hour = 15  # 15K per hour
        return int(total_hours * cost_per_hour)

    @classmethod
    def build_presentation_data(cls):
        sessions = TeacherProductionSession.objects.all().select_related(
            'cost', 'room', 'course', 'course__instructor', 
            'course__subject', 'course__instructor__instructor_profile'
        ).order_by('exam_date', 'course__instructor__first_name', 'teacher_name')

        if not sessions.exists():
            return cls._empty_data()

        all_rows = []
        schedule_date = cls.SCHEDULE_START_DATE

        for i, session in enumerate(sessions):
            subject_name = session.subject_name
            teacher_name = session.instructor_name
            
            price = cls.get_platform_price(subject_name, session.branch)
            hours = cls.get_production_hours(subject_name, session.branch)

            # Shooting date
            if session.shooting_date:
                shooting_date = session.shooting_date
            else:
                shooting_date = cls.calculate_shooting_date(
                    session.exam_date, subject_name, session.branch, schedule_date
                )

            # Dynamic Pricing/Cost
            actual_price = session.platform_price or price
            
            # Prioritize manually entered production cost if available
            prod_cost = 0
            if hasattr(session, 'cost') and session.cost and session.cost.production_cost > 0:
                prod_cost = session.cost.production_cost
            else:
                prod_cost = cls.get_production_cost(subject_name, session.branch)

            row = {
                'id': session.id,
                'row_number': i + 1,
                'teacher_name': teacher_name,
                'subject': subject_name,
                'branch': session.get_branch_display(),
                'branch_code': session.branch,
                'session_type': 'جلسة',
                'exam_date': session.exam_date,
                'exam_date_str': session.exam_date.strftime('%Y-%m-%d') if session.exam_date else '',
                'day_name': ARABIC_DAYS.get(session.exam_date.weekday(), '') if session.exam_date else '',
                'exam_time': session.exam_time.strftime('%H:%M') if session.exam_time else '09:00',
                'exam_duration': cls.get_exam_duration(subject_name, session.branch),
                'production_cost': prod_cost,
                'platform_price': actual_price,
                'price_display': cls._format_price(actual_price),
                'priority': i + 1,
                'shooting_date': shooting_date,
                'shooting_date_str': shooting_date.strftime('%Y-%m-%d') if shooting_date else '',
                'shooting_time': '09:00',
                'shoot_hours': cls.format_duration(hours['shoot_max']),
                'montage_hours': cls.format_duration(hours['edit_max']),
                'design_hours': cls.format_duration(hours['design']),
                'review_hours': cls.format_duration(hours['review']),
                'upload_hours': cls.format_duration(hours['upload']),
                'status': session.status,
                'status_display': session.get_status_display(),
                'notes': session.notes or '',
                'photo_url': session.teacher_photo_url,
                'static_photo_path': session.course.instructor_cover_static_path if session.course else None,
            }
            all_rows.append(row)
            schedule_date = shooting_date + timedelta(days=1)

        # Split into chunks of 10
        grid_slides = cls._chunk_list(all_rows, 10)

        # Teacher cards
        teacher_cards = cls._build_teacher_cards(all_rows)

        # Stats
        total_price = sum(r['platform_price'] for r in all_rows)
        stats = {
            'total_sessions': len(all_rows),
            'total_teachers': len(set(r['teacher_name'] for r in all_rows)),
            'total_subjects': len(set(r['subject'] for r in all_rows)),
            'total_revenue': cls._format_price(total_price),
            'total_revenue_raw': total_price,
            'ninth_count': sum(1 for r in all_rows if r['branch_code'] == 'ninth'),
            'science_count': sum(1 for r in all_rows if r['branch_code'] == 'science'),
            'literal_count': sum(1 for r in all_rows if r['branch_code'] == 'literal'),
            'first_exam': min(r['exam_date'] for r in all_rows) if all_rows else None,
            'last_exam': max(r['exam_date'] for r in all_rows) if all_rows else None,
        }

        return {
            'all_rows': all_rows,
            'grid_slides': grid_slides,
            'teacher_cards': teacher_cards,
            'stats': stats,
            'schedule_start': cls.SCHEDULE_START_DATE,
        }

    @classmethod
    def _build_teacher_cards(cls, all_rows):
        teachers = OrderedDict()
        for row in all_rows:
            name = row['teacher_name']
            if name not in teachers:
                teachers[name] = {
                    'name': name, 
                    'sessions': [], 
                    'total_price': 0,
                    'photo_url': row.get('photo_url'),
                    'static_photo_path': row.get('static_photo_path')
                }
            teachers[name]['sessions'].append(row)
            teachers[name]['total_price'] += row['platform_price']
            
            # Update photo if missing
            if not teachers[name]['photo_url'] and row.get('photo_url'):
                teachers[name]['photo_url'] = row.get('photo_url')
            if not teachers[name]['static_photo_path'] and row.get('static_photo_path'):
                teachers[name]['static_photo_path'] = row.get('static_photo_path')

        cards = []
        for name, data in teachers.items():
            data['total_price_display'] = cls._format_price(data['total_price'])
            data['session_count'] = len(data['sessions'])
            cards.append(data)
        return cards

    @classmethod
    def _empty_data(cls):
        return {
            'all_rows': [], 'grid_slides': [], 'teacher_cards': [],
            'stats': {
                'total_sessions': 0, 'total_teachers': 0, 'total_subjects': 0,
                'total_revenue': '0', 'total_revenue_raw': 0,
                'ninth_count': 0, 'science_count': 0, 'literal_count': 0,
                'first_exam': None, 'last_exam': None,
            },
            'schedule_start': cls.SCHEDULE_START_DATE,
        }

    @staticmethod
    def _format_price(amount):
        if not amount:
            return '0'
        thousands = int(float(amount) / 1000)
        return f"{thousands:,} ألف"

    @staticmethod
    def _chunk_list(lst, size):
        return [lst[i:i + size] for i in range(0, len(lst), size)]
