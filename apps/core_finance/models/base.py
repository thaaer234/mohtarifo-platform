import uuid
from django.db import models
from django.utils import timezone

class UUIDModel(models.Model):
    """Base model utilizing UUID for keys as per requirements."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    class Meta:
        abstract = True

class FinancialTrackingModel(UUIDModel):
    """Provides standardized auditing attributes for all finance records."""
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        abstract = True
