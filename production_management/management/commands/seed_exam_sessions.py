"""
Management command to seed all 38 exam production sessions 
with the exact data provided for the 2026 exam program.
"""
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from production_management.models import TeacherProductionSession, ProductionCost
from production_management.presentation_service import PresentationBuilder


class Command(BaseCommand):
    help = 'Seed all 38 exam production sessions for the 2026 program'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing sessions before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            count = TeacherProductionSession.objects.all().count()
            TeacherProductionSession.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Cleared {count} existing sessions.'))

        # ═══════════════════════════════════════════════════════════
        # All 38 exam sessions data
        # ═══════════════════════════════════════════════════════════
        sessions_data = [
            # Slide 2 (Rows 1-10)
            {'teacher': 'إسراء عودة', 'subject': 'فيزياء وكيمياء', 'branch': 'ninth', 'exam': date(2026, 6, 1)},
            {'teacher': 'علي بدوي', 'subject': 'فيزياء وكيمياء', 'branch': 'ninth', 'exam': date(2026, 6, 1)},
            {'teacher': 'نبيل القسطي', 'subject': 'العلوم', 'branch': 'ninth', 'exam': date(2026, 6, 3)},
            {'teacher': 'رياض دالاتي', 'subject': 'الإنكليزية', 'branch': 'ninth', 'exam': date(2026, 6, 5)},
            {'teacher': 'قصي الجابي', 'subject': 'الفيزياء', 'branch': 'science', 'exam': date(2026, 6, 6)},
            {'teacher': 'ضياء الدين عريبي', 'subject': 'الاجتماعيات', 'branch': 'ninth', 'exam': date(2026, 6, 8)},
            {'teacher': 'عيسى الدندن', 'subject': 'الاجتماعيات', 'branch': 'ninth', 'exam': date(2026, 6, 8)},
            {'teacher': 'رامي حلاق', 'subject': 'الإنكليزية', 'branch': 'literal', 'exam': date(2026, 6, 9)},
            {'teacher': 'سامر محاحي', 'subject': 'الإنكليزية', 'branch': 'literal', 'exam': date(2026, 6, 9)},
            {'teacher': 'عبد الله سلطجي', 'subject': 'الإنكليزية', 'branch': 'literal', 'exam': date(2026, 6, 9)},

            # Slide 3 (Rows 11-20)
            {'teacher': 'محمد السعدي', 'subject': 'الفلسفة', 'branch': 'literal', 'exam': date(2026, 6, 9)},
            {'teacher': 'هلا الهمج', 'subject': 'الرياضيات', 'branch': 'ninth', 'exam': date(2026, 6, 11)},
            {'teacher': 'علاء رحال', 'subject': 'الرياضيات', 'branch': 'science', 'exam': date(2026, 6, 13)},
            {'teacher': 'ربيع نجار', 'subject': 'الرياضيات', 'branch': 'science', 'exam': date(2026, 6, 13)},
            {'teacher': 'محمد نتوف', 'subject': 'الرياضيات', 'branch': 'science', 'exam': date(2026, 6, 13)},
            {'teacher': 'آلاء الدمشقي', 'subject': 'الرياضيات', 'branch': 'science', 'exam': date(2026, 6, 13)},
            {'teacher': 'خالد منير', 'subject': 'الرياضيات', 'branch': 'science', 'exam': date(2026, 6, 13)},
            {'teacher': 'عيسى الدندن', 'subject': 'الجغرافيا', 'branch': 'literal', 'exam': date(2026, 6, 13)},
            {'teacher': 'ضياء الدين عريبي', 'subject': 'الجغرافيا', 'branch': 'literal', 'exam': date(2026, 6, 13)},
            {'teacher': 'عمار سليمان', 'subject': 'الجغرافيا', 'branch': 'literal', 'exam': date(2026, 6, 13)},

            # Slide 4 (Rows 21-30)
            {'teacher': 'عبد الوهاب كلاوي', 'subject': 'الفرنسية', 'branch': 'ninth', 'exam': date(2026, 6, 15)},
            {'teacher': 'رامه مطر', 'subject': 'الفرنسية', 'branch': 'ninth', 'exam': date(2026, 6, 15)},
            {'teacher': 'نبيل القسطي', 'subject': 'العلوم', 'branch': 'science', 'exam': date(2026, 6, 16)},
            {'teacher': 'ملهم علي', 'subject': 'العلوم', 'branch': 'science', 'exam': date(2026, 6, 16)},
            {'teacher': 'خالد الميداني', 'subject': 'العلوم', 'branch': 'science', 'exam': date(2026, 6, 16)},
            {'teacher': 'ضياء الدين عريبي', 'subject': 'التاريخ', 'branch': 'literal', 'exam': date(2026, 6, 16)},
            {'teacher': 'محمد خير السعدي', 'subject': 'الديانة', 'branch': 'ninth', 'exam': date(2026, 6, 17)},
            {'teacher': 'عامر حداد', 'subject': 'الفرنسية', 'branch': 'literal', 'exam': date(2026, 6, 18)},
            {'teacher': 'عبد الوهاب كلاوي', 'subject': 'الفرنسية', 'branch': 'literal', 'exam': date(2026, 6, 18)},
            {'teacher': 'رامه مطر', 'subject': 'الفرنسية', 'branch': 'literal', 'exam': date(2026, 6, 18)},

            # Slide 5 (Rows 31-38)
            {'teacher': 'محمد خير السعدي', 'subject': 'الديانة', 'branch': 'literal', 'exam': date(2026, 6, 21)},
            {'teacher': 'عمار مرزوق', 'subject': 'العربية', 'branch': 'ninth', 'exam': date(2026, 6, 21)},
            {'teacher': 'عهد عمر', 'subject': 'العربية', 'branch': 'ninth', 'exam': date(2026, 6, 21)},
            {'teacher': 'طارق الصعيدي', 'subject': 'العربية', 'branch': 'literal', 'exam': date(2026, 6, 25)},
            {'teacher': 'عمار مرزوق', 'subject': 'العربية', 'branch': 'literal', 'exam': date(2026, 6, 25)},
            {'teacher': 'مهند الخياط', 'subject': 'الكيمياء', 'branch': 'science', 'exam': date(2026, 6, 28)},
            {'teacher': 'أسامة حيدر', 'subject': 'الكيمياء', 'branch': 'science', 'exam': date(2026, 6, 28)},
        ]

        created_count = 0
        skipped_count = 0
        schedule_date = PresentationBuilder.SCHEDULE_START_DATE

        for i, data in enumerate(sessions_data):
            # Check if already exists
            exists = TeacherProductionSession.objects.filter(
                teacher_name=data['teacher'],
                subject=data['subject'],
                branch=data['branch'],
                exam_date=data['exam'],
            ).exists()

            if exists:
                skipped_count += 1
                continue

            # Calculate shooting date
            shooting_date = PresentationBuilder.calculate_shooting_date(
                data['exam'], data['subject'], data['branch'], schedule_date
            )

            # Calculate platform price
            price = PresentationBuilder.get_platform_price(data['subject'], data['branch'])

            # Calculate priority (closer exam = higher priority)
            days_until_exam = (data['exam'] - PresentationBuilder.SCHEDULE_START_DATE).days
            priority = max(1, 50 - days_until_exam)

            session = TeacherProductionSession.objects.create(
                teacher_name=data['teacher'],
                subject=data['subject'],
                branch=data['branch'],
                exam_date=data['exam'],
                shooting_date=shooting_date,
                status='scheduled',
                priority=priority,
            )

            # Create cost record
            ProductionCost.objects.create(
                session=session,
                platform_price=price,
            )

            created_count += 1
            schedule_date = shooting_date + timedelta(days=1)

            self.stdout.write(
                f"  ✅ {data['teacher']} | {data['subject']} | "
                f"{session.get_branch_display()} | {data['exam']} | "
                f"{price:,.0f} SYP | تصوير: {shooting_date}"
            )

        self.stdout.write(self.style.SUCCESS(
            f'\n═══════════════════════════════════════'
            f'\n✅ Created: {created_count} sessions'
            f'\n⏭️  Skipped: {skipped_count} (already exist)'
            f'\n═══════════════════════════════════════'
        ))
