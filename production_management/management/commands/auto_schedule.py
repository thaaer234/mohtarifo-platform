"""
Auto-generate production schedule from platform courses.
Pulls teachers, subjects, prices from existing Course model
and matches with the official exam schedule dates.
"""
from datetime import date, timedelta, time
from django.core.management.base import BaseCommand
from django.db.models import Q
from learning.models import Course, Subject
from production_management.models import TeacherProductionSession, ProductionCost
from production_management.presentation_service import PresentationBuilder


# ═══════════════════════════════════════════════════════════════
# Official Exam Schedule 2026 (from Ministry photos)
# Key: (subject_keywords, branch) → (exam_date, exam_time, duration_str)
# ═══════════════════════════════════════════════════════════════
EXAM_SCHEDULE = {
    # ── 9th Grade (تاسع) ──
    ('ninth', 'العلوم'): {'date': date(2026, 6, 4), 'time': time(8, 30), 'duration': '2'},
    ('ninth', 'فيزياء'): {'date': date(2026, 6, 4), 'time': time(8, 30), 'duration': '2'},
    ('ninth', 'كيمياء'): {'date': date(2026, 6, 4), 'time': time(8, 30), 'duration': '2'},
    ('ninth', 'الإنكليزية'): {'date': date(2026, 6, 7), 'time': time(8, 30), 'duration': '1:30'},
    ('ninth', 'إنكليزي'): {'date': date(2026, 6, 7), 'time': time(8, 30), 'duration': '1:30'},
    ('ninth', 'الاجتماعيات'): {'date': date(2026, 6, 11), 'time': time(8, 30), 'duration': '2'},
    ('ninth', 'اجتماعيات'): {'date': date(2026, 6, 11), 'time': time(8, 30), 'duration': '2'},
    ('ninth', 'الرياضيات'): {'date': date(2026, 6, 15), 'time': time(8, 30), 'duration': '2'},
    ('ninth', 'رياضيات'): {'date': date(2026, 6, 15), 'time': time(8, 30), 'duration': '2'},
    ('ninth', 'الفرنسية'): {'date': date(2026, 6, 17), 'time': time(8, 30), 'duration': '1:30'},
    ('ninth', 'فرنسي'): {'date': date(2026, 6, 17), 'time': time(8, 30), 'duration': '1:30'},
    ('ninth', 'الديانة'): {'date': date(2026, 6, 20), 'time': time(8, 30), 'duration': '1:30'},
    ('ninth', 'ديانة'): {'date': date(2026, 6, 20), 'time': time(8, 30), 'duration': '1:30'},
    ('ninth', 'العربية'): {'date': date(2026, 6, 24), 'time': time(8, 30), 'duration': '2:30'},
    ('ninth', 'عربي'): {'date': date(2026, 6, 24), 'time': time(8, 30), 'duration': '2:30'},

    # ── Scientific (علمي) ──
    ('science', 'الفيزياء'): {'date': date(2026, 6, 6), 'time': time(8, 30), 'duration': '3'},
    ('science', 'فيزياء'): {'date': date(2026, 6, 6), 'time': time(8, 30), 'duration': '3'},
    ('science', 'الإنكليزية'): {'date': date(2026, 6, 9), 'time': time(8, 30), 'duration': '2'},
    ('science', 'إنكليزي'): {'date': date(2026, 6, 9), 'time': time(8, 30), 'duration': '2'},
    ('science', 'الرياضيات'): {'date': date(2026, 6, 13), 'time': time(8, 30), 'duration': '3:30'},
    ('science', 'رياضيات'): {'date': date(2026, 6, 13), 'time': time(8, 30), 'duration': '3:30'},
    ('science', 'العلوم'): {'date': date(2026, 6, 16), 'time': time(8, 30), 'duration': '2:30'},
    ('science', 'أحياء'): {'date': date(2026, 6, 16), 'time': time(8, 30), 'duration': '2:30'},
    ('science', 'الفرنسية'): {'date': date(2026, 6, 18), 'time': time(8, 30), 'duration': '2'},
    ('science', 'فرنسي'): {'date': date(2026, 6, 18), 'time': time(8, 30), 'duration': '2'},
    ('science', 'الديانة'): {'date': date(2026, 6, 21), 'time': time(8, 30), 'duration': '1:30'},
    ('science', 'ديانة'): {'date': date(2026, 6, 21), 'time': time(8, 30), 'duration': '1:30'},
    ('science', 'العربية'): {'date': date(2026, 6, 25), 'time': time(8, 30), 'duration': '2:30'},
    ('science', 'عربي'): {'date': date(2026, 6, 25), 'time': time(8, 30), 'duration': '2:30'},
    ('science', 'الكيمياء'): {'date': date(2026, 6, 28), 'time': time(8, 30), 'duration': '2'},
    ('science', 'كيمياء'): {'date': date(2026, 6, 28), 'time': time(8, 30), 'duration': '2'},

    # ── Literary (أدبي) ──
    ('literal', 'الفلسفة'): {'date': date(2026, 6, 6), 'time': time(8, 30), 'duration': '3'},
    ('literal', 'فلسفة'): {'date': date(2026, 6, 6), 'time': time(8, 30), 'duration': '3'},
    ('literal', 'الإنكليزية'): {'date': date(2026, 6, 9), 'time': time(8, 30), 'duration': '2:30'},
    ('literal', 'إنكليزي'): {'date': date(2026, 6, 9), 'time': time(8, 30), 'duration': '2:30'},
    ('literal', 'الجغرافيا'): {'date': date(2026, 6, 13), 'time': time(8, 30), 'duration': '2:30'},
    ('literal', 'جغرافيا'): {'date': date(2026, 6, 13), 'time': time(8, 30), 'duration': '2:30'},
    ('literal', 'التاريخ'): {'date': date(2026, 6, 16), 'time': time(8, 30), 'duration': '2'},
    ('literal', 'تاريخ'): {'date': date(2026, 6, 16), 'time': time(8, 30), 'duration': '2'},
    ('literal', 'الفرنسية'): {'date': date(2026, 6, 18), 'time': time(8, 30), 'duration': '2:30'},
    ('literal', 'فرنسي'): {'date': date(2026, 6, 18), 'time': time(8, 30), 'duration': '2:30'},
    ('literal', 'الديانة'): {'date': date(2026, 6, 21), 'time': time(8, 30), 'duration': '1:30'},
    ('literal', 'ديانة'): {'date': date(2026, 6, 21), 'time': time(8, 30), 'duration': '1:30'},
    ('literal', 'العربية'): {'date': date(2026, 6, 25), 'time': time(8, 30), 'duration': '2:30'},
    ('literal', 'عربي'): {'date': date(2026, 6, 25), 'time': time(8, 30), 'duration': '2:30'},
}

# Track mapping: Course.academic_track → ProductionSession.branch
TRACK_TO_BRANCH = {
    'scientific': 'science',
    'literary': 'literal',
    'ninth': 'ninth',
    'general': 'literal',  # Default for general
}


def find_exam_date(subject_name, branch):
    """Find exam date by fuzzy-matching subject name against schedule."""
    # Direct match
    key = (branch, subject_name)
    if key in EXAM_SCHEDULE:
        return EXAM_SCHEDULE[key]

    # Partial match - check if any keyword is in the subject name
    for (b, subj), info in EXAM_SCHEDULE.items():
        if b == branch and subj in subject_name:
            return info

    # Try the other direction
    for (b, subj), info in EXAM_SCHEDULE.items():
        if b == branch and subject_name in subj:
            return info

    return None


class Command(BaseCommand):
    help = 'Auto-generate production schedule from platform courses + official exam dates'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Clear existing sessions first')
        parser.add_argument('--dry-run', action='store_true', help='Show what would be created without creating')

    def handle(self, *args, **options):
        if options['clear']:
            count = TeacherProductionSession.objects.count()
            TeacherProductionSession.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'🗑️  Cleared {count} existing sessions.'))

        # Get all published/active courses
        courses = Course.objects.filter(
            status__in=['published', 'review', 'draft']
        ).select_related('subject', 'instructor').order_by('academic_track', 'subject__name')

        self.stdout.write(self.style.HTTP_INFO(f'\n📚 Found {courses.count()} courses on the platform\n'))

        created = 0
        skipped = 0
        no_exam = 0
        schedule_date = PresentationBuilder.SCHEDULE_START_DATE

        for course in courses:
            teacher_name = course.instructor.get_full_name() or course.instructor.username
            subject_name = course.subject.name
            branch = TRACK_TO_BRANCH.get(course.academic_track, 'ninth')

            # Find exam date for this subject+branch
            exam_info = find_exam_date(subject_name, branch)

            if not exam_info:
                no_exam += 1
                if not options['dry_run']:
                    self.stdout.write(f'  ⚠️  No exam found: {teacher_name} | {subject_name} | {branch}')
                continue

            # Check if already exists
            exists = TeacherProductionSession.objects.filter(
                teacher_name=teacher_name,
                subject=subject_name,
                branch=branch,
                exam_date=exam_info['date'],
            ).exists()

            if exists:
                skipped += 1
                continue

            # Calculate shooting date
            shooting_date = PresentationBuilder.calculate_shooting_date(
                exam_info['date'], subject_name, branch, schedule_date
            )

            # Get platform price from course or calculate
            if course.price_cents:
                platform_price = course.price_cents / 100  # Convert cents to units
            else:
                platform_price = PresentationBuilder.get_platform_price(subject_name, branch)

            # Priority (closer exam = higher)
            days_until = (exam_info['date'] - PresentationBuilder.SCHEDULE_START_DATE).days
            priority = max(1, 50 - days_until)

            if options['dry_run']:
                self.stdout.write(
                    f'  📋 {teacher_name} | {subject_name} | {branch} | '
                    f'Exam: {exam_info["date"]} | Shoot: {shooting_date} | '
                    f'Price: {platform_price:,.0f}'
                )
            else:
                session = TeacherProductionSession.objects.create(
                    teacher_name=teacher_name,
                    subject=subject_name,
                    branch=branch,
                    exam_date=exam_info['date'],
                    exam_time=exam_info['time'],
                    shooting_date=shooting_date,
                    status='scheduled',
                    priority=priority,
                )

                ProductionCost.objects.create(
                    session=session,
                    platform_price=platform_price,
                )

                self.stdout.write(
                    f'  ✅ {teacher_name} | {subject_name} | '
                    f'{session.get_branch_display()} | {exam_info["date"]} | '
                    f'{platform_price:,.0f} | تصوير: {shooting_date}'
                )

            created += 1
            schedule_date = shooting_date + timedelta(days=1)

        prefix = '[DRY RUN] ' if options['dry_run'] else ''
        self.stdout.write(self.style.SUCCESS(
            f'\n═══════════════════════════════════════'
            f'\n{prefix}✅ Created: {created}'
            f'\n{prefix}⏭️  Skipped: {skipped} (already exist)'
            f'\n{prefix}⚠️  No exam match: {no_exam}'
            f'\n═══════════════════════════════════════'
        ))
