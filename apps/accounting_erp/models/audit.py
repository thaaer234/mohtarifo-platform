from django.db import models
from django.conf import settings
import uuid

class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    action = models.CharField(max_length=100) # e.g. 'CREATE_JOURNAL', 'VOID_INVOICE'
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    
    before_data = models.JSONField(null=True, blank=True)
    after_data = models.JSONField(null=True, blank=True)
    
    reason = models.TextField(blank=True)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    browser_info = models.TextField(blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp} | {self.user} | {self.action}"
