"""
بذرة دليل الحسابات الموحّد — لمنصة تعليمية
تحتوي على جميع الحسابات اللازمة للعمليات التلقائية والقيود اليدوية.
"""
from apps.accounting_erp.models import Account, AccountCategory
from django.db import transaction


class ChartOfAccountsSeeder:

    CHART = [
        # ── الأصول ────────────────────────────────────────────────────────
        dict(code='1',    name='الأصول',                         cat='asset',     group=True,  parent=None),
        dict(code='11',   name='الأصول المتداولة',               cat='asset',     group=True,  parent='1'),
        dict(code='1101', name='الصندوق الرئيسي (كاش)',          cat='asset',     group=False, parent='11'),
        dict(code='1102', name='البنك / المحفظة الإلكترونية',    cat='asset',     group=False, parent='11'),
        dict(code='1103', name='ذمم الطلاب المدينة (مستحقات)',   cat='asset',     group=False, parent='11'),
        dict(code='12',   name='أصول متداولة أخرى',              cat='asset',     group=True,  parent='1'),
        dict(code='1201', name='ذمم مراكز بيع مدينة',            cat='asset',     group=False, parent='12'),
        dict(code='1202', name='أكواد وصول معلّقة (جرد)',        cat='asset',     group=False, parent='12'),

        # ── الالتزامات ────────────────────────────────────────────────────
        dict(code='2',    name='الالتزامات',                     cat='liability', group=True,  parent=None),
        dict(code='21',   name='الالتزامات المتداولة',           cat='liability', group=True,  parent='2'),
        dict(code='2101', name='مستحقات المدرسين (أمانات)',      cat='liability', group=False, parent='21'),
        dict(code='2102', name='إيرادات مؤجلة (أكواد غير مفعّلة)', cat='liability', group=False, parent='21'),
        dict(code='2103', name='مستحقات مراكز البيع',           cat='liability', group=False, parent='21'),

        # ── حقوق الملكية ──────────────────────────────────────────────────
        dict(code='3',    name='حقوق الملكية',                   cat='equity',    group=True,  parent=None),
        dict(code='31',   name='رأس المال',                      cat='equity',    group=True,  parent='3'),
        dict(code='3101', name='رأس مال المالك',                 cat='equity',    group=False, parent='31'),
        dict(code='3102', name='الأرباح المحتجزة',               cat='equity',    group=False, parent='31'),

        # ── الإيرادات ─────────────────────────────────────────────────────
        dict(code='4',    name='الإيرادات',                      cat='revenue',   group=True,  parent=None),
        dict(code='41',   name='الإيرادات التشغيلية',            cat='revenue',   group=True,  parent='4'),
        dict(code='4101', name='مبيعات الكورسات المباشرة',       cat='revenue',   group=False, parent='41'),
        dict(code='4102', name='مبيعات الباقات السنوية',         cat='revenue',   group=False, parent='41'),
        dict(code='4103', name='رسوم تسجيل وشهادات',            cat='revenue',   group=False, parent='41'),
        dict(code='4104', name='حسومات مبيعات مسموح بها',       cat='revenue',   group=False, parent='41'),
        dict(code='4105', name='إيرادات اشتراكات شهرية',        cat='revenue',   group=False, parent='41'),

        # ── المصاريف ──────────────────────────────────────────────────────
        dict(code='5',    name='المصاريف',                       cat='expense',   group=True,  parent=None),
        dict(code='51',   name='تكاليف النشاط المباشرة (COGS)', cat='expense',   group=True,  parent='5'),
        dict(code='5101', name='حصة المدرسين من المبيعات',      cat='expense',   group=False, parent='51'),
        dict(code='5102', name='تكاليف بث الفيديو (Bunny)',      cat='expense',   group=False, parent='51'),
        dict(code='5103', name='عمولات مراكز البيع',            cat='expense',   group=False, parent='51'),
        dict(code='52',   name='مصاريف إدارية وعمومية (SGA)',  cat='expense',   group=True,  parent='5'),
        dict(code='5201', name='رواتب الموظفين والدعم',         cat='expense',   group=False, parent='52'),
        dict(code='5202', name='استضافة الخوادم (VPS/Cloud)',   cat='expense',   group=False, parent='52'),
        dict(code='5203', name='مصاريف تسويق وإعلانات',        cat='expense',   group=False, parent='52'),
        dict(code='5204', name='مصاريف نثرية متنوعة',          cat='expense',   group=False, parent='52'),
    ]

    @classmethod
    @transaction.atomic
    def seed_standard_tree(cls):
        """يضيف الحسابات الناقصة فقط — لا يحذف ولا يعدّل الموجود."""
        created_count = 0
        code_to_obj = {a.code: a for a in Account.objects.all()}

        for entry in cls.CHART:
            if entry['code'] in code_to_obj:
                continue  # موجود مسبقاً

            parent = code_to_obj.get(entry['parent']) if entry['parent'] else None
            obj = Account.objects.create(
                code=entry['code'],
                name=entry['name'],
                category=entry['cat'],
                is_group=entry['group'],
                parent=parent,
            )
            code_to_obj[entry['code']] = obj
            created_count += 1

        msg = f"Chart of Accounts: {created_count} new accounts added."
        return msg
