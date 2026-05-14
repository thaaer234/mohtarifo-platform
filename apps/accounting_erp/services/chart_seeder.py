from apps.accounting_erp.models import Account, AccountType
from django.db import transaction

class ChartOfAccountsSeeder:

    CHART = [
        # 1. الأصول (Assets)
        dict(code='1',    name='Assets',           name_ar='الأصول',             type=AccountType.ASSET, group=True,  parent=None),
        dict(code='11',   name='Current Assets',   name_ar='الأصول المتداولة',   type=AccountType.ASSET, group=True,  parent='1'),
        dict(code='111',  name='Cash on Hand',     name_ar='الصندوق (كاش)',      type=AccountType.ASSET, group=False, parent='11'),
        dict(code='112',  name='Bank Accounts',    name_ar='البنوك',             type=AccountType.ASSET, group=False, parent='11'),
        dict(code='113',  name='Receivables',      name_ar='الذمم المدينة',      type=AccountType.ASSET, group=True,  parent='11'),
        dict(code='113-1', name='Sales Centers AR', name_ar='ذمم مراكز البيع',   type=AccountType.ASSET, group=False, parent='113'),
        
        # 2. الخصوم (Liabilities)
        dict(code='2',    name='Liabilities',      name_ar='الالتزامات',         type=AccountType.LIABILITY, group=True,  parent=None),
        dict(code='21',   name='Current Liabs',    name_ar='الالتزامات المتداولة', type=AccountType.LIABILITY, group=True,  parent='2'),
        dict(code='211',  name='Payables',         name_ar='الذمم الدائنة',      type=AccountType.LIABILITY, group=True,  parent='21'),
        dict(code='211-1', name='Instructors AP',   name_ar='مستحقات المدرسين',   type=AccountType.LIABILITY, group=False, parent='211'),
        dict(code='212',  name='Deferred Revenue', name_ar='إيرادات مؤجلة',      type=AccountType.LIABILITY, group=False, parent='21'),
        
        # 3. حقوق الملكية (Equity)
        dict(code='3',    name='Equity',           name_ar='حقوق الملكية',       type=AccountType.EQUITY, group=True,  parent=None),
        dict(code='31',   name='Capital',          name_ar='رأس المال',          type=AccountType.EQUITY, group=False, parent='31'),

        # 4. الإيرادات (Revenue)
        dict(code='4',    name='Revenue',          name_ar='الإيرادات',          type=AccountType.REVENUE, group=True,  parent=None),
        dict(code='41',   name='Operating Rev',    name_ar='إيرادات النشاط',     type=AccountType.REVENUE, group=False, parent='41'),
        
        # 5. المصروفات (Expenses)
        dict(code='5',    name='Expenses',         name_ar='المصاريف',           type=AccountType.EXPENSE, group=True,  parent=None),
        dict(code='51',   name='Direct Costs',     name_ar='تكاليف النشاط',      type=AccountType.EXPENSE, group=False, parent='51'),
        dict(code='52',   name='General Admin',    name_ar='مصاريف إدارية',      type=AccountType.EXPENSE, group=False, parent='52'),
    ]

    @classmethod
    @transaction.atomic
    def seed_standard_tree(cls):
        created = 0
        code_to_obj = {a.code: a for a in Account.objects.all()}

        for entry in cls.CHART:
            if entry['code'] in code_to_obj:
                acc = code_to_obj[entry['code']]
                acc.name_ar = entry['name_ar'] # Update names
                acc.save()
                continue 

            parent = code_to_obj.get(entry['parent']) if entry['parent'] else None
            obj = Account.objects.create(
                code=entry['code'],
                name=entry['name'],
                name_ar=entry['name_ar'],
                account_type=entry['type'],
                is_group=entry['group'],
                parent=parent,
            )
            code_to_obj[entry['code']] = obj
            created += 1

        return f"Tree updated: {created} new accounts."
