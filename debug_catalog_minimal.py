import os
import django
import sys

sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from learning.models import Course
from dashboard.views import _catalog_tabs
from django.db.models import Count
from django.db import models

def test_catalog_data():
    tabs = _catalog_tabs(include_hidden=True)
    print(f"Found {len(tabs)} tabs.")
    
    for tab in tabs:
        print(f"\nChecking tab: {tab['label']} ({tab['kind']}, {tab['track']})")
        if tab["track"] in {"scientific", "literary"}:
            qs = Course.objects.filter(kind=tab["kind"]).filter(
                models.Q(academic_track=tab["track"]) | models.Q(academic_track="general")
            )
        else:
            qs = Course.objects.filter(kind=tab["kind"], academic_track=tab["track"])
            
        courses = qs.select_related("subject", "instructor").annotate(
            lessons_total=Count("units__lessons", distinct=True),
            codes_total=Count("access_codes", distinct=True),
            students_total=Count("access_grants", distinct=True),
        ).order_by("subject__name", "title")
        
        # Force evaluation of entire list
        lst = list(courses)
        print(f"  Success loaded {len(lst)} courses.")
        for c in lst:
            # Test accessed attributes in template
            try:
                _ = c.cover.url if c.cover else "No Cover"
                _ = c.instructor_cover_static_path
                s_name = c.subject.name if c.subject else "NO SUBJECT"
                ins_name = c.instructor.get_full_name()
                print(f"    Course OK: {c.title} / Subj: {s_name}")
            except Exception as e:
                print(f"    !!! EXCEPTION IN COURSE '{c.title}' (ID: {c.id}): {str(e)}")
                raise

try:
    test_catalog_data()
    print("\nDATA VALIDATION COMPLETED SUCCESSFULLY")
except Exception as e:
    import traceback
    traceback.print_exc()
