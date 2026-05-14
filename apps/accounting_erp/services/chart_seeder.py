from ..models import Account, AccountType

def seed_enterprise_coa():
    """
    Seed the Enterprise Chart of Accounts (COA) with professional hierarchical structure.
    """
    coa_data = [
        # ASSETS (1000)
        {'code': '1', 'name': 'Assets', 'name_ar': 'الأصول', 'type': AccountType.ASSET, 'is_group': True},
        {'code': '11', 'name': 'Current Assets', 'name_ar': 'الأصول المتداولة', 'type': AccountType.ASSET, 'parent': '1', 'is_group': True},
        {'code': '1101', 'name': 'Cash on Hand', 'name_ar': 'الصندوق الرئيسي', 'type': AccountType.ASSET, 'parent': '11'},
        {'code': '1102', 'name': 'Bank Accounts', 'name_ar': 'الحسابات البنكية', 'type': AccountType.ASSET, 'parent': '11'},
        {'code': '1103', 'name': 'Student Receivables', 'name_ar': 'ذمم الطلاب', 'type': AccountType.ASSET, 'parent': '11'},
        {'code': '1104', 'name': 'Center Receivables', 'name_ar': 'ذمم مراكز البيع', 'type': AccountType.ASSET, 'parent': '11'},
        
        # LIABILITIES (2000)
        {'code': '2', 'name': 'Liabilities', 'name_ar': 'الخصوم / الالتزامات', 'type': AccountType.LIABILITY, 'is_group': True},
        {'code': '21', 'name': 'Current Liabilities', 'name_ar': 'الالتزامات المتداولة', 'type': AccountType.LIABILITY, 'parent': '2', 'is_group': True},
        {'code': '2101', 'name': 'Deferred Revenue', 'name_ar': 'الإيرادات المؤجلة', 'type': AccountType.LIABILITY, 'parent': '21'},
        {'code': '22', 'name': 'Payables', 'name_ar': 'الذمم الدائنة', 'type': AccountType.LIABILITY, 'parent': '2', 'is_group': True},
        {'code': '2201', 'name': 'Teacher Payables', 'name_ar': 'مستحقات المدرسين', 'type': AccountType.LIABILITY, 'parent': '22'},
        {'code': '2202', 'name': 'Center Payables', 'name_ar': 'مستحقات المراكز', 'type': AccountType.LIABILITY, 'parent': '22'},
        
        # EQUITY (3000)
        {'code': '3', 'name': 'Equity', 'name_ar': 'حقوق الملكية', 'type': AccountType.EQUITY, 'is_group': True},
        {'code': '3101', 'name': 'Owner Capital', 'name_ar': 'رأس المال', 'type': AccountType.EQUITY, 'parent': '3'},
        {'code': '3102', 'name': 'Retained Earnings', 'name_ar': 'الأرباح المحتجزة', 'type': AccountType.EQUITY, 'parent': '3'},
        
        # REVENUE (4000)
        {'code': '4', 'name': 'Revenue', 'name_ar': 'الإيرادات', 'type': AccountType.REVENUE, 'is_group': True},
        {'code': '4101', 'name': 'Course Sales Revenue', 'name_ar': 'إيرادات مبيعات الدورات', 'type': AccountType.REVENUE, 'parent': '4'},
        {'code': '4102', 'name': 'Subscription Revenue', 'name_ar': 'إيرادات الاشتراكات', 'type': AccountType.REVENUE, 'parent': '4'},
        {'code': '4103', 'name': 'Exam Session Revenue', 'name_ar': 'إيرادات الجلسات الامتحانية', 'type': AccountType.REVENUE, 'parent': '4'},
        
        # EXPENSES (5000)
        {'code': '5', 'name': 'Expenses', 'name_ar': 'المصاريف', 'type': AccountType.EXPENSE, 'is_group': True},
        {'code': '51', 'name': 'Direct Costs (COGS)', 'name_ar': 'التكاليف المباشرة', 'type': AccountType.EXPENSE, 'parent': '5', 'is_group': True},
        {'code': '5101', 'name': 'Teacher Commission Expense', 'name_ar': 'مصاريف عمولات المدرسين', 'type': AccountType.EXPENSE, 'parent': '51'},
        {'code': '5102', 'name': 'Center Commission Expense', 'name_ar': 'مصاريف عمولات المراكز', 'type': AccountType.EXPENSE, 'parent': '51'},
        {'code': '52', 'name': 'Operating Expenses', 'name_ar': 'المصاريف التشغيلية', 'type': AccountType.EXPENSE, 'parent': '5', 'is_group': True},
        {'code': '5201', 'name': 'Hosting & Infrastructure', 'name_ar': 'مصاريف الاستضافة والبنية التحتية', 'type': AccountType.EXPENSE, 'parent': '52'},
        {'code': '5202', 'name': 'Marketing & Ads', 'name_ar': 'مصاريف التسويق والإعلانات', 'type': AccountType.EXPENSE, 'parent': '52'},
    ]
    
    created_count = 0
    for data in coa_data:
        parent_obj = None
        if 'parent' in data:
            parent_obj = Account.objects.get(code=data['parent'])
            
        obj, created = Account.objects.get_or_create(
            code=data['code'],
            defaults={
                'name': data['name'],
                'name_ar': data['name_ar'],
                'account_type': data['type'],
                'is_group': data.get('is_group', False),
                'parent': parent_obj
            }
        )
        if created:
            created_count += 1
            
    return created_count
