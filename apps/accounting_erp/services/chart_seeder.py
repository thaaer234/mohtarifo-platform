"""
بذرة دليل الحسابات الموحّد — لمنصة تعليمية (محدثة لتطابق النظام القديم)
"""
from apps.accounting_erp.models import Account, AccountCategory
from django.db import transaction


class ChartOfAccountsSeeder:

    CHART = [
        # ── الأصول ────────────────────────────────────────────────────────
        dict(code='1',    name='Assets',               name_ar='الأصول',               cat=AccountCategory.ASSET,     group=True,  parent=None),
        dict(code='11',   name='Current Assets',        name_ar='الأصول المتداولة',     cat=AccountCategory.ASSET,     group=True,  parent='1'),
        dict(code='1101', name='Main Cash',             name_ar='الصندوق الرئيسي',      cat=AccountCategory.ASSET,     group=False, parent='11'),
        dict(code='1102', name='Bank / E-Wallet',       name_ar='البنك / المحفظة',      cat=AccountCategory.ASSET,     group=False, parent='11'),
        dict(code='12',   name='Other Current Assets',  name_ar='أصول متداولة أخرى',    cat=AccountCategory.ASSET,     group=True,  parent='1'),
        dict(code='1201', name='Accounts Receivable',   name_ar='الذمم المدينة',        cat=AccountCategory.ASSET,     group=True, parent='12'),
        dict(code='1202', name='Student AR',            name_ar='ذمم الطلاب المدينة',   cat=AccountCategory.ASSET,     group=False, parent='1201'),
        
        # ── الالتزامات ────────────────────────────────────────────────────
        dict(code='2',    name='Liabilities',          name_ar='الالتزامات',           cat=AccountCategory.LIABILITY, group=True,  parent=None),
        dict(code='21',   name='Current Liabilities',   name_ar='الالتزامات المتداولة', cat=AccountCategory.LIABILITY, group=True,  parent='2'),
        dict(code='2101', name='Instructors Payables',  name_ar='مستحقات المدرسين',     cat=AccountCategory.LIABILITY, group=False, parent='21'),
        dict(code='2102', name='Deferred Revenue',      name_ar='إيرادات مؤجلة',        cat=AccountCategory.LIABILITY, group=False, parent='21'),

        # ── حقوق الملكية ──────────────────────────────────────────────────
        dict(code='3',    name='Equity',               name_ar='حقوق الملكية',         cat=AccountCategory.EQUITY,    group=True,  parent=None),
        dict(code='31',   name='Capital',               name_ar='رأس المال',            cat=AccountCategory.EQUITY,    group=True,  parent='3'),
        dict(code='3101', name='Owner Equity',          name_ar='رأس مال المالك',       cat=AccountCategory.EQUITY,    group=False, parent='31'),

        # ── الإيرادات ─────────────────────────────────────────────────────
        dict(code='4',    name='Revenue',              name_ar='الإيرادات',            cat=AccountCategory.REVENUE,   group=True,  parent=None),
        dict(code='41',   name='Operating Revenue',     name_ar='الإيرادات التشغيلية',  cat=AccountCategory.REVENUE,   group=True,  parent='4'),
        dict(code='4101', name='Course Sales',          name_ar='مبيعات الكورسات',      cat=AccountCategory.REVENUE,   group=False, parent='41'),

        # ── المصاريف ──────────────────────────────────────────────────────
        dict(code='5',    name='Expenses',             name_ar='المصاريف',             cat=AccountCategory.EXPENSE,   group=True,  parent=None),
        dict(code='51',   name='Direct Costs',          name_ar='تكاليف النشاط المباشرة', cat=AccountCategory.EXPENSE,   group=True,  parent='5'),
        dict(code='5101', name='Instructor Share',      name_ar='حصة المدرسين',         cat=AccountCategory.EXPENSE,   group=False, parent='51'),
        dict(code='52',   name='General Expenses',      name_ar='مصاريف إدارية وعمومية', cat=AccountCategory.EXPENSE,   group=True,  parent='5'),
        dict(code='5201', name='Salaries',              name_ar='الرواتب والأجور',      cat=AccountCategory.EXPENSE,   group=False, parent='52'),
    ]

    @classmethod
    @transaction.atomic
    def seed_standard_tree(cls):
        created_count = 0
        code_to_obj = {a.code: a for a in Account.objects.all()}

        for entry in cls.CHART:
            if entry['code'] in code_to_obj:
                # تحديث الاسم إذا تغير
                acc = code_to_obj[entry['code']]
                if acc.name_ar != entry['name_ar']:
                    acc.name_ar = entry['name_ar']
                    acc.save()
                continue 

            parent = code_to_obj.get(entry['parent']) if entry['parent'] else None
            obj = Account.objects.create(
                code=entry['code'],
                name=entry['name'],
                name_ar=entry['name_ar'],
                category=entry['cat'],
                is_group=entry['group'],
                parent=parent,
            )
            code_to_obj[entry['code']] = obj
            created_count += 1

        return f"Chart of Accounts updated: {created_count} new accounts added."
