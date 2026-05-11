"""
Presentation Builder Service
Builds the full exam production presentation data with smart scheduling,
pricing logic, and teacher card generation.
"""
from datetime import date, timedelta
from collections import OrderedDict
from django.db.models import Q, Sum, Count
from .models import TeacherProductionSession, ProductionCost, ProductionStatus


class PresentationBuilder:
    """
    Builds presentation slides from TeacherProductionSession data.
    Applies smart scheduling and pricing rules.
    """

    # ───────── Pricing Rules ─────────
    PRICING_RULES = {
        'ninth': {
            'default': 75000,
        },
        'literal': {
            'default': 100000,
            'الفلسفة': 150000,
        },
        'science': {
            'default': 100000,
            'الرياضيات': 200000,
            'الفيزياء': 150000,
        },
    }

    # ───────── Production Duration (hours) ─────────
    PRODUCTION_HOURS = {
        'science': {'shoot_min': 4, 'shoot_max': 6, 'edit_min': 5, 'edit_max': 8},
        'literal': {'shoot_min': 2, 'shoot_max': 4, 'edit_min': 3, 'edit_max': 5},
        'ninth': {'shoot_min': 3, 'shoot_max': 5, 'edit_min': 4, 'edit_max': 6},
        'other': {'shoot_min': 3, 'shoot_max': 5, 'edit_min': 4, 'edit_max': 6},
    }

    # ───────── Subject Categories ─────────
    SCIENTIFIC_SUBJECTS = ['الرياضيات', 'الفيزياء', 'الكيمياء', 'العلوم', 'فيزياء وكيمياء']
    LANGUAGE_SUBJECTS = ['الإنكليزية', 'الفرنسية', 'العربية']
    THEORY_SUBJECTS = ['الاجتماعيات', 'الجغرافيا', 'التاريخ', 'الفلسفة', 'الديانة']

    SCHEDULE_START_DATE = date(2026, 5, 17)

    @classmethod
    def get_platform_price(cls, subject, branch):
        """Calculate platform price based on subject and branch rules."""
        branch_rules = cls.PRICING_RULES.get(branch, cls.PRICING_RULES.get('other', {'default': 100000}))
        return branch_rules.get(subject, branch_rules.get('default', 100000))

    @classmethod
    def get_production_hours(cls, subject, branch):
        """Get estimated production hours based on subject type."""
        if subject in cls.SCIENTIFIC_SUBJECTS:
            hours = cls.PRODUCTION_HOURS.get('science', cls.PRODUCTION_HOURS['other'])
        elif subject in cls.LANGUAGE_SUBJECTS:
            hours = cls.PRODUCTION_HOURS.get('ninth', cls.PRODUCTION_HOURS['other'])
        else:
            hours = cls.PRODUCTION_HOURS.get('literal', cls.PRODUCTION_HOURS['other'])
        return hours

    @classmethod
    def calculate_shooting_date(cls, exam_date, subject, branch, current_schedule_date=None):
        """
        Smart scheduling: calculate optimal shooting date.
        - Prioritize materials closest to exam date
        - Start from SCHEDULE_START_DATE
        - Add buffer before exam
        """
        if current_schedule_date is None:
            current_schedule_date = cls.SCHEDULE_START_DATE

        hours = cls.get_production_hours(subject, branch)
        total_production_days = max(3, (hours['edit_max'] + hours['shoot_max']) // 8 + 2)

        # Shooting must be at least total_production_days before exam
        latest_shooting = exam_date - timedelta(days=total_production_days)

        # Use the current schedule date or latest possible
        shooting_date = max(current_schedule_date, cls.SCHEDULE_START_DATE)
        if shooting_date > latest_shooting:
            shooting_date = latest_shooting

        return shooting_date

    @classmethod
    def build_presentation_data(cls):
        """Build the full presentation data structure."""
        sessions = TeacherProductionSession.objects.all().select_related(
            'cost', 'room'
        ).order_by('exam_date', 'teacher_name')

        if not sessions.exists():
            return cls._build_default_presentation()

        # Build rows with pricing and scheduling
        all_rows = []
        schedule_date = cls.SCHEDULE_START_DATE

        for session in sessions:
            price = cls.get_platform_price(session.subject, session.branch)

            # Use existing shooting_date or calculate
            if session.shooting_date:
                shooting_date = session.shooting_date
            else:
                shooting_date = cls.calculate_shooting_date(
                    session.exam_date, session.subject, session.branch, schedule_date
                )

            hours = cls.get_production_hours(session.subject, session.branch)

            # Update cost if exists
            if hasattr(session, 'cost') and session.cost:
                actual_price = session.cost.platform_price
            else:
                actual_price = price

            row = {
                'id': session.id,
                'teacher_name': session.teacher_name,
                'subject': session.subject,
                'branch': session.get_branch_display(),
                'branch_code': session.branch,
                'exam_date': session.exam_date,
                'shooting_date': shooting_date,
                'status': session.status,
                'status_display': session.get_status_display(),
                'priority': session.priority,
                'platform_price': actual_price if actual_price else price,
                'price_display': cls._format_price(actual_price if actual_price else price),
                'shoot_hours': f"{hours['shoot_min']}-{hours['shoot_max']}",
                'edit_hours': f"{hours['edit_min']}-{hours['edit_max']}",
                'notes': session.notes or '',
            }
            all_rows.append(row)

            # Advance schedule_date
            schedule_date = shooting_date + timedelta(days=1)

        # Split into slide groups (10 per slide)
        grid_slides = cls._chunk_list(all_rows, 10)

        # Build teacher cards (group by teacher)
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
            'scheduled_count': sum(1 for r in all_rows if r['status'] == 'scheduled'),
            'completed_count': sum(1 for r in all_rows if r['status'] == 'completed'),
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
        """Group sessions by teacher for individual cards."""
        teachers = OrderedDict()
        for row in all_rows:
            name = row['teacher_name']
            if name not in teachers:
                teachers[name] = {
                    'name': name,
                    'sessions': [],
                    'total_price': 0,
                }
            teachers[name]['sessions'].append(row)
            teachers[name]['total_price'] += row['platform_price']

        # Only include teachers with multiple sessions or special pricing
        cards = []
        for name, data in teachers.items():
            data['total_price_display'] = cls._format_price(data['total_price'])
            data['session_count'] = len(data['sessions'])
            cards.append(data)

        return cards

    @classmethod
    def _build_default_presentation(cls):
        """Return empty presentation structure when no data exists."""
        return {
            'all_rows': [],
            'grid_slides': [],
            'teacher_cards': [],
            'stats': {
                'total_sessions': 0,
                'total_teachers': 0,
                'total_subjects': 0,
                'total_revenue': '0',
                'total_revenue_raw': 0,
                'ninth_count': 0,
                'science_count': 0,
                'literal_count': 0,
                'scheduled_count': 0,
                'completed_count': 0,
                'first_exam': None,
                'last_exam': None,
            },
            'schedule_start': cls.SCHEDULE_START_DATE,
        }

    @staticmethod
    def _format_price(amount):
        """Format price in thousands (e.g., 75,000 → '75 ألف')."""
        if not amount:
            return '0'
        thousands = int(amount / 1000)
        return f"{thousands:,} ألف"

    @staticmethod
    def _chunk_list(lst, chunk_size):
        """Split a list into chunks."""
        return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]
