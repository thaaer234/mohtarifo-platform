import os
import django
import sys

sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from learning.models import Course

print("Scanning ALL courses in Database...")
all_c = Course.objects.all()
print(f"Found Total: {all_c.count()} courses.")

for c in all_c:
    try:
        # Simulate common template rendering paths
        title = c.title
        track = c.academic_track
        kind = c.kind
        instructor = c.instructor
        subject = c.subject
        
        print(f"ID: {c.id} - Processing '{title[:20]}...'")
        
        # Test cover URL logic
        if c.cover:
            try:
                url = c.cover.url
            except ValueError:
                print(f"  [WARNING] Course ID {c.id} has invalid ImageField value.")
        
        # Test property
        path = c.instructor_cover_static_path
        
        # Test relations
        ins_name = c.instructor.get_full_name() or c.instructor.username
        sub_name = c.subject.name if c.subject else "NONE"
        
    except Exception as e:
        print(f"\n!!! ERROR IN COURSE ID {c.id} !!!")
        import traceback
        traceback.print_exc()
        sys.exit(1)

print("\nALL COURSES SCANNED. NO CRITICAL ERRORS DETECTED.")
