import os
from django.db import connection
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils import timezone

class SystemDiagnostics:
    @staticmethod
    def run_all_checks():
        results = {
            "database": SystemDiagnostics.check_database(),
            "cache": SystemDiagnostics.check_cache(),
            "storage": SystemDiagnostics.check_storage(),
            "environment": SystemDiagnostics.check_environment(),
            "traffic": SystemDiagnostics.check_traffic(),
            "timestamp": timezone.now(),
        }
        return results

    @staticmethod
    def check_traffic():
        try:
            from analytics.models import LandingVisit
            from datetime import timedelta
            from django.conf import settings
            
            now = timezone.now()
            if not getattr(settings, 'USE_TZ', False) and timezone.is_aware(now):
                now = timezone.make_naive(now)
            
            time_limit = now - timedelta(hours=24)
            recent_exists = LandingVisit.objects.filter(visited_at__gte=time_limit).exists()
            if recent_exists:
                return {"status": "healthy", "message": "نظام تتبع الزوار نشط (سجل زيارات خلال الـ 24 ساعة الماضية)."}
            return {"status": "warning", "message": "لا توجد زيارات مسجلة خلال الـ 24 ساعة الماضية."}
        except Exception as e:
            return {"status": "error", "message": f"خطأ في نظام التتبع: {str(e)}"}


    @staticmethod
    def check_database():
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return {"status": "healthy", "message": "اتصال قاعدة البيانات سليم."}
        except Exception as e:
            return {"status": "error", "message": f"خطأ في الاتصال بقاعدة البيانات: {str(e)}"}

    @staticmethod
    def check_cache():
        try:
            cache.set("diag_test", "ok", 10)
            val = cache.get("diag_test")
            if val == "ok":
                return {"status": "healthy", "message": "نظام الكاش (Cache) يعمل بشكل صحيح."}
            return {"status": "warning", "message": "نظام الكاش لا يسترجع البيانات بشكل صحيح."}
        except Exception as e:
            return {"status": "error", "message": f"خطأ في نظام الكاش: {str(e)}"}

    @staticmethod
    def check_storage():
        try:
            test_file_path = "diag_test.txt"
            content = "test"
            path = default_storage.save(test_file_path, ContentFile(content))
            if default_storage.exists(path):
                default_storage.delete(path)
                return {"status": "healthy", "message": "صلاحيات التخزين (Media Storage) سليمة."}
            return {"status": "error", "message": "فشل في التحقق من وجود الملف بعد حفظه."}
        except Exception as e:
            return {"status": "error", "message": f"خطأ في صلاحيات التخزين: {str(e)}"}

    @staticmethod
    def check_environment():
        critical_vars = ["DATABASE_URL", "SECRET_KEY"]
        missing = [v for v in critical_vars if not os.environ.get(v) and not hasattr(settings, v)]
        if not settings.DEBUG and not os.environ.get("DATABASE_URL"):
            missing.append("DATABASE_URL (Production)")
        
        if not missing:
            return {"status": "healthy", "message": "إعدادات البيئة (Environment) مكتملة."}
        return {"status": "warning", "message": f"متغيرات بيئة مفقودة: {', '.join(missing)}"}
