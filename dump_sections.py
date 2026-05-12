import os
import django
import sys

sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from dashboard.models import CatalogSection
from learning.models import Course
from django.db.models import Count

print("--- SECTIONS ---")
sections = CatalogSection.objects.all()
for s in sections:
    print(f"ID: {s.id} | LABEL: {s.label} | KIND: {s.kind} | TRACK: {s.track}")

print("\n--- CHECKING VIEW COUNTS ---")
for s in sections:
    if s.track in {'scientific', 'literary'}:
        qs = Course.objects.filter(kind=s.kind).filter(
            django.db.models.Q(academic_track=s.track) | django.db.models.Q(academic_track='general')
        )
    else:
        qs = Course.objects.filter(kind=s.kind, academic_track=s.track)
    
    print(f"Section {s.label} count: {qs.count()}")
