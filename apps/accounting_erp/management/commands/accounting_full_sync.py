"""
أمر إدارة شامل: تهيئة + مزامنة + معالجة البيانات القديمة

الاستخدام:
    python manage.py accounting_full_sync
    python manage.py accounting_full_sync --force-rebuild
"""
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'تهيئة دليل الحسابات ومزامنة جميع البيانات القديمة مع النظام المحاسبي'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-rebuild',
            action='store_true',
            help='حذف القيود التلقائية السابقة وإعادة بناءها من الصفر',
        )
        parser.add_argument(
            '--seed-only',
            action='store_true',
            help='فقط بذر دليل الحسابات بدون معالجة البيانات',
        )

    def handle(self, *args, **options):
        start = timezone.now()
        self.stdout.write(self.style.MIGRATE_HEADING('\n======================================='))
        self.stdout.write(self.style.MIGRATE_HEADING('  [ERP]  النظام المحاسبي - مزامنة شاملة'))
        self.stdout.write(self.style.MIGRATE_HEADING('=======================================\n'))

        # ─── الخطوة 1: دليل الحسابات ──────────────────────────────────────
        self.stdout.write('📊  بناء دليل الحسابات (Chart of Accounts)...')
        try:
            from apps.accounting_erp.services.chart_seeder import ChartOfAccountsSeeder
            msg = ChartOfAccountsSeeder.seed_standard_tree()
            self.stdout.write(self.style.SUCCESS(f'   ✅ {msg}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ خطأ في دليل الحسابات: {e}'))
            return

        if options['seed_only']:
            self.stdout.write(self.style.SUCCESS('\n✅ اكتملت عملية البذر فقط.'))
            return

        # ─── الخطوة 2: المعالجة الشاملة للبيانات القديمة ─────────────────
        self.stdout.write('\n📂  معالجة البيانات القديمة...')
        force = options['force_rebuild']
        if force:
            self.stdout.write(self.style.WARNING('   ⚠️  force-rebuild مفعّل — سيتم حذف القيود التلقائية القديمة'))

        try:
            from apps.accounting_erp.services.legacy_transformer import LegacyAccountingTransformer
            result = LegacyAccountingTransformer.run_full_migration(force_rebuild=force)
            self.stdout.write(self.style.SUCCESS(f'   ✅ {result}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ خطأ في المعالجة: {e}'))
            import traceback
            self.stdout.write(traceback.format_exc())
            return

        # ─── الخطوة 3: التحقق من الميزان ──────────────────────────────────
        self.stdout.write('\n⚖️   التحقق من توازن الميزان المراجعة...')
        try:
            from apps.accounting_erp.services.trial_balance import TrialBalanceEngine
            tb = TrialBalanceEngine.get_full_trial_balance()
            totals = tb['grand_totals']
            is_balanced = totals['is_balanced']
            status_icon = '✅' if is_balanced else '⚠️'
            self.stdout.write(
                f'   {status_icon} إجمالي مدين: {totals["debit"]:,.2f} | '
                f'إجمالي دائن: {totals["credit"]:,.2f} | '
                f'متوازن: {"نعم" if is_balanced else "لا — يوجد فارق!"}'
            )
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'   ⚠️ تعذّر التحقق من الميزان: {e}'))

        elapsed = (timezone.now() - start).total_seconds()
        self.stdout.write(self.style.MIGRATE_HEADING(f'\n═══════════════════════════════════════'))
        self.stdout.write(self.style.SUCCESS(f'🎉  اكتملت المزامنة في {elapsed:.1f} ثانية'))
        self.stdout.write(self.style.MIGRATE_HEADING('═══════════════════════════════════════\n'))
