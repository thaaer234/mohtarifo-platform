from apps.accounting_erp.models import Account, AccountCategory
from django.db import transaction

class ChartOfAccountsSeeder:
    """
    Generates standard structured educational enterprise Chart of Accounts.
    Tailored for Arabic region LMS platforms.
    """
    @classmethod
    @transaction.atomic
    def seed_standard_tree(cls):
        if Account.objects.exists():
            return "CoA already contains data. Skipping seed."
            
        # Level 1: Root Nodes
        assets = Account.objects.create(code='1', name='الأصول', category=AccountCategory.ASSET, is_group=True)
        liabilities = Account.objects.create(code='2', name='الالتزامات', category=AccountCategory.LIABILITY, is_group=True)
        equity = Account.objects.create(code='3', name='حقوق الملكية', category=AccountCategory.EQUITY, is_group=True)
        revenue = Account.objects.create(code='4', name='الإيرادات', category=AccountCategory.REVENUE, is_group=True)
        expenses = Account.objects.create(code='5', name='المصاريف', category=AccountCategory.EXPENSE, is_group=True)
        
        # Level 2 - Assets
        c_assets = Account.objects.create(code='11', name='الأصول المتداولة', category=AccountCategory.ASSET, parent=assets, is_group=True)
        # Leaf Assets
        Account.objects.create(code='1101', name='الصندوق الرئيسي (كاش)', category=AccountCategory.ASSET, parent=c_assets)
        Account.objects.create(code='1102', name='البنك / المحفظة الإلكترونية', category=AccountCategory.ASSET, parent=c_assets)
        Account.objects.create(code='1103', name='ذمم الطلاب المدينة (مستحقات)', category=AccountCategory.ASSET, parent=c_assets)
        
        # Level 2 - Liabilities
        c_liab = Account.objects.create(code='21', name='الالتزامات المتداولة', category=AccountCategory.LIABILITY, parent=liabilities, is_group=True)
        # Leaf Liabilities
        Account.objects.create(code='2101', name='مستحقات المدرسين (أمانات)', category=AccountCategory.LIABILITY, parent=c_liab)
        Account.objects.create(code='2102', name='إيرادات مؤجلة (اشتراكات غير مستهلكة)', category=AccountCategory.LIABILITY, parent=c_liab)
        
        # Level 2 - Revenue
        op_rev = Account.objects.create(code='41', name='الإيرادات التشغيلية', category=AccountCategory.REVENUE, parent=revenue, is_group=True)
        Account.objects.create(code='4101', name='مبيعات الكورسات المباشرة', category=AccountCategory.REVENUE, parent=op_rev)
        Account.objects.create(code='4102', name='مبيعات الباقات السنوية', category=AccountCategory.REVENUE, parent=op_rev)
        Account.objects.create(code='4103', name='رسوم تسجيل وشهادات', category=AccountCategory.REVENUE, parent=op_rev)
        
        # Level 2 - Expenses
        dir_exp = Account.objects.create(code='51', name='تكاليف النشاط المباشرة', category=AccountCategory.EXPENSE, parent=expenses, is_group=True)
        Account.objects.create(code='5101', name='حصة المدرسين من المبيعات', category=AccountCategory.EXPENSE, parent=dir_exp)
        Account.objects.create(code='5102', name='تكاليف البث واستضافة الفيديوهات (Bunny)', category=AccountCategory.EXPENSE, parent=dir_exp)
        
        admin_exp = Account.objects.create(code='52', name='مصاريف إدارية وعمومية', category=AccountCategory.EXPENSE, parent=expenses, is_group=True)
        Account.objects.create(code='5201', name='رواتب الموظفين والدعم', category=AccountCategory.EXPENSE, parent=admin_exp)
        Account.objects.create(code='5202', name='مصاريف استضافة الخوادم (VPS)', category=AccountCategory.EXPENSE, parent=admin_exp)
        Account.objects.create(code='5203', name='مصاريف تسويق وإعلانات', category=AccountCategory.EXPENSE, parent=admin_exp)

        return "Global Arabic LMS Chart of Accounts seeded successfully."
