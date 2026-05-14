from django.apps import AppConfig

class AccountingErpConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounting_erp'
    verbose_name = 'النظام المحاسبي ERP'

    def ready(self):
        # تفعيل الإشارات المحاسبية عند بدء التشغيل
        import apps.accounting_erp.signals  # noqa: F401
